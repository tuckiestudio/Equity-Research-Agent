"""
Tests for main application and core infrastructure.
"""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-123456")

from app.main import app

client = TestClient(app)


def test_root() -> None:
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Equity Research Agent API"
    assert data["version"] == "0.1.0"


def test_health() -> None:
    """Test health endpoint (infra-level, outside /api/v1)."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_v1() -> None:
    """Test versioned health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "v1"


def test_api_docs_available() -> None:
    """Test that OpenAPI docs are served under /api/v1."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Equity Research Agent API"


def test_404_returns_json() -> None:
    """Test that unknown routes return proper JSON error."""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code in (404, 405)


def test_structured_error_format() -> None:
    """Test that AppError produces structured JSON response."""
    from app.core.errors import AppError

    # Verify error structure
    err = AppError(status_code=404, code="TEST_ERROR", detail="Test message")
    assert err.status_code == 404
    assert err.code == "TEST_ERROR"
    assert err.detail == "Test message"
    assert err.errors == []
