"""Unit tests for src/attune/workflows/builder.py

Tests cover WorkflowBuilder[T] fluent API, configuration chaining,
dependency injection, and build() correctness.

Key corrections vs naive generation:
- Attribute is `workflow_class` (not `_workflow_cls`)
- Telemetry attribute is `_telemetry_backend` (not `_telemetry`)
- Progress attribute is `_progress_callback` (not `_progress`)
- Routing attribute is `_routing_strategy` (not `_routing`)
- Context attribute is `_ctx`
- No None-validation in `with_*` setters — builder accepts None
- build() passes kwargs to workflow constructor, does NOT call config.validate()
- Progress method is `with_progress_callback()` (not `with_progress()`)
- Factory function `workflow_builder()` also available
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from attune.workflows.builder import WorkflowBuilder, workflow_builder

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


class _FakeWorkflow:
    """Minimal workflow substitute that accepts **kwargs without complaint."""

    def __init__(self, **kwargs: Any):
        self._init_kwargs = kwargs

    async def run(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return "ran"


class _AnotherWorkflow(_FakeWorkflow):
    pass


def _make_builder() -> WorkflowBuilder[_FakeWorkflow]:
    return WorkflowBuilder(_FakeWorkflow)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def builder() -> WorkflowBuilder[_FakeWorkflow]:
    return _make_builder()


# ---------------------------------------------------------------------------
# 1. Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    def test_accepts_workflow_class(self):
        builder = WorkflowBuilder(_FakeWorkflow)
        assert builder is not None

    def test_workflow_class_stored(self):
        builder = WorkflowBuilder(_FakeWorkflow)
        assert builder.workflow_class is _FakeWorkflow

    def test_different_workflow_classes_produce_independent_builders(self):
        b1 = WorkflowBuilder(_FakeWorkflow)
        b2 = WorkflowBuilder(_AnotherWorkflow)
        assert b1.workflow_class is not b2.workflow_class

    def test_initial_config_is_none(self, builder):
        assert builder._config is None

    def test_initial_executor_is_none(self, builder):
        assert builder._executor is None

    def test_initial_cache_is_none(self, builder):
        assert builder._cache is None

    def test_initial_telemetry_backend_is_none(self, builder):
        assert builder._telemetry_backend is None

    def test_initial_progress_callback_is_none(self, builder):
        assert builder._progress_callback is None

    def test_initial_routing_strategy_is_none(self, builder):
        assert builder._routing_strategy is None

    def test_initial_ctx_is_none(self, builder):
        assert builder._ctx is None

    def test_enable_cache_true_by_default(self, builder):
        assert builder._enable_cache is True

    def test_enable_telemetry_true_by_default(self, builder):
        assert builder._enable_telemetry is True


# ---------------------------------------------------------------------------
# 2. Fluent API — all with_*() methods return self
# ---------------------------------------------------------------------------


class TestFluentApiReturnsSelf:
    def test_with_config_returns_self(self, builder):
        cfg = MagicMock()
        assert builder.with_config(cfg) is builder

    def test_with_executor_returns_self(self, builder):
        assert builder.with_executor(MagicMock()) is builder

    def test_with_provider_returns_self(self, builder):
        assert builder.with_provider(MagicMock()) is builder

    def test_with_cache_returns_self(self, builder):
        assert builder.with_cache(MagicMock()) is builder

    def test_with_cache_enabled_returns_self(self, builder):
        assert builder.with_cache_enabled(False) is builder

    def test_with_telemetry_returns_self(self, builder):
        assert builder.with_telemetry(MagicMock()) is builder

    def test_with_telemetry_enabled_returns_self(self, builder):
        assert builder.with_telemetry_enabled(False) is builder

    def test_with_progress_callback_returns_self(self, builder):
        assert builder.with_progress_callback(MagicMock()) is builder

    def test_with_tier_tracker_returns_self(self, builder):
        assert builder.with_tier_tracker(MagicMock()) is builder

    def test_with_routing_returns_self(self, builder):
        assert builder.with_routing(MagicMock()) is builder

    def test_with_context_returns_self(self, builder):
        assert builder.with_context(MagicMock()) is builder

    def test_full_chain_returns_builder(self, builder):
        result = (
            builder.with_config(MagicMock())
            .with_executor(MagicMock())
            .with_cache(MagicMock())
            .with_cache_enabled(True)
            .with_telemetry(MagicMock())
            .with_telemetry_enabled(True)
            .with_progress_callback(MagicMock())
            .with_routing(MagicMock())
            .with_context(MagicMock())
        )
        assert result is builder


# ---------------------------------------------------------------------------
# 3. Setter storage — correct attribute names
# ---------------------------------------------------------------------------


class TestSetterStorage:
    def test_with_config_stores_to_config(self, builder):
        cfg = MagicMock()
        builder.with_config(cfg)
        assert builder._config is cfg

    def test_with_executor_stores_to_executor(self, builder):
        ex = MagicMock()
        builder.with_executor(ex)
        assert builder._executor is ex

    def test_with_provider_stores_to_provider(self, builder):
        prov = MagicMock()
        builder.with_provider(prov)
        assert builder._provider is prov

    def test_with_cache_stores_to_cache(self, builder):
        cache = MagicMock()
        builder.with_cache(cache)
        assert builder._cache is cache

    def test_with_cache_enabled_updates_enable_cache(self, builder):
        builder.with_cache_enabled(False)
        assert builder._enable_cache is False

    def test_with_telemetry_stores_to_telemetry_backend(self, builder):
        tel = MagicMock()
        builder.with_telemetry(tel)
        assert builder._telemetry_backend is tel

    def test_with_telemetry_enabled_updates_enable_telemetry(self, builder):
        builder.with_telemetry_enabled(False)
        assert builder._enable_telemetry is False

    def test_with_progress_callback_stores_to_progress_callback(self, builder):
        cb = MagicMock()
        builder.with_progress_callback(cb)
        assert builder._progress_callback is cb

    def test_with_tier_tracker_stores_to_tier_tracker(self, builder):
        tracker = MagicMock()
        builder.with_tier_tracker(tracker)
        assert builder._tier_tracker is tracker

    def test_with_routing_stores_to_routing_strategy(self, builder):
        strategy = MagicMock()
        builder.with_routing(strategy)
        assert builder._routing_strategy is strategy

    def test_with_context_stores_to_ctx(self, builder):
        ctx = MagicMock()
        builder.with_context(ctx)
        assert builder._ctx is ctx

    def test_last_caller_wins_on_repeated_with_config(self, builder):
        cfg1, cfg2 = MagicMock(), MagicMock()
        builder.with_config(cfg1).with_config(cfg2)
        assert builder._config is cfg2

    def test_last_caller_wins_on_repeated_with_routing(self, builder):
        s1, s2 = MagicMock(), MagicMock()
        builder.with_routing(s1).with_routing(s2)
        assert builder._routing_strategy is s2


# ---------------------------------------------------------------------------
# 4. build() — success paths
# ---------------------------------------------------------------------------


class TestBuildSuccess:
    def test_build_returns_workflow_instance(self, builder):
        instance = builder.build()
        assert isinstance(instance, _FakeWorkflow)

    def test_build_produces_new_instance_each_time(self, builder):
        w1 = builder.build()
        w2 = builder.build()
        assert w1 is not w2

    def test_build_passes_config_in_kwargs(self, builder):
        cfg = MagicMock()
        instance = builder.with_config(cfg).build()
        assert instance._init_kwargs.get("config") is cfg

    def test_build_passes_executor_in_kwargs(self, builder):
        ex = MagicMock()
        instance = builder.with_executor(ex).build()
        assert instance._init_kwargs.get("executor") is ex

    def test_build_passes_cache_in_kwargs(self, builder):
        cache = MagicMock()
        instance = builder.with_cache(cache).build()
        assert instance._init_kwargs.get("cache") is cache

    def test_build_passes_routing_strategy_in_kwargs(self, builder):
        strategy = MagicMock()
        instance = builder.with_routing(strategy).build()
        assert instance._init_kwargs.get("routing_strategy") is strategy

    def test_build_passes_ctx_in_kwargs(self, builder):
        ctx = MagicMock()
        instance = builder.with_context(ctx).build()
        assert instance._init_kwargs.get("ctx") is ctx

    def test_build_always_passes_enable_cache(self, builder):
        instance = builder.with_cache_enabled(False).build()
        assert instance._init_kwargs.get("enable_cache") is False

    def test_build_always_passes_enable_telemetry(self, builder):
        instance = builder.with_telemetry_enabled(False).build()
        assert instance._init_kwargs.get("enable_telemetry") is False

    def test_build_does_not_mutate_builder_config(self, builder):
        cfg = MagicMock()
        builder.with_config(cfg)
        builder.build()
        assert builder._config is cfg

    def test_build_result_is_not_builder(self, builder):
        assert not isinstance(builder.build(), WorkflowBuilder)

    def test_build_correct_type_for_different_class(self):
        b = WorkflowBuilder(_AnotherWorkflow)
        instance = b.build()
        assert isinstance(instance, _AnotherWorkflow)

    def test_build_subclassed_workflow(self):
        class _SubWorkflow(_FakeWorkflow):
            pass

        b = WorkflowBuilder(_SubWorkflow)
        instance = b.build()
        assert isinstance(instance, _SubWorkflow)
        assert isinstance(instance, _FakeWorkflow)


# ---------------------------------------------------------------------------
# 5. build() — omits None optional args from kwargs
# ---------------------------------------------------------------------------


class TestBuildOmitsNoneArgs:
    """build() should not pass None values for optional args."""

    def test_config_absent_from_kwargs_when_not_set(self, builder):
        instance = builder.build()
        assert "config" not in instance._init_kwargs

    def test_executor_absent_from_kwargs_when_not_set(self, builder):
        instance = builder.build()
        assert "executor" not in instance._init_kwargs

    def test_cache_absent_from_kwargs_when_not_set(self, builder):
        instance = builder.build()
        assert "cache" not in instance._init_kwargs

    def test_routing_strategy_absent_from_kwargs_when_not_set(self, builder):
        instance = builder.build()
        assert "routing_strategy" not in instance._init_kwargs

    def test_ctx_absent_from_kwargs_when_not_set(self, builder):
        instance = builder.build()
        assert "ctx" not in instance._init_kwargs


# ---------------------------------------------------------------------------
# 6. workflow_builder() factory function
# ---------------------------------------------------------------------------


class TestWorkflowBuilderFactory:
    def test_factory_returns_workflow_builder(self):
        b = workflow_builder(_FakeWorkflow)
        assert isinstance(b, WorkflowBuilder)

    def test_factory_stores_correct_class(self):
        b = workflow_builder(_FakeWorkflow)
        assert b.workflow_class is _FakeWorkflow

    def test_factory_produces_chainable_builder(self):
        instance = workflow_builder(_FakeWorkflow).with_cache_enabled(False).build()
        assert isinstance(instance, _FakeWorkflow)


# ---------------------------------------------------------------------------
# 7. Generic type parameter
# ---------------------------------------------------------------------------


class TestGenericTypeParameter:
    def test_builder_preserves_generic_type_at_build(self):
        b: WorkflowBuilder[_FakeWorkflow] = WorkflowBuilder(_FakeWorkflow)
        instance = b.build()
        assert isinstance(instance, _FakeWorkflow)

    def test_different_generic_types_build_correct_class(self):
        b1 = WorkflowBuilder(_FakeWorkflow)
        b2 = WorkflowBuilder(_AnotherWorkflow)
        assert isinstance(b1.build(), _FakeWorkflow)
        assert isinstance(b2.build(), _AnotherWorkflow)


# ---------------------------------------------------------------------------
# 8. Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_builder_repr_does_not_raise(self, builder):
        _ = repr(builder)

    def test_builder_str_does_not_raise(self, builder):
        _ = str(builder)

    def test_chaining_order_independent_for_config_and_routing(self):
        cfg = MagicMock()
        strategy = MagicMock()
        w1 = WorkflowBuilder(_FakeWorkflow).with_config(cfg).with_routing(strategy).build()
        w2 = WorkflowBuilder(_FakeWorkflow).with_routing(strategy).with_config(cfg).build()
        assert type(w1) is type(w2)

    def test_progress_callback_lambda_accepted(self, builder):
        cb = lambda update: None  # noqa: E731
        result = builder.with_progress_callback(cb)
        assert result is builder

    def test_build_idempotent_with_same_configuration(self, builder):
        builder.with_cache_enabled(False)
        w1 = builder.build()
        w2 = builder.build()
        assert isinstance(w1, _FakeWorkflow)
        assert isinstance(w2, _FakeWorkflow)
