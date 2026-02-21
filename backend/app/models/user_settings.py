"""
User Settings database model.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base, UUIDMixin, TimestampMixin):
    """User-specific settings, including data provider selections and API keys."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Provider Selections
    fundamentals_provider: Mapped[str] = mapped_column(String(50), default="fmp", nullable=False)
    price_provider: Mapped[str] = mapped_column(String(50), default="finnhub", nullable=False)
    profile_provider: Mapped[str] = mapped_column(String(50), default="fmp", nullable=False)
    news_provider: Mapped[str] = mapped_column(String(50), default="finnhub", nullable=False)

    # Financial Data API Keys
    fmp_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    finnhub_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    alpha_vantage_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    eodhd_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    polygon_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # AI API Keys
    openai_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    anthropic_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    glm_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kimi_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")
