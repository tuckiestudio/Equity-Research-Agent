"""
Tests for authentication — password hashing (argon2), JWT tokens, and auth API endpoints.
"""
from __future__ import annotations

import os
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-123456")

from app.main import app
from app.services.auth import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Password Hashing (Argon2)
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    """Tests for argon2 password hashing utilities."""

    def test_hash_password_returns_argon2_hash(self) -> None:
        """hash_password() returns an argon2 hash string."""
        hashed = hash_password("securepassword123")
        assert hashed.startswith("$argon2"), f"Expected argon2 hash, got: {hashed[:20]}"

    def test_verify_password_correct(self) -> None:
        """verify_password() returns True for correct password."""
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """verify_password() returns False for wrong password."""
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_hash_uniqueness(self) -> None:
        """Same password produces different hashes (salt-based)."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2, "Hashes should differ due to random salt"

    def test_hash_long_password(self) -> None:
        """Argon2 can handle passwords longer than 72 bytes (bcrypt limit)."""
        long_password = "a" * 128
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True

    def test_hash_unicode_password(self) -> None:
        """Unicode passwords are hashed correctly."""
        password = "pässwörd🔒"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_empty_password_verify_fails(self) -> None:
        """Empty string does not verify against a real hash."""
        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False


# ---------------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------------


class TestJWTTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token_returns_string(self) -> None:
        """create_access_token() returns a JWT string."""
        token = create_access_token({"sub": "user123"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_access_token_roundtrip(self) -> None:
        """Token can be decoded back to original payload."""
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id})
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert "exp" in payload

    def test_decode_invalid_token_returns_none(self) -> None:
        """Invalid token string returns None."""
        result = decode_access_token("not-a-valid-jwt-token")
        assert result is None

    def test_decode_tampered_token_returns_none(self) -> None:
        """Tampered token returns None."""
        token = create_access_token({"sub": "user123"})
        tampered = token[:-5] + "XXXXX"
        result = decode_access_token(tampered)
        assert result is None

    def test_decode_wrong_secret_returns_none(self) -> None:
        """Token signed with different secret fails verification."""
        from jose import jwt as jose_jwt

        token = jose_jwt.encode(
            {"sub": "user123", "exp": 9999999999},
            "wrong-secret-key",
            algorithm=ALGORITHM,
        )
        result = decode_access_token(token)
        assert result is None

    def test_expired_token_returns_none(self) -> None:
        """Expired token returns None."""
        token = create_access_token(
            {"sub": "user123"},
            expires_delta=timedelta(seconds=-10),
        )
        result = decode_access_token(token)
        assert result is None

    def test_custom_expiry_delta(self) -> None:
        """Custom expiry delta is respected."""
        token = create_access_token(
            {"sub": "user123"},
            expires_delta=timedelta(hours=1),
        )
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"


# ---------------------------------------------------------------------------
# Auth API Endpoints
# ---------------------------------------------------------------------------


class TestAuthAPI:
    """Tests for /api/v1/auth/ endpoints via TestClient."""

    def test_register_validation_short_password(self) -> None:
        """Registration rejects passwords shorter than 8 characters."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "short", "full_name": "Test"},
        )
        assert response.status_code == 422

    def test_register_validation_invalid_email(self) -> None:
        """Registration rejects invalid email formats."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "securepass123", "full_name": "Test"},
        )
        assert response.status_code == 422

    def test_register_validation_missing_fields(self) -> None:
        """Registration rejects missing required fields."""
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422

    def test_login_validation_missing_fields(self) -> None:
        """Login rejects missing credentials."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_me_without_token_returns_401(self) -> None:
        """GET /me without Authorization header returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token_returns_401(self) -> None:
        """GET /me with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401

    def test_me_with_malformed_header_returns_401(self) -> None:
        """GET /me with malformed Authorization header returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer some-token"},
        )
        assert response.status_code == 401

    def test_login_wrong_password_returns_401(self) -> None:
        """Login with wrong password returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpass123"},
        )
        assert response.status_code == 401

    def test_register_password_max_length_hashing(self) -> None:
        """Argon2 can hash a 128-character password without error."""
        long_password = "a" * 128
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True
        # Confirm no validation error for 128-char body
        # (tested via Pydantic model directly, not API, to avoid async DB)
        from app.api.v1.auth import RegisterRequest
        req = RegisterRequest(
            email="longpass@example.com",
            password=long_password,
            full_name="Long Pass User",
        )
        assert len(req.password) == 128

    def test_register_password_too_long(self) -> None:
        """Registration rejects passwords over 128 characters."""
        too_long = "a" * 129
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "toolong@example.com",
                "password": too_long,
                "full_name": "Too Long",
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Auth Dependency (get_current_user)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    def test_valid_token_for_nonexistent_user_decoded_ok(self) -> None:
        """Token with valid signature for non-existent user decodes successfully.
        (Actual 401 requires async DB lookup — tested via integration tests.)
        """
        fake_id = str(uuid.uuid4())
        token = create_access_token({"sub": fake_id})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == fake_id

    def test_token_without_sub_claim_returns_401(self) -> None:
        """Token missing 'sub' claim returns 401."""
        token = create_access_token({"role": "admin"})
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_token_with_invalid_uuid_sub_returns_401(self) -> None:
        """Token with non-UUID sub claim returns 401."""
        token = create_access_token({"sub": "not-a-uuid"})
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
