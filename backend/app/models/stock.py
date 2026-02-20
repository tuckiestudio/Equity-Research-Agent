"""
Stock and Portfolio database models.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# Many-to-many association table
portfolio_stocks = Table(
    "portfolio_stocks",
    Base.metadata,
    Column("portfolio_id", UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), primary_key=True),
    Column("stock_id", UUID(as_uuid=True), ForeignKey("stocks.id", ondelete="CASCADE"), primary_key=True),
)


class Stock(Base, UUIDMixin, TimestampMixin):
    """A stock/equity that can be tracked."""

    __tablename__ = "stocks"

    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    portfolios: Mapped[list[Portfolio]] = relationship(
        "Portfolio", secondary=portfolio_stocks, back_populates="stocks"
    )


class Portfolio(Base, UUIDMixin, TimestampMixin):
    """User's portfolio (collection of watched stocks)."""

    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolios")  # type: ignore[name-defined]
    stocks: Mapped[list[Stock]] = relationship(
        "Stock", secondary=portfolio_stocks, back_populates="portfolios"
    )
