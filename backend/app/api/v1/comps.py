"""Comps API endpoints — comparable analysis and suggestions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.services.model.comp_suggestions import CompSuggestion, CompSuggestionEngine
from app.services.model.comps import CompsEngine, CompsResult

router = APIRouter(prefix="/comps", tags=["comps"])


@router.get("/{ticker}/suggest", response_model=list[CompSuggestion])
async def suggest_comps(
    ticker: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
) -> list[CompSuggestion]:
    """Suggest comparable companies for a target ticker."""
    _ = current_user
    engine = CompSuggestionEngine()
    return await engine.suggest_peers(ticker=ticker, limit=limit)


@router.post("/{ticker}/analyze", response_model=CompsResult)
async def analyze_comps(
    ticker: str,
    peers: list[str],
    current_user: User = Depends(get_current_user),
) -> CompsResult:
    """Analyze comparable companies using the CompsEngine."""
    _ = current_user
    engine = CompsEngine()
    return await engine.analyze(target_ticker=ticker, peers=peers)
