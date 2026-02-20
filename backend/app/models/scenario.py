"""Scenario database model for valuation cases."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Scenario(Base, UUIDMixin, TimestampMixin):
    """Valuation scenario for a stock and user."""

    __tablename__ = "scenarios"

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
    assumption_set_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assumption_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    case_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue_growth_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_margin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wacc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    terminal_growth_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dcf_per_share: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comps_implied_pe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comps_implied_ev_ebitda: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
