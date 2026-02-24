"""Tests for comp suggestion engine."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.financial import CompanyProfile
from app.services.llm.router import LLMRouter
from app.services.llm.types import LLMResponse
from app.services.model import comp_suggestions as comp_module
from app.services.model.comp_suggestions import CompSuggestionEngine


class DummyProfiles:
    """Dummy profiles provider for comp suggestion tests."""

    def __init__(self, profiles):
        self._profiles = profiles

    async def get_company_profile(self, ticker: str) -> CompanyProfile:
        if ticker not in self._profiles:
            raise KeyError(ticker)
        return self._profiles[ticker]


class TestCompSuggestions:
    """Tests for comp suggestion engine."""

    @pytest.mark.asyncio
    async def test_suggests_valid_companies(self, monkeypatch) -> None:
        """LLM suggestions are validated with profiles and returned."""
        profiles = {
            "AAPL": CompanyProfile(
                ticker="AAPL",
                company_name="Apple Inc",
                sector="Technology",
                industry="Hardware",
                market_cap=2000.0,
                source="test",
            ),
            "MSFT": CompanyProfile(
                ticker="MSFT",
                company_name="Microsoft",
                sector="Technology",
                industry="Software",
                market_cap=1800.0,
                source="test",
            ),
        }
        monkeypatch.setattr(comp_module, "get_profiles", lambda user_settings=None: DummyProfiles(profiles))

        mock_response = LLMResponse(
            content=json.dumps([
                {"ticker": "MSFT", "reason": "Similar scale", "similarity_score": 0.8},
            ]),
            model="gpt-4o",
            provider="openai",
            input_tokens=10,
            output_tokens=20,
            latency_ms=50.0,
        )
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        engine = CompSuggestionEngine(llm_router=mock_router)
        suggestions = await engine.suggest_peers("AAPL", limit=5)

        assert len(suggestions) == 1
        assert suggestions[0].ticker == "MSFT"
        assert suggestions[0].similarity_score == pytest.approx(0.8)
        assert suggestions[0].sector == "Technology"

    @pytest.mark.asyncio
    async def test_invalid_ticker_filtered(self, monkeypatch) -> None:
        """Suggestions without profiles are filtered out."""
        profiles = {
            "AAPL": CompanyProfile(
                ticker="AAPL",
                company_name="Apple Inc",
                sector="Technology",
                industry="Hardware",
                market_cap=2000.0,
                source="test",
            )
        }
        monkeypatch.setattr(comp_module, "get_profiles", lambda user_settings=None: DummyProfiles(profiles))

        mock_response = LLMResponse(
            content=json.dumps([
                {"ticker": "NOPE", "reason": "Unknown", "similarity_score": 0.5},
            ]),
            model="gpt-4o",
            provider="openai",
            input_tokens=10,
            output_tokens=20,
            latency_ms=50.0,
        )
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        engine = CompSuggestionEngine(llm_router=mock_router)
        suggestions = await engine.suggest_peers("AAPL", limit=5)

        assert suggestions == []

    @pytest.mark.asyncio
    async def test_limit_respected(self, monkeypatch) -> None:
        """Limit truncates the suggestion list."""
        profiles = {
            "AAPL": CompanyProfile(
                ticker="AAPL",
                company_name="Apple Inc",
                sector="Technology",
                industry="Hardware",
                market_cap=2000.0,
                source="test",
            ),
            "MSFT": CompanyProfile(
                ticker="MSFT",
                company_name="Microsoft",
                sector="Technology",
                industry="Software",
                market_cap=1800.0,
                source="test",
            ),
            "GOOG": CompanyProfile(
                ticker="GOOG",
                company_name="Alphabet",
                sector="Technology",
                industry="Internet",
                market_cap=1500.0,
                source="test",
            ),
        }
        monkeypatch.setattr(comp_module, "get_profiles", lambda user_settings=None: DummyProfiles(profiles))

        mock_response = LLMResponse(
            content=json.dumps([
                {"ticker": "MSFT", "reason": "Similar scale", "similarity_score": 0.8},
                {"ticker": "GOOG", "reason": "Platform peer", "similarity_score": 0.7},
            ]),
            model="gpt-4o",
            provider="openai",
            input_tokens=10,
            output_tokens=20,
            latency_ms=50.0,
        )
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        engine = CompSuggestionEngine(llm_router=mock_router)
        suggestions = await engine.suggest_peers("AAPL", limit=1)

        assert len(suggestions) == 1
        assert suggestions[0].ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty(self, monkeypatch) -> None:
        """LLM errors return empty list."""
        profiles = {
            "AAPL": CompanyProfile(
                ticker="AAPL",
                company_name="Apple Inc",
                sector="Technology",
                industry="Hardware",
                market_cap=2000.0,
                source="test",
            )
        }
        monkeypatch.setattr(comp_module, "get_profiles", lambda user_settings=None: DummyProfiles(profiles))

        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(side_effect=Exception("LLM error"))

        engine = CompSuggestionEngine(llm_router=mock_router)
        suggestions = await engine.suggest_peers("AAPL", limit=5)

        assert suggestions == []

    @pytest.mark.asyncio
    async def test_similarity_score_in_range(self, monkeypatch) -> None:
        """Similarity score must be between 0 and 1."""
        profiles = {
            "AAPL": CompanyProfile(
                ticker="AAPL",
                company_name="Apple Inc",
                sector="Technology",
                industry="Hardware",
                market_cap=2000.0,
                source="test",
            ),
            "MSFT": CompanyProfile(
                ticker="MSFT",
                company_name="Microsoft",
                sector="Technology",
                industry="Software",
                market_cap=1800.0,
                source="test",
            ),
        }
        monkeypatch.setattr(comp_module, "get_profiles", lambda user_settings=None: DummyProfiles(profiles))

        mock_response = LLMResponse(
            content=json.dumps([
                {"ticker": "MSFT", "reason": "Similar scale", "similarity_score": 1.5},
            ]),
            model="gpt-4o",
            provider="openai",
            input_tokens=10,
            output_tokens=20,
            latency_ms=50.0,
        )
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        engine = CompSuggestionEngine(llm_router=mock_router)
        suggestions = await engine.suggest_peers("AAPL", limit=5)

        assert suggestions == []
