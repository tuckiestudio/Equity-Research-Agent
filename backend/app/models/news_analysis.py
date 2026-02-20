"""News analysis database model."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class NewsAnalysis(Base, UUIDMixin, TimestampMixin):
    """AI-powered news analysis for a stock."""

    __tablename__ = "news_analyses"

    # Foreign keys
    stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Original article data
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # AI analysis results
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # -1.0 to 1.0
    impact_label: Mapped[str] = mapped_column(
        String(20), nullable=False, default="neutral"
    )  # "bullish", "bearish", "neutral"
    thesis_alignment: Mapped[str] = mapped_column(
        String(20), nullable=False, default="neutral"
    )  # "supports", "challenges", "neutral"
    key_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of strings
    affected_metrics: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON list of affected line items
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Provider metadata
    provider_sentiment_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # Original provider sentiment
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default=""
    )  # e.g. "finnhub", "fmp"

    def get_key_points(self) -> list[str]:
        """Parse key_points JSON string into list."""
        if not self.key_points:
            return []
        try:
            return json.loads(self.key_points)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_key_points(self, points: list[str]) -> None:
        """Store key_points list as JSON string."""
        self.key_points = json.dumps(points)

    def get_affected_metrics(self) -> list[str]:
        """Parse affected_metrics JSON string into list."""
        if not self.affected_metrics:
            return []
        try:
            return json.loads(self.affected_metrics)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_affected_metrics(self, metrics: list[str]) -> None:
        """Store affected_metrics list as JSON string."""
        self.affected_metrics = json.dumps(metrics)
