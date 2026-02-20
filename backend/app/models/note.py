"""Analyst notes database model."""
from __future__ import annotations

import json
import uuid
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Note(Base, UUIDMixin, TimestampMixin):
    """Analyst note for a stock and user."""

    __tablename__ = "notes"

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

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    extracted_sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    extracted_key_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_price_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extracted_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_ai_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def get_extracted_key_points(self) -> list[str]:
        """Parse extracted_key_points JSON string into list."""
        if not self.extracted_key_points:
            return []
        try:
            return json.loads(self.extracted_key_points)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_extracted_key_points(self, points: list[str]) -> None:
        """Store extracted_key_points list as JSON string."""
        self.extracted_key_points = json.dumps(points)

    def get_extracted_metrics(self) -> dict[str, float | str]:
        """Parse extracted_metrics JSON string into dict."""
        if not self.extracted_metrics:
            return {}
        try:
            return json.loads(self.extracted_metrics)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_extracted_metrics(self, metrics: dict[str, float | str]) -> None:
        """Store extracted_metrics dict as JSON string."""
        self.extracted_metrics = json.dumps(metrics)

    def get_tags(self) -> list[str]:
        """Parse tags JSON string into list."""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags: list[str]) -> None:
        """Store tags list as JSON string."""
        self.tags = json.dumps(tags)
