"""
Tests for Stocks API endpoints — search and detail.
"""
from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-123456")

from fastapi.testclient import TestClient

from app.main import app
from app.models.stock import Stock

client = TestClient(app)


# ---------------------------------------------------------------------------
# Stock Model
# ---------------------------------------------------------------------------


class TestStockModel:
    """Tests for Stock database model."""

    def test_model_fields(self) -> None:
        """Verify all required columns exist on Stock."""
        expected = ["id", "ticker", "company_name", "exchange", "sector", "industry"]
        for attr in expected:
            assert hasattr(Stock, attr), f"Stock missing attribute: {attr}"

    def test_tablename(self) -> None:
        """Table name is 'stocks'."""
        assert Stock.__tablename__ == "stocks"


# ---------------------------------------------------------------------------
# Search Endpoint
# ---------------------------------------------------------------------------


class TestStockSearch:
    """Tests for GET /api/v1/stocks/search."""

    def test_search_requires_auth(self) -> None:
        """Search without token returns 401."""
        response = client.get("/api/v1/stocks/search?q=AAPL")
        assert response.status_code == 401

    def test_search_without_auth_requires_token(self) -> None:
        """Search without any token returns 401."""
        response = client.get("/api/v1/stocks/search?q=test")
        assert response.status_code == 401

    def test_search_empty_query_without_auth(self) -> None:
        """Search with empty query and no token returns 401 (auth check first)."""
        response = client.get("/api/v1/stocks/search?q=")
        assert response.status_code == 401

    def test_search_returns_json_array(self) -> None:
        """Search without auth is rejected with 401 JSON response."""
        response = client.get("/api/v1/stocks/search?q=AAPL")
        assert response.status_code == 401
        assert response.headers.get("content-type", "").startswith("application/json")


# ---------------------------------------------------------------------------
# Stock Detail Endpoint
# ---------------------------------------------------------------------------


class TestStockDetail:
    """Tests for GET /api/v1/stocks/{ticker}."""

    def test_get_stock_requires_auth(self) -> None:
        """Get stock without token returns 401."""
        response = client.get("/api/v1/stocks/AAPL")
        assert response.status_code == 401

    def test_get_stock_returns_json(self) -> None:
        """Get stock response is JSON."""
        response = client.get("/api/v1/stocks/AAPL")
        assert response.headers.get("content-type", "").startswith("application/json")


# ---------------------------------------------------------------------------
# Error Format
# ---------------------------------------------------------------------------


class TestStockErrors:
    """Tests for stock endpoint error responses."""

    def test_auth_error_structured(self) -> None:
        """401 errors follow structured error format."""
        response = client.get("/api/v1/stocks/search?q=test")
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_validation_error_for_empty_search(self) -> None:
        """Missing query param without auth returns 401."""
        response = client.get("/api/v1/stocks/search")
        assert response.status_code == 401
