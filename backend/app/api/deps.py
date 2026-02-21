"""
FastAPI dependencies — shared across all API endpoints.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError
from app.db.session import get_db
from app.models.user import User
from app.services.auth import decode_access_token


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization header, return user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if payload is None:
        raise AuthenticationError("Invalid or expired token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Invalid token payload")

    from sqlalchemy.orm import selectinload
    result = await db.execute(select(User).options(selectinload(User.settings)).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    return user
