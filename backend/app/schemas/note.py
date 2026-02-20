"""Note schemas for analyst notes API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    """Structured extraction output from analyst note."""

    sentiment: Optional[str] = Field(default=None, description="Extracted sentiment")
    key_points: list[str] = Field(default_factory=list)
    price_target: Optional[float] = Field(default=None)
    metrics: dict[str, float | str] = Field(default_factory=dict)


class NoteBase(BaseModel):
    """Base note fields."""

    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content")
    note_type: Optional[str] = Field(default=None, description="Note type")
    tags: list[str] = Field(default_factory=list)


class NoteCreate(NoteBase):
    """Schema for creating a note."""

    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note."""

    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[str] = None
    tags: Optional[list[str]] = None


class NoteResponse(NoteBase):
    """Schema for note responses."""

    id: str
    stock_id: str
    user_id: str
    extracted_sentiment: Optional[str]
    extracted_key_points: list[str]
    extracted_price_target: Optional[float]
    extracted_metrics: dict[str, float | str]
    is_ai_processed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
