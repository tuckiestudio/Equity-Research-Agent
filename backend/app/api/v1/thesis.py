"""Thesis API endpoints — manage investment thesis generation and evolution."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.stock import Stock
from app.models.thesis import Thesis
from app.models.thesis_change import ThesisChange
from app.models.user import User
from app.services.llm.router import LLMRouter
from app.services.thesis.generator import ThesisService

router = APIRouter(prefix="/thesis", tags=["thesis"])


# =============================================================================
# Request Schemas
# =============================================================================


class ThesisUpdateRequest(BaseModel):
    """Request to update thesis with new information."""

    new_information: str = Field(
        ..., description="New information to incorporate (news, earnings, etc.)"
    )


class ThesisManualEdit(BaseModel):
    """Request to manually edit thesis without AI."""

    title: Optional[str] = Field(None, description="Thesis title")
    summary: Optional[str] = Field(None, description="Executive summary")
    full_text: Optional[str] = Field(None, description="Full thesis document")
    stance: Optional[str] = Field(None, description="bullish/bearish/neutral")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_price: Optional[float] = Field(None, description="Price target")


# =============================================================================
# Response Schemas
# =============================================================================


class ThesisResponse(BaseModel):
    """Thesis response schema."""

    id: str
    stock_id: str
    title: str
    summary: str
    full_text: str
    stance: str
    confidence: float
    target_price: Optional[float]
    current_price_at_generation: Optional[float]
    upside_pct: Optional[float]
    version: int
    is_active: bool
    generated_by: str
    llm_model_used: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ThesisChangeResponse(BaseModel):
    """Thesis change audit trail response."""

    id: str
    change_type: str
    previous_stance: Optional[str]
    new_stance: Optional[str]
    previous_target_price: Optional[float]
    new_target_price: Optional[float]
    previous_confidence: Optional[float]
    new_confidence: Optional[float]
    trigger: Optional[str]
    change_summary: str
    version_from: int
    version_to: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ThesisTimelineItem(BaseModel):
    """Timeline entry for thesis evolution."""

    date: datetime
    version: int
    stance: str
    confidence: float
    target_price: Optional[float]
    change_summary: str


# =============================================================================
# Helper Functions
# =============================================================================


async def get_stock_by_ticker(
    ticker: str, db: AsyncSession, user: User
) -> Stock:
    """Get a stock by ticker, raising NotFoundError if missing."""
    result = await db.execute(
        select(Stock).where(Stock.ticker == ticker.upper())
    )
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)
    return stock


async def get_thesis_by_id(
    thesis_id: str, db: AsyncSession, user: User
) -> Thesis:
    """Get thesis by ID, ensuring it belongs to the user."""
    try:
        thesis_uuid = uuid.UUID(thesis_id)
    except ValueError:
        raise NotFoundError("Thesis", thesis_id)

    result = await db.execute(
        select(Thesis).where(
            Thesis.id == thesis_uuid,
            Thesis.user_id == user.id,
        )
    )
    thesis = result.scalar_one_or_none()
    if not thesis:
        raise NotFoundError("Thesis", thesis_id)
    return thesis


def db_to_response(thesis: Thesis) -> ThesisResponse:
    """Convert database model to response schema."""
    return ThesisResponse(
        id=str(thesis.id),
        stock_id=str(thesis.stock_id),
        title=thesis.title,
        summary=thesis.summary,
        full_text=thesis.full_text,
        stance=thesis.stance,
        confidence=thesis.confidence,
        target_price=thesis.target_price,
        current_price_at_generation=thesis.current_price_at_generation,
        upside_pct=thesis.upside_pct,
        version=thesis.version,
        is_active=thesis.is_active,
        generated_by=thesis.generated_by,
        llm_model_used=thesis.llm_model_used,
        created_at=thesis.created_at,
        updated_at=thesis.updated_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/{ticker}/generate", response_model=ThesisResponse)
async def generate_thesis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThesisResponse:
    """Generate a new investment thesis for a stock.

    This endpoint:
    1. Fetches company profile, financials, and recent news
    2. Uses LLM to generate a comprehensive investment thesis
    3. Deactivates any existing active thesis for this stock
    4. Saves the new thesis with version=1
    5. Creates an audit trail entry
    """
    stock = await get_stock_by_ticker(ticker, db, current_user)

    # Initialize LLM router and thesis service
    # In production, these would be singletons at app startup
    llm_router = LLMRouter()
    # TODO: Register providers from app startup
    # For now, the service will use whatever providers are registered

    service = ThesisService(llm_router)

    thesis = await service.generate_thesis(
        ticker=ticker.upper(),
        stock_id=stock.id,
        user_id=current_user.id,
        db=db,
        user_settings=current_user.settings,
    )

    return db_to_response(thesis)


@router.get("/{ticker}", response_model=ThesisResponse)
async def get_active_thesis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThesisResponse:
    """Get the active investment thesis for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    llm_router = LLMRouter()
    service = ThesisService(llm_router)

    thesis = await service.get_active_thesis(
        stock_id=stock.id,
        user_id=current_user.id,
        db=db,
    )

    if not thesis:
        raise NotFoundError("Thesis", f"active thesis for {ticker}")

    return db_to_response(thesis)


@router.put("/{thesis_id}/update", response_model=ThesisResponse)
async def update_thesis(
    thesis_id: str,
    update_data: ThesisUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThesisResponse:
    """Update an existing thesis with new information.

    This endpoint:
    1. Fetches the existing thesis
    2. Uses LLM to update the thesis based on new information
    3. Detects changes (stance, target, confidence)
    4. Increments version and creates audit trail entry
    """
    thesis = await get_thesis_by_id(thesis_id, db, current_user)

    llm_router = LLMRouter()
    service = ThesisService(llm_router)

    updated_thesis = await service.update_thesis(
        thesis_id=thesis.id,
        new_information=update_data.new_information,
        user_id=current_user.id,
        db=db,
    )

    return db_to_response(updated_thesis)


@router.get("/{thesis_id}/history", response_model=list[ThesisChangeResponse])
async def get_thesis_history(
    thesis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThesisChangeResponse]:
    """Get the audit trail for a thesis."""
    thesis = await get_thesis_by_id(thesis_id, db, current_user)

    # Get all changes for this thesis
    result = await db.execute(
        select(ThesisChange)
        .where(ThesisChange.thesis_id == thesis.id)
        .order_by(ThesisChange.created_at.desc())
    )
    changes = result.scalars().all()

    return [
        ThesisChangeResponse(
            id=str(change.id),
            change_type=change.change_type,
            previous_stance=change.previous_stance,
            new_stance=change.new_stance,
            previous_target_price=change.previous_target_price,
            new_target_price=change.new_target_price,
            previous_confidence=change.previous_confidence,
            new_confidence=change.new_confidence,
            trigger=change.trigger,
            change_summary=change.change_summary,
            version_from=change.version_from,
            version_to=change.version_to,
            created_at=change.created_at,
        )
        for change in changes
    ]


@router.get("/{ticker}/timeline", response_model=list[ThesisTimelineItem])
async def get_thesis_timeline(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThesisTimelineItem]:
    """Get the evolution timeline for a stock's thesis.

    Returns all thesis versions with their key metrics,
    useful for visualizing how the thesis has evolved over time.
    """
    stock = await get_stock_by_ticker(ticker, db, current_user)

    llm_router = LLMRouter()
    service = ThesisService(llm_router)

    timeline = await service.get_thesis_timeline(
        stock_id=stock.id,
        user_id=current_user.id,
        db=db,
    )

    return [
        ThesisTimelineItem(
            date=item["date"],
            version=item["version"],
            stance=item["stance"],
            confidence=item["confidence"],
            target_price=item["target_price"],
            change_summary=item["change_summary"],
        )
        for item in timeline
    ]


@router.put("/{thesis_id}", response_model=ThesisResponse)
async def manual_edit_thesis(
    thesis_id: str,
    edit_data: ThesisManualEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThesisResponse:
    """Manually edit a thesis without AI.

    This allows direct editing of thesis fields.
    Changes are logged in the audit trail.
    """
    thesis = await get_thesis_by_id(thesis_id, db, current_user)

    # Track old values for audit
    old_stance = thesis.stance
    old_target = thesis.target_price
    old_confidence = thesis.confidence
    old_version = thesis.version

    # Update fields
    if edit_data.title is not None:
        thesis.title = edit_data.title
    if edit_data.summary is not None:
        thesis.summary = edit_data.summary
    if edit_data.full_text is not None:
        thesis.full_text = edit_data.full_text
    if edit_data.stance is not None:
        thesis.stance = edit_data.stance
    if edit_data.confidence is not None:
        thesis.confidence = edit_data.confidence
    if edit_data.target_price is not None:
        thesis.target_price = edit_data.target_price

    thesis.version += 1
    thesis.generated_by = "manual"

    # Recalculate upside percentage
    if thesis.target_price and thesis.current_price_at_generation:
        thesis.upside_pct = (
            (thesis.target_price - thesis.current_price_at_generation)
            / thesis.current_price_at_generation
        ) * 100

    await db.commit()
    await db.refresh(thesis)

    # Create change record
    changes = []
    if old_stance != thesis.stance:
        changes.append(f"stance: {old_stance} → {thesis.stance}")
    if old_target != thesis.target_price:
        changes.append(f"target: ${old_target} → ${thesis.target_price}")
    if abs(old_confidence - thesis.confidence) > 0.01:
        changes.append(f"confidence: {old_confidence:.2f} → {thesis.confidence:.2f}")

    change_summary = "Manual edit: " + ", ".join(changes) if changes else "Manual edit"

    change = ThesisChange(
        thesis_id=thesis.id,
        user_id=current_user.id,
        change_type="full_rewrite" if edit_data.full_text else "manual_edit",
        previous_stance=old_stance if old_stance != thesis.stance else None,
        new_stance=thesis.stance if old_stance != thesis.stance else None,
        previous_target_price=old_target if old_target != thesis.target_price else None,
        new_target_price=thesis.target_price if old_target != thesis.target_price else None,
        previous_confidence=old_confidence if abs(old_confidence - thesis.confidence) > 0.01 else None,
        new_confidence=thesis.confidence if abs(old_confidence - thesis.confidence) > 0.01 else None,
        trigger=None,
        change_summary=change_summary,
        version_from=old_version,
        version_to=thesis.version,
    )
    db.add(change)
    await db.commit()

    return db_to_response(thesis)
