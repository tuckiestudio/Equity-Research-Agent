"""Prompt templates for equity research analysis.

Provides structured prompt templates for different types of financial analysis.
"""

from __future__ import annotations

from app.services.llm.prompts.templates import (
    PromptTemplate,
    get_assumption_generation_template,
    get_company_comparison_template,
    get_news_analysis_template,
    get_note_extraction_template,
    get_thesis_generation_template,
    get_thesis_update_template,
    get_watch_items_template,
)

__all__ = [
    "PromptTemplate",
    "get_thesis_generation_template",
    "get_thesis_update_template",
    "get_news_analysis_template",
    "get_assumption_generation_template",
    "get_company_comparison_template",
    "get_note_extraction_template",
    "get_watch_items_template",
]
