"""News API endpoints — analyze and retrieve news with AI insights."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.news_analysis import NewsAnalysis
from app.models.stock import Stock
from app.models.user import User
from app.services.llm.router import LLMRouter
from app.services.news.service import NewsService

router = APIRouter(prefix="/news", tags=["news"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class NewsAnalysisResponse(BaseModel):
    """Response model for a single news analysis."""

    id: str
    headline: str
    summary: Optional[str]
    source_name: str
    source_url: Optional[str]
    published_at: datetime
    relevance_score: float
    impact_score: float
    impact_label: str
    thesis_alignment: str
    key_points: list[str]  # Parsed from JSON
    affected_metrics: list[str]
    ai_summary: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_analysis(cls, analysis: NewsAnalysis) -> NewsAnalysisResponse:
        """Create response from NewsAnalysis model."""
        return cls(
            id=str(analysis.id),
            headline=analysis.headline,
            summary=analysis.summary,
            source_name=analysis.source_name,
            source_url=analysis.source_url,
            published_at=analysis.published_at,
            relevance_score=analysis.relevance_score,
            impact_score=analysis.impact_score,
            impact_label=analysis.impact_label,
            thesis_alignment=analysis.thesis_alignment,
            key_points=analysis.get_key_points(),
            affected_metrics=analysis.get_affected_metrics(),
            ai_summary=analysis.ai_summary or "",
            created_at=analysis.created_at,
        )


class SentimentSummaryResponse(BaseModel):
    """Response model for sentiment summary."""

    ticker: str
    period_days: int
    avg_impact_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    total_articles: int
    top_key_points: list[str]


class AnalyzeNewsRequest(BaseModel):
    """Request model for news analysis."""

    thesis: Optional[str] = Field(
        None, description="Current investment thesis for alignment checking"
    )
    limit: int = Field(20, ge=1, le=100, description="Maximum number of articles to analyze")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/{ticker}/analyze", response_model=list[NewsAnalysisResponse])
async def analyze_news(
    ticker: str,
    request: AnalyzeNewsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NewsAnalysisResponse]:
    """Fetch and analyze news for a ticker using AI.

    This endpoint:
    1. Fetches recent news from the configured data provider
    2. Runs AI analysis on each article (relevance, impact, thesis alignment)
    3. Stores results in the database
    4. Returns the analyzed articles

    The analysis includes:
    - **Relevance score** (0.0-1.0): How relevant to the investment thesis
    - **Impact score** (-1.0 to 1.0): Price impact (negative=bearish, positive=bullish)
    - **Thesis alignment**: Supports, challenges, or neutral to existing thesis
    - **Key points**: 2-3 bullet points on what matters most
    - **Affected metrics**: Which financial metrics could be impacted
    """
    # Find the stock in our database
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)

    # Create news service with LLM router
    # Note: In production, LLMRouter would be injected as a dependency
    llm_router = LLMRouter()  # Would be properly initialized via DI
    news_service = NewsService(llm_router=llm_router)

    # Fetch and analyze
    analyses = await news_service.fetch_and_analyze(
        ticker=ticker.upper(),
        stock_id=stock.id,
        user_id=current_user.id,
        current_thesis=request.thesis,
        db=db,
        limit=request.limit,
        user_settings=current_user.settings,
    )

    return [NewsAnalysisResponse.from_analysis(a) for a in analyses]


@router.get("/{ticker}", response_model=list[NewsAnalysisResponse])
async def get_news_analyses(
    ticker: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    min_relevance: float = Query(0.0, ge=0.0, le=1.0, description="Minimum relevance score"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NewsAnalysisResponse]:
    """Get previously analyzed news for a ticker from the database.

    Returns cached AI-powered news analysis without making new API calls.
    """
    # Find the stock
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)

    # Create news service and query
    llm_router = LLMRouter()
    news_service = NewsService(llm_router=llm_router)

    analyses = await news_service.get_recent_analyses(
        stock_id=stock.id,
        user_id=current_user.id,
        db=db,
        limit=limit,
        min_relevance=min_relevance,
    )

    return [NewsAnalysisResponse.from_analysis(a) for a in analyses]


@router.get("/{ticker}/sentiment", response_model=SentimentSummaryResponse)
async def get_sentiment_summary(
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentimentSummaryResponse:
    """Get sentiment summary for a ticker over a time period.

    Aggregates news sentiment analysis to provide:
    - Average impact score
    - Count of bullish/bearish/neutral articles
    - Top key points by frequency
    """
    # Find the stock
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)

    # Create news service and get summary
    llm_router = LLMRouter()
    news_service = NewsService(llm_router=llm_router)

    summary = await news_service.get_sentiment_summary(
        stock_id=stock.id,
        db=db,
        days=days,
    )

    return SentimentSummaryResponse(
        ticker=ticker.upper(),
        period_days=days,
        avg_impact_score=summary["avg_impact_score"],
        bullish_count=summary["bullish_count"],
        bearish_count=summary["bearish_count"],
        neutral_count=summary["neutral_count"],
        total_articles=summary["total_articles"],
        top_key_points=summary["top_key_points"],
    )


@router.get("/{ticker}/{analysis_id}", response_model=NewsAnalysisResponse)
async def get_news_analysis_detail(
    ticker: str,
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsAnalysisResponse:
    """Get a single news analysis by ID.

    Returns detailed AI analysis for a specific news article.
    """
    # Verify stock exists
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)

    # Parse analysis_id
    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise NotFoundError("NewsAnalysis", analysis_id)

    # Find analysis
    result = await db.execute(
        select(NewsAnalysis).where(
            NewsAnalysis.id == analysis_uuid,
            NewsAnalysis.stock_id == stock.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise NotFoundError("NewsAnalysis", analysis_id)

    return NewsAnalysisResponse.from_analysis(analysis)
