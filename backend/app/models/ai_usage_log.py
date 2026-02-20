"""
AI usage log database model for tracking LLM costs and token usage.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class AIUsageLog(Base, UUIDMixin):
    """Log entry for every LLM API call.

    Tracks token usage, cost, latency, and which task triggered the call.
    Used for cost monitoring, billing, and performance analysis.
    """

    __tablename__ = "ai_usage_log"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    cost_usd: Mapped[float] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional context
    ticker: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    prompt_template: Mapped[str] = mapped_column(String(100), nullable=True)
    finish_reason: Mapped[str] = mapped_column(String(50), nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
