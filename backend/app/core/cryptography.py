"""
Cryptography utilities for encrypting sensitive data at rest.

This module provides Fernet-based symmetric encryption for API keys and other
sensitive credentials stored in the database.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Salt for deriving encryption key from SECRET_KEY
# This is a fixed salt to ensure consistent key derivation
ENCRYPTION_SALT = b"equity-research-agent-api-key-encryption-salt-v1"


def _derive_encryption_key(secret_key: str) -> bytes:
    """
    Derive a Fernet-compatible encryption key from the application SECRET_KEY.

    Uses PBKDF2HMAC with SHA256 to derive a 32-byte key, then base64-encodes
    it for Fernet compatibility.

    Args:
        secret_key: The application's SECRET_KEY

    Returns:
        A URL-safe base64-encoded 32-byte key suitable for Fernet
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=ENCRYPTION_SALT,
        iterations=100_000,
        backend=default_backend(),
    )
    key = kdf.derive(secret_key.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    """
    Get a cached Fernet instance for encryption/decryption.

    Uses lru_cache to avoid repeated key derivation. The Fernet instance
    is thread-safe and can be reused across requests.

    Returns:
        A Fernet instance configured with the derived key
    """
    encrypted_key = _derive_encryption_key(settings.SECRET_KEY)
    return Fernet(encrypted_key)


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using Fernet symmetric encryption.

    Args:
        value: The plaintext string to encrypt

    Returns:
        The encrypted value as a UTF-8 string

    Raises:
        ValueError: If the value is empty or None
    """
    if not value:
        raise ValueError("Cannot encrypt empty or None value")

    fernet = get_fernet()
    encrypted_bytes = fernet.encrypt(value.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt a previously encrypted string value.

    Args:
        encrypted_value: The encrypted string to decrypt

    Returns:
        The original plaintext string

    Raises:
        ValueError: If the encrypted_value is empty, None, or invalid
    """
    if not encrypted_value:
        raise ValueError("Cannot decrypt empty or None value")

    fernet = get_fernet()
    try:
        decrypted_bytes = fernet.decrypt(encrypted_value.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to decrypt value: {e}")
        raise ValueError(f"Invalid encrypted value: {e}")


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted (Fernet token format).

    This is a heuristic check - Fernet tokens are URL-safe base64-encoded
    and contain a version byte, timestamp, IV, and ciphertext with HMAC.

    Args:
        value: The string to check

    Returns:
        True if the value appears to be a valid Fernet token
    """
    if not value or len(value) < 44:  # Minimum Fernet token length
        return False

    try:
        # Fernet tokens are base64-encoded and start with version byte 0x80
        decoded = base64.urlsafe_b64decode(value)
        return len(decoded) >= 33 and decoded[0] == 0x80
    except Exception:
        return False
