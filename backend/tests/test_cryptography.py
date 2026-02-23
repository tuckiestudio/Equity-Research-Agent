"""Tests for cryptography utilities."""
import os
import pytest

from app.core.cryptography import encrypt_value, decrypt_value, is_encrypted


class TestCryptography:
    """Test encryption and decryption functions."""

    def test_encrypt_decrypt_round_trip(self):
        """Test that encrypting then decrypting returns the original value."""
        original = "test_api_key_12345"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_encrypted_values_are_different(self):
        """Test that encrypted values differ from plaintext."""
        original = "test_api_key_12345"
        encrypted = encrypt_value(original)
        assert encrypted != original
        assert len(encrypted) > len(original)

    def test_is_encrypted_detects_encrypted(self):
        """Test that is_encrypted correctly identifies encrypted values."""
        original = "test_api_key_12345"
        encrypted = encrypt_value(original)
        assert is_encrypted(encrypted) is True

    def test_is_encrypted_detects_plaintext(self):
        """Test that is_encrypted correctly identifies plaintext values."""
        plaintext = "sk-1234567890abcdef"
        assert is_encrypted(plaintext) is False

    def test_is_encrypted_short_string(self):
        """Test that is_encrypted handles short strings."""
        assert is_encrypted("short") is False
        assert is_encrypted("") is False
        assert is_encrypted(None) is False

    def test_encrypt_empty_raises(self):
        """Test that encrypting empty string raises ValueError."""
        with pytest.raises(ValueError):
            encrypt_value("")
        with pytest.raises(ValueError):
            encrypt_value(None)

    def test_decrypt_empty_raises(self):
        """Test that decrypting empty string raises ValueError."""
        with pytest.raises(ValueError):
            decrypt_value("")
        with pytest.raises(ValueError):
            decrypt_value(None)

    def test_decrypt_invalid_raises(self):
        """Test that decrypting invalid ciphertext raises ValueError."""
        with pytest.raises(ValueError):
            decrypt_value("not_a_valid_encrypted_string")

    def test_special_characters(self):
        """Test encryption with special characters."""
        original = "sk-test_123!@#$%^&*()"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_unicode_characters(self):
        """Test encryption with unicode characters."""
        original = "api_key_unicode_\u4e2d\u6587"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original
