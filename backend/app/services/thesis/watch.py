"""Watch item generation and management service."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.thesis import Thesis
from app.models.watch_item import WatchItem
from app.services.data.registry import get_profiles
from app.services.llm.prompts.templates import get_watch_items_template
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType

logger = get_logger(__name__)


class WatchItemSuggestion(BaseModel):
    """LLM watch item suggestion."""

    title: str = Field(..., description="Short item title")
    description: Optional[str] = Field(None, description="Details about the watch item")
    category: Optional[str] = Field(None, description="Category such as earnings or product")
    expected_date: Optional[str] = Field(None, description="Expected date or timing window")
    is_recurring: Optional[bool] = Field(False, description="Recurring indicator")
    potential_impact: Optional[str] = Field(None, description="Impact summary")
    impact_direction: Optional[str] = Field(None, description="positive/negative/mixed")
    affected_assumptions: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class WatchService:
    """Service for generating and managing watch items."""

    def __init__(self, llm_router: LLMRouter) -> None:
        """Initialize watch service.

        Args:
            llm_router: LLM router for model routing
        """
        self._llm = llm_router

    async def generate_watch_items(
        self,
        ticker: str,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
        user_settings=None,
    ) -> list[WatchItem]:
        """Generate watch items using LLM and persist them.

        Args:
            ticker: Stock ticker symbol
            stock_id: Stock UUID
            user_id: User UUID
            db: Database session

        Returns:
            List of created WatchItem records
        """
        profiles = get_profiles(user_settings)
        profile = await profiles.get_company_profile(ticker)
        company_name = profile.get("companyName", ticker)

        result = await db.execute(
            select(Thesis).where(
                Thesis.stock_id == stock_id,
                Thesis.user_id == user_id,
                Thesis.is_active == True,
            )
        )
        thesis = result.scalar_one_or_none()
        investment_thesis = thesis.full_text if thesis else "No active thesis available."

        upcoming_events = "No known upcoming events."

        template = get_watch_items_template()
        messages = template.render(
            ticker=ticker,
            company_name=company_name,
            investment_thesis=investment_thesis,
            upcoming_events=upcoming_events,
        )

        try:
            response = await self._llm.complete(
                task_type=TaskType.WATCH_ITEMS,
                messages=messages,
                json_mode=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Watch item LLM generation failed: %s", exc)
            return []

        suggestions = self._parse_suggestions(response.content)
        if not suggestions:
            return []

        items: list[WatchItem] = []
        for suggestion in suggestions:
            item = WatchItem(
                stock_id=stock_id,
                user_id=user_id,
                title=suggestion.title,
                description=suggestion.description,
                category=suggestion.category,
                expected_date=self._parse_expected_date(suggestion.expected_date),
                is_recurring=bool(suggestion.is_recurring),
                potential_impact=suggestion.potential_impact,
                impact_direction=suggestion.impact_direction,
                status="active",
                triggered_at=None,
                trigger_outcome=None,
                generated_by="ai",
                confidence=suggestion.confidence,
            )
            item.set_affected_assumptions(suggestion.affected_assumptions)
            db.add(item)
            items.append(item)

        await db.commit()
        for item in items:
            await db.refresh(item)

        return items

    async def get_active_items(
        self,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[WatchItem]:
        """Get active watch items for a stock and user.

        Args:
            stock_id: Stock UUID
            user_id: User UUID
            db: Database session

        Returns:
            List of active WatchItem records
        """
        result = await db.execute(
            select(WatchItem)
            .where(
                WatchItem.stock_id == stock_id,
                WatchItem.user_id == user_id,
                WatchItem.status == "active",
            )
            .order_by(WatchItem.expected_date.asc().nulls_last())
        )
        return list(result.scalars().all())

    async def trigger_item(
        self,
        watch_id: uuid.UUID,
        user_id: uuid.UUID,
        outcome: Optional[str],
        db: AsyncSession,
    ) -> WatchItem:
        """Mark a watch item as triggered.

        Args:
            watch_id: Watch item UUID
            user_id: User UUID
            outcome: Trigger outcome summary
            db: Database session

        Returns:
            Updated WatchItem
        """
        result = await db.execute(
            select(WatchItem).where(
                WatchItem.id == watch_id,
                WatchItem.user_id == user_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            from app.core.errors import NotFoundError

            raise NotFoundError("WatchItem", str(watch_id))

        item.status = "triggered"
        item.triggered_at = datetime.utcnow()
        item.trigger_outcome = outcome

        await db.commit()
        await db.refresh(item)
        return item

    async def dismiss_item(
        self,
        watch_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> WatchItem:
        """Dismiss a watch item.

        Args:
            watch_id: Watch item UUID
            user_id: User UUID
            db: Database session

        Returns:
            Updated WatchItem
        """
        result = await db.execute(
            select(WatchItem).where(
                WatchItem.id == watch_id,
                WatchItem.user_id == user_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            from app.core.errors import NotFoundError

            raise NotFoundError("WatchItem", str(watch_id))

        item.status = "dismissed"
        await db.commit()
        await db.refresh(item)
        return item

    def _parse_suggestions(self, content: str) -> list[WatchItemSuggestion]:
        """Parse JSON content into watch item suggestions.

        Args:
            content: Raw LLM response content

        Returns:
            List of WatchItemSuggestion entries
        """
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return []

        if isinstance(payload, dict):
            items = payload.get("items") or payload.get("watch_items") or payload.get("watchItems")
        else:
            items = payload

        if not isinstance(items, list):
            return []

        if not items:
            return []

        suggestions: list[WatchItemSuggestion] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            try:
                suggestions.append(WatchItemSuggestion(**raw))
            except Exception:  # noqa: BLE001
                continue
        return suggestions

    def _parse_expected_date(self, value: Optional[str]) -> Optional[date]:
        """Parse expected date string into date if possible.

        Args:
            value: Expected date string

        Returns:
            Parsed date or None
        """
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
