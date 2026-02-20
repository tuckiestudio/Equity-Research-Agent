from typing import Optional, Any
"""Assumption schemas for financial modeling API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AssumptionBase(BaseModel):
    """Base assumption fields."""

    name: str = Field(..., description="Name of the assumption set (e.g., 'Base Case', 'Bull Case')")
    revenue_growth_rates: list[float] = Field(
        ..., description="Year-over-year revenue growth rates for projection period"
    )
    projection_years: int = Field(default=5, ge=1, le=10, description="Number of projection years")
    gross_margin: float = Field(..., ge=0, le=1, description="Gross margin as decimal (e.g., 0.45)")
    operating_margin: float = Field(..., ge=0, le=1, description="Operating margin as decimal (e.g., 0.30)")
    tax_rate: float = Field(default=0.21, ge=0, le=1, description="Effective tax rate as decimal")
    wacc: float = Field(..., ge=0, le=1, description="Weighted average cost of capital as decimal")
    terminal_growth_rate: float = Field(
        default=0.025, ge=0, le=0.1, description="Long-term terminal growth rate as decimal"
    )
    capex_as_pct_revenue: float = Field(
        default=0.05, ge=0, le=1, description="Capital expenditure as percentage of revenue"
    )
    da_as_pct_revenue: float = Field(
        default=0.03, ge=0, le=1, description="Depreciation & amortization as percentage of revenue"
    )
    shares_outstanding: Optional[float] = Field(
        default=None, gt=0, description="Override shares outstanding from latest filing"
    )
    net_debt: Optional[float] = Field(
        default=None, description="Net debt (total debt minus cash). Positive = debt."
    )

    @field_validator("revenue_growth_rates")
    @classmethod
    def validate_growth_rates(cls, v: list[float], info) -> list[float]:
        """Validate that growth rates list length matches projection_years."""
        if "projection_years" in info.data:
            projection_years = info.data["projection_years"]
            if len(v) != projection_years:
                raise ValueError(
                    f"revenue_growth_rates must have {projection_years} values, got {len(v)}"
                )
        return v


class AssumptionCreate(AssumptionBase):
    """Schema for creating a new assumption set."""

    pass


class AssumptionUpdate(BaseModel):
    """Schema for updating an existing assumption set."""

    name: Optional[str] = None
    revenue_growth_rates: Optional[list[float]] = None
    projection_years: Optional[int] = Field(None, ge=1, le=10)
    gross_margin: Optional[float] = Field(None, ge=0, le=1)
    operating_margin: Optional[float] = Field(None, ge=0, le=1)
    tax_rate: Optional[float] = Field(None, ge=0, le=1)
    wacc: Optional[float] = Field(None, ge=0, le=1)
    terminal_growth_rate: Optional[float] = Field(None, ge=0, le=0.1)
    capex_as_pct_revenue: Optional[float] = Field(None, ge=0, le=1)
    da_as_pct_revenue: Optional[float] = Field(None, ge=0, le=1)
    shares_outstanding: Optional[float] = None
    net_debt: Optional[float] = None
    is_active: Optional[bool] = None

    @field_validator("revenue_growth_rates")
    @classmethod
    def validate_growth_rates(cls, v: Optional[list[float]], info) -> Optional[list[float]]:
        """Validate that growth rates list length matches projection_years if both provided."""
        if v is not None and "projection_years" in info.data and info.data["projection_years"] is not None:
            projection_years = info.data["projection_years"]
            if len(v) != projection_years:
                raise ValueError(
                    f"revenue_growth_rates must have {projection_years} values, got {len(v)}"
                )
        return v


class AssumptionResponse(BaseModel):
    """Schema for assumption set responses."""

    id: str
    stock_id: str
    user_id: str
    name: str
    is_active: bool
    revenue_growth_rates: list[float]
    projection_years: int
    gross_margin: float
    operating_margin: float
    tax_rate: float
    wacc: float
    terminal_growth_rate: float
    capex_as_pct_revenue: float
    da_as_pct_revenue: float
    shares_outstanding: Optional[float]
    net_debt: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssumptionGenerateRequest(BaseModel):
    """Schema for AI-generated assumptions request."""

    name: Optional[str] = Field(
        default="AI Generated Base Case",
        description="Name for the generated assumption set",
    )
    business_description: Optional[str] = Field(
        default=None,
        description="Optional business description to guide assumption generation",
    )


class ProjectedFinancialsResponse(BaseModel):
    """Schema for a single year of projected financials."""

    year: int
    revenue: float
    gross_profit: float
    operating_income: float
    ebitda: float
    net_income: float
    free_cash_flow: float
    eps: float
    capex: float
    depreciation_amortization: float

    model_config = {"from_attributes": True}


class ModelOutputResponse(BaseModel):
    """Schema for model output from projection engine."""

    ticker: str
    assumption_set_name: str
    projection_years: int
    projections: list[ProjectedFinancialsResponse]
    base_year_revenue: float
    base_year: int

    model_config = {"from_attributes": True}


class DCFResultResponse(BaseModel):
    """Schema for DCF valuation result."""

    ticker: str
    assumption_set_name: str
    enterprise_value: float
    equity_value: float
    per_share_value: float
    terminal_value: float
    pv_of_fcfs: float
    pv_of_terminal: float
    upside_pct: float
    wacc: float
    terminal_growth_rate: float
    current_price: float
    projection_years: int

    model_config = {"from_attributes": True}
