"""Watch item database model for catalysts and monitoring items."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WatchItem(Base, UUIDMixin, TimestampMixin):
    """Watch item for catalysts, metrics, and monitoring triggers."""

    __tablename__ = "watch_items"

    stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    potential_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact_direction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    affected_assumptions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trigger_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def get_affected_assumptions(self) -> list[str]:
        """Parse affected_assumptions JSON string into list."""
        if not self.affected_assumptions:
            return []
        try:
            return json.loads(self.affected_assumptions)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_affected_assumptions(self, assumptions: list[str]) -> None:
        """Store affected_assumptions list as JSON string."""
        self.affected_assumptions = json.dumps(assumptions)
