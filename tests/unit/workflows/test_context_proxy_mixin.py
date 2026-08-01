"""Coverage tests for ContextProxyMixin's ctx-vs-fallback proxy branches.

ContextProxyMixin proxies BaseWorkflow's mixin methods to WorkflowContext
services when ``self._ctx`` (and the relevant service slot) is populated,
and falls back to the original mixin implementation via ``super()``
otherwise. Each test pairs a ctx-populated case (asserts the ctx service
method was called with the right args and its return value passed through)
with a no-ctx case (asserts the mixin fallback still runs).

Targets: src/attune/workflows/context_proxy_mixin.py lines
47, 60, 64-66, 91, 152-153, 166-167, 190-191, 194, 203, 228, 257,
333, 351, 373, 394 (per Codecov main, 68.7% -> target >=85%).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from attune.workflows.base import BaseWorkflow, ModelTier
from attune.workflows.caching import CachedResponse
from attune.workflows.context import WorkflowContext


class SimpleWorkflow(BaseWorkflow):
    """Minimal concrete host workflow for exercising ContextProxyMixin."""

    name = "context-proxy-test-workflow"
    description = "Host for context proxy mixin coverage"
    stages = ["stage1"]
    tier_map = {"stage1": ModelTier.CHEAP}

    async def run_stage(self, stage_name, tier, input_data):
        return {"stage": stage_name}, 1, 1


@pytest.fixture
def workflow() -> SimpleWorkflow:
    """Workflow with no ctx -- exercises the mixin-fallback (super()) branches."""
    return SimpleWorkflow()


@pytest.fixture
def ctx_workflow() -> tuple[SimpleWorkflow, WorkflowContext]:
    """Workflow with a fully-mocked WorkflowContext -- exercises ctx branches."""
    ctx = WorkflowContext(
        cache=MagicMock(name="cache_service"),
        cost=MagicMock(name="cost_service"),
        telemetry=MagicMock(name="telemetry_service"),
        prompt=MagicMock(name="prompt_service"),
        parsing=MagicMock(name="parsing_service"),
        tier=MagicMock(name="tier_service"),
        coordination=MagicMock(name="coordination_service"),
    )
    wf = SimpleWorkflow(ctx=ctx)
    return wf, ctx


# ---------------------------------------------------------------------------
# Cache proxies (line 47, 60, 64-66)
# ---------------------------------------------------------------------------


class TestCacheProxies:
    """_try_cache_lookup / _store_in_cache / _get_cache_type."""

    def test_try_cache_lookup_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        ctx.cache.lookup.return_value = "cached-response"

        result = wf._try_cache_lookup("stage", "sys", "msg", "model")

        ctx.cache.lookup.assert_called_once_with("stage", "sys", "msg", "model")
        assert result == "cached-response"

    def test_try_cache_lookup_falls_back_without_ctx(self, workflow):
        # CachingMixin is a no-op cache -- fallback always misses (None).
        assert workflow._try_cache_lookup("stage", "sys", "msg", "model") is None

    def test_store_in_cache_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        response = CachedResponse(content="c", input_tokens=1, output_tokens=2)
        ctx.cache.store.return_value = True

        result = wf._store_in_cache("stage", "sys", "msg", "model", response)

        ctx.cache.store.assert_called_once_with("stage", "sys", "msg", "model", response)
        assert result is True

    def test_store_in_cache_falls_back_without_ctx(self, workflow):
        response = CachedResponse(content="c", input_tokens=1, output_tokens=2)
        assert workflow._store_in_cache("stage", "sys", "msg", "model", response) is False

    def test_get_cache_type_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        ctx.cache.get_cache_type.return_value = "redis"

        assert wf._get_cache_type() == "redis"
        ctx.cache.get_cache_type.assert_called_once_with()

    def test_get_cache_type_falls_back_without_ctx(self, workflow):
        # CachingMixin's no-op fallback reports server-side ("anthropic") caching.
        assert workflow._get_cache_type() == "anthropic"


# ---------------------------------------------------------------------------
# Cost proxies (line 91)
# ---------------------------------------------------------------------------


class TestCostProxies:
    """_generate_cost_report."""

    def test_generate_cost_report_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        wf._stages_run = ["stage-a", "stage-b"]
        ctx.cost.generate_report.return_value = "report-object"

        result = wf._generate_cost_report()

        ctx.cost.generate_report.assert_called_once_with(["stage-a", "stage-b"])
        assert result == "report-object"


# ---------------------------------------------------------------------------
# Telemetry proxies (lines 152-153, 166-167, 190-191, 194, 203)
# ---------------------------------------------------------------------------


class TestTelemetryProxies:
    """_emit_call_telemetry / _emit_workflow_telemetry / _generate_run_id."""

    def test_emit_call_telemetry_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow

        result = wf._emit_call_telemetry(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model-x",
            input_tokens=10,
            output_tokens=20,
            cost=0.05,
            latency_ms=100,
            success=False,
            error_message="boom",
            fallback_used=True,
        )

        ctx.telemetry.emit_call_record.assert_called_once_with(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model-x",
            input_tokens=10,
            output_tokens=20,
            cost=0.05,
            latency_ms=100,
            success=False,
            error_message="boom",
            fallback_used=True,
        )
        assert result is None

    def test_emit_call_telemetry_falls_back_without_ctx(self, workflow):
        # TelemetryMixin's fallback never raises even without a real backend
        # wired up for this stand-alone host -- exercises the super() path.
        result = workflow._emit_call_telemetry(
            step_name="step",
            task_type="task",
            tier="cheap",
            model_id="model-x",
            input_tokens=10,
            output_tokens=20,
            cost=0.05,
            latency_ms=100,
        )
        assert result is None

    def test_emit_workflow_telemetry_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        result_obj = MagicMock(name="workflow_result")

        wf._emit_workflow_telemetry(result_obj, started_at=None, completed_at=None)

        ctx.telemetry.emit_workflow_record.assert_called_once()
        call_args = ctx.telemetry.emit_workflow_record.call_args
        assert call_args.args[0] is result_obj
        assert call_args.args[1] == wf.get_model_for_tier
        assert call_args.kwargs == {"started_at": None, "completed_at": None}

    def test_generate_run_id_falls_back_without_ctx(self, workflow):
        run_id = workflow._generate_run_id()

        assert isinstance(run_id, str)
        assert run_id
        assert workflow._run_id == run_id


# ---------------------------------------------------------------------------
# Prompt proxies (lines 228, 257)
# ---------------------------------------------------------------------------


class TestPromptProxies:
    """_build_cached_system_prompt / _render_xml_prompt fallback branches."""

    def test_build_cached_system_prompt_falls_back_without_ctx(self, workflow):
        prompt = workflow._build_cached_system_prompt(
            role="code reviewer",
            guidelines=["Follow PEP 8"],
            documentation="Some docs",
            examples=[{"input": "in", "output": "out"}],
        )

        assert "code reviewer" in prompt
        assert "Follow PEP 8" in prompt

    def test_render_xml_prompt_falls_back_without_ctx(self, workflow):
        prompt = workflow._render_xml_prompt(
            role="analyst",
            goal="review the diff",
            instructions=["step one"],
            constraints=["be concise"],
            input_type="diff",
            input_payload="diff content",
        )

        assert isinstance(prompt, str)
        assert prompt


# ---------------------------------------------------------------------------
# Tier routing proxy (line 333)
# ---------------------------------------------------------------------------


class TestTierRoutingProxy:
    """_get_tier_with_routing."""

    def test_get_tier_with_routing_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        ctx.tier.get_tier.return_value = ModelTier.PREMIUM

        result = wf._get_tier_with_routing("stage1", {"key": "val"}, budget_remaining=42.0)

        ctx.tier.get_tier.assert_called_once_with("stage1", {"key": "val"}, 42.0)
        assert result is ModelTier.PREMIUM


# ---------------------------------------------------------------------------
# Coordination proxies (lines 351, 373, 394)
# ---------------------------------------------------------------------------


class TestCoordinationProxies:
    """send_signal / wait_for_signal / check_signal ctx branches."""

    def test_send_signal_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        ctx.coordination.send_signal.return_value = "signal-id-123"

        result = wf.send_signal("ready", "peer-agent", {"data": 1}, ttl_seconds=60)

        ctx.coordination.send_signal.assert_called_once_with("ready", "peer-agent", {"data": 1}, 60)
        assert result == "signal-id-123"

    def test_wait_for_signal_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        ctx.coordination.wait_for_signal.return_value = {"payload": "hi"}

        result = wf.wait_for_signal("ready", source_agent="peer", timeout=5.0, poll_interval=0.1)

        ctx.coordination.wait_for_signal.assert_called_once_with("ready", "peer", 5.0, 0.1)
        assert result == {"payload": "hi"}

    def test_check_signal_delegates_to_ctx(self, ctx_workflow):
        wf, ctx = ctx_workflow
        ctx.coordination.check_signal.return_value = None

        result = wf.check_signal("ready", source_agent="peer", consume=False)

        ctx.coordination.check_signal.assert_called_once_with("ready", "peer", False)
        assert result is None
