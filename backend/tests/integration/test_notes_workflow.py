"""
Integration tests for notes workflow.

Tests:
1. Create note
2. List notes
3. Update note
4. Delete note
5. Note isolation between users
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient


class TestNotesWorkflow:
    """Test notes management via API."""

    @pytest.mark.asyncio
    async def test_create_and_list_note(
        self,
        client: AsyncClient,
    ) -> None:
        """Test creating a note and listing it."""
        email = f"note1_{uuid.uuid4()}@example.com"

        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "Notes Test",
            },
        )
        token = register_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Create note
        create_response = await client.post(
            "/api/v1/notes/AAPL",
            json={"title": "Apple Analysis", "content": "This is my first note about Apple"},
        )
        assert create_response.status_code == 200
        note = create_response.json()
        assert note["content"] == "This is my first note about Apple"
        note_id = note["id"]

        # List notes
        list_response = await client.get("/api/v1/notes/AAPL")
        assert list_response.status_code == 200
        notes = list_response.json()
        assert len(notes) >= 1

        # Get note detail
        detail_response = await client.get(f"/api/v1/notes/detail/{note_id}")
        assert detail_response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_note(
        self,
        client: AsyncClient,
    ) -> None:
        """Test updating a note."""
        email = f"note2_{uuid.uuid4()}@example.com"

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

        # Create note
        create_response = await client.post(
            "/api/v1/notes/GOOGL",
            json={"title": "Google Note", "content": "Original content"},
        )
        note_id = create_response.json()["id"]

        # Update note
        update_response = await client.put(
            f"/api/v1/notes/{note_id}",
            json={"content": "Updated content"},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["content"] == "Updated content"

    @pytest.mark.asyncio
    async def test_delete_note(
        self,
        client: AsyncClient,
    ) -> None:
        """Test deleting a note."""
        email = f"note3_{uuid.uuid4()}@example.com"

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

        # Create note
        create_response = await client.post(
            "/api/v1/notes/MSFT",
            json={"title": "MSFT Note", "content": "Note to delete"},
        )
        note_id = create_response.json()["id"]

        # Delete note
        delete_response = await client.delete(f"/api/v1/notes/{note_id}")
        assert delete_response.status_code == 200

        # Verify deleted - list should be empty or not contain deleted note
        list_response = await client.get("/api/v1/notes/MSFT")
        notes = list_response.json()
        # Note should be deleted
        assert len(notes) == 0

    @pytest.mark.asyncio
    async def test_note_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that note endpoints require authentication."""
        # Try to create without auth
        response = await client.post(
            "/api/v1/notes/AAPL",
            json={"title": "Test Note", "content": "Test"},
        )
        assert response.status_code == 401

        # Try to list without auth
        response = await client.get("/api/v1/notes/AAPL")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_note_validation_empty_content(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that note with missing required fields is rejected."""
        email = f"note4_{uuid.uuid4()}@example.com"

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

        # Test missing content field
        response = await client.post(
            "/api/v1/notes/AAPL",
            json={"title": "Missing Content"},
        )
        assert response.status_code == 422

        # Test missing title field
        response = await client.post(
            "/api/v1/notes/AAPL",
            json={"content": "Some content without title"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_multi_user_note_isolation(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that users cannot access each other's notes."""
        # User 1 registers and creates note
        email1 = f"noteuser1_{uuid.uuid4()}@example.com"
        register1 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email1,
                "password": "password123",
                "full_name": "User 1",
            },
        )
        token1 = register1.json()["access_token"]

        client.headers["Authorization"] = f"Bearer {token1}"
        create_response = await client.post(
            "/api/v1/notes/TSLA",
            json={"title": "TSLA Secret Note", "content": "User 1's secret note"},
        )
        note_id = create_response.json()["id"]

        # User 2 registers
        email2 = f"noteuser2_{uuid.uuid4()}@example.com"
        register2 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email2,
                "password": "password123",
                "full_name": "User 2",
            },
        )
        token2 = register2.json()["access_token"]

        # User 2 tries to view User 1's note
        client.headers["Authorization"] = f"Bearer {token2}"
        get_response = await client.get(f"/api/v1/notes/detail/{note_id}")
        assert get_response.status_code in [403, 404]

        # User 2's note list should not include User 1's note
        list_response = await client.get("/api/v1/notes/TSLA")
        notes = list_response.json()
        for note in notes:
            assert note["id"] != note_id

    @pytest.mark.asyncio
    async def test_free_tier_note_limit(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that free tier users are limited in notes per stock."""
        email = f"note5_{uuid.uuid4()}@example.com"

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

        # Create 5 notes (should succeed for free tier)
        for i in range(5):
            response = await client.post(
                "/api/v1/notes/NVDA",
                json={"title": f"NVDA Note {i + 1}", "content": f"Note {i + 1}"},
            )
            assert response.status_code == 200

        # 6th note should fail for free tier
        response = await client.post(
            "/api/v1/notes/NVDA",
            json={"title": "NVDA Note 6", "content": "Note 6"},
        )
        assert response.status_code in [400, 403, 429]
