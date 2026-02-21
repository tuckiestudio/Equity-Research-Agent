"""
User database model.
"""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """Application user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")  # free, pro, premium
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # Admin flag

    # Relationships
    portfolios: Mapped[list["Portfolio"]] = relationship(  # type: ignore[name-defined]
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettings"] = relationship(  # type: ignore[name-defined]
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
