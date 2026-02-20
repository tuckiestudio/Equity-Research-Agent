"""Multi-LLM service layer for equity research agent.

This module provides a unified interface to multiple LLM providers (OpenAI, Anthropic, etc.)
with intelligent task routing, fallback handling, and cost tracking.
"""

from __future__ import annotations

from app.services.llm.protocols import LLMProvider
from app.services.llm.types import (
    LLMMessage,
    LLMResponse,
    LLMRole,
    TaskType,
)

__all__ = [
    "LLMMessage",
    "LLMResponse",
    "LLMRole",
    "TaskType",
    "LLMProvider",
]
