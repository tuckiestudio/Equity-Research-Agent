"""Tests for scenario weighting logic."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Optional

import pytest

from app.api.v1.scenarios import compute_weighted_summary


class TestScenarioWeighting:
    """Test suite for scenario weighted summary."""

    def _scenario(self, name: str, probability: Optional[float], dcf: Optional[float]):
        """Create a minimal scenario-like object."""
        return SimpleNamespace(
            id=uuid.uuid4(),
            name=name,
            probability=probability,
            dcf_per_share=dcf,
        )

    def test_weighted_average(self) -> None:
        """Weighted average uses probability weights."""
        scenarios = [
            self._scenario("Base", 0.5, 100.0),
            self._scenario("Bull", 0.5, 200.0),
        ]

        summary = compute_weighted_summary(scenarios)

        assert summary.total_probability == pytest.approx(1.0)
        assert summary.target_price == pytest.approx(150.0)
        assert len(summary.breakdown) == 2
        assert summary.breakdown[0].weighted_value == pytest.approx(50.0)

    def test_excludes_zero_probability(self) -> None:
        """Zero-probability scenarios are excluded from totals."""
        scenarios = [
            self._scenario("Base", 0.0, 100.0),
            self._scenario("Bull", 0.5, 200.0),
        ]

        summary = compute_weighted_summary(scenarios)

        assert summary.total_probability == pytest.approx(0.5)
        assert summary.target_price == pytest.approx(200.0)

    def test_excludes_missing_dcf(self) -> None:
        """Scenarios without DCF per share are excluded from totals."""
        scenarios = [
            self._scenario("Base", 0.5, None),
            self._scenario("Bull", 0.5, 120.0),
        ]

        summary = compute_weighted_summary(scenarios)

        assert summary.total_probability == pytest.approx(0.5)
        assert summary.target_price == pytest.approx(120.0)

    def test_single_scenario(self) -> None:
        """Single scenario behavior returns that DCF value."""
        scenarios = [self._scenario("Base", 1.0, 125.0)]

        summary = compute_weighted_summary(scenarios)

        assert summary.total_probability == pytest.approx(1.0)
        assert summary.target_price == pytest.approx(125.0)

    def test_no_valid_probabilities(self) -> None:
        """No valid scenarios yields None target price."""
        scenarios = [
            self._scenario("Base", 0.0, 100.0),
            self._scenario("Bear", None, 80.0),
        ]

        summary = compute_weighted_summary(scenarios)

        assert summary.total_probability == 0.0
        assert summary.target_price is None
