"""
Tier management API endpoints — for admins to manage user tiers.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError, NotFoundError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.services.permissions import Tier, check_limits

logger = get_logger(__name__)

router = APIRouter(prefix="/tiers", tags=["tiers"])


# --- Request/Response Schemas ---

class UpdateUserTierRequest(BaseModel):
    """Request to update a user's tier."""

    tier: Tier = Field(..., description="New tier for the user")
    reason: Optional[str] = Field(None, description="Reason for tier change (for audit)")


class TierLimitsResponse(BaseModel):
    """Response showing tier limits."""

    tier: str
    max_portfolios: int
    max_stocks_per_portfolio: int
    max_watch_lists: int
    max_notes_per_stock: int
    api_calls_per_day: int

    model_config = {"from_attributes": True}


class UserTierResponse(BaseModel):
    """Response showing user tier info."""

    user_id: str
    email: str
    full_name: Optional[str]
    tier: str
    limits: TierLimitsResponse


# --- Helper Functions ---

def is_admin_user(user: User) -> bool:
    """Check if user has admin privileges via is_admin flag."""
    return getattr(user, 'is_admin', False)


async def get_user_by_id_or_email(
    db: AsyncSession,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    """Get user by ID or email."""
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    elif email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    else:
        raise AppError(400, "MISSING_IDENTIFIER", "Either user_id or email must be provided")

    if not user:
        identifier = user_id or email or "unknown"
        raise NotFoundError("user", identifier)

    return user


# --- Endpoints ---

@router.get("/my-limits", response_model=TierLimitsResponse)
async def get_my_tier_limits(current_user: User = Depends(get_current_user)) -> TierLimitsResponse:
    """Get current user's tier limits."""
    return TierLimitsResponse(
        tier=current_user.tier,
        max_portfolios=check_limits(current_user, "portfolios"),
        max_stocks_per_portfolio=check_limits(current_user, "stocks"),
        max_watch_lists=check_limits(current_user, "watch_lists"),
        max_notes_per_stock=check_limits(current_user, "notes"),
        api_calls_per_day=1000,  # This would come from the limits config
    )


@router.get("/user", response_model=UserTierResponse)
async def get_user_tier(
    user_id: Optional[str] = Query(None, description="User ID to look up"),
    email: Optional[str] = Query(None, description="User email to look up"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserTierResponse:
    """
    Get tier information for a user.

    Users can look up their own tier. Admins can look up any user's tier.
    """
    target_user = await get_user_by_id_or_email(db, user_id, email)

    # Check permissions: users can only view their own tier unless they're admin
    if str(target_user.id) != str(current_user.id) and not is_admin_user(current_user):
        raise AppError(403, "FORBIDDEN", "You can only view your own tier information")

    return UserTierResponse(
        user_id=str(target_user.id),
        email=target_user.email,
        full_name=target_user.full_name,
        tier=target_user.tier,
        limits=TierLimitsResponse(
            tier=target_user.tier,
            max_portfolios=check_limits(target_user, "portfolios"),
            max_stocks_per_portfolio=check_limits(target_user, "stocks"),
            max_watch_lists=check_limits(target_user, "watch_lists"),
            max_notes_per_stock=check_limits(target_user, "notes"),
            api_calls_per_day=1000,
        ),
    )


@router.post("/admin/update-user-tier", response_model=UserTierResponse)
async def update_user_tier(
    body: UpdateUserTierRequest,
    user_id: Optional[str] = Query(None, description="User ID to update"),
    email: Optional[str] = Query(None, description="User email to update"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserTierResponse:
    """
    Update a user's tier (Admin only).

    This endpoint allows administrators to upgrade or downgrade user tiers.
    """
    # Verify current user is admin
    if not is_admin_user(current_user):
        raise AppError(403, "FORBIDDEN", "Only administrators can update user tiers")

    target_user = await get_user_by_id_or_email(db, user_id, email)

    # Update tier
    old_tier = target_user.tier
    target_user.tier = body.tier.value
    await db.commit()

    # Log the tier change (in production, this would go to an audit log)
    logger.info(
        "Tier change: User %s (%s) from %s to %s. Reason: %s",
        target_user.email,
        target_user.id,
        old_tier,
        body.tier.value,
        body.reason,
    )

    return UserTierResponse(
        user_id=str(target_user.id),
        email=target_user.email,
        full_name=target_user.full_name,
        tier=target_user.tier,
        limits=TierLimitsResponse(
            tier=target_user.tier,
            max_portfolios=check_limits(target_user, "portfolios"),
            max_stocks_per_portfolio=check_limits(target_user, "stocks"),
            max_watch_lists=check_limits(target_user, "watch_lists"),
            max_notes_per_stock=check_limits(target_user, "notes"),
            api_calls_per_day=1000,
        ),
    )


@router.get("/admin/users-by-tier", response_model=list[UserTierResponse])
async def get_users_by_tier(
    tier: Tier = Query(..., description="Filter users by tier"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserTierResponse]:
    """
    Get all users in a specific tier (Admin only).
    """
    # Verify current user is admin
    if not is_admin_user(current_user):
        raise AppError(403, "FORBIDDEN", "Only administrators can view users by tier")

    result = await db.execute(select(User).where(User.tier == tier.value))
    users = result.scalars().all()

    return [
        UserTierResponse(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            tier=user.tier,
            limits=TierLimitsResponse(
                tier=user.tier,
                max_portfolios=check_limits(user, "portfolios"),
                max_stocks_per_portfolio=check_limits(user, "stocks"),
                max_watch_lists=check_limits(user, "watch_lists"),
                max_notes_per_stock=check_limits(user, "notes"),
                api_calls_per_day=1000,
            ),
        )
        for user in users
    ]
