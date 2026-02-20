"""Tests for notes model and extraction."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1 import notes as notes_module
from app.models.note import Note
from app.schemas.note import ExtractionResult
from app.services.llm.router import LLMRouter
from app.services.llm.types import LLMResponse, TaskType


class TestNoteModel:
    """Tests for Note database model."""

    def test_model_fields(self) -> None:
        """Verify all required columns exist on Note."""
        expected_attrs = [
            "id",
            "stock_id",
            "user_id",
            "title",
            "content",
            "note_type",
            "extracted_sentiment",
            "extracted_key_points",
            "extracted_price_target",
            "extracted_metrics",
            "is_ai_processed",
            "tags",
            "created_at",
            "updated_at",
        ]

        for attr in expected_attrs:
            assert hasattr(Note, attr), f"Note missing attribute: {attr}"

    def test_tablename(self) -> None:
        """Table name is 'notes'."""
        assert Note.__tablename__ == "notes"

    def test_json_helpers_round_trip(self) -> None:
        """JSON helper methods store and parse lists/dicts."""
        note = Note(
            stock_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test",
            content="Some note content",
        )

        tags = ["earnings", "guidance"]
        note.set_tags(tags)
        assert note.get_tags() == tags

        key_points = ["Revenue growth", "Margin pressure"]
        note.set_extracted_key_points(key_points)
        assert note.get_extracted_key_points() == key_points

        metrics = {"revenue_growth": 0.12}
        note.set_extracted_metrics(metrics)
        assert note.get_extracted_metrics() == metrics


class TestNoteExtraction:
    """Tests for note extraction handling."""

    @pytest.mark.asyncio
    async def test_extraction_parses_json(self, monkeypatch) -> None:
        """Valid JSON should parse into ExtractionResult."""
        payload = {
            "sentiment": "positive",
            "key_points": ["Strong demand"],
            "price_target": 150.0,
            "metrics": {"margin": 0.3},
        }
        mock_response = LLMResponse(
            content=json.dumps(payload),
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=10,
            output_tokens=20,
            latency_ms=50.0,
        )
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)
        monkeypatch.setattr(notes_module, "LLMRouter", lambda: mock_router)

        note = Note(
            stock_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test",
            content="Some note content",
        )

        class DummySession:
            async def commit(self) -> None:
                return None

            async def refresh(self, _note: Note) -> None:
                return None

        async def fake_get_note_by_id(note_id: str, db, user):
            return note

        monkeypatch.setattr(notes_module, "get_note_by_id", fake_get_note_by_id)

        result = await notes_module.extract_note(
            note_id=str(note.id),
            current_user=MagicMock(id=note.user_id),
            db=DummySession(),
        )

        assert isinstance(result, ExtractionResult)
        assert result.sentiment == "positive"
        assert result.key_points == ["Strong demand"]
        assert result.price_target == 150.0
        assert result.metrics == {"margin": 0.3}
        assert note.is_ai_processed is True

        mock_router.complete.assert_called_once()
        call_kwargs = mock_router.complete.call_args.kwargs
        assert call_kwargs["task_type"] == TaskType.NOTE_EXTRACTION
        assert call_kwargs["json_mode"] is True

    @pytest.mark.asyncio
    async def test_extraction_handles_bad_json(self, monkeypatch) -> None:
        """Malformed JSON returns default ExtractionResult."""
        mock_response = LLMResponse(
            content="not-json",
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=10,
            output_tokens=20,
            latency_ms=50.0,
        )
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)
        monkeypatch.setattr(notes_module, "LLMRouter", lambda: mock_router)

        note = Note(
            stock_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test",
            content="Some note content",
        )

        class DummySession:
            async def commit(self) -> None:
                return None

            async def refresh(self, _note: Note) -> None:
                return None

        async def fake_get_note_by_id(note_id: str, db, user):
            return note

        monkeypatch.setattr(notes_module, "get_note_by_id", fake_get_note_by_id)

        result = await notes_module.extract_note(
            note_id=str(note.id),
            current_user=MagicMock(id=note.user_id),
            db=DummySession(),
        )

        assert result.sentiment is None
        assert result.key_points == []
        assert result.price_target is None
        assert result.metrics == {}
        assert note.is_ai_processed is True
