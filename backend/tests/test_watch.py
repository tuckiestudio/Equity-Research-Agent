"""Tests for watch items service and model."""
from __future__ import annotations

import json
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.watch_item import WatchItem
from app.services.llm.router import LLMRouter
from app.services.llm.types import LLMResponse
from app.services.thesis.watch import WatchItemSuggestion, WatchService


class TestWatchItemModel:
    """Tests for WatchItem database model."""

    def test_model_fields(self) -> None:
        """Verify all required columns exist on WatchItem."""
        expected_attrs = [
            "id",
            "stock_id",
            "user_id",
            "title",
            "description",
            "category",
            "expected_date",
            "is_recurring",
            "potential_impact",
            "impact_direction",
            "affected_assumptions",
            "status",
            "triggered_at",
            "trigger_outcome",
            "generated_by",
            "confidence",
            "created_at",
            "updated_at",
        ]

        for attr in expected_attrs:
            assert hasattr(WatchItem, attr), f"WatchItem missing attribute: {attr}"

    def test_tablename(self) -> None:
        """Table name is 'watch_items'."""
        assert WatchItem.__tablename__ == "watch_items"

    def test_affected_assumptions_round_trip(self) -> None:
        """Affected assumptions can round-trip through JSON field."""
        item = WatchItem(
            stock_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test",
            description=None,
            category=None,
            expected_date=None,
            is_recurring=False,
            potential_impact=None,
            impact_direction=None,
            status="active",
            triggered_at=None,
            trigger_outcome=None,
            generated_by="manual",
            confidence=None,
        )
        assumptions = ["wacc", "operating_margin"]
        item.set_affected_assumptions(assumptions)
        assert item.get_affected_assumptions() == assumptions


class FakeDBSession:
    """Fake database session for watch item tests."""

    def __init__(self) -> None:
        self.added = []
        self.committed = False
        self.refreshed = []
        self._scalar = None

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj) -> None:
        self.refreshed.append(obj)
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()

    async def execute(self, stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = self._scalar
        return result


class FakeProfiles:
    """Fake profiles provider for testing."""

    async def get_company_profile(self, ticker: str):
        return {"companyName": "Test Co"}


class TestWatchService:
    """Tests for WatchService."""

    @pytest.mark.asyncio
    async def test_generate_watch_items_calls_llm(self, monkeypatch) -> None:
        """LLM is called and items are persisted."""
        mock_response = LLMResponse(
            content=json.dumps([
                {
                    "title": "Earnings print",
                    "description": "Watch for revenue beat",
                    "category": "earnings",
                    "expected_date": "2026-03-01",
                    "is_recurring": False,
                    "potential_impact": "Could re-rate stock",
                    "impact_direction": "positive",
                    "affected_assumptions": ["revenue_growth_rates"],
                    "confidence": 0.7,
                }
            ]),
            model="gpt-4o",
            provider="openai",
            input_tokens=10,
            output_tokens=20,
            latency_ms=10.0,
        )

        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        db = FakeDBSession()

        monkeypatch.setattr(
            "app.services.thesis.watch.get_profiles",
            lambda user_settings=None: FakeProfiles(),
        )

        service = WatchService(mock_router)
        items = await service.generate_watch_items(
            ticker="AAPL",
            stock_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            db=db,
        )

        assert len(items) == 1
        assert db.committed is True
        assert items[0].title == "Earnings print"
        assert items[0].generated_by == "ai"
        assert items[0].expected_date == date(2026, 3, 1)

    @pytest.mark.asyncio
    async def test_generate_watch_items_handles_llm_error(self, monkeypatch) -> None:
        """LLM errors return empty list."""
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(side_effect=RuntimeError("LLM down"))

        db = FakeDBSession()

        monkeypatch.setattr(
            "app.services.thesis.watch.get_profiles",
            lambda user_settings=None: FakeProfiles(),
        )

        service = WatchService(mock_router)
        items = await service.generate_watch_items(
            ticker="AAPL",
            stock_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            db=db,
        )

        assert items == []

    @pytest.mark.asyncio
    async def test_trigger_and_dismiss(self, monkeypatch) -> None:
        """Trigger and dismiss update status."""
        watch_id = uuid.uuid4()
        item = WatchItem(
            id=watch_id,
            stock_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test",
            description=None,
            category=None,
            expected_date=None,
            is_recurring=False,
            potential_impact=None,
            impact_direction=None,
            status="active",
            triggered_at=None,
            trigger_outcome=None,
            generated_by="manual",
            confidence=None,
        )

        db = FakeDBSession()
        db._scalar = item

        service = WatchService(MagicMock(spec=LLMRouter))
        updated = await service.trigger_item(watch_id, item.user_id, "Hit", db)
        assert updated.status == "triggered"
        assert updated.trigger_outcome == "Hit"

        db._scalar = updated
        dismissed = await service.dismiss_item(watch_id, item.user_id, db)
        assert dismissed.status == "dismissed"


class TestWatchItemSuggestion:
    """Tests for WatchItemSuggestion schema."""

    def test_valid_suggestion(self) -> None:
        """Valid suggestion passes validation."""
        suggestion = WatchItemSuggestion(
            title="Catalyst",
            description="Test",
            category="earnings",
            expected_date="2026-03-01",
            is_recurring=False,
            potential_impact="Impact",
            impact_direction="positive",
            affected_assumptions=["wacc"],
            confidence=0.8,
        )
        assert suggestion.title == "Catalyst"
        assert suggestion.confidence == 0.8
