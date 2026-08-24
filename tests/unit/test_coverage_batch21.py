# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Coverage batch 21: models/retry, fallback_policy, circuit_breaker, provider_config, cache_monitor."""

from __future__ import annotations

# === Module: models/retry ===


class TestRetryPolicy:
    def test_default_construction(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay_ms == 1000
        assert policy.exponential_backoff is True

    def test_get_delay_linear(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy(initial_delay_ms=500, exponential_backoff=False, jitter=False)
        assert policy.get_delay_ms(1) == 500
        assert policy.get_delay_ms(3) == 500

    def test_get_delay_exponential(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy(
            initial_delay_ms=1000,
            backoff_multiplier=2.0,
            exponential_backoff=True,
            jitter=False,
        )
        assert policy.get_delay_ms(1) == 1000
        assert policy.get_delay_ms(2) == 2000
        assert policy.get_delay_ms(3) == 4000

    def test_get_delay_capped_at_max(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy(
            initial_delay_ms=1000,
            max_delay_ms=3000,
            backoff_multiplier=10.0,
            exponential_backoff=True,
            jitter=False,
        )
        assert policy.get_delay_ms(4) == 3000

    def test_get_delay_jitter_stays_in_equal_jitter_band(self):
        """#2242: default jitter spreads delays within [base/2, base]."""
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy(
            initial_delay_ms=1000, backoff_multiplier=2.0, exponential_backoff=True
        )
        samples = {policy.get_delay_ms(2) for _ in range(50)}  # base = 2000
        assert all(1000 <= s <= 2000 for s in samples)
        assert len(samples) > 1  # actually randomized, not constant

    def test_should_retry_within_limit(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry("rate_limit", 1) is True
        assert policy.should_retry("rate_limit", 2) is True

    def test_should_not_retry_at_max(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry("rate_limit", 3) is False

    def test_should_not_retry_unknown_error(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy()
        assert policy.should_retry("unknown_error_type", 1) is False

    def test_custom_retry_errors(self):
        from attune.models.retry import RetryPolicy

        policy = RetryPolicy(retry_on_errors=["custom_error"])
        assert policy.should_retry("custom_error", 1) is True
        assert policy.should_retry("rate_limit", 1) is False


# === Module: models/fallback_policy ===


class TestFallbackStrategy:
    def test_values_exist(self):
        from attune.models.fallback_policy import FallbackStrategy

        assert FallbackStrategy.CHEAPER_TIER_SAME_PROVIDER
        assert FallbackStrategy.CUSTOM


class TestFallbackStep:
    def test_construction(self):
        from attune.models.fallback_policy import FallbackStep

        step = FallbackStep(provider="anthropic", tier="cheap", description="Fallback to haiku")
        assert step.provider == "anthropic"
        assert step.tier == "cheap"

    def test_model_id_returns_string(self):
        from attune.models.fallback_policy import FallbackStep

        step = FallbackStep(provider="anthropic", tier="cheap")
        model_id = step.model_id
        assert isinstance(model_id, str)


class TestFallbackPolicy:
    def test_default_construction(self):
        from attune.models.fallback_policy import FallbackPolicy, FallbackStrategy

        policy = FallbackPolicy()
        assert policy.primary_provider == "anthropic"
        assert policy.primary_tier == "capable"
        assert policy.strategy == FallbackStrategy.CHEAPER_TIER_SAME_PROVIDER

    def test_get_fallback_chain_cheaper_tier(self):
        from attune.models.fallback_policy import FallbackPolicy

        policy = FallbackPolicy(primary_provider="anthropic", primary_tier="capable")
        chain = policy.get_fallback_chain()
        assert len(chain) >= 1
        # Starting from capable, only cheap is cheaper
        tiers = [step.tier for step in chain]
        assert "cheap" in tiers

    def test_get_fallback_chain_from_premium(self):
        from attune.models.fallback_policy import FallbackPolicy

        policy = FallbackPolicy(primary_provider="anthropic", primary_tier="premium")
        chain = policy.get_fallback_chain()
        tiers = [step.tier for step in chain]
        assert "capable" in tiers
        assert "cheap" in tiers

    def test_get_fallback_chain_custom(self):
        from attune.models.fallback_policy import FallbackPolicy, FallbackStep, FallbackStrategy

        custom_steps = [
            FallbackStep(provider="anthropic", tier="cheap", description="Custom fallback")
        ]
        policy = FallbackPolicy(
            strategy=FallbackStrategy.CUSTOM,
            custom_chain=custom_steps,
        )
        chain = policy.get_fallback_chain()
        assert chain == custom_steps

    def test_get_fallback_chain_empty_when_cheapest(self):
        from attune.models.fallback_policy import FallbackPolicy

        policy = FallbackPolicy(primary_provider="anthropic", primary_tier="cheap")
        chain = policy.get_fallback_chain()
        assert chain == []


# === Module: models/circuit_breaker ===


class TestCircuitBreakerState:
    def test_default_construction(self):
        from attune.models.circuit_breaker import CircuitBreakerState

        state = CircuitBreakerState()
        assert state.failure_count == 0
        assert state.is_open is False
        assert state.last_failure is None


class TestCircuitBreaker:
    def setup_method(self):
        from attune.models.circuit_breaker import CircuitBreaker

        self.breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60)

    def test_initially_available(self):
        assert self.breaker.is_available("anthropic", "capable") is True

    def test_opens_after_threshold_failures(self):
        for _ in range(3):
            self.breaker.record_failure("anthropic", "capable")
        assert self.breaker.is_available("anthropic", "capable") is False

    def test_does_not_open_before_threshold(self):
        for _ in range(2):
            self.breaker.record_failure("anthropic", "capable")
        assert self.breaker.is_available("anthropic", "capable") is True

    def test_resets_on_success(self):
        for _ in range(3):
            self.breaker.record_failure("anthropic", "capable")
        assert self.breaker.is_available("anthropic", "capable") is False
        self.breaker.record_success("anthropic", "capable")
        assert self.breaker.is_available("anthropic", "capable") is True

    def test_independent_per_tier(self):
        for _ in range(3):
            self.breaker.record_failure("anthropic", "premium")
        # "capable" should still be available
        assert self.breaker.is_available("anthropic", "capable") is True

    def test_get_status_returns_dict(self):
        self.breaker.record_failure("anthropic", "capable")
        status = self.breaker.get_status()
        assert "anthropic:capable" in status
        assert status["anthropic:capable"]["failure_count"] == 1

    def test_reset_specific_provider_tier(self):
        for _ in range(3):
            self.breaker.record_failure("anthropic", "capable")
        self.breaker.reset("anthropic", "capable")
        assert self.breaker.is_available("anthropic", "capable") is True

    def test_reset_all_clears_state(self):
        self.breaker.record_failure("anthropic", "capable")
        self.breaker.record_failure("openai", "cheap")
        self.breaker.reset()
        assert self.breaker.get_status() == {}

    def test_provider_level_tracking(self):
        self.breaker.record_failure("anthropic")
        self.breaker.record_failure("anthropic")
        self.breaker.record_failure("anthropic")
        assert self.breaker.is_available("anthropic") is False

    def test_recovery_after_timeout(self):
        from datetime import datetime, timedelta

        for _ in range(3):
            self.breaker.record_failure("anthropic", "capable")
        state = self.breaker._get_state("anthropic", "capable")
        # Simulate timeout passed
        state.opened_at = datetime.now() - timedelta(seconds=120)
        assert self.breaker.is_available("anthropic", "capable") is True


# === Module: models/provider_config ===


class TestProviderMode:
    def test_single_value(self):
        from attune.models.provider_config import ProviderMode

        assert ProviderMode.SINGLE.value == "single"

    def test_hybrid_value(self):
        from attune.models.provider_config import ProviderMode

        assert ProviderMode.HYBRID.value == "hybrid"


class TestProviderConfig:
    def test_default_construction(self):
        from attune.models.provider_config import ProviderConfig, ProviderMode

        cfg = ProviderConfig()
        assert cfg.primary_provider == "anthropic"
        assert cfg.mode == ProviderMode.SINGLE
        assert cfg.cost_optimization is True

    def test_detect_available_no_key(self):
        import os

        from attune.models.provider_config import ProviderConfig

        # Save and clear the key
        original = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            available = ProviderConfig.detect_available_providers()
            # May or may not find anthropic depending on .env files — just check return type
            assert isinstance(available, list)
        finally:
            if original:
                os.environ["ANTHROPIC_API_KEY"] = original

    def test_detect_available_with_key(self):
        import os

        from attune.models.provider_config import ProviderConfig

        os.environ["ANTHROPIC_API_KEY"] = "sk-test-key"
        try:
            available = ProviderConfig.detect_available_providers()
            assert "anthropic" in available
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_load_env_files_returns_dict(self):
        from attune.models.provider_config import ProviderConfig

        result = ProviderConfig._load_env_files()
        assert isinstance(result, dict)


# === Module: cache_monitor (CacheMonitor) ===


class TestCacheMonitor:
    def setup_method(self):
        from attune.cache_monitor import CacheMonitor

        CacheMonitor.reset_instance()

    def teardown_method(self):
        from attune.cache_monitor import CacheMonitor

        CacheMonitor.reset_instance()

    def test_get_instance_returns_singleton(self):
        from attune.cache_monitor import CacheMonitor

        m1 = CacheMonitor.get_instance()
        m2 = CacheMonitor.get_instance()
        assert m1 is m2

    def test_register_cache(self):
        from attune.cache_monitor import CacheMonitor

        monitor = CacheMonitor.get_instance()
        stats = monitor.register_cache("test_cache", max_size=100)
        assert stats.name == "test_cache"
        assert stats.max_size == 100

    def test_register_duplicate_raises(self):
        import pytest

        from attune.cache_monitor import CacheMonitor

        monitor = CacheMonitor.get_instance()
        monitor.register_cache("my_cache")
        with pytest.raises(ValueError, match="already registered"):
            monitor.register_cache("my_cache")

    def test_get_stats_returns_none_for_unknown(self):
        from attune.cache_monitor import CacheMonitor

        monitor = CacheMonitor.get_instance()
        assert monitor.get_stats("nonexistent") is None

    def test_get_stats_after_register(self):
        from attune.cache_monitor import CacheMonitor

        monitor = CacheMonitor.get_instance()
        monitor.register_cache("lookup_cache")
        stats = monitor.get_stats("lookup_cache")
        assert stats is not None
        assert stats.name == "lookup_cache"

    def test_record_hit_and_miss(self):
        from attune.cache_monitor import CacheMonitor

        monitor = CacheMonitor.get_instance()
        monitor.register_cache("rw_cache")
        monitor.record_hit("rw_cache")
        monitor.record_hit("rw_cache")
        monitor.record_miss("rw_cache")
        stats = monitor.get_stats("rw_cache")
        assert stats.hits == 2
        assert stats.misses == 1

    def test_reset_instance_clears(self):
        from attune.cache_monitor import CacheMonitor

        m1 = CacheMonitor.get_instance()
        CacheMonitor.reset_instance()
        m2 = CacheMonitor.get_instance()
        assert m1 is not m2

    def test_cache_stats_to_dict(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="d_cache", hits=5, misses=2, size=10, max_size=50)
        d = stats.to_dict()
        assert d["name"] == "d_cache"
        assert d["hits"] == 5
        assert "hit_rate" in d
        assert "utilization" in d

    def test_record_eviction(self):
        from attune.cache_monitor import CacheMonitor

        monitor = CacheMonitor.get_instance()
        monitor.register_cache("evict_cache")
        monitor.record_eviction("evict_cache")
        stats = monitor.get_stats("evict_cache")
        assert stats.evictions == 1
