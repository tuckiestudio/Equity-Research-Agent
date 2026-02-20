"""ThesisChange database model for thesis change audit trail."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ThesisChange(Base, UUIDMixin):
    """Audit trail entry for thesis changes."""

    __tablename__ = "thesis_changes"

    thesis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("theses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # What changed
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_stance: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    new_stance: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    previous_target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    previous_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Context
    trigger: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    version_from: Mapped[int] = mapped_column(nullable=False)
    version_to: Mapped[int] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
