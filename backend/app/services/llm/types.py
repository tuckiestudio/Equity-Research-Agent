"""Shared types for the LLM service layer."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class LLMRole(str, Enum):
    """Role of a message in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """A single message in an LLM conversation."""

    role: LLMRole
    content: str


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: Optional[float] = None
    finish_reason: Optional[str] = None


class TaskType(str, Enum):
    """Task types that map to specific models via the router.

    Different analysis tasks require different capabilities:
    - Complex reasoning → Claude Sonnet
    - Quick summaries → GPT-4o-mini / Haiku
    - Structured output → GPT-4o-mini
    """

    THESIS_GENERATION = "thesis_generation"  # Complex reasoning → Claude Sonnet
    THESIS_UPDATE = "thesis_update"  # Update existing thesis
    NEWS_ANALYSIS = "news_analysis"  # Analyze news impact
    ASSUMPTION_GENERATION = "assumption_generation"  # Generate financial assumptions
    COMPANY_COMPARISON = "company_comparison"  # Compare companies
    NOTE_EXTRACTION = "note_extraction"  # Extract data from analyst notes
    WATCH_ITEMS = "watch_items"  # Generate watch items / catalysts
    QUICK_SUMMARY = "quick_summary"  # Short summaries → Haiku/mini
    DATA_FORMATTING = "data_formatting"  # Structured output → GPT-4o-mini
