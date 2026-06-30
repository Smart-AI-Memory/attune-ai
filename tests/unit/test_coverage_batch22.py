# Copyright 2025 Smart AI Memory, LLC
# Licensed under the Apache License, Version 2.0

"""Batch 22: models/registry, models/tasks, models/token_estimator,
models/adaptive_routing, models/resilient_executor."""

from __future__ import annotations

import pytest

# =============================================================================
# models/registry.py
# =============================================================================


class TestModelInfo:
    def setup_method(self):
        from attune.models.registry import ModelInfo

        self.info = ModelInfo(
            id="claude-sonnet-5",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=3.0,
            output_cost_per_million=15.0,
            max_tokens=8192,
            supports_vision=True,
            supports_tools=True,
        )

    def test_id(self):
        assert self.info.id == "claude-sonnet-5"

    def test_model_id_alias(self):
        assert self.info.model_id == "claude-sonnet-5"

    def test_name_alias(self):
        assert self.info.name == "claude-sonnet-5"

    def test_cost_per_1k_input(self):
        assert self.info.cost_per_1k_input == pytest.approx(0.003)

    def test_cost_per_1k_output(self):
        assert self.info.cost_per_1k_output == pytest.approx(0.015)

    def test_to_router_config(self):
        cfg = self.info.to_router_config()
        assert cfg["model_id"] == "claude-sonnet-5"
        assert "cost_per_1k_input" in cfg
        assert "max_tokens" in cfg

    def test_to_workflow_config(self):
        cfg = self.info.to_workflow_config()
        assert cfg["name"] == "claude-sonnet-5"
        assert cfg["tier"] == "capable"

    def test_to_cost_tracker_pricing(self):
        pricing = self.info.to_cost_tracker_pricing()
        assert pricing == {"input": 3.0, "output": 15.0}


class TestModelRegistry:
    def setup_method(self):
        from attune.models.registry import ModelRegistry

        self.registry = ModelRegistry()

    def test_get_model_anthropic_capable(self):
        model = self.registry.get_model("anthropic", "capable")
        assert model is not None
        assert model.id == "claude-sonnet-5"

    def test_get_model_anthropic_cheap(self):
        model = self.registry.get_model("anthropic", "cheap")
        assert model is not None
        assert "haiku" in model.id.lower()

    def test_get_model_anthropic_premium(self):
        model = self.registry.get_model("anthropic", "premium")
        assert model is not None
        assert "opus" in model.id.lower()

    def test_get_model_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="not supported"):
            self.registry.get_model("openai", "capable")

    def test_get_model_invalid_tier_returns_none(self):
        result = self.registry.get_model("anthropic", "nonexistent")
        assert result is None

    def test_get_model_by_id_found(self):
        model = self.registry.get_model_by_id("claude-sonnet-5")
        assert model is not None
        assert model.tier == "capable"

    def test_get_model_by_id_not_found(self):
        result = self.registry.get_model_by_id("nonexistent-model")
        assert result is None

    def test_get_models_by_tier_cheap(self):
        models = self.registry.get_models_by_tier("cheap")
        assert len(models) == 1
        assert models[0].provider == "anthropic"

    def test_get_models_by_tier_unknown(self):
        models = self.registry.get_models_by_tier("nonexistent")
        assert models == []

    def test_list_providers(self):
        providers = self.registry.list_providers()
        assert "anthropic" in providers

    def test_list_tiers(self):
        tiers = self.registry.list_tiers()
        assert "cheap" in tiers
        assert "capable" in tiers
        assert "premium" in tiers

    def test_get_all_models(self):
        all_models = self.registry.get_all_models()
        assert "anthropic" in all_models

    def test_get_pricing_for_model_found(self):
        pricing = self.registry.get_pricing_for_model("claude-sonnet-5")
        assert pricing is not None
        assert pricing["input"] == 3.0
        assert pricing["output"] == 15.0

    def test_get_pricing_for_model_not_found(self):
        pricing = self.registry.get_pricing_for_model("nonexistent")
        assert pricing is None


class TestRegistryHelpers:
    def test_get_model_function(self):
        from attune.models.registry import get_model

        model = get_model("anthropic", "capable")
        assert model is not None

    def test_get_all_models_function(self):
        from attune.models.registry import get_all_models

        models = get_all_models()
        assert "anthropic" in models

    def test_get_pricing_for_model_function(self):
        from attune.models.registry import get_pricing_for_model

        pricing = get_pricing_for_model("claude-opus-4-8")
        assert pricing is not None
        assert pricing["input"] == 5.0

    def test_get_supported_providers(self):
        from attune.models.registry import get_supported_providers

        providers = get_supported_providers()
        assert "anthropic" in providers

    def test_get_tiers(self):
        from attune.models.registry import get_tiers

        tiers = get_tiers()
        assert "cheap" in tiers

    def test_tier_pricing_constant(self):
        from attune.models.registry import TIER_PRICING

        assert "cheap" in TIER_PRICING
        assert "capable" in TIER_PRICING
        assert "premium" in TIER_PRICING


# =============================================================================
# models/tasks.py
# =============================================================================


class TestTaskType:
    def test_enum_values(self):
        from attune.models.tasks import TaskType

        assert TaskType.SUMMARIZE.value == "summarize"
        assert TaskType.GENERATE_CODE.value == "generate_code"
        assert TaskType.COORDINATE.value == "coordinate"

    def test_all_three_tiers_represented(self):
        from attune.models.tasks import CAPABLE_TASKS, CHEAP_TASKS, PREMIUM_TASKS

        assert "summarize" in CHEAP_TASKS
        assert "generate_code" in CAPABLE_TASKS
        assert "coordinate" in PREMIUM_TASKS


class TestTaskHelpers:
    def test_normalize_task_type_lowercase(self):
        from attune.models.tasks import normalize_task_type

        assert normalize_task_type("Fix-Bug") == "fix_bug"

    def test_normalize_task_type_spaces(self):
        from attune.models.tasks import normalize_task_type

        assert normalize_task_type("fix bug") == "fix_bug"

    def test_normalize_task_type_already_normalized(self):
        from attune.models.tasks import normalize_task_type

        assert normalize_task_type("fix_bug") == "fix_bug"

    def test_get_tier_for_task_cheap(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import get_tier_for_task

        tier = get_tier_for_task("summarize")
        assert tier == ModelTier.CHEAP

    def test_get_tier_for_task_capable(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import get_tier_for_task

        tier = get_tier_for_task("fix_bug")
        assert tier == ModelTier.CAPABLE

    def test_get_tier_for_task_premium(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import get_tier_for_task

        tier = get_tier_for_task("coordinate")
        assert tier == ModelTier.PREMIUM

    def test_get_tier_for_task_unknown_defaults_capable(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import get_tier_for_task

        tier = get_tier_for_task("totally_unknown_task")
        assert tier == ModelTier.CAPABLE

    def test_get_tier_for_task_enum_input(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import TaskType, get_tier_for_task

        tier = get_tier_for_task(TaskType.SUMMARIZE)
        assert tier == ModelTier.CHEAP

    def test_get_tasks_for_tier_cheap(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import get_tasks_for_tier

        tasks = get_tasks_for_tier(ModelTier.CHEAP)
        assert "summarize" in tasks

    def test_get_tasks_for_tier_capable(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import get_tasks_for_tier

        tasks = get_tasks_for_tier(ModelTier.CAPABLE)
        assert "fix_bug" in tasks

    def test_get_tasks_for_tier_premium(self):
        from attune.models.registry import ModelTier
        from attune.models.tasks import get_tasks_for_tier

        tasks = get_tasks_for_tier(ModelTier.PREMIUM)
        assert "coordinate" in tasks

    def test_get_all_tasks(self):
        from attune.models.tasks import get_all_tasks

        all_tasks = get_all_tasks()
        assert "cheap" in all_tasks
        assert "capable" in all_tasks
        assert "premium" in all_tasks

    def test_is_known_task_known(self):
        from attune.models.tasks import is_known_task

        assert is_known_task("summarize") is True

    def test_is_known_task_unknown(self):
        from attune.models.tasks import is_known_task

        assert is_known_task("totally_unknown") is False

    def test_is_known_task_normalizes(self):
        from attune.models.tasks import is_known_task

        assert is_known_task("Fix-Bug") is True

    def test_batch_eligible_tasks(self):
        from attune.models.tasks import BATCH_ELIGIBLE_TASKS

        assert "summarize" in BATCH_ELIGIBLE_TASKS

    def test_realtime_required_tasks(self):
        from attune.models.tasks import REALTIME_REQUIRED_TASKS

        assert "chat" in REALTIME_REQUIRED_TASKS

    def test_task_info_registry(self):
        from attune.models.tasks import TASK_INFO, TaskType

        assert TaskType.SUMMARIZE in TASK_INFO
        info = TASK_INFO[TaskType.SUMMARIZE]
        assert info.description != ""


# =============================================================================
# models/token_estimator.py
# =============================================================================


class TestEstimateTokens:
    def test_empty_text_returns_zero(self):
        from attune.models.token_estimator import estimate_tokens

        assert estimate_tokens("") == 0

    def test_empty_model_id_raises(self):
        from attune.models.token_estimator import estimate_tokens

        with pytest.raises(ValueError, match="model_id"):
            estimate_tokens("hello", model_id="")

    def test_nonempty_text_returns_positive(self):
        from attune.models.token_estimator import estimate_tokens

        count = estimate_tokens("Hello, world!", model_id="claude-sonnet-5")
        assert count > 0

    def test_longer_text_more_tokens(self):
        from attune.models.token_estimator import estimate_tokens

        short = estimate_tokens("hi", model_id="claude-sonnet-5")
        long = estimate_tokens("hi " * 100, model_id="claude-sonnet-5")
        assert long > short


class TestDetermineRiskLevel:
    def test_low_risk(self):
        from attune.models.token_estimator import _determine_risk_level

        assert _determine_risk_level(0.05) == "low"

    def test_medium_risk(self):
        from attune.models.token_estimator import _determine_risk_level

        assert _determine_risk_level(0.5) == "medium"

    def test_high_risk(self):
        from attune.models.token_estimator import _determine_risk_level

        assert _determine_risk_level(2.0) == "high"


class TestEstimateWorkflowCost:
    def test_empty_workflow_name_raises(self):
        from attune.models.token_estimator import estimate_workflow_cost

        with pytest.raises(ValueError, match="workflow_name"):
            estimate_workflow_cost("", "some input")

    def test_empty_provider_raises(self):
        from attune.models.token_estimator import estimate_workflow_cost

        with pytest.raises(ValueError, match="provider"):
            estimate_workflow_cost("security-audit", "some input", provider="")

    def test_known_workflow_returns_dict(self):
        from attune.models.token_estimator import estimate_workflow_cost

        result = estimate_workflow_cost("security-audit", "def foo(): pass")
        assert result["workflow"] == "security-audit"
        assert "input_tokens" in result
        assert "stages" in result
        assert "total_min" in result
        assert "total_max" in result
        assert "display" in result
        assert "risk" in result

    def test_unknown_workflow_uses_default_stages(self):
        from attune.models.token_estimator import estimate_workflow_cost

        result = estimate_workflow_cost("nonexistent-workflow", "some code")
        assert result["stages"] != []

    def test_invalid_provider_falls_back_to_anthropic(self):
        from attune.models.token_estimator import estimate_workflow_cost

        result = estimate_workflow_cost("code-review", "code", provider="openai")
        assert result["provider"] == "anthropic"

    def test_risk_field_is_valid(self):
        from attune.models.token_estimator import estimate_workflow_cost

        result = estimate_workflow_cost("code-review", "some input")
        assert result["risk"] in ("low", "medium", "high")

    def test_display_starts_with_dollar(self):
        from attune.models.token_estimator import estimate_workflow_cost

        result = estimate_workflow_cost("doc-gen", "text here")
        assert result["display"].startswith("$")


class TestEstimateSingleCallCost:
    def test_empty_task_type_raises(self):
        from attune.models.token_estimator import estimate_single_call_cost

        with pytest.raises(ValueError, match="task_type"):
            estimate_single_call_cost("text", "")

    def test_empty_provider_raises(self):
        from attune.models.token_estimator import estimate_single_call_cost

        with pytest.raises(ValueError, match="provider"):
            estimate_single_call_cost("text", "summarize", provider="")

    def test_known_task_type_returns_dict(self):
        from attune.models.token_estimator import estimate_single_call_cost

        result = estimate_single_call_cost("hello world", "summarize")
        assert result["task_type"] == "summarize"
        assert "input_tokens" in result
        assert "estimated_cost" in result

    def test_display_starts_with_dollar(self):
        from attune.models.token_estimator import estimate_single_call_cost

        result = estimate_single_call_cost("hello", "generate_code")
        assert result["display"].startswith("$")


class TestWorkflowStagesConstant:
    def test_security_audit_stages(self):
        from attune.models.token_estimator import WORKFLOW_STAGES

        assert "security-audit" in WORKFLOW_STAGES
        stages = WORKFLOW_STAGES["security-audit"]
        assert len(stages) >= 2

    def test_output_multipliers(self):
        from attune.models.token_estimator import OUTPUT_MULTIPLIERS

        assert "generate" in OUTPUT_MULTIPLIERS
        assert OUTPUT_MULTIPLIERS["generate"] > 1.0


# =============================================================================
# models/adaptive_routing.py
# =============================================================================


class FakeTelemetry:
    """Minimal telemetry stub for AdaptiveModelRouter tests."""

    def __init__(self, entries=None):
        self._entries = entries or []

    def get_recent_entries(self, limit=10000, days=7):
        return self._entries


class TestModelPerformance:
    def test_quality_score_high_success(self):
        from attune.models.adaptive_routing import ModelPerformance

        perf = ModelPerformance(
            model_id="claude-sonnet-5",
            tier="capable",
            success_rate=1.0,
            avg_latency_ms=500,
            avg_cost=0.001,
            sample_size=100,
        )
        assert perf.quality_score > 90

    def test_quality_score_zero_success(self):
        from attune.models.adaptive_routing import ModelPerformance

        perf = ModelPerformance(
            model_id="some-model",
            tier="cheap",
            success_rate=0.0,
            avg_latency_ms=100,
            avg_cost=0.0,
            sample_size=50,
        )
        assert perf.quality_score == 0.0


class TestAdaptiveModelRouterNoHistory:
    def setup_method(self):
        from attune.models.adaptive_routing import AdaptiveModelRouter

        self.router = AdaptiveModelRouter(FakeTelemetry())

    def test_get_best_model_no_history_returns_default(self):
        model = self.router.get_best_model("code-review", "analysis")
        assert isinstance(model, str)
        assert len(model) > 0

    def test_recommend_tier_upgrade_insufficient_data(self):
        should_upgrade, reason = self.router.recommend_tier_upgrade("code-review", "analysis")
        assert should_upgrade is False
        assert "Insufficient" in reason

    def test_get_routing_stats_no_history(self):
        stats = self.router.get_routing_stats("code-review")
        assert stats["total_calls"] == 0
        assert stats["models_used"] == []


class TestAdaptiveModelRouterWithHistory:
    def _make_entries(self, n_success, n_failure, workflow="code-review", stage="analysis"):
        entries = []
        for _ in range(n_success):
            entries.append(
                {
                    "workflow": workflow,
                    "stage": stage,
                    "model": "claude-sonnet-5",
                    "tier": "capable",
                    "success": True,
                    "cost": 0.001,
                    "duration_ms": 500,
                }
            )
        for _ in range(n_failure):
            entries.append(
                {
                    "workflow": workflow,
                    "stage": stage,
                    "model": "claude-sonnet-5",
                    "tier": "capable",
                    "success": False,
                    "cost": 0.001,
                    "duration_ms": 500,
                }
            )
        return entries

    def test_get_best_model_with_good_history(self):
        from attune.models.adaptive_routing import AdaptiveModelRouter

        entries = self._make_entries(15, 0)
        router = AdaptiveModelRouter(FakeTelemetry(entries))
        model = router.get_best_model("code-review", "analysis", min_success_rate=0.8)
        assert model == "claude-sonnet-5"

    def test_get_best_model_all_filtered_returns_default(self):
        from unittest.mock import patch

        from attune.models.adaptive_routing import AdaptiveModelRouter

        entries = self._make_entries(15, 0)
        router = AdaptiveModelRouter(FakeTelemetry(entries))
        # Require zero cost — all candidates filtered; patch logger to avoid structlog-style call
        with patch("attune.models.adaptive_routing.logger"):
            model = router.get_best_model("code-review", "analysis", max_cost=0.0)
        assert isinstance(model, str)

    def test_recommend_tier_upgrade_low_failure_rate(self):
        from attune.models.adaptive_routing import AdaptiveModelRouter

        entries = self._make_entries(15, 1)
        router = AdaptiveModelRouter(FakeTelemetry(entries))
        should_upgrade, reason = router.recommend_tier_upgrade("code-review", "analysis")
        assert should_upgrade is False

    def test_recommend_tier_upgrade_high_failure_rate(self):
        from attune.models.adaptive_routing import AdaptiveModelRouter

        # 8 failures in 20 = 40% failure rate
        entries = self._make_entries(12, 8)
        router = AdaptiveModelRouter(FakeTelemetry(entries))
        should_upgrade, reason = router.recommend_tier_upgrade("code-review", "analysis")
        assert should_upgrade is True
        assert "failure rate" in reason.lower()

    def test_get_routing_stats_with_data(self):
        from attune.models.adaptive_routing import AdaptiveModelRouter

        entries = self._make_entries(10, 0)
        router = AdaptiveModelRouter(FakeTelemetry(entries))
        stats = router.get_routing_stats("code-review", stage="analysis")
        assert stats["total_calls"] == 10
        assert "claude-sonnet-5" in stats["models_used"]
        assert stats["avg_success_rate"] == 1.0

    def test_get_routing_stats_all_stages(self):
        from attune.models.adaptive_routing import AdaptiveModelRouter

        entries = self._make_entries(5, 0)
        router = AdaptiveModelRouter(FakeTelemetry(entries))
        stats = router.get_routing_stats("code-review")
        assert stats["total_calls"] == 5


# =============================================================================
# models/resilient_executor.py
# =============================================================================


class TestAllProvidersFailedError:
    def test_has_attempts_attribute(self):
        from attune.models.resilient_executor import AllProvidersFailedError

        err = AllProvidersFailedError("All failed", attempts=[{"provider": "anthropic"}])
        assert len(err.attempts) == 1
        assert str(err) == "All failed"


class TestResilientExecutorInit:
    def test_defaults(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex.fallback_policy is not None
        assert ex.circuit_breaker is not None
        assert ex.retry_policy is not None

    def test_no_executor_raises_on_run(self):
        import asyncio

        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()

        with pytest.raises(RuntimeError, match="requires an inner executor"):
            asyncio.run(ex.run("summarize", "test"))

    def test_get_model_for_task_no_inner(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex.get_model_for_task("summarize") == ""

    def test_estimate_cost_no_inner(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex.estimate_cost("summarize", 100, 50) == 0.0

    def test_classify_error_rate_limit(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex._classify_error(Exception("rate limit exceeded")) == "rate_limit"

    def test_classify_error_timeout(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex._classify_error(Exception("request timeout")) == "timeout"

    def test_classify_error_connection(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex._classify_error(Exception("connection refused")) == "connection_error"

    def test_classify_error_server_500(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex._classify_error(Exception("500 internal server error")) == "server_error"

    def test_classify_error_unknown(self):
        from attune.models.resilient_executor import ResilientExecutor

        ex = ResilientExecutor()
        assert ex._classify_error(Exception("something weird")) == "unknown"


class TestFallbackModule:
    def test_imports(self):
        from attune.models.fallback import (
            DEFAULT_FALLBACK_POLICY,
            DEFAULT_RETRY_POLICY,
            SONNET_TO_OPUS_FALLBACK,
            AllProvidersFailedError,
            CircuitBreaker,
            FallbackPolicy,
            ResilientExecutor,
            RetryPolicy,
        )

        assert DEFAULT_FALLBACK_POLICY is not None
        assert DEFAULT_RETRY_POLICY is not None
        assert SONNET_TO_OPUS_FALLBACK is not None
        assert AllProvidersFailedError is not None
        assert CircuitBreaker is not None
        assert FallbackPolicy is not None
        assert ResilientExecutor is not None
        assert RetryPolicy is not None
