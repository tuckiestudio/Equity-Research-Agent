"""Thesis generation and update service.

This service handles:
- Initial investment thesis generation from financial data + news
- Thesis updates based on new information
- Thesis versioning with audit trail
- Change detection and logging
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.thesis import Thesis
from app.models.thesis_change import ThesisChange
from app.services.data.registry import get_fundamentals, get_news, get_profiles
from app.services.llm.prompts.templates import (
    get_thesis_generation_template,
    get_thesis_update_template,
)
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType

logger = get_logger(__name__)


class ThesisContent(BaseModel):
    """Parsed thesis from LLM output."""

    title: str = Field(..., description="Thesis title")
    summary: str = Field(..., description="2-3 sentence executive summary")
    full_text: str = Field(..., description="Full thesis document (markdown)")
    stance: str = Field(..., description="bullish/bearish/neutral")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    target_price: Optional[float] = Field(None, description="Price target")
    key_risks: list[str] = Field(default_factory=list, description="Key investment risks")
    key_catalysts: list[str] = Field(default_factory=list, description="Key catalysts")

    @field_validator("stance")
    @classmethod
    def validate_stance(cls, v: str) -> str:
        """Validate stance is one of the allowed values."""
        v_lower = v.lower()
        if v_lower not in ("bullish", "bearish", "neutral"):
            logger.warning(f"Invalid stance '{v}', defaulting to 'neutral'")
            return "neutral"
        return v_lower


class ThesisService:
    """Service for generating and managing investment theses."""

    def __init__(self, llm_router: LLMRouter) -> None:
        """Initialize the thesis service.

        Args:
            llm_router: LLM router for model routing
        """
        self._llm = llm_router

    async def generate_thesis(
        self,
        ticker: str,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
        user_settings=None,
    ) -> Thesis:
        """Generate an initial investment thesis.

        The process:
        1. Fetch company profile, financials, recent news
        2. Build a financial summary string
        3. Render the thesis_generation template
        4. Call LLMRouter.complete() with TaskType.THESIS_GENERATION
        5. Parse response into ThesisContent
        6. Deactivate any existing active thesis for this stock+user
        7. Save new Thesis to DB with version=1
        8. Create ThesisChange with change_type="created"
        9. Return the thesis

        Args:
            ticker: Stock ticker symbol
            stock_id: Stock UUID
            user_id: User UUID
            db: Database session

        Returns:
            Created Thesis record

        Raises:
            ProviderError: If data providers or LLM fail
        """
        logger.info(f"Generating thesis for {ticker}")

        # Step 1: Fetch data from providers
        profiles = get_profiles(user_settings)
        profile = await profiles.get_company_profile(ticker)

        fundamentals = get_fundamentals(user_settings)
        income = await fundamentals.get_income_statement(ticker, limit=1)
        ratios = await fundamentals.get_financial_ratios(ticker)

        news = get_news(user_settings)
        articles = await news.get_news(ticker, limit=10)

        # Step 2: Build financial summary
        key_metrics = self._build_key_metrics(profile, income, ratios)

        # Step 3: Build news summary
        recent_news = self._build_news_summary(articles)

        # Step 4: Get business description and industry context
        company_name = profile.get("companyName", ticker)
        business_description = profile.get("description", "No description available")
        industry_context = profile.get("industry", "Unknown industry")

        # Step 5: Render template
        template = get_thesis_generation_template()
        messages = template.render(
            ticker=ticker,
            company_name=company_name,
            business_description=business_description,
            key_metrics=key_metrics,
            recent_news=recent_news,
            industry_context=industry_context,
        )

        # Step 6: Call LLM
        response = await self._llm.complete(
            task_type=TaskType.THESIS_GENERATION,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )

        # Step 7: Parse response
        content = self._parse_thesis_content(response.content)

        # Step 8: Calculate upside percentage if we have target and current price
        current_price = profile.get("price")
        upside_pct = None
        if content.target_price and current_price and current_price > 0:
            upside_pct = ((content.target_price - current_price) / current_price) * 100

        # Step 9: Deactivate existing active thesis
        await self._deactivate_active_thesis(stock_id, user_id, db)

        # Step 10: Create new thesis
        thesis = Thesis(
            stock_id=stock_id,
            user_id=user_id,
            title=content.title,
            summary=content.summary,
            full_text=content.full_text,
            stance=content.stance,
            confidence=content.confidence,
            target_price=content.target_price,
            current_price_at_generation=current_price,
            upside_pct=upside_pct,
            version=1,
            is_active=True,
            generated_by="ai",
            llm_model_used=f"{response.provider}/{response.model}",
        )

        db.add(thesis)
        await db.commit()
        await db.refresh(thesis)

        # Step 11: Create change record
        change = ThesisChange(
            thesis_id=thesis.id,
            user_id=user_id,
            change_type="created",
            previous_stance=None,
            new_stance=thesis.stance,
            previous_target_price=None,
            new_target_price=thesis.target_price,
            previous_confidence=None,
            new_confidence=thesis.confidence,
            trigger=None,
            change_summary=f"Initial thesis generated: {thesis.title}",
            version_from=0,
            version_to=1,
        )
        db.add(change)
        await db.commit()

        logger.info(f"Generated thesis {thesis.id} for {ticker}")
        return thesis

    async def update_thesis(
        self,
        thesis_id: uuid.UUID,
        new_information: str,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Thesis:
        """Update an existing thesis with new information.

        The process:
        1. Fetch existing thesis
        2. Render thesis_update template with existing_thesis + new_information
        3. Call LLMRouter.complete() with TaskType.THESIS_UPDATE
        4. Parse updated thesis
        5. Detect changes (stance, target, confidence)
        6. Update the thesis record (increment version)
        7. Create ThesisChange with detected changes
        8. Return updated thesis

        Args:
            thesis_id: Thesis UUID to update
            new_information: New information to incorporate
            user_id: User UUID
            db: Database session

        Returns:
            Updated Thesis record

        Raises:
            NotFoundError: If thesis not found
            ProviderError: If LLM fails
        """
        logger.info(f"Updating thesis {thesis_id}")

        # Step 1: Fetch existing thesis
        result = await db.execute(
            select(Thesis).where(
                Thesis.id == thesis_id,
                Thesis.user_id == user_id,
            )
        )
        thesis = result.scalar_one_or_none()
        if not thesis:
            from app.core.errors import NotFoundError
            raise NotFoundError("Thesis", str(thesis_id))

        # Step 2: Calculate time elapsed
        time_elapsed = self._format_time_elapsed(thesis.created_at)

        # Step 3: Fetch ticker for the stock
        stock_result = await db.execute(select(Thesis).where(Thesis.id == thesis_id))
        # We need the ticker - fetch from stock relationship or cache
        # For now, use the thesis title as a fallback
        ticker = thesis.title.split(":")[0].strip() if ":" in thesis.title else "Unknown"

        # Step 4: Render template
        template = get_thesis_update_template()
        messages = template.render(
            ticker=ticker,
            existing_thesis=thesis.full_text,
            new_information=new_information,
            time_elapsed=time_elapsed,
        )

        # Step 5: Call LLM
        response = await self._llm.complete(
            task_type=TaskType.THESIS_UPDATE,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )

        # Step 6: Parse response
        content = self._parse_thesis_content(response.content)

        # Step 7: Detect changes
        changes = self._detect_changes(thesis, content)

        # Step 8: Calculate upside percentage if we have target and current price
        if content.target_price and thesis.current_price_at_generation:
            content.upside_pct = (
                (content.target_price - thesis.current_price_at_generation)
                / thesis.current_price_at_generation
            ) * 100

        # Step 9: Update thesis
        old_version = thesis.version
        thesis.title = content.title
        thesis.summary = content.summary
        thesis.full_text = content.full_text
        thesis.stance = content.stance
        thesis.confidence = content.confidence
        thesis.target_price = content.target_price
        thesis.version += 1
        thesis.generated_by = "ai_updated"
        thesis.llm_model_used = f"{response.provider}/{response.model}"

        await db.commit()
        await db.refresh(thesis)

        # Step 10: Create change record
        change_type = self._determine_change_type(changes)
        change = ThesisChange(
            thesis_id=thesis.id,
            user_id=user_id,
            change_type=change_type,
            previous_stance=changes.get("previous_stance"),
            new_stance=changes.get("new_stance"),
            previous_target_price=changes.get("previous_target_price"),
            new_target_price=changes.get("new_target_price"),
            previous_confidence=changes.get("previous_confidence"),
            new_confidence=changes.get("new_confidence"),
            trigger=new_information[:500] if new_information else None,  # Truncate if too long
            change_summary=changes.get("summary", "Thesis updated with new information"),
            version_from=old_version,
            version_to=thesis.version,
        )
        db.add(change)
        await db.commit()

        logger.info(f"Updated thesis {thesis.id} to version {thesis.version}")
        return thesis

    async def get_active_thesis(
        self,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Optional[Thesis]:
        """Get the active thesis for a stock+user.

        Args:
            stock_id: Stock UUID
            user_id: User UUID
            db: Database session

        Returns:
            Active Thesis or None if not found
        """
        result = await db.execute(
            select(Thesis).where(
                Thesis.stock_id == stock_id,
                Thesis.user_id == user_id,
                Thesis.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_thesis_history(
        self,
        thesis_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[ThesisChange]:
        """Get the change history for a thesis.

        Args:
            thesis_id: Thesis UUID
            db: Database session

        Returns:
            List of ThesisChange records ordered by created_at
        """
        result = await db.execute(
            select(ThesisChange)
            .where(ThesisChange.thesis_id == thesis_id)
            .order_by(ThesisChange.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_thesis_timeline(
        self,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Build a timeline of thesis evolution.

        Returns list of {date, version, stance, confidence, target_price, change_summary}
        Useful for frontend timeline visualization.

        Args:
            stock_id: Stock UUID
            user_id: User UUID
            db: Database session

        Returns:
            List of timeline dictionaries
        """
        # Get all theses for this stock+user, ordered by version
        result = await db.execute(
            select(Thesis)
            .where(
                Thesis.stock_id == stock_id,
                Thesis.user_id == user_id,
            )
            .order_by(Thesis.version.asc())
        )
        theses = list(result.scalars().all())

        timeline = []
        for thesis in theses:
            # Get the change that created this version
            change_result = await db.execute(
                select(ThesisChange).where(
                    ThesisChange.thesis_id == thesis.id,
                    ThesisChange.version_to == thesis.version,
                )
            )
            change = change_result.scalar_one_or_none()

            timeline.append({
                "date": thesis.created_at,
                "version": thesis.version,
                "stance": thesis.stance,
                "confidence": thesis.confidence,
                "target_price": thesis.target_price,
                "change_summary": change.change_summary if change else thesis.title,
            })

        return timeline

    def _parse_thesis_content(self, raw_text: str) -> ThesisContent:
        """Parse LLM output into structured thesis.

        Try JSON first, fall back to text parsing.
        Handle gracefully — never crash.

        Args:
            raw_text: Raw LLM response text

        Returns:
            Parsed ThesisContent with safe defaults
        """
        # Try JSON parsing first
        try:
            # Look for JSON block in markdown
            if "```json" in raw_text:
                json_start = raw_text.find("```json") + 7
                json_end = raw_text.find("```", json_start)
                json_str = raw_text[json_start:json_end].strip()
                data = json.loads(json_str)
                return ThesisContent(**data)
            elif raw_text.strip().startswith("{"):
                data = json.loads(raw_text)
                return ThesisContent(**data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.debug(f"JSON parsing failed: {e}, falling back to text parsing")

        # Fall back to text parsing
        return self._parse_thesis_from_text(raw_text)

    def _parse_thesis_from_text(self, text: str) -> ThesisContent:
        """Parse thesis from unstructured text.

        Extract key fields using heuristics.

        Args:
            text: Raw thesis text

        Returns:
            ThesisContent with extracted or default values
        """
        # Default values
        title = "Investment Thesis"
        summary = text[:300] if len(text) > 300 else text
        stance = "neutral"
        confidence = 0.5
        target_price = None

        # Extract title (first # heading or first line)
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break
            elif line and not title.startswith("Investment Thesis"):
                title = line[:100]
                break

        # Extract stance from text
        text_lower = text.lower()
        bullish_keywords = ["bullish", "buy", "overweight", "outperform", "positive outlook"]
        bearish_keywords = ["bearish", "sell", "underweight", "underperform", "negative outlook"]

        bullish_score = sum(1 for kw in bullish_keywords if kw in text_lower)
        bearish_score = sum(1 for kw in bearish_keywords if kw in text_lower)

        if bullish_score > bearish_score:
            stance = "bullish"
            confidence = 0.7
        elif bearish_score > bullish_score:
            stance = "bearish"
            confidence = 0.7

        # Try to extract price target (look for $ followed by number)
        import re
        price_pattern = r'\$(\d+\.?\d*)'
        prices = re.findall(price_pattern, text)
        if prices:
            try:
                target_price = float(prices[0])
            except ValueError:
                pass

        return ThesisContent(
            title=title,
            summary=summary,
            full_text=text,
            stance=stance,
            confidence=confidence,
            target_price=target_price,
            key_risks=[],
            key_catalysts=[],
        )

    def _detect_changes(
        self, old: Thesis, new_content: ThesisContent
    ) -> dict:
        """Compare old thesis with new content, return change details.

        Args:
            old: Existing Thesis record
            new_content: New parsed thesis content

        Returns:
            Dictionary with detected changes
        """
        changes = {
            "previous_stance": None,
            "new_stance": None,
            "previous_target_price": None,
            "new_target_price": None,
            "previous_confidence": None,
            "new_confidence": None,
            "summary": "Thesis updated",
        }

        # Check stance change first (highest priority)
        if old.stance != new_content.stance:
            changes["previous_stance"] = old.stance
            changes["new_stance"] = new_content.stance
            changes["summary"] = f"Stance changed from {old.stance} to {new_content.stance}"
            return changes  # Return early for stance change

        # Check target price change
        if old.target_price != new_content.target_price:
            changes["previous_target_price"] = old.target_price
            changes["new_target_price"] = new_content.target_price
            if new_content.target_price:
                if old.target_price:
                    pct_change = ((new_content.target_price - old.target_price) / old.target_price) * 100
                    changes["summary"] = f"Target price changed from ${old.target_price:.2f} to ${new_content.target_price:.2f} ({pct_change:+.1f}%)"
                else:
                    changes["summary"] = f"Target price set to ${new_content.target_price:.2f}"
            else:
                changes["summary"] = "Target price removed"
            return changes  # Return early for target price change

        # Check confidence change
        if abs(old.confidence - new_content.confidence) > 0.1:
            changes["previous_confidence"] = old.confidence
            changes["new_confidence"] = new_content.confidence
            changes["summary"] = f"Confidence changed from {old.confidence:.2f} to {new_content.confidence:.2f}"

        return changes

    def _determine_change_type(self, changes: dict) -> str:
        """Determine the change type based on what changed.

        Args:
            changes: Change details from _detect_changes

        Returns:
            Change type string
        """
        if changes.get("previous_stance") and changes["previous_stance"] != changes["new_stance"]:
            return "stance_changed"
        if changes.get("previous_target_price") != changes.get("new_target_price"):
            return "target_updated"
        if changes.get("previous_confidence") and changes["previous_confidence"] != changes["new_confidence"]:
            return "confidence_changed"
        return "news_driven_update"

    async def _deactivate_active_thesis(
        self, stock_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
    ) -> None:
        """Deactivate any existing active thesis for this stock+user.

        Args:
            stock_id: Stock UUID
            user_id: User UUID
            db: Database session
        """
        result = await db.execute(
            select(Thesis).where(
                Thesis.stock_id == stock_id,
                Thesis.user_id == user_id,
                Thesis.is_active == True,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_active = False
            await db.commit()

    def _build_key_metrics(
        self, profile: dict, income: list[dict], ratios: list[dict]
    ) -> str:
        """Build a formatted string of key financial metrics.

        Args:
            profile: Company profile data
            income: Income statement data
            ratios: Financial ratios data

        Returns:
            Formatted metrics string
        """
        lines = []

        # Basic info
        market_cap = profile.get("mktCap")
        if market_cap:
            lines.append(f"Market Cap: ${market_cap:,.0f}")

        price = profile.get("price")
        if price:
            lines.append(f"Current Price: ${price:.2f}")

        # Latest income statement
        if income:
            latest = income[0]
            revenue = latest.get("revenue") or latest.get("totalRevenue")
            if revenue:
                lines.append(f"Revenue: ${revenue:,.0f}")
            ebitda = latest.get("ebitda")
            if ebitda:
                lines.append(f"EBITDA: ${ebitda:,.0f}")
            net_income = latest.get("netIncome")
            if net_income:
                lines.append(f"Net Income: ${net_income:,.0f}")

        # Key ratios
        if ratios:
            latest = ratios[0]
            pe = latest.get("peRatio")
            if pe:
                lines.append(f"P/E Ratio: {pe:.2f}")
            roe = latest.get("returnOnEquity")
            if roe:
                lines.append(f"ROE: {roe * 100:.1f}%")
            debt_to_equity = latest.get("debtToEquity")
            if debt_to_equity:
                lines.append(f"Debt/Equity: {debt_to_equity:.2f}")

        return "\n".join(lines) if lines else "Financial metrics not available"

    def _build_news_summary(self, articles: list[dict]) -> str:
        """Build a summary of recent news articles.

        Args:
            articles: List of news article dicts

        Returns:
            Formatted news summary
        """
        if not articles:
            return "No recent news available"

        lines = []
        for article in articles[:5]:  # Top 5 articles
            title = article.get("headline", article.get("title", ""))
            date = article.get("date", "")
            if title:
                if date:
                    lines.append(f"- {title} ({date})")
                else:
                    lines.append(f"- {title}")

        return "\n".join(lines)

    def _format_time_elapsed(self, since: datetime) -> str:
        """Format time elapsed since a given datetime.

        Args:
            since: Datetime to calculate from

        Returns:
            Human-readable time elapsed string
        """
        delta = datetime.now(since.tzinfo) - since
        days = delta.days
        hours = delta.seconds // 3600

        if days > 30:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''}"
        elif days > 0:
            return f"{days} day{'s' if days > 1 else ''}"
        elif hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            return "less than an hour"
