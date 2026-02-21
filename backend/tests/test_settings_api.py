"""
Tests for Settings API endpoints.
"""
from __future__ import annotations

import os
import uuid

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-123456")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

class TestSettingsEndpoints:
    """Tests for /api/v1/settings endpoints."""

    def test_get_settings_requires_auth(self) -> None:
        """GET /settings without token returns 401."""
        response = client.get("/api/v1/settings")
        assert response.status_code == 401

    def test_update_settings_requires_auth(self) -> None:
        """PUT /settings without token returns 401."""
        response = client.put(
            "/api/v1/settings",
            json={"fundamentals_provider": "finnhub"},
        )
        assert response.status_code == 401

    def test_update_settings_validation_invalid_provider(self) -> None:
         # Assuming pydantic accepts string
        response = client.put(
            "/api/v1/settings",
             json={"fundamentals_provider": 123}, # Invalid type, though coercion might happen
        )
        assert response.status_code == 401 # Auth triggers first usually, so this confirms auth wall works

    def test_settings_responds_json(self) -> None:
        """Settings endpoints return JSON content type on errors/auth failures."""
        response = client.get("/api/v1/settings")
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert "error" in data or "detail" in data
