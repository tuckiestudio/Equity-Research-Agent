"""
API v1 router — aggregates all versioned endpoint routers.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.assumptions import router as assumptions_router
from app.api.v1.auth import router as auth_router
from app.api.v1.comps import router as comps_router
from app.api.v1.export import router as export_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.market import router as market_router
from app.api.v1.news import router as news_router
from app.api.v1.notes import router as notes_router
from app.api.v1.portfolios import router as portfolios_router
from app.api.v1.scenarios import router as scenarios_router
from app.api.v1.settings import router as settings_router
from app.api.v1.stocks import router as stocks_router
from app.api.v1.thesis import router as thesis_router
from app.api.v1.tiers import router as tiers_router
from app.api.v1.watch import router as watch_router
from app.api.v1.waterfall import router as waterfall_router

api_v1_router = APIRouter()

# Include sub-routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tiers_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(stocks_router)
api_v1_router.include_router(portfolios_router)
api_v1_router.include_router(assumptions_router)
api_v1_router.include_router(scenarios_router)
api_v1_router.include_router(export_router)
api_v1_router.include_router(news_router)
api_v1_router.include_router(notes_router)
api_v1_router.include_router(comps_router)
api_v1_router.include_router(thesis_router)
api_v1_router.include_router(watch_router)
api_v1_router.include_router(waterfall_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(market_router)


@api_v1_router.get("/health")
async def health_v1() -> dict[str, str]:
    """Versioned health check."""
    return {"status": "healthy", "version": "v1"}
