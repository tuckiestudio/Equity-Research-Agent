"""
Tests for Portfolio API endpoints — model structure and endpoint validation.
"""
from __future__ import annotations

import os
import uuid

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-123456")

from fastapi.testclient import TestClient

from app.main import app
from app.models.stock import Portfolio, Stock, portfolio_stocks

client = TestClient(app)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class TestPortfolioModel:
    """Tests for Portfolio database model structure."""

    def test_model_fields(self) -> None:
        """Verify all required columns exist on Portfolio."""
        expected = ["id", "name", "user_id", "created_at", "updated_at", "stocks", "user"]
        for attr in expected:
            assert hasattr(Portfolio, attr), f"Portfolio missing attribute: {attr}"

    def test_tablename(self) -> None:
        """Table name is 'portfolios'."""
        assert Portfolio.__tablename__ == "portfolios"

    def test_stock_model_fields(self) -> None:
        """Verify all required columns exist on Stock."""
        expected = ["id", "ticker", "company_name", "exchange", "sector", "industry", "portfolios"]
        for attr in expected:
            assert hasattr(Stock, attr), f"Stock missing attribute: {attr}"

    def test_stock_tablename(self) -> None:
        """Table name is 'stocks'."""
        assert Stock.__tablename__ == "stocks"

    def test_association_table_exists(self) -> None:
        """portfolio_stocks M2M table is defined."""
        assert portfolio_stocks is not None
        assert portfolio_stocks.name == "portfolio_stocks"
        columns = {c.name for c in portfolio_stocks.columns}
        assert "portfolio_id" in columns
        assert "stock_id" in columns


# ---------------------------------------------------------------------------
# API Endpoint Tests (Validation / Auth)
# ---------------------------------------------------------------------------


class TestPortfolioEndpoints:
    """Tests for /api/v1/portfolios endpoints."""

    def test_list_portfolios_requires_auth(self) -> None:
        """GET /portfolios without token returns 401."""
        response = client.get("/api/v1/portfolios")
        assert response.status_code == 401

    def test_create_portfolio_requires_auth(self) -> None:
        """POST /portfolios without token returns 401."""
        response = client.post(
            "/api/v1/portfolios",
            json={"name": "My Portfolio"},
        )
        assert response.status_code == 401

    def test_get_portfolio_requires_auth(self) -> None:
        """GET /portfolios/{id} without token returns 401."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/portfolios/{fake_id}")
        assert response.status_code == 401

    def test_add_stock_requires_auth(self) -> None:
        """POST /portfolios/{id}/stocks without token returns 401."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/portfolios/{fake_id}/stocks",
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 401

    def test_remove_stock_requires_auth(self) -> None:
        """DELETE /portfolios/{id}/stocks/{ticker} without token returns 401."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/portfolios/{fake_id}/stocks/AAPL")
        assert response.status_code == 401

    def test_create_portfolio_validation_empty_name(self) -> None:
        """CreatePortfolioRequest rejects empty name via Pydantic."""
        from app.api.v1.portfolios import CreatePortfolioRequest
        with pytest.raises(Exception):  # Pydantic ValidationError
            CreatePortfolioRequest(name="")

    def test_create_portfolio_validation_long_name(self) -> None:
        """CreatePortfolioRequest rejects names over 100 characters."""
        from app.api.v1.portfolios import CreatePortfolioRequest
        with pytest.raises(Exception):  # Pydantic ValidationError
            CreatePortfolioRequest(name="x" * 101)

    def test_add_stock_validation_empty_ticker(self) -> None:
        """AddStockRequest rejects empty ticker via Pydantic."""
        from app.api.v1.portfolios import AddStockRequest
        with pytest.raises(Exception):  # Pydantic ValidationError
            AddStockRequest(ticker="")

    def test_add_stock_validation_valid_ticker(self) -> None:
        """AddStockRequest accepts valid tickers."""
        from app.api.v1.portfolios import AddStockRequest
        req = AddStockRequest(ticker="AAPL")
        assert req.ticker == "AAPL"

    def test_get_portfolio_invalid_uuid(self) -> None:
        """Get portfolio with invalid UUID without auth returns 401."""
        response = client.get("/api/v1/portfolios/not-a-uuid")
        assert response.status_code == 401

    def test_portfolios_responds_json(self) -> None:
        """Portfolio endpoints return JSON content type."""
        response = client.get("/api/v1/portfolios")
        assert response.headers.get("content-type", "").startswith("application/json")


# ---------------------------------------------------------------------------
# Response Format Tests
# ---------------------------------------------------------------------------


class TestPortfolioResponseFormat:
    """Tests for portfolio response schema compliance."""

    def test_list_portfolios_without_token_returns_401(self) -> None:
        """GET /portfolios without Authorization header returns 401."""
        response = client.get("/api/v1/portfolios")
        assert response.status_code == 401

    def test_auth_error_has_structured_format(self) -> None:
        """401 errors follow the structured error format."""
        response = client.get("/api/v1/portfolios")
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
