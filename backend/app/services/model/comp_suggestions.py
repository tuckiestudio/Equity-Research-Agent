"""Comparable company suggestion engine."""
from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field

from app.core.errors import NotFoundError
from app.schemas.financial import CompanyProfile
from app.services.data.registry import get_profiles
from app.services.llm.router import LLMRouter
from app.services.llm.types import LLMMessage, LLMRole, TaskType


class CompSuggestion(BaseModel):
    """Comparable company suggestion returned by the engine."""

    ticker: str
    reason: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None


class CompSuggestionEngine:
    """Suggest comparable companies using LLM guidance and profile validation."""

    def __init__(self, llm_router: Optional[LLMRouter] = None) -> None:
        """Initialize the suggestion engine."""
        self._llm = llm_router or LLMRouter()

    async def suggest_peers(self, ticker: str, limit: int = 5) -> list[CompSuggestion]:
        """Suggest comparable companies for a target ticker.

        Args:
            ticker: Target ticker to find peers for.
            limit: Maximum number of suggestions to return.

        Returns:
            List of validated comp suggestions.
        """
        normalized = ticker.upper()
        profiles = get_profiles()

        try:
            target_profile = await profiles.get_company_profile(normalized)
        except Exception as exc:
            raise NotFoundError("Stock", normalized) from exc

        raw_suggestions = await self._get_llm_suggestions(
            target_ticker=normalized,
            target_profile=target_profile,
            limit=limit,
        )
        if not raw_suggestions:
            return []

        suggestions: list[CompSuggestion] = []
        seen = {normalized}

        for suggestion in raw_suggestions:
            raw_ticker = suggestion.get("ticker") if isinstance(suggestion, dict) else None
            if not raw_ticker:
                continue
            candidate = str(raw_ticker).upper()
            if candidate in seen:
                continue

            similarity_score = suggestion.get("similarity_score") if isinstance(suggestion, dict) else None
            if not isinstance(similarity_score, (int, float)):
                continue
            if similarity_score < 0 or similarity_score > 1:
                continue

            try:
                profile = await profiles.get_company_profile(candidate)
            except Exception:
                continue

            reason = suggestion.get("reason") if isinstance(suggestion, dict) else ""
            suggestions.append(
                CompSuggestion(
                    ticker=candidate,
                    reason=str(reason or ""),
                    similarity_score=float(similarity_score),
                    sector=profile.sector,
                    industry=profile.industry,
                    market_cap=profile.market_cap,
                )
            )
            seen.add(candidate)

            if len(suggestions) >= limit:
                break

        return suggestions

    async def _get_llm_suggestions(
        self,
        target_ticker: str,
        target_profile: CompanyProfile,
        limit: int,
    ) -> list[dict[str, object]]:
        """Call the LLM to suggest comparable tickers.

        Returns an empty list on LLM errors.
        """
        system_prompt = (
            "You are an equity research analyst. Return a JSON array of comparable "
            "companies for the target ticker. Each item must include: ticker, reason, "
            "similarity_score (0 to 1). Return only JSON."
        )
        user_prompt = (
            "Target company details:\n"
            f"Ticker: {target_ticker}\n"
            f"Company: {target_profile.company_name}\n"
            f"Sector: {target_profile.sector}\n"
            f"Industry: {target_profile.industry}\n"
            f"Market cap: {target_profile.market_cap}\n\n"
            f"Return up to {limit} comparable tickers as JSON array."
        )
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content=system_prompt),
            LLMMessage(role=LLMRole.USER, content=user_prompt),
        ]

        try:
            response = await self._llm.complete(
                task_type=TaskType.COMPANY_COMPARISON,
                messages=messages,
                json_mode=True,
            )
            payload = json.loads(response.content)
            if not isinstance(payload, list):
                return []
            return payload
        except Exception:
            return []
