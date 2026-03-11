"""add openrouter and chutes API keys

Revision ID: 002_add_openrouter_chutes
Revises: 5434eda6045a
Create Date: 2026-02-24 06:00:00.000000
"""
from __future__ import annotations

import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '002_add_openrouter_chutes'
down_revision: Union[str, None] = '0001_archive_stocks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def encrypt_value(value: str, secret_key: str) -> str:
    """Encrypt a value using Fernet encryption."""
    import base64
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend

    ENCRYPTION_SALT = b"equity-research-agent-api-key-encryption-salt-v1"

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=ENCRYPTION_SALT,
        iterations=100000,
        backend=default_backend(),
    )

    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    f = Fernet(key)

    return f.encrypt(value.encode()).decode()


def upgrade() -> None:
    """Add openrouter_api_key and chutes_api_key columns to user_settings."""
    # Get the secret key for encryption
    secret_key = os.environ.get("SECRET_KEY", "")
    if not secret_key:
        # Try to import from app config
        try:
            from app.core.config import settings
            secret_key = settings.SECRET_KEY
        except Exception:
            print("WARNING: SECRET_KEY not found. Existing API keys will not be migrated.")

    # Add new columns
    op.add_column("user_settings", sa.Column("openrouter_api_key", sa.String(512), nullable=True))
    op.add_column("user_settings", sa.Column("chutes_api_key", sa.String(512), nullable=True))

    # Create indexes for the new columns
    op.create_index("ix_user_settings_openrouter_api_key", "user_settings", ["openrouter_api_key"], unique=False)
    op.create_index("ix_user_settings_chutes_api_key", "user_settings", ["chutes_api_key"], unique=False)

    print("Added openrouter_api_key and chutes_api_key columns to user_settings")


def downgrade() -> None:
    """Remove openrouter_api_key and chutes_api_key columns from user_settings."""
    op.drop_index("ix_user_settings_chutes_api_key", table_name="user_settings")
    op.drop_index("ix_user_settings_openrouter_api_key", table_name="user_settings")

    op.drop_column("user_settings", "chutes_api_key")
    op.drop_column("user_settings", "openrouter_api_key")

    print("Removed openrouter_api_key and chutes_api_key columns from user_settings")
