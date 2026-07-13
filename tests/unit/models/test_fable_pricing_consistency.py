"""Fable-5 premium pricing + baseline consistency (task 7).

Per-tier pricing has historically drifted across three sites that must
change together (twice-earned lesson): (1) the model registry —
ModelInfo entries and TIER_PRICING, (2) the AnthropicProvider
``get_model_info`` table, (3) the telemetry savings baseline in
``models/telemetry/analytics.py``. These tests pin all three to the
same numbers so a future premium-price change can't land partially.

Also covers the 2026-07-10 BASELINE_MODEL amendment: cost_tracker's
baseline moves to claude-fable-5 (log-time storage keeps history at
opus math) and the report label derives from BASELINE_MODEL.

Mock-only — no live API calls.
"""

import tempfile
from datetime import datetime, timezone

from attune.models.registry import (
    ADDITIONAL_MODELS,
    MODEL_REGISTRY,
    TIER_PRICING,
    ModelRegistry,
)

FABLE = "claude-fable-5"
FABLE_INPUT = 10.00
FABLE_OUTPUT = 50.00


class TestRegistryEntry:
    """Site 1: registry ModelInfo + TIER_PRICING."""

    def test_premium_tier_is_fable(self):
        premium = MODEL_REGISTRY["anthropic"]["premium"]
        assert premium.id == FABLE
        assert premium.input_cost_per_million == FABLE_INPUT
        assert premium.output_cost_per_million == FABLE_OUTPUT
        assert premium.max_tokens == 128000

    def test_tier_pricing_matches_registry_entry(self):
        premium = MODEL_REGISTRY["anthropic"]["premium"]
        assert TIER_PRICING["premium"]["input"] == premium.input_cost_per_million
        assert TIER_PRICING["premium"]["output"] == premium.output_cost_per_million

    def test_opus_stays_resolvable_by_id(self):
        """Batch premium downgrades fable -> opus-4-8; opus must stay priced."""
        registry = ModelRegistry()
        opus = registry.get_model_by_id("claude-opus-4-8")
        assert opus is not None
        assert opus.input_cost_per_million == 5.00
        assert opus.output_cost_per_million == 25.00
        assert "claude-opus-4-8" in ADDITIONAL_MODELS

    def test_opus_not_tier_routed(self):
        """Tier lookups see exactly one premium model: fable."""
        registry = ModelRegistry()
        premium_models = registry.get_models_by_tier("premium")
        assert [m.id for m in premium_models] == [FABLE]


class TestProviderTable:
    """Site 2: AnthropicProvider.get_model_info pricing table."""

    def _provider(self):
        from attune.llm.providers import AnthropicProvider

        return AnthropicProvider(api_key="test-key", model=FABLE)

    def test_fable_row_matches_registry(self):
        info = self._provider().get_model_info()
        premium = MODEL_REGISTRY["anthropic"]["premium"]
        assert info["cost_per_1m_input"] == premium.input_cost_per_million
        assert info["cost_per_1m_output"] == premium.output_cost_per_million

    def test_cache_pricing_derivation(self):
        """Cache write $12.50 / read $1.00 per MTok (1.25x / 0.1x input)."""
        cost = self._provider().calculate_actual_cost(
            input_tokens=0,
            output_tokens=0,
            cache_creation_tokens=1_000_000,
            cache_read_tokens=1_000_000,
        )
        assert cost["cache_write_cost"] == 12.50
        assert cost["cache_read_cost"] == 1.00


class TestTelemetryBaseline:
    """Site 3: analytics savings baseline prices from the registry."""

    def test_always_premium_cost_uses_fable_pricing(self):
        from attune.models.telemetry.analytics import TelemetryAnalytics
        from attune.models.telemetry.data_models import LLMCallRecord
        from attune.models.telemetry.storage import TelemetryStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            store.log_call(
                LLMCallRecord(
                    call_id="c1",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-5",
                    input_tokens=1_000_000,
                    output_tokens=1_000_000,
                    estimated_cost=18.0,
                    success=True,
                ),
            )
            stats = TelemetryAnalytics(store).sonnet_opus_fallback_analysis()

        assert stats["always_opus_cost"] == FABLE_INPUT + FABLE_OUTPUT

    def test_fable_calls_count_as_premium_fallbacks(self):
        from attune.models.telemetry.analytics import TelemetryAnalytics
        from attune.models.telemetry.data_models import LLMCallRecord
        from attune.models.telemetry.storage import TelemetryStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            store.log_call(
                LLMCallRecord(
                    call_id="c2",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id=FABLE,
                    input_tokens=1000,
                    output_tokens=500,
                    estimated_cost=0.035,
                    success=True,
                    fallback_used=True,
                ),
            )
            stats = TelemetryAnalytics(store).sonnet_opus_fallback_analysis()

        assert stats["total_calls"] == 1
        assert stats["opus_fallbacks"] == 1


class TestCostTrackerBaseline:
    """BASELINE_MODEL amendment: fable baseline, dynamic report label."""

    def test_baseline_model_is_fable(self):
        from attune.cost_tracker import BASELINE_MODEL

        assert BASELINE_MODEL == FABLE

    def test_baseline_cost_computed_at_log_time_with_fable_pricing(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / ".attune"))
        record = tracker.log_request(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            task_type="summarize",
        )
        assert record["baseline_cost"] == FABLE_INPUT + FABLE_OUTPUT
        # Haiku ($1/$5) vs fable baseline ($10/$50)
        assert record["savings"] == 54.0

    def test_fable_detected_as_premium_tier(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / ".attune"))
        assert tracker._get_tier(FABLE) == "premium"

    def test_report_label_derives_from_baseline_model(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / ".attune"))
        tracker.log_request("claude-haiku-4-5", 1000, 500, "summarize")
        tracker.flush()
        report = tracker.get_report()
        assert "Baseline (Fable):" in report
        assert "Baseline (Opus)" not in report

    def test_model_pricing_has_both_fable_and_opus(self):
        from attune.cost_tracker import MODEL_PRICING

        assert MODEL_PRICING[FABLE] == {"input": FABLE_INPUT, "output": FABLE_OUTPUT}
        assert MODEL_PRICING["claude-opus-4-8"] == {"input": 5.00, "output": 25.00}
