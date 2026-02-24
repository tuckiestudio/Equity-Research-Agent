"""
Integration tests for portfolio management workflow.

Tests:
1. Create portfolio
2. List portfolios
3. Portfolio validation
4. Multi-user isolation (portfolios are user-scoped)
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient


class TestPortfolioManagementFlow:
    """Test portfolio management via API."""

    @pytest.mark.asyncio
    async def test_create_and_list_portfolio(
        self,
        client: AsyncClient,
    ) -> None:
        """Test creating portfolio and listing it."""
        email = f"portfolio1_{uuid.uuid4()}@example.com"

        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "Portfolio Test",
            },
        )
        token = register_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Note: Registration creates a default portfolio, so free tier users
        # cannot create additional portfolios (limit is 1)
        # List portfolios - should have the default one
        list_response = await client.get("/api/v1/portfolios")
        assert list_response.status_code == 200
        portfolios = list_response.json()
        assert len(portfolios) == 1
        default_portfolio = portfolios[0]
        assert default_portfolio["name"] == "My Portfolio"

    @pytest.mark.asyncio
    async def test_portfolio_validation_empty_name(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that portfolio with empty name is rejected."""
        email = f"portfolio2_{uuid.uuid4()}@example.com"

        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "Test",
            },
        )
        token = register_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        response = await client.post(
            "/api/v1/portfolios",
            json={"name": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_portfolio_validation_long_name(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that portfolio with very long name is rejected."""
        email = f"portfolio3_{uuid.uuid4()}@example.com"

        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "Test",
            },
        )
        token = register_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        response = await client.post(
            "/api/v1/portfolios",
            json={"name": "A" * 101},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_portfolio_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that portfolio endpoints require authentication."""
        # Try to list without auth
        response = await client.get("/api/v1/portfolios")
        assert response.status_code == 401

        # Try to create without auth
        response = await client.post(
            "/api/v1/portfolios",
            json={"name": "Test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_free_tier_portfolio_limit(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that free tier users are limited to 1 portfolio."""
        email = f"portfolio4_{uuid.uuid4()}@example.com"

        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "Test",
            },
        )
        token = register_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Free tier users already have a default portfolio from registration
        # Trying to create another should fail (limit is 1)
        response1 = await client.post(
            "/api/v1/portfolios",
            json={"name": "Portfolio 1"},
        )
        # Should fail because free tier already has default portfolio
        assert response1.status_code in [400, 403, 429]

    @pytest.mark.asyncio
    async def test_multi_user_portfolio_isolation(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that users cannot access each other's portfolios."""
        # User 1 registers
        email1 = f"user1_{uuid.uuid4()}@example.com"
        register1 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email1,
                "password": "password123",
                "full_name": "User 1",
            },
        )
        token1 = register1.json()["access_token"]

        # User 1 has a default portfolio from registration
        client.headers["Authorization"] = f"Bearer {token1}"
        list_response = await client.get("/api/v1/portfolios")
        user1_portfolios = list_response.json()
        assert len(user1_portfolios) == 1
        portfolio_id = user1_portfolios[0]["id"]

        # User 2 registers
        email2 = f"user2_{uuid.uuid4()}@example.com"
        register2 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email2,
                "password": "password123",
                "full_name": "User 2",
            },
        )
        token2 = register2.json()["access_token"]

        # User 2 tries to access User 1's portfolio
        client.headers["Authorization"] = f"Bearer {token2}"
        get_response = await client.get(f"/api/v1/portfolios/{portfolio_id}")
        # Should fail with 403 or 404
        assert get_response.status_code in [403, 404]

        # User 2's portfolio list should not include User 1's portfolio
        list_response = await client.get("/api/v1/portfolios")
        portfolios = list_response.json()
        for p in portfolios:
            assert p["id"] != portfolio_id
