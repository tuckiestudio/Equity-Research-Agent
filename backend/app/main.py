"""
Equity Research Agent - FastAPI Application
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown tasks."""
    logger.info(
        "Starting Equity Research Agent API | env=%s | fundamentals=%s | prices=%s",
        settings.APP_ENV,
        settings.FUNDAMENTALS_PROVIDER,
        settings.PRICE_PROVIDER,
    )

    # Start background task scheduler
    from app.tasks.scheduler import start_scheduler, stop_scheduler
    from app.services.data.registry import initialize_providers
    try:
        initialize_providers()
        logger.info("Data providers initialized")
        await start_scheduler()
        logger.info("Background task scheduler started")
    except Exception as e:
        logger.error(f"Failed to start background task scheduler: {e}")

    yield

    # Stop background task scheduler
    try:
        await stop_scheduler()
        logger.info("Background task scheduler stopped")
    except Exception as e:
        logger.error(f"Failed to stop background task scheduler: {e}")

    logger.info("Shutting down Equity Research Agent API")


app = FastAPI(
    title="Equity Research Agent API",
    description="AI-powered equity research and analysis platform",
    version="0.1.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Explicit methods for security
    allow_headers=["Authorization", "Content-Type"],  # Only necessary headers
)

# Configure rate limiting
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.limiter import limiter

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests",
                "errors": [],
            }
        },
    )

# Register structured error handlers
register_error_handlers(app)

# Mount versioned API router
from app.api.v1.router import api_v1_router

app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Equity Research Agent API", "version": "0.1.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint (outside versioned API for infra probes)."""
    return {"status": "healthy"}
