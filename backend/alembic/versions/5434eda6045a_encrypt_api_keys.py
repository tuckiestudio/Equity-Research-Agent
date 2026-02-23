"""encrypt api keys

Revision ID: 5434eda6045a
Revises: 3b03004f3fed
Create Date: 2026-02-22 23:54:29.705602
"""
from __future__ import annotations

import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '5434eda6045a'
down_revision: Union[str, None] = '3b03004f3fed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# API key columns to encrypt
API_KEY_COLUMNS = [
    "fmp_api_key",
    "finnhub_api_key",
    "alpha_vantage_api_key",
    "eodhd_api_key",
    "polygon_api_key",
    "openai_api_key",
    "anthropic_api_key",
    "glm_api_key",
    "kimi_api_key",
]


def encrypt_value(value: str, secret_key: str) -> str:
    """
    Encrypt a value using Fernet encryption.
    """
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
        iterations=100_000,
        backend=default_backend(),
    )
    key = kdf.derive(secret_key.encode("utf-8"))
    fernet_key = base64.urlsafe_b64encode(key)
    fernet = Fernet(fernet_key)

    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def is_already_encrypted(value: str) -> bool:
    """Check if a value appears to be already encrypted (Fernet token format)."""
    import base64

    if not value or len(value) < 44:
        return False

    try:
        decoded = base64.urlsafe_b64decode(value)
        return len(decoded) >= 33 and decoded[0] == 0x80
    except Exception:
        return False


def upgrade() -> None:
    """Encrypt all existing plaintext API keys in user_settings table."""
    secret_key = os.environ.get("SECRET_KEY", "")

    if not secret_key or len(secret_key) < 32:
        print("WARNING: SECRET_KEY not properly set. Skipping encryption.")
        return

    connection = op.get_bind()

    # Step 1: Expand column sizes using raw SQL for reliability
    print("Expanding API key column sizes to VARCHAR(512)...")
    for column in API_KEY_COLUMNS:
        connection.execute(
            text(f'ALTER TABLE user_settings ALTER COLUMN "{column}" TYPE VARCHAR(512)')
        )
    print("Column expansion complete.")

    # Step 2: Encrypt existing keys
    for column in API_KEY_COLUMNS:
        print(f"Encrypting {column}...")
        result = connection.execute(
            text(f'SELECT id, "{column}" FROM user_settings WHERE "{column}" IS NOT NULL')
        )
        rows = result.fetchall()

        count = 0
        for row in rows:
            row_id, value = row
            if value and not is_already_encrypted(value):
                encrypted_value = encrypt_value(value, secret_key)
                connection.execute(
                    text(f'UPDATE user_settings SET "{column}" = :val WHERE id = :id'),
                    {"val": encrypted_value, "id": row_id}
                )
                count += 1
        if count > 0:
            print(f"  Encrypted {count} values")

    print("Encryption migration complete.")


def downgrade() -> None:
    """Downgrade not supported - cannot decrypt safely."""
    print("WARNING: Cannot downgrade encryption migration.")
