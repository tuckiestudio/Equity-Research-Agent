from __future__ import annotations

from typing import Optional, Any
"""
Assumption set database model for financial modeling.
"""

import json
import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AssumptionSet(Base, UUIDMixin, TimestampMixin):
    """Financial assumptions for DCF and other valuation models.

    Each user can create multiple assumption sets per stock (e.g., "Base Case",
    "Bull Case", "Bear Case"). One set is marked as active and used for valuation.
    """

    __tablename__ = "assumption_sets"

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
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Base Case"
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, index=True
    )

    # Revenue assumptions (JSON-stored for flexibility)
    revenue_growth_rates: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )
    projection_years: Mapped[int] = mapped_column(
        nullable=False, default=5
    )

    # Margin assumptions
    gross_margin: Mapped[float] = mapped_column(
        nullable=False
    )
    operating_margin: Mapped[float] = mapped_column(
        nullable=False
    )
    tax_rate: Mapped[float] = mapped_column(
        nullable=False, default=0.21
    )

    # DCF-specific
    wacc: Mapped[float] = mapped_column(
        nullable=False
    )
    terminal_growth_rate: Mapped[float] = mapped_column(
        nullable=False, default=0.025
    )
    capex_as_pct_revenue: Mapped[float] = mapped_column(
        nullable=False, default=0.05
    )
    da_as_pct_revenue: Mapped[float] = mapped_column(
        nullable=False, default=0.03
    )

    # Optional overrides
    shares_outstanding: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )
    net_debt: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )

    def get_revenue_growth_rates(self) -> list[float]:
        """Parse JSON string into list of floats."""
        return json.loads(self.revenue_growth_rates)

    def set_revenue_growth_rates(self, rates: list[float]) -> None:
        """Store list of floats as JSON string."""
        self.revenue_growth_rates = json.dumps(rates)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "stock_id": str(self.stock_id),
            "user_id": str(self.user_id),
            "name": self.name,
            "is_active": self.is_active,
            "revenue_growth_rates": self.get_revenue_growth_rates(),
            "projection_years": self.projection_years,
            "gross_margin": self.gross_margin,
            "operating_margin": self.operating_margin,
            "tax_rate": self.tax_rate,
            "wacc": self.wacc,
            "terminal_growth_rate": self.terminal_growth_rate,
            "capex_as_pct_revenue": self.capex_as_pct_revenue,
            "da_as_pct_revenue": self.da_as_pct_revenue,
            "shares_outstanding": self.shares_outstanding,
            "net_debt": self.net_debt,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
