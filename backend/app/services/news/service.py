"""News analysis service — fetches news and runs AI analysis."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.news_analysis import NewsAnalysis
from app.schemas.financial import NewsItem
from app.services.data.registry import get_news
from app.services.llm.prompts.templates import get_news_analysis_template
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType

logger = get_logger(__name__)


class NewsAnalysisResult(BaseModel):
    """Result of AI news analysis."""

    relevance_score: float
    impact_score: float
    impact_label: str  # bullish / bearish / neutral
    thesis_alignment: str  # supports / challenges / neutral
    key_points: list[str]
    affected_metrics: list[str]
    ai_summary: str


class NewsService:
    """Service for fetching and analyzing news with AI."""

    def __init__(self, llm_router: LLMRouter) -> None:
        """Initialize the news service.

        Args:
            llm_router: LLM router for AI analysis
        """
        self._llm = llm_router

    async def fetch_and_analyze(
        self,
        ticker: str,
        stock_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        current_thesis: Optional[str],
        db: AsyncSession,
        limit: int = 20,
    ) -> list[NewsAnalysis]:
        """Fetch news for a ticker and run AI analysis on each article.

        Args:
            ticker: Stock ticker symbol
            stock_id: Stock UUID for database association
            user_id: User UUID for database association (optional)
            current_thesis: Existing investment thesis for alignment check
            db: Database session
            limit: Maximum number of articles to fetch and analyze

        Returns:
            List of NewsAnalysis records saved to database
        """
        # Fetch news from the data provider
        news_provider = get_news()
        articles = await news_provider.get_news(ticker=ticker, limit=limit)

        if not articles:
            logger.info(f"No news articles found for {ticker}")
            return []

        # Analyze each article and save to database
        analyses: list[NewsAnalysis] = []
        for article in articles:
            try:
                result = await self._analyze_article(
                    article=article,
                    ticker=ticker,
                    company_name="",  # Could be enhanced to fetch from stock
                    current_thesis=current_thesis,
                )

                # Create NewsAnalysis record
                analysis = NewsAnalysis(
                    stock_id=stock_id,
                    user_id=user_id,
                    headline=article.headline,
                    summary=article.summary,
                    source_name=article.source_name,
                    source_url=article.source_url,
                    published_at=article.published_at,
                    relevance_score=result.relevance_score,
                    impact_score=result.impact_score,
                    impact_label=result.impact_label,
                    thesis_alignment=result.thesis_alignment,
                    provider_sentiment_score=article.sentiment_score,
                    data_source=article.source,
                )

                # Set JSON fields
                analysis.set_key_points(result.key_points)
                analysis.set_affected_metrics(result.affected_metrics)
                analysis.ai_summary = result.ai_summary

                db.add(analysis)
                analyses.append(analysis)

            except Exception as e:
                logger.error(
                    f"Error analyzing article for {ticker}: {article.headline}. Error: {e}"
                )
                # Continue with next article
                continue

        # Commit all analyses
        await db.commit()

        # Refresh to get IDs and timestamps
        for analysis in analyses:
            await db.refresh(analysis)

        logger.info(f"Analyzed {len(analyses)} news articles for {ticker}")
        return analyses

    async def _analyze_article(
        self,
        article: NewsItem,
        ticker: str,
        company_name: str,
        current_thesis: Optional[str],
    ) -> NewsAnalysisResult:
        """Analyze a single news article using AI.

        Args:
            article: News article to analyze
            ticker: Stock ticker symbol
            company_name: Company name (for context)
            current_thesis: Existing investment thesis for alignment check

        Returns:
            NewsAnalysisResult with AI analysis
        """
        # Build prompt using news analysis template
        template = get_news_analysis_template()

        # Format thesis for prompt
        thesis_text = current_thesis or "No existing thesis available"

        # Render template
        messages = template.render(
            ticker=ticker,
            news_headline=article.headline,
            news_content=article.summary or article.headline,
            current_thesis=thesis_text,
            publication_date=article.published_at.isoformat(),
        )

        try:
            # Call LLM with JSON mode
            response = await self._llm.complete(
                task_type=TaskType.NEWS_ANALYSIS,
                messages=messages,
                json_mode=True,
            )

            # Parse JSON response
            analysis_data = json.loads(response.content)

            return NewsAnalysisResult(
                relevance_score=self._parse_relevance(analysis_data.get("relevance", "Medium")),
                impact_score=self._parse_impact_score(analysis_data.get("sentiment")),
                impact_label=self._parse_impact_label(analysis_data.get("sentiment")),
                thesis_alignment=self._parse_thesis_alignment(
                    analysis_data.get("thesis_alignment")
                ),
                key_points=analysis_data.get("key_takeaways", [])[:5],  # Limit to 5
                affected_metrics=analysis_data.get("affected_metrics", []),
                ai_summary=analysis_data.get("summary", ""),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse LLM response for news analysis: {e}")
            # Return neutral defaults
            return NewsAnalysisResult(
                relevance_score=0.5,
                impact_score=0.0,
                impact_label="neutral",
                thesis_alignment="neutral",
                key_points=[],
                affected_metrics=[],
                ai_summary="Analysis unavailable - LLM response parsing failed",
            )

        except Exception as e:
            logger.error(f"LLM error during news analysis: {e}")
            # Return neutral defaults
            return NewsAnalysisResult(
                relevance_score=0.3,
                impact_score=0.0,
                impact_label="neutral",
                thesis_alignment="neutral",
                key_points=[],
                affected_metrics=[],
                ai_summary="Analysis unavailable - LLM error",
            )

    def _parse_relevance(self, relevance: str) -> float:
        """Parse relevance string to score 0.0-1.0."""
        relevance_lower = relevance.lower()
        if "high" in relevance_lower:
            return 0.8
        elif "medium" in relevance_lower or "moderate" in relevance_lower:
            return 0.5
        elif "low" in relevance_lower:
            return 0.2
        else:
            return 0.5  # Default to medium

    def _parse_impact_score(self, sentiment: Optional[str]) -> float:
        """Parse sentiment string to impact score -1.0 to 1.0."""
        if not sentiment:
            return 0.0

        sentiment_lower = sentiment.lower()
        if "positive" in sentiment_lower or "bullish" in sentiment_lower:
            return 0.7
        elif "negative" in sentiment_lower or "bearish" in sentiment_lower:
            return -0.7
        else:
            return 0.0

    def _parse_impact_label(self, sentiment: Optional[str]) -> str:
        """Parse sentiment string to impact label."""
        if not sentiment:
            return "neutral"

        sentiment_lower = sentiment.lower()
        if "positive" in sentiment_lower or "bullish" in sentiment_lower:
            return "bullish"
        elif "negative" in sentiment_lower or "bearish" in sentiment_lower:
            return "bearish"
        else:
            return "neutral"

    def _parse_thesis_alignment(self, alignment: Optional[str]) -> str:
        """Parse thesis alignment string."""
        if not alignment:
            return "neutral"

        alignment_lower = alignment.lower()
        if "confirm" in alignment_lower or "support" in alignment_lower:
            return "supports"
        elif "challenge" in alignment_lower or "contradict" in alignment_lower:
            return "challenges"
        else:
            return "neutral"

    async def get_recent_analyses(
        self,
        stock_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        db: AsyncSession,
        limit: int = 20,
        min_relevance: float = 0.0,
    ) -> list[NewsAnalysis]:
        """Query database for recent analyses, ordered by published_at DESC.

        Args:
            stock_id: Stock UUID to filter by
            user_id: User UUID to filter by (optional)
            db: Database session
            limit: Maximum number of analyses to return
            min_relevance: Minimum relevance score filter

        Returns:
            List of NewsAnalysis records
        """
        query = select(NewsAnalysis).where(
            NewsAnalysis.stock_id == stock_id,
            NewsAnalysis.relevance_score >= min_relevance,
        )

        if user_id is not None:
            query = query.where(NewsAnalysis.user_id == user_id)

        query = query.order_by(NewsAnalysis.published_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_sentiment_summary(
        self,
        stock_id: uuid.UUID,
        db: AsyncSession,
        days: int = 30,
    ) -> dict[str, any]:
        """Aggregate sentiment over the last N days.

        Args:
            stock_id: Stock UUID to analyze
            db: Database session
            days: Number of days to look back

        Returns:
            Dict with avg_impact_score, bullish_count, bearish_count,
            neutral_count, total_articles, top_key_points
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = select(NewsAnalysis).where(
            NewsAnalysis.stock_id == stock_id,
            NewsAnalysis.published_at >= cutoff_date,
        )

        result = await db.execute(query)
        analyses = list(result.scalars().all())

        if not analyses:
            return {
                "avg_impact_score": 0.0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "total_articles": 0,
                "top_key_points": [],
            }

        # Calculate aggregates
        total_impact = sum(a.impact_score for a in analyses)
        bullish_count = sum(1 for a in analyses if a.impact_label == "bullish")
        bearish_count = sum(1 for a in analyses if a.impact_label == "bearish")
        neutral_count = sum(1 for a in analyses if a.impact_label == "neutral")

        # Aggregate key points by frequency
        key_point_freq: dict[str, int] = {}
        for analysis in analyses:
            for point in analysis.get_key_points():
                key_point_freq[point] = key_point_freq.get(point, 0) + 1

        # Get top 5 most common key points
        top_key_points = [
            point for point, _ in sorted(key_point_freq.items(), key=lambda x: -x[1])[:5]
        ]

        return {
            "avg_impact_score": total_impact / len(analyses),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "total_articles": len(analyses),
            "top_key_points": top_key_points,
        }
