"""Direct tests for CostTrackingMixin branches not exercised elsewhere.

Covers: skipped-stage skip, cache-savings calculation, default _get_cache_stats.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.models import ModelTier
from attune.workflows.cost_mixin import CostTrackingMixin
from attune.workflows.data_classes import WorkflowStage


class _Harness(CostTrackingMixin):
    """Minimal subclass to drive CostTrackingMixin in isolation."""

    def __init__(self, stages, cache_stats=None):
        self._stages_run = stages
        self._cache_stats = cache_stats

    def _get_cache_stats(self):
        if self._cache_stats is None:
            # Defer to default implementation (the line we want to cover)
            return CostTrackingMixin._get_cache_stats(self)
        return self._cache_stats


@pytest.mark.unit
class TestCostMixinReportBranches:
    def _stage(
        self, *, name="s", tier=ModelTier.CAPABLE, cost=0.10, in_t=1000, out_t=500, skipped=False
    ):
        return WorkflowStage(
            name=name,
            tier=tier,
            description="d",
            input_tokens=in_t,
            output_tokens=out_t,
            cost=cost,
            skipped=skipped,
        )

    def test_skipped_stage_is_excluded(self):
        """Skipped stages are skipped during cost aggregation (line 99)."""
        stages = [
            self._stage(name="ok", cost=0.5),
            self._stage(name="skipme", cost=99.0, skipped=True),
        ]
        h = _Harness(stages, cache_stats={"hits": 0, "misses": 0, "hit_rate": 0.0})
        report = h._generate_cost_report()
        assert report.total_cost == pytest.approx(0.5)
        assert "ok" in report.by_stage
        assert "skipme" not in report.by_stage

    def test_cache_savings_computed_when_hits_present(self):
        """cache_hits > 0 path computes estimated cache savings (lines 122-126)."""
        stages = [self._stage(name="a", cost=0.5)]
        # 2 misses, 1 hit → avg = 0.5/2 = 0.25, savings = 1 * 0.25 = 0.25
        h = _Harness(stages, cache_stats={"hits": 1, "misses": 2, "hit_rate": 0.5})
        report = h._generate_cost_report()

        assert report.cache_hits == 1
        assert report.savings_from_cache == pytest.approx(0.25)
        assert report.estimated_cost_without_cache == pytest.approx(0.75)

    def test_cache_hits_with_zero_misses_avoids_div_by_zero(self):
        """cache_hits > 0 but cache_misses == 0 → avg defaults to 0.0 (line 123 False branch)."""
        stages = [self._stage(name="a", cost=0.5)]
        h = _Harness(stages, cache_stats={"hits": 1, "misses": 0, "hit_rate": 1.0})
        report = h._generate_cost_report()
        # No misses → can't infer per-call cost → savings_from_cache stays 0
        assert report.savings_from_cache == 0.0
        assert report.estimated_cost_without_cache == pytest.approx(0.5)


@pytest.mark.unit
class TestCostMixinDefaultCacheStats:
    def test_default_get_cache_stats_returns_zeros(self):
        """The default _get_cache_stats() returns zeros (line 145)."""
        h = _Harness(stages=[], cache_stats=None)
        # Force the default impl by clearing the override
        result = h._get_cache_stats()
        assert result == {"hits": 0, "misses": 0, "hit_rate": 0.0}
