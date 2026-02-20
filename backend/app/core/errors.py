"""
Structured error handling for the application.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error with structured response format."""

    def __init__(
        self,
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
        detail: str = "An unexpected error occurred",
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.errors = errors or []
        super().__init__(self.detail)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            status_code=404,
            code=f"{resource.upper()}_NOT_FOUND",
            detail=f"{resource} '{identifier}' not found",
        )


class ValidationError(AppError):
    """Request validation error."""

    def __init__(self, detail: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            status_code=422,
            code="VALIDATION_ERROR",
            detail=detail,
            errors=errors,
        )


class AuthenticationError(AppError):
    """Authentication failed."""

    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(
            status_code=401,
            code="AUTHENTICATION_ERROR",
            detail=detail,
        )


class AuthorizationError(AppError):
    """Insufficient permissions."""

    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(
            status_code=403,
            code="AUTHORIZATION_ERROR",
            detail=detail,
        )


class ProviderError(AppError):
    """External data/AI provider error."""

    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(
            status_code=502,
            code="PROVIDER_ERROR",
            detail=f"[{provider}] {detail}",
        )


class RateLimitError(AppError):
    """Rate limit exceeded."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            detail=f"Rate limit exceeded for {provider}",
        )


def register_error_handlers(app: FastAPI) -> None:
    """Register structured error handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.detail,
                    "errors": exc.errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "errors": [],
                }
            },
        )
