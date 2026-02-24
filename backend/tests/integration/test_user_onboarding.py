"""
Integration tests for user onboarding flow.

Tests the complete journey from registration to first analysis:
1. Register new user
2. Login
3. Access user profile
4. Verify tier info
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient


class TestUserOnboardingFlow:
    """Test the complete user onboarding journey."""

    @pytest.mark.asyncio
    async def test_full_registration_and_login(
        self,
        client: AsyncClient,
    ) -> None:
        """Test complete registration and login flow."""
        email = f"newuser_{uuid.uuid4()}@example.com"

        # Step 1: Register new user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "New User",
            },
        )
        assert register_response.status_code == 201
        register_data = register_response.json()
        assert "access_token" in register_data
        token = register_data["access_token"]

        # Step 2: Login with same credentials
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "securepassword123",
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data

    @pytest.mark.asyncio
    async def test_access_profile_after_login(
        self,
        client: AsyncClient,
    ) -> None:
        """Test accessing user profile after registration."""
        email = f"profiletest_{uuid.uuid4()}@example.com"

        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "Profile Test",
            },
        )

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "securepassword123",
            },
        )
        token = login_response.json()["access_token"]

        # Set auth header
        client.headers["Authorization"] = f"Bearer {token}"

        # Get profile
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == email
        assert user_data["full_name"] == "Profile Test"

    @pytest.mark.asyncio
    async def test_registration_validation(
        self,
        client: AsyncClient,
    ) -> None:
        """Test registration validation rules."""
        # Test short password
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"test1_{uuid.uuid4()}@example.com",
                "password": "short",
                "full_name": "Test",
            },
        )
        assert response.status_code == 422

        # Test invalid email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepass123",
                "full_name": "Test",
            },
        )
        assert response.status_code == 422

        # Test missing fields
        response = await client.post(
            "/api/v1/auth/register",
            json={},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that wrong password fails login."""
        email = f"wrongpass_{uuid.uuid4()}@example.com"

        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "correctpass123",
                "full_name": "Test",
            },
        )

        # Login with wrong password
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "wrongpass123",
            },
        )
        assert login_response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_tier_info(
        self,
        client: AsyncClient,
    ) -> None:
        """Test getting tier information after registration."""
        email = f"tiertest_{uuid.uuid4()}@example.com"

        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "Tier Test",
            },
        )
        token = register_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Get tier info - need to provide email or user_id as query param
        tier_response = await client.get(f"/api/v1/tiers/user?email={email}")
        assert tier_response.status_code == 200
        tier_data = tier_response.json()
        assert tier_data["tier"] == "free"

        # Get limits
        limits_response = await client.get("/api/v1/tiers/my-limits")
        assert limits_response.status_code == 200
        limits_data = limits_response.json()
        assert limits_data["tier"] == "free"
        assert "max_portfolios" in limits_data
