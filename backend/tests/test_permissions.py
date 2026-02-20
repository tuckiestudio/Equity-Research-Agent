"""
Tests for tier-based access control and permissions.
"""
from __future__ import annotations

import pytest
from fastapi import status

from app.core.errors import AppError
from app.models.user import User
from app.services.permissions import (
    Feature,
    Tier,
    check_limits,
    create_require_feature_dependency,
    create_require_tier_dependency,
    has_feature_access,
    require_dcf_custom,
    require_premium,
    require_pro,
    require_scenarios,
)


@pytest.fixture
def free_user():
    """Create a free tier user."""
    user = User(
        id="user-free",
        email="free@example.com",
        full_name="Free User",
        tier="free",
        is_active=True,
    )
    return user


@pytest.fixture
def pro_user():
    """Create a pro tier user."""
    user = User(
        id="user-pro",
        email="pro@example.com",
        full_name="Pro User",
        tier="pro",
        is_active=True,
    )
    return user


@pytest.fixture
def premium_user():
    """Create a premium tier user."""
    user = User(
        id="user-premium",
        email="premium@example.com",
        full_name="Premium User",
        tier="premium",
        is_active=True,
    )
    return user


class TestFeatureAccess:
    """Test feature access by tier."""

    def test_free_user_has_basic_features(self, free_user):
        """Free users have access to basic features."""
        assert has_feature_access(free_user, Feature.STOCK_SEARCH)
        assert has_feature_access(free_user, Feature.STOCK_DETAIL)
        assert has_feature_access(free_user, Feature.PORTFOLIO_CREATE)
        assert has_feature_access(free_user, Feature.DCF_MODEL)
        assert has_feature_access(free_user, Feature.RESEARCH_NOTES)
        assert has_feature_access(free_user, Feature.WATCH_LISTS)

    def test_free_user_lacks_advanced_features(self, free_user):
        """Free users don't have access to advanced features."""
        assert not has_feature_access(free_user, Feature.STOCK_FUNDAMENTALS)
        assert not has_feature_access(free_user, Feature.STOCK_NEWS)
        assert not has_feature_access(free_user, Feature.DCF_CUSTOM_ASSUMPTIONS)
        assert not has_feature_access(free_user, Feature.DCF_SCENARIOS)
        assert not has_feature_access(free_user, Feature.COMPS_ANALYSIS)
        assert not has_feature_access(free_user, Feature.AI_THESIS_GENERATION)
        assert not has_feature_access(free_user, Feature.PORTFOLIO_EXPORT)

    def test_pro_user_has_free_and_pro_features(self, pro_user):
        """Pro users have access to Free + Pro features."""
        # All free features
        assert has_feature_access(pro_user, Feature.STOCK_SEARCH)
        assert has_feature_access(pro_user, Feature.STOCK_DETAIL)
        assert has_feature_access(pro_user, Feature.PORTFOLIO_CREATE)

        # Pro features
        assert has_feature_access(pro_user, Feature.STOCK_FUNDAMENTALS)
        assert has_feature_access(pro_user, Feature.STOCK_NEWS)
        assert has_feature_access(pro_user, Feature.PORTFOLIO_MULTIPLE)
        assert has_feature_access(pro_user, Feature.DCF_CUSTOM_ASSUMPTIONS)
        assert has_feature_access(pro_user, Feature.DCF_SCENARIOS)
        assert has_feature_access(pro_user, Feature.COMPS_ANALYSIS)
        assert has_feature_access(pro_user, Feature.AI_SENTIMENT_ANALYSIS)
        assert has_feature_access(pro_user, Feature.HISTORICAL_DATA)

    def test_pro_user_lacks_premium_features(self, pro_user):
        """Pro users don't have access to Premium-only features."""
        assert not has_feature_access(pro_user, Feature.AI_THESIS_GENERATION)
        assert not has_feature_access(pro_user, Feature.AI_NEWS_ANALYSIS)
        assert not has_feature_access(pro_user, Feature.REAL_TIME_DATA)
        assert not has_feature_access(pro_user, Feature.ANALYST_ESTIMATES)
        assert not has_feature_access(pro_user, Feature.PORTFOLIO_EXPORT)
        assert not has_feature_access(pro_user, Feature.ALERTS)

    def test_premium_user_has_all_features(self, premium_user):
        """Premium users have access to all features."""
        # Sample features from each category
        assert has_feature_access(premium_user, Feature.STOCK_SEARCH)
        assert has_feature_access(premium_user, Feature.STOCK_FUNDAMENTALS)
        assert has_feature_access(premium_user, Feature.DCF_CUSTOM_ASSUMPTIONS)
        assert has_feature_access(premium_user, Feature.AI_THESIS_GENERATION)
        assert has_feature_access(premium_user, Feature.REAL_TIME_DATA)
        assert has_feature_access(premium_user, Feature.PORTFOLIO_EXPORT)
        assert has_feature_access(premium_user, Feature.ALERTS)


class TestTierLimits:
    """Test tier limits."""

    def test_free_user_limits(self, free_user):
        """Free users have basic limits."""
        assert check_limits(free_user, "portfolios") == 1
        assert check_limits(free_user, "stocks") == 10
        assert check_limits(free_user, "watch_lists") == 1
        assert check_limits(free_user, "notes") == 5

    def test_pro_user_limits(self, pro_user):
        """Pro users have higher limits."""
        assert check_limits(pro_user, "portfolios") == 5
        assert check_limits(pro_user, "stocks") == 50
        assert check_limits(pro_user, "watch_lists") == 10
        assert check_limits(pro_user, "notes") == 50

    def test_premium_user_unlimited_limits(self, premium_user):
        """Premium users have unlimited limits (-1)."""
        assert check_limits(premium_user, "portfolios") == -1
        assert check_limits(premium_user, "stocks") == -1
        assert check_limits(premium_user, "watch_lists") == -1
        assert check_limits(premium_user, "notes") == -1


class TestRequireTierDependency:
    """Test tier requirement dependencies."""

    @pytest.mark.asyncio
    async def test_free_user_can_access_free_endpoint(self, free_user):
        """Free users can access free-tier endpoints."""
        dependency = create_require_tier_dependency(Tier.FREE)
        result = await dependency(free_user)
        assert result == free_user

    @pytest.mark.asyncio
    async def test_pro_user_can_access_free_endpoint(self, pro_user):
        """Pro users can access free-tier endpoints."""
        dependency = create_require_tier_dependency(Tier.FREE)
        result = await dependency(pro_user)
        assert result == pro_user

    @pytest.mark.asyncio
    async def test_free_user_cannot_access_pro_endpoint(self, free_user):
        """Free users cannot access pro-tier endpoints."""
        dependency = create_require_tier_dependency(Tier.PRO)
        with pytest.raises(AppError) as exc_info:
            await dependency(free_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.code == "INSUFFICIENT_TIER"
        assert "requires pro tier" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_pro_user_can_access_pro_endpoint(self, pro_user):
        """Pro users can access pro-tier endpoints."""
        dependency = create_require_tier_dependency(Tier.PRO)
        result = await dependency(pro_user)
        assert result == pro_user

    @pytest.mark.asyncio
    async def test_free_user_cannot_access_premium_endpoint(self, free_user):
        """Free users cannot access premium-tier endpoints."""
        dependency = create_require_tier_dependency(Tier.PREMIUM)
        with pytest.raises(AppError) as exc_info:
            await dependency(free_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.code == "INSUFFICIENT_TIER"

    @pytest.mark.asyncio
    async def test_pro_user_cannot_access_premium_endpoint(self, pro_user):
        """Pro users cannot access premium-tier endpoints."""
        dependency = create_require_tier_dependency(Tier.PREMIUM)
        with pytest.raises(AppError) as exc_info:
            await dependency(pro_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.code == "INSUFFICIENT_TIER"

    @pytest.mark.asyncio
    async def test_premium_user_can_access_premium_endpoint(self, premium_user):
        """Premium users can access premium-tier endpoints."""
        dependency = create_require_tier_dependency(Tier.PREMIUM)
        result = await dependency(premium_user)
        assert result == premium_user


class TestRequireFeatureDependency:
    """Test feature requirement dependencies."""

    @pytest.mark.asyncio
    async def test_free_user_with_basic_feature(self, free_user):
        """Free users can access basic features."""
        dependency = create_require_feature_dependency(Feature.STOCK_SEARCH)
        result = await dependency(free_user)
        assert result == free_user

    @pytest.mark.asyncio
    async def test_free_user_without_advanced_feature(self, free_user):
        """Free users cannot access advanced features."""
        dependency = create_require_feature_dependency(Feature.DCF_CUSTOM_ASSUMPTIONS)
        with pytest.raises(AppError) as exc_info:
            await dependency(free_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.code == "FEATURE_NOT_AVAILABLE"
        assert "not available in your current tier" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_pro_user_with_pro_feature(self, pro_user):
        """Pro users can access pro features."""
        dependency = create_require_feature_dependency(Feature.DCF_CUSTOM_ASSUMPTIONS)
        result = await dependency(pro_user)
        assert result == pro_user

    @pytest.mark.asyncio
    async def test_premium_user_with_any_feature(self, premium_user):
        """Premium users can access any feature."""
        dependency = create_require_feature_dependency(Feature.AI_THESIS_GENERATION)
        result = await dependency(premium_user)
        assert result == premium_user


class TestConvenienceDependencies:
    """Test pre-configured convenience dependencies."""

    @pytest.mark.asyncio
    async def test_require_pro_blocks_free_user(self, free_user):
        """require_pro dependency blocks free users."""
        with pytest.raises(AppError) as exc_info:
            await require_pro(free_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_require_pro_allows_pro_user(self, pro_user):
        """require_pro dependency allows pro users."""
        result = await require_pro(pro_user)
        assert result == pro_user

    @pytest.mark.asyncio
    async def test_require_premium_blocks_pro_user(self, pro_user):
        """require_premium dependency blocks pro users."""
        with pytest.raises(AppError) as exc_info:
            await require_premium(pro_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_require_dcf_custom_blocks_free_user(self, free_user):
        """require_dcf_custom dependency blocks free users."""
        with pytest.raises(AppError) as exc_info:
            await require_dcf_custom(free_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_require_scenarios_allows_pro_user(self, pro_user):
        """require_scenarios dependency allows pro users."""
        result = await require_scenarios(pro_user)
        assert result == pro_user
