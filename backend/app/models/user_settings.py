"""
User Settings database model.

API keys are encrypted at rest using Fernet symmetric encryption.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.core.cryptography import encrypt_value, decrypt_value, is_encrypted

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base, UUIDMixin, TimestampMixin):
    """User-specific settings, including data provider selections and API keys.

    All API key fields store encrypted values in the database. The encryption
    and decryption happens transparently via hybrid properties.
    """

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Provider Selections
    fundamentals_provider: Mapped[str] = mapped_column(String(50), default="fmp", nullable=False)
    price_provider: Mapped[str] = mapped_column(String(50), default="finnhub", nullable=False)
    profile_provider: Mapped[str] = mapped_column(String(50), default="fmp", nullable=False)
    news_provider: Mapped[str] = mapped_column(String(50), default="finnhub", nullable=False)

    # Encrypted API Key Storage (private columns - store encrypted values)
    _fmp_api_key: Mapped[Optional[str]] = mapped_column("fmp_api_key", String(512), nullable=True)
    _finnhub_api_key: Mapped[Optional[str]] = mapped_column("finnhub_api_key", String(512), nullable=True)
    _alpha_vantage_api_key: Mapped[Optional[str]] = mapped_column("alpha_vantage_api_key", String(512), nullable=True)
    _eodhd_api_key: Mapped[Optional[str]] = mapped_column("eodhd_api_key", String(512), nullable=True)
    _polygon_api_key: Mapped[Optional[str]] = mapped_column("polygon_api_key", String(512), nullable=True)
    _openai_api_key: Mapped[Optional[str]] = mapped_column("openai_api_key", String(512), nullable=True)
    _anthropic_api_key: Mapped[Optional[str]] = mapped_column("anthropic_api_key", String(512), nullable=True)
    _glm_api_key: Mapped[Optional[str]] = mapped_column("glm_api_key", String(512), nullable=True)
    _kimi_api_key: Mapped[Optional[str]] = mapped_column("kimi_api_key", String(512), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")

    # =========================================================================
    # Financial Data API Keys - Encrypted hybrid properties
    # =========================================================================

    @hybrid_property
    def fmp_api_key(self) -> Optional[str]:
        """Get the decrypted FMP API key."""
        if self._fmp_api_key is None:
            return None
        if is_encrypted(self._fmp_api_key):
            return decrypt_value(self._fmp_api_key)
        # Backward compatibility: return plaintext if not encrypted
        return self._fmp_api_key

    @fmp_api_key.setter
    def fmp_api_key(self, value: Optional[str]) -> None:
        """Set the FMP API key (encrypted)."""
        if value is None or value == "":
            self._fmp_api_key = None
        else:
            self._fmp_api_key = encrypt_value(value)

    @hybrid_property
    def finnhub_api_key(self) -> Optional[str]:
        """Get the decrypted Finnhub API key."""
        if self._finnhub_api_key is None:
            return None
        if is_encrypted(self._finnhub_api_key):
            return decrypt_value(self._finnhub_api_key)
        return self._finnhub_api_key

    @finnhub_api_key.setter
    def finnhub_api_key(self, value: Optional[str]) -> None:
        """Set the Finnhub API key (encrypted)."""
        if value is None or value == "":
            self._finnhub_api_key = None
        else:
            self._finnhub_api_key = encrypt_value(value)

    @hybrid_property
    def alpha_vantage_api_key(self) -> Optional[str]:
        """Get the decrypted Alpha Vantage API key."""
        if self._alpha_vantage_api_key is None:
            return None
        if is_encrypted(self._alpha_vantage_api_key):
            return decrypt_value(self._alpha_vantage_api_key)
        return self._alpha_vantage_api_key

    @alpha_vantage_api_key.setter
    def alpha_vantage_api_key(self, value: Optional[str]) -> None:
        """Set the Alpha Vantage API key (encrypted)."""
        if value is None or value == "":
            self._alpha_vantage_api_key = None
        else:
            self._alpha_vantage_api_key = encrypt_value(value)

    @hybrid_property
    def eodhd_api_key(self) -> Optional[str]:
        """Get the decrypted EODHD API key."""
        if self._eodhd_api_key is None:
            return None
        if is_encrypted(self._eodhd_api_key):
            return decrypt_value(self._eodhd_api_key)
        return self._eodhd_api_key

    @eodhd_api_key.setter
    def eodhd_api_key(self, value: Optional[str]) -> None:
        """Set the EODHD API key (encrypted)."""
        if value is None or value == "":
            self._eodhd_api_key = None
        else:
            self._eodhd_api_key = encrypt_value(value)

    @hybrid_property
    def polygon_api_key(self) -> Optional[str]:
        """Get the decrypted Polygon API key."""
        if self._polygon_api_key is None:
            return None
        if is_encrypted(self._polygon_api_key):
            return decrypt_value(self._polygon_api_key)
        return self._polygon_api_key

    @polygon_api_key.setter
    def polygon_api_key(self, value: Optional[str]) -> None:
        """Set the Polygon API key (encrypted)."""
        if value is None or value == "":
            self._polygon_api_key = None
        else:
            self._polygon_api_key = encrypt_value(value)

    # =========================================================================
    # AI API Keys - Encrypted hybrid properties
    # =========================================================================

    @hybrid_property
    def openai_api_key(self) -> Optional[str]:
        """Get the decrypted OpenAI API key."""
        if self._openai_api_key is None:
            return None
        if is_encrypted(self._openai_api_key):
            return decrypt_value(self._openai_api_key)
        return self._openai_api_key

    @openai_api_key.setter
    def openai_api_key(self, value: Optional[str]) -> None:
        """Set the OpenAI API key (encrypted)."""
        if value is None or value == "":
            self._openai_api_key = None
        else:
            self._openai_api_key = encrypt_value(value)

    @hybrid_property
    def anthropic_api_key(self) -> Optional[str]:
        """Get the decrypted Anthropic API key."""
        if self._anthropic_api_key is None:
            return None
        if is_encrypted(self._anthropic_api_key):
            return decrypt_value(self._anthropic_api_key)
        return self._anthropic_api_key

    @anthropic_api_key.setter
    def anthropic_api_key(self, value: Optional[str]) -> None:
        """Set the Anthropic API key (encrypted)."""
        if value is None or value == "":
            self._anthropic_api_key = None
        else:
            self._anthropic_api_key = encrypt_value(value)

    @hybrid_property
    def glm_api_key(self) -> Optional[str]:
        """Get the decrypted GLM API key."""
        if self._glm_api_key is None:
            return None
        if is_encrypted(self._glm_api_key):
            return decrypt_value(self._glm_api_key)
        return self._glm_api_key

    @glm_api_key.setter
    def glm_api_key(self, value: Optional[str]) -> None:
        """Set the GLM API key (encrypted)."""
        if value is None or value == "":
            self._glm_api_key = None
        else:
            self._glm_api_key = encrypt_value(value)

    @hybrid_property
    def kimi_api_key(self) -> Optional[str]:
        """Get the decrypted Kimi API key."""
        if self._kimi_api_key is None:
            return None
        if is_encrypted(self._kimi_api_key):
            return decrypt_value(self._kimi_api_key)
        return self._kimi_api_key

    @kimi_api_key.setter
    def kimi_api_key(self, value: Optional[str]) -> None:
        """Set the Kimi API key (encrypted)."""
        if value is None or value == "":
            self._kimi_api_key = None
        else:
            self._kimi_api_key = encrypt_value(value)
