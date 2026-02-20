"""
Example: Tier-protected scenarios endpoint.
This demonstrates how to use the tier gating system.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.scenario import Scenario
from app.models.user import User
from app.services.permissions import (
    Feature,
    Tier,
    create_require_feature_dependency,
    create_require_tier_dependency,
)

router = APIRouter(prefix="/scenarios-protected", tags=["scenarios-protected"])


# --- Request/Response Schemas ---

class ScenarioRequest(BaseModel):
    """Request to create a scenario."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    ticker: str = Field(..., min_length=1, max_length=10)


class ScenarioResponse(BaseModel):
    """Scenario response."""

    id: str
    name: str
    description: Optional[str]
    ticker: str
    user_id: str

    model_config = {"from_attributes": True}


# --- Example 1: Require Pro Tier or Higher ---

@router.get("/pro-feature", response_model=dict)
async def pro_only_feature(
    _: User = Depends(get_current_user),
    __=Depends(create_require_tier_dependency(Tier.PRO)),
) -> dict:
    """
    This endpoint requires Pro tier or higher.

    Usage:
        - Free users will get 403 Forbidden
        - Pro and Premium users can access
    """
    return {
        "message": "This is a Pro feature",
        "tier": "pro or higher",
    }


# --- Example 2: Require Specific Feature ---

@router.post("/create-scenario", response_model=ScenarioResponse, status_code=201)
async def create_scenario(
    body: ScenarioRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(create_require_feature_dependency(Feature.DCF_SCENARIOS)),
) -> Scenario:
    """
    Create a valuation scenario.

    This endpoint requires the DCF_SCENARIOS feature, which is available to:
    - Pro users
    - Premium users

    Free users will receive a 403 error with upgrade instructions.
    """
    scenario = Scenario(
        name=body.name,
        description=body.description,
        ticker=body.ticker,
        user_id=current_user.id,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)

    return scenario


# --- Example 3: Using Pre-configured Feature Dependencies ---

from app.services.permissions import require_ai_thesis, require_comps, require_dcf_custom


@router.get("/advanced-dcf")
async def advanced_dcf_features(
    current_user: User = Depends(get_current_user),
    _=Depends(require_dcf_custom),
) -> dict:
    """
    Advanced DCF features endpoint.

    Uses the pre-configured `require_dcf_custom` dependency.
    """
    return {
        "message": "Access to advanced DCF features granted",
        "user_tier": current_user.tier,
    }


@router.get("/comparable-analysis")
async def comparable_companies_analysis(
    current_user: User = Depends(get_current_user),
    _=Depends(require_comps),
) -> dict:
    """
    Comparable companies analysis endpoint.

    Uses the pre-configured `require_comps` dependency.
    """
    return {
        "message": "Access to comparable companies analysis granted",
        "user_tier": current_user.tier,
    }


@router.post("/generate-thesis")
async def generate_investment_thesis(
    current_user: User = Depends(get_current_user),
    _=Depends(require_ai_thesis),
) -> dict:
    """
    Generate AI-powered investment thesis.

    Uses the pre-configured `require_ai_thesis` dependency.
    This is a Premium-only feature.
    """
    return {
        "message": "AI thesis generation enabled",
        "user_tier": current_user.tier,
    }


# --- Example 4: Conditional Feature Access ---

@router.get("/check-feature-access")
async def check_feature_access(
    feature: Feature,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Check if current user has access to a specific feature.

    This demonstrates programmatic feature checking without blocking.
    """
    from app.services.permissions import has_feature_access

    has_access = has_feature_access(current_user, feature)

    return {
        "feature": feature.value,
        "has_access": has_access,
        "user_tier": current_user.tier,
        "required_tier": _get_minimum_tier_for_feature(feature),
    }


def _get_minimum_tier_for_feature(feature: Feature) -> str:
    """Helper to determine minimum tier for a feature."""
    from app.services.permissions import TIER_FEATURES

    if feature in TIER_FEATURES[Tier.FREE]:
        return "free"
    elif feature in TIER_FEATURES[Tier.PRO]:
        return "pro"
    else:
        return "premium"


# --- Example 5: Checking Limits ---

@router.get("/check-limits")
async def check_user_limits(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get current user's tier limits.

    This demonstrates how to check usage limits per tier.
    """
    from app.services.permissions import check_limits

    return {
        "user_tier": current_user.tier,
        "limits": {
            "max_portfolios": check_limits(current_user, "portfolios"),
            "max_stocks_per_portfolio": check_limits(current_user, "stocks"),
            "max_watch_lists": check_limits(current_user, "watch_lists"),
            "max_notes_per_stock": check_limits(current_user, "notes"),
        }
    }
