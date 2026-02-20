"""
Tier-based access control and permissions.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Literal

from fastapi import status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.models.user import User

if TYPE_CHECKING:
    pass

# Security scheme for API documentation
security = HTTPBearer(auto_error=False)


class Tier(str, Enum):
    """User subscription tiers."""

    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class Feature(str, Enum):
    """Features that can be gated by tier."""

    # Stock Analysis Features
    STOCK_SEARCH = "stock_search"
    STOCK_DETAIL = "stock_detail"
    STOCK_FUNDAMENTALS = "stock_fundamentals"
    STOCK_NEWS = "stock_news"

    # Portfolio Features
    PORTFOLIO_CREATE = "portfolio_create"
    PORTFOLIO_MULTIPLE = "portfolio_multiple"
    PORTFOLIO_EXPORT = "portfolio_export"

    # Model Features
    DCF_MODEL = "dcf_model"
    DCF_CUSTOM_ASSUMPTIONS = "dcf_custom_assumptions"
    DCF_SCENARIOS = "dcf_scenarios"
    COMPS_ANALYSIS = "comps_analysis"

    # AI Features
    AI_THESIS_GENERATION = "ai_thesis_generation"
    AI_SENTIMENT_ANALYSIS = "ai_sentiment_analysis"
    AI_NEWS_ANALYSIS = "ai_news_analysis"

    # Data Features
    REAL_TIME_DATA = "real_time_data"
    HISTORICAL_DATA = "historical_data"
    ANALYST_ESTIMATES = "analyst_estimates"

    # Research Features
    RESEARCH_NOTES = "research_notes"
    WATCH_LISTS = "watch_lists"
    ALERTS = "alerts"


# Define feature sets for each tier to avoid forward reference issues
FREE_FEATURES: set[Feature] = {
    # Stock Analysis - Limited
    Feature.STOCK_SEARCH,
    Feature.STOCK_DETAIL,
    # Portfolio - Basic
    Feature.PORTFOLIO_CREATE,
    # Model - Basic DCF
    Feature.DCF_MODEL,
    # Research - Limited
    Feature.RESEARCH_NOTES,
    Feature.WATCH_LISTS,
}

PRO_FEATURES: set[Feature] = {
    # All Free features
    *FREE_FEATURES,
    # Stock Analysis - Extended
    Feature.STOCK_FUNDAMENTALS,
    Feature.STOCK_NEWS,
    # Portfolio - Extended
    Feature.PORTFOLIO_MULTIPLE,
    # Model - Advanced
    Feature.DCF_CUSTOM_ASSUMPTIONS,
    Feature.DCF_SCENARIOS,
    Feature.COMPS_ANALYSIS,
    # AI - Basic
    Feature.AI_SENTIMENT_ANALYSIS,
    # Data - Extended
    Feature.HISTORICAL_DATA,
}

PREMIUM_FEATURES: set[Feature] = {
    # All Pro features
    *PRO_FEATURES,
    # AI - Full
    Feature.AI_THESIS_GENERATION,
    Feature.AI_NEWS_ANALYSIS,
    # Data - Full
    Feature.REAL_TIME_DATA,
    Feature.ANALYST_ESTIMATES,
    # Portfolio - Full
    Feature.PORTFOLIO_EXPORT,
    # Research - Full
    Feature.ALERTS,
}

# Tier feature matrix
TIER_FEATURES: dict[Tier, set[Feature]] = {
    Tier.FREE: FREE_FEATURES,
    Tier.PRO: PRO_FEATURES,
    Tier.PREMIUM: PREMIUM_FEATURES,
}


class TierLimits(BaseModel):
    """Usage limits per tier."""

    max_portfolios: int = Field(default=1, description="Maximum number of portfolios")
    max_stocks_per_portfolio: int = Field(default=10, description="Maximum stocks per portfolio")
    max_watch_lists: int = Field(default=1, description="Maximum number of watch lists")
    max_notes_per_stock: int = Field(default=5, description="Maximum research notes per stock")
    api_calls_per_day: int = Field(default=100, description="API calls per day limit")


TIER_LIMITS: dict[Tier, TierLimits] = {
    Tier.FREE: TierLimits(
        max_portfolios=1,
        max_stocks_per_portfolio=10,
        max_watch_lists=1,
        max_notes_per_stock=5,
        api_calls_per_day=100,
    ),
    Tier.PRO: TierLimits(
        max_portfolios=5,
        max_stocks_per_portfolio=50,
        max_watch_lists=10,
        max_notes_per_stock=50,
        api_calls_per_day=1000,
    ),
    Tier.PREMIUM: TierLimits(
        max_portfolios=-1,  # Unlimited
        max_stocks_per_portfolio=-1,  # Unlimited
        max_watch_lists=-1,  # Unlimited
        max_notes_per_stock=-1,  # Unlimited
        api_calls_per_day=-1,  # Unlimited
    ),
}


def has_feature_access(user: User, feature: Feature) -> bool:
    """Check if user's tier has access to a feature."""
    try:
        user_tier = Tier(user.tier)
    except (ValueError, KeyError):
        user_tier = Tier.FREE
    return feature in TIER_FEATURES.get(user_tier, set())


def check_limits(user: User, limit_type: Literal["portfolios", "stocks", "watch_lists", "notes"]) -> int:
    """
    Check user's tier limit for a specific resource type.

    Returns the maximum allowed count (-1 for unlimited).
    """
    try:
        user_tier = Tier(user.tier)
    except (ValueError, KeyError):
        user_tier = Tier.FREE
    limits = TIER_LIMITS.get(user_tier, TIER_LIMITS[Tier.FREE])

    limit_map = {
        "portfolios": limits.max_portfolios,
        "stocks": limits.max_stocks_per_portfolio,
        "watch_lists": limits.max_watch_lists,
        "notes": limits.max_notes_per_stock,
    }

    return limit_map.get(limit_type, -1)


def create_require_tier_dependency(minimum_tier: Tier = Tier.FREE):
    """
    Create a dependency that enforces minimum tier requirement.

    Usage:
        from app.services.permissions import Tier, create_require_tier_dependency
        from app.api.deps import get_current_user

        @router.get("/premium-feature")
        async def premium_feature(
            user: User = Depends(get_current_user),
            _=Depends(create_require_tier_dependency(Tier.PRO))
        ):
            return {"message": "This is a Pro feature"}
    """

    async def check_tier(current_user: User) -> User:
        try:
            user_tier = Tier(current_user.tier)
        except (ValueError, KeyError):
            user_tier = Tier.FREE

        # Define tier hierarchy
        tier_hierarchy = {Tier.FREE: 0, Tier.PRO: 1, Tier.PREMIUM: 2}

        if tier_hierarchy[user_tier] < tier_hierarchy[minimum_tier]:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="INSUFFICIENT_TIER",
                detail=f"This feature requires {minimum_tier.value} tier or higher. "
                f"Your current tier: {user_tier.value}.",
            )

        return current_user

    return check_tier


def create_require_feature_dependency(feature: Feature):
    """
    Create a dependency that enforces specific feature access.

    Usage:
        from app.services.permissions import Feature, create_require_feature_dependency
        from app.api.deps import get_current_user

        @router.get("/dcf-custom")
        async def custom_dcf(
            user: User = Depends(get_current_user),
            _=Depends(create_require_feature_dependency(Feature.DCF_CUSTOM_ASSUMPTIONS))
        ):
            return {"message": "Custom DCF assumptions"}
    """

    async def check_feature(current_user: User) -> User:
        if not has_feature_access(current_user, feature):
            try:
                user_tier = Tier(current_user.tier)
            except (ValueError, KeyError):
                user_tier = Tier.FREE
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FEATURE_NOT_AVAILABLE",
                detail=f"The '{feature.value}' feature is not available in your current tier. "
                f"Upgrade to Pro or Premium to access this feature.",
            )

        return current_user

    return check_feature


# Convenience functions for common tier requirements
require_pro = create_require_tier_dependency(Tier.PRO)
require_premium = create_require_tier_dependency(Tier.PREMIUM)
require_free = create_require_tier_dependency(Tier.FREE)


# Convenience functions for common feature requirements
require_dcf_custom = create_require_feature_dependency(Feature.DCF_CUSTOM_ASSUMPTIONS)
require_scenarios = create_require_feature_dependency(Feature.DCF_SCENARIOS)
require_comps = create_require_feature_dependency(Feature.COMPS_ANALYSIS)
require_ai_thesis = create_require_feature_dependency(Feature.AI_THESIS_GENERATION)
require_portfolio_export = create_require_feature_dependency(Feature.PORTFOLIO_EXPORT)
require_alerts = create_require_feature_dependency(Feature.ALERTS)
