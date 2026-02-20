"""
API v1 router — aggregates all versioned endpoint routers.
"""
from __future__ import annotations

from fastapi import APIRouter

api_v1_router = APIRouter()


@api_v1_router.get("/health")
async def health_v1() -> dict[str, str]:
    """Versioned health check."""
    return {"status": "healthy", "version": "v1"}
