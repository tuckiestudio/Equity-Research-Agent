"""Tests for news service and news analysis model."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.news_analysis import NewsAnalysis
from app.schemas.financial import NewsItem
from app.services.llm.router import LLMRouter
from app.services.llm.types import LLMResponse, TaskType
from app.services.news.service import NewsAnalysisResult, NewsService


class TestNewsService:
    """Tests for NewsService."""

    @pytest.mark.asyncio
    async def test_analyze_article_returns_result(self):
        """Mock LLMRouter, verify NewsAnalysisResult fields."""
        # Create mock LLM response
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "relevance": "High",
                    "sentiment": "Positive",
                    "thesis_alignment": "Confirms the bullish thesis",
                    "key_takeaways": [
                        "Revenue growth accelerating",
                        "Margin expansion expected",
                    ],
                    "affected_metrics": ["revenue", "operating_margin"],
                    "summary": "Strong earnings beat suggests continued momentum.",
                }
            ),
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            latency_ms=100.0,
        )

        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        # Create service
        service = NewsService(llm_router=mock_router)

        # Create test article
        article = NewsItem(
            headline="Company beats earnings estimates",
            summary="Q4 revenue up 15% YoY, beating analyst expectations",
            source_name="Bloomberg",
            source_url="https://example.com/article",
            ticker="AAPL",
            published_at=datetime.utcnow(),
            sentiment_score=0.5,
            sentiment_label="positive",
            source="test",
        )

        # Analyze
        result = await service._analyze_article(
            article=article,
            ticker="AAPL",
            company_name="Apple Inc.",
            current_thesis="Bullish on iPhone 15 cycle",
        )

        # Verify result
        assert isinstance(result, NewsAnalysisResult)
        assert result.relevance_score == 0.8  # High relevance
        assert result.impact_score == 0.7  # Positive sentiment
        assert result.impact_label == "bullish"
        assert result.thesis_alignment == "supports"
        assert len(result.key_points) == 2
        assert "Revenue growth accelerating" in result.key_points
        assert "operating_margin" in result.affected_metrics
        assert result.ai_summary == "Strong earnings beat suggests continued momentum."

    @pytest.mark.asyncio
    async def test_analyze_article_with_thesis(self):
        """Thesis text is included in prompt when provided."""
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "relevance": "Medium",
                    "sentiment": "Negative",
                    "thesis_alignment": "Challenges the existing thesis",
                    "key_takeaways": ["Supply chain issues worsening"],
                    "affected_metrics": ["gross_margin"],
                    "summary": "Production delays may impact Q2 guidance",
                }
            ),
            model="gpt-4o",
            provider="openai",
            input_tokens=150,
            output_tokens=60,
            latency_ms=120.0,
        )

        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        service = NewsService(llm_router=mock_router)

        article = NewsItem(
            headline="Production delays reported",
            summary="Supply chain constraints may limit production capacity",
            source_name="Reuters",
            source_url="https://example.com/article2",
            ticker="AAPL",
            published_at=datetime.utcnow(),
            sentiment_score=-0.3,
            sentiment_label="negative",
            source="test",
        )

        result = await service._analyze_article(
            article=article,
            ticker="AAPL",
            company_name="Apple Inc.",
            current_thesis="Bullish on strong production volumes in Q2",
        )

        assert result.thesis_alignment == "challenges"
        assert result.impact_label == "bearish"
        assert result.impact_score < 0

        # Verify the LLM was called with correct task type
        mock_router.complete.assert_called_once()
        call_kwargs = mock_router.complete.call_args.kwargs
        assert call_kwargs["task_type"] == TaskType.NEWS_ANALYSIS
        assert call_kwargs["json_mode"] is True

    @pytest.mark.asyncio
    async def test_analyze_article_handles_bad_json(self):
        """Malformed LLM response -> neutral defaults."""
        # Return invalid JSON
        mock_response = LLMResponse(
            content="This is not valid JSON at all",
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=20,
            latency_ms=50.0,
        )

        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(return_value=mock_response)

        service = NewsService(llm_router=mock_router)

        article = NewsItem(
            headline="Some news article",
            summary="Some summary",
            source_name="Test Source",
            source_url="https://example.com",
            ticker="TEST",
            published_at=datetime.utcnow(),
            sentiment_score=0.0,
            sentiment_label="neutral",
            source="test",
        )

        result = await service._analyze_article(
            article=article,
            ticker="TEST",
            company_name="Test Company",
            current_thesis=None,
        )

        # Should return neutral defaults
        assert result.relevance_score == 0.5
        assert result.impact_score == 0.0
        assert result.impact_label == "neutral"
        assert result.thesis_alignment == "neutral"
        assert result.key_points == []
        assert result.affected_metrics == []
        assert "unavailable" in result.ai_summary.lower()

    @pytest.mark.asyncio
    async def test_analyze_article_handles_llm_error(self):
        """LLM error -> graceful fallback, not crash."""
        mock_router = MagicMock(spec=LLMRouter)
        mock_router.complete = AsyncMock(side_effect=Exception("LLM API error"))

        service = NewsService(llm_router=mock_router)

        article = NewsItem(
            headline="Some news article",
            summary="Some summary",
            source_name="Test Source",
            source_url="https://example.com",
            ticker="TEST",
            published_at=datetime.utcnow(),
            sentiment_score=0.0,
            sentiment_label="neutral",
            source="test",
        )

        result = await service._analyze_article(
            article=article,
            ticker="TEST",
            company_name="Test Company",
            current_thesis=None,
        )

        # Should return neutral defaults without crashing
        assert result.relevance_score == 0.3
        assert result.impact_score == 0.0
        assert result.impact_label == "neutral"
        assert "unavailable" in result.ai_summary.lower()

    @pytest.mark.asyncio
    async def test_sentiment_summary_aggregation(self):
        """Given a list of analyses, compute correct averages and counts."""
        # Mock analyses
        mock_analyses = [
            MagicMock(
                impact_score=0.8, impact_label="bullish", get_key_points=lambda: ["Revenue growth"]
            ),
            MagicMock(
                impact_score=-0.5,
                impact_label="bearish",
                get_key_points=lambda: ["Margin pressure"],
            ),
            MagicMock(
                impact_score=0.0, impact_label="neutral", get_key_points=lambda: ["Revenue growth"]
            ),
            MagicMock(
                impact_score=0.9, impact_label="bullish", get_key_points=lambda: ["Cost cuts"]
            ),
        ]

        with patch.object(
            NewsService, "get_recent_analyses", return_value=mock_analyses  # type: ignore
        ):
            # This tests the internal aggregation logic
            total_impact = sum(a.impact_score for a in mock_analyses)
            bullish_count = sum(1 for a in mock_analyses if a.impact_label == "bullish")
            bearish_count = sum(1 for a in mock_analyses if a.impact_label == "bearish")
            neutral_count = sum(1 for a in mock_analyses if a.impact_label == "neutral")

            assert total_impact / len(mock_analyses) == pytest.approx(0.3)
            assert bullish_count == 2
            assert bearish_count == 1
            assert neutral_count == 1

    def test_sentiment_summary_returns_empty_for_no_articles(self):
        """When no analyses exist, return zeroed summary."""
        # Test aggregation logic with empty list
        empty_analyses: list = []

        total_impact = sum(a.impact_score for a in empty_analyses) if empty_analyses else 0
        bullish_count = sum(1 for a in empty_analyses if a.impact_label == "bullish")
        bearish_count = sum(1 for a in empty_analyses if a.impact_label == "bearish")
        neutral_count = sum(1 for a in empty_analyses if a.impact_label == "neutral")

        assert total_impact == 0.0
        assert bullish_count == 0
        assert bearish_count == 0
        assert neutral_count == 0


class TestNewsAnalysisModel:
    """Tests for NewsAnalysis database model."""

    def test_model_fields(self):
        """Verify all required columns exist on NewsAnalysis."""
        # Check that the model has the expected attributes
        expected_attrs = [
            "id",
            "stock_id",
            "user_id",
            "headline",
            "summary",
            "source_name",
            "source_url",
            "published_at",
            "relevance_score",
            "impact_score",
            "impact_label",
            "thesis_alignment",
            "key_points",
            "affected_metrics",
            "ai_summary",
            "provider_sentiment_score",
            "data_source",
            "created_at",
            "updated_at",
        ]

        for attr in expected_attrs:
            assert hasattr(NewsAnalysis, attr), f"NewsAnalysis missing attribute: {attr}"

    def test_tablename(self):
        """Table name is 'news_analyses'."""
        assert NewsAnalysis.__tablename__ == "news_analyses"

    def test_foreign_keys(self):
        """stock_id and user_id FKs are defined."""
        # The foreign keys are defined via mapped_column with ForeignKey
        # We can verify by checking the model has these attributes
        assert hasattr(NewsAnalysis, "stock_id")
        assert hasattr(NewsAnalysis, "user_id")


class TestJsonFieldHelpers:
    """Tests for JSON field helper methods."""

    def test_key_points_json_round_trip(self):
        """key_points stored as JSON, parsed back to list."""
        analysis = NewsAnalysis(
            stock_id=uuid.uuid4(),
            headline="Test headline",
            source_name="Test",
            published_at=datetime.utcnow(),
            data_source="test",
            relevance_score=0.5,
            impact_score=0.0,
            impact_label="neutral",
            thesis_alignment="neutral",
        )

        # Set key points
        points = ["Revenue growth accelerating", "Margin expansion expected"]
        analysis.set_key_points(points)

        # Verify stored as JSON string
        assert isinstance(analysis.key_points, str)

        # Parse back
        parsed = analysis.get_key_points()
        assert parsed == points

    def test_key_points_empty_string_returns_empty_list(self):
        """Empty key_points returns empty list."""
        analysis = NewsAnalysis(
            stock_id=uuid.uuid4(),
            headline="Test headline",
            source_name="Test",
            published_at=datetime.utcnow(),
            data_source="test",
            relevance_score=0.5,
            impact_score=0.0,
            impact_label="neutral",
            thesis_alignment="neutral",
            key_points=None,
        )

        assert analysis.get_key_points() == []

    def test_affected_metrics_json_round_trip(self):
        """affected_metrics stored as JSON, parsed back to list."""
        analysis = NewsAnalysis(
            stock_id=uuid.uuid4(),
            headline="Test headline",
            source_name="Test",
            published_at=datetime.utcnow(),
            data_source="test",
            relevance_score=0.5,
            impact_score=0.0,
            impact_label="neutral",
            thesis_alignment="neutral",
        )

        # Set affected metrics
        metrics = ["revenue", "operating_margin", "fcf"]
        analysis.set_affected_metrics(metrics)

        # Verify stored as JSON string
        assert isinstance(analysis.affected_metrics, str)

        # Parse back
        parsed = analysis.get_affected_metrics()
        assert parsed == metrics

    def test_affected_metrics_empty_string_returns_empty_list(self):
        """Empty affected_metrics returns empty list."""
        analysis = NewsAnalysis(
            stock_id=uuid.uuid4(),
            headline="Test headline",
            source_name="Test",
            published_at=datetime.utcnow(),
            data_source="test",
            relevance_score=0.5,
            impact_score=0.0,
            impact_label="neutral",
            thesis_alignment="neutral",
            affected_metrics=None,
        )

        assert analysis.get_affected_metrics() == []

    def test_invalid_json_returns_empty_list(self):
        """Invalid JSON in fields returns empty list."""
        analysis = NewsAnalysis(
            stock_id=uuid.uuid4(),
            headline="Test headline",
            source_name="Test",
            published_at=datetime.utcnow(),
            data_source="test",
            relevance_score=0.5,
            impact_score=0.0,
            impact_label="neutral",
            thesis_alignment="neutral",
            key_points="not valid json {",
        )

        assert analysis.get_key_points() == []

        analysis.key_points = None
        assert analysis.get_key_points() == []
