"""Thesis database model for investment thesis generation and versioning."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Thesis(Base, UUIDMixin, TimestampMixin):
    """Investment thesis for a stock and user."""

    __tablename__ = "theses"

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

    # Thesis content
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    stance: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Valuation context
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_price_at_generation: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    upside_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
