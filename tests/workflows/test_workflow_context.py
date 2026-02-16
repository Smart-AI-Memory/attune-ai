"""Tests for WorkflowContext and composition-based proxy methods.

Phase 2B-2C: Verifies that WorkflowContext enables service composition
and that proxy methods in BaseWorkflow correctly delegate to services
when ctx is provided, falling back to mixins when ctx is None.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from attune.workflows.base import BaseWorkflow, ModelTier
from attune.workflows.builder import WorkflowBuilder
from attune.workflows.caching import CachedResponse
from attune.workflows.context import WorkflowContext
from attune.workflows.services import (
    CacheService,
    CoordinationService,
    CostService,
    ParsingService,
    PromptService,
    TelemetryService,
    TierService,
)

# --- Test fixtures ---


class DummyWorkflow(BaseWorkflow):
    """Minimal concrete workflow for testing."""

    name = "dummy"
    description = "Dummy workflow for tests"
    stages = ["stage1", "stage2"]
    tier_map = {
        "stage1": ModelTier.CHEAP,
        "stage2": ModelTier.CAPABLE,
    }

    async def run_stage(
        self, stage_name: str, tier: ModelTier, input_data: Any
    ) -> tuple[Any, int, int]:
        return {"result": stage_name}, 100, 50


# --- WorkflowContext dataclass tests ---


class TestWorkflowContext:
    """Tests for WorkflowContext creation and introspection."""

    def test_default_context_has_no_services(self):
        """Test that default context has all services as None."""
        ctx = WorkflowContext()
        assert ctx.cache is None
        assert ctx.cost is None
        assert ctx.telemetry is None
        assert ctx.prompt is None
        assert ctx.parsing is None
        assert ctx.tier is None
        assert ctx.coordination is None

    def test_services_property_returns_non_none(self):
        """Test that services property only returns populated services."""
        ctx = WorkflowContext(cost=CostService())
        services = ctx.services
        assert "cost" in services
        assert "cache" not in services
        assert len(services) == 1

    def test_services_property_full_context(self):
        """Test services property with all services populated."""
        ctx = WorkflowContext(
            cache=CacheService("test"),
            cost=CostService(),
            telemetry=TelemetryService("test"),
            prompt=PromptService("test"),
            parsing=ParsingService(),
            tier=TierService("test", [], {}),
            coordination=CoordinationService("test"),
        )
        assert len(ctx.services) == 7

    def test_minimal_factory(self):
        """Test minimal() factory method."""
        ctx = WorkflowContext.minimal()
        assert ctx.cost is not None
        assert ctx.cache is None
        assert len(ctx.services) == 1

    def test_standard_factory(self):
        """Test standard() factory method."""
        ctx = WorkflowContext.standard("test-workflow")
        assert ctx.cache is not None
        assert ctx.cost is not None
        assert ctx.telemetry is not None
        assert ctx.prompt is not None
        assert ctx.parsing is not None
        assert ctx.tier is None
        assert ctx.coordination is None
        assert len(ctx.services) == 5

    def test_standard_factory_disable_cache(self):
        """Test standard() with cache disabled."""
        ctx = WorkflowContext.standard("test", enable_cache=False)
        assert ctx.cache is not None
        assert ctx.cache.enabled is False

    def test_extras_dict(self):
        """Test extras dict for custom metadata."""
        ctx = WorkflowContext(extras={"custom_key": "value"})
        assert ctx.extras["custom_key"] == "value"

    def test_extras_default_empty(self):
        """Test that extras defaults to empty dict."""
        ctx = WorkflowContext()
        assert ctx.extras == {}


# --- BaseWorkflow ctx parameter tests ---


class TestBaseWorkflowCtxParam:
    """Tests for ctx parameter acceptance in BaseWorkflow."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_accepts_ctx_none(self, mock_config, mock_tracker):
        """Test that ctx=None (default) works as before."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"
        wf = DummyWorkflow()
        assert wf._ctx is None

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_accepts_ctx_instance(self, mock_config, mock_tracker):
        """Test that ctx=WorkflowContext is stored."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"
        ctx = WorkflowContext(cost=CostService())
        wf = DummyWorkflow(ctx=ctx)
        assert wf._ctx is ctx
        assert wf._ctx.cost is not None


# --- Proxy method delegation tests ---


class TestCostProxyDelegation:
    """Tests for cost-related proxy method delegation."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_calculate_cost_delegates_to_service(self, mock_config, mock_tracker):
        """Test _calculate_cost delegates to CostService when ctx is provided."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_cost = MagicMock(spec=CostService)
        mock_cost.calculate_cost.return_value = 0.042
        ctx = WorkflowContext(cost=mock_cost)

        wf = DummyWorkflow(ctx=ctx)
        result = wf._calculate_cost(ModelTier.CAPABLE, 1000, 500)

        assert result == 0.042
        mock_cost.calculate_cost.assert_called_once_with(ModelTier.CAPABLE, 1000, 500)

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_calculate_cost_falls_back_to_mixin(self, mock_config, mock_tracker):
        """Test _calculate_cost falls back to mixin when ctx has no cost service."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        # ctx without cost service
        ctx = WorkflowContext()
        wf = DummyWorkflow(ctx=ctx)
        result = wf._calculate_cost(ModelTier.CAPABLE, 1000, 500)

        # Should get a real cost from the mixin
        assert isinstance(result, float)
        assert result >= 0

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_calculate_cost_falls_back_without_ctx(self, mock_config, mock_tracker):
        """Test _calculate_cost falls back to mixin when ctx is None."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        wf = DummyWorkflow()
        result = wf._calculate_cost(ModelTier.CAPABLE, 1000, 500)

        assert isinstance(result, float)
        assert result >= 0

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_calculate_baseline_cost_delegates(self, mock_config, mock_tracker):
        """Test _calculate_baseline_cost delegates to CostService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_cost = MagicMock(spec=CostService)
        mock_cost.calculate_baseline_cost.return_value = 0.10
        ctx = WorkflowContext(cost=mock_cost)

        wf = DummyWorkflow(ctx=ctx)
        result = wf._calculate_baseline_cost(1000, 500)

        assert result == 0.10
        mock_cost.calculate_baseline_cost.assert_called_once_with(1000, 500)


class TestCacheProxyDelegation:
    """Tests for cache-related proxy method delegation."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_maybe_setup_cache_delegates(self, mock_config, mock_tracker):
        """Test _maybe_setup_cache delegates to CacheService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_cache = MagicMock(spec=CacheService)
        ctx = WorkflowContext(cache=mock_cache)

        wf = DummyWorkflow(ctx=ctx)
        wf._maybe_setup_cache()

        mock_cache.setup.assert_called_once()

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_try_cache_lookup_delegates(self, mock_config, mock_tracker):
        """Test _try_cache_lookup delegates to CacheService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_cache = MagicMock(spec=CacheService)
        cached = CachedResponse(content="cached!", input_tokens=10, output_tokens=5)
        mock_cache.lookup.return_value = cached
        ctx = WorkflowContext(cache=mock_cache)

        wf = DummyWorkflow(ctx=ctx)
        result = wf._try_cache_lookup("stage1", "sys", "user", "model-1")

        assert result is cached
        mock_cache.lookup.assert_called_once_with("stage1", "sys", "user", "model-1")

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_store_in_cache_delegates(self, mock_config, mock_tracker):
        """Test _store_in_cache delegates to CacheService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_cache = MagicMock(spec=CacheService)
        mock_cache.store.return_value = True
        ctx = WorkflowContext(cache=mock_cache)

        wf = DummyWorkflow(ctx=ctx)
        resp = CachedResponse(content="test", input_tokens=10, output_tokens=5)
        result = wf._store_in_cache("stage1", "sys", "user", "model-1", resp)

        assert result is True
        mock_cache.store.assert_called_once()

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_get_cache_stats_delegates(self, mock_config, mock_tracker):
        """Test _get_cache_stats delegates to CacheService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_cache = MagicMock(spec=CacheService)
        mock_cache.get_stats.return_value = {"hits": 5, "misses": 3, "hit_rate": 0.625}
        ctx = WorkflowContext(cache=mock_cache)

        wf = DummyWorkflow(ctx=ctx)
        stats = wf._get_cache_stats()

        assert stats["hits"] == 5
        assert stats["hit_rate"] == 0.625


class TestTelemetryProxyDelegation:
    """Tests for telemetry-related proxy method delegation."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_track_telemetry_delegates(self, mock_config, mock_tracker):
        """Test _track_telemetry delegates to TelemetryService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_tel = MagicMock(spec=TelemetryService)
        ctx = WorkflowContext(telemetry=mock_tel)

        wf = DummyWorkflow(ctx=ctx)
        wf._track_telemetry(
            stage="stage1",
            tier=ModelTier.CHEAP,
            model="claude-3-haiku",
            cost=0.001,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=500,
        )

        mock_tel.track_call.assert_called_once()

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_generate_run_id_delegates(self, mock_config, mock_tracker):
        """Test _generate_run_id delegates to TelemetryService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_tel = MagicMock(spec=TelemetryService)
        mock_tel.generate_run_id.return_value = "test-run-id-123"
        ctx = WorkflowContext(telemetry=mock_tel)

        wf = DummyWorkflow(ctx=ctx)
        run_id = wf._generate_run_id()

        assert run_id == "test-run-id-123"
        assert wf._run_id == "test-run-id-123"


class TestPromptProxyDelegation:
    """Tests for prompt-related proxy method delegation."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_build_cached_system_prompt_delegates(self, mock_config, mock_tracker):
        """Test _build_cached_system_prompt delegates to PromptService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_prompt = MagicMock(spec=PromptService)
        mock_prompt.build_cached_system_prompt.return_value = "You are an expert."
        ctx = WorkflowContext(prompt=mock_prompt)

        wf = DummyWorkflow(ctx=ctx)
        result = wf._build_cached_system_prompt("expert reviewer")

        assert result == "You are an expert."
        mock_prompt.build_cached_system_prompt.assert_called_once()

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_render_plain_prompt_delegates(self, mock_config, mock_tracker):
        """Test _render_plain_prompt delegates to PromptService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_prompt = MagicMock(spec=PromptService)
        mock_prompt.render_plain.return_value = "Plain prompt text"
        ctx = WorkflowContext(prompt=mock_prompt)

        wf = DummyWorkflow(ctx=ctx)
        result = wf._render_plain_prompt(
            "reviewer",
            "find bugs",
            ["step1"],
            ["rule1"],
            "code",
            "def foo(): pass",
        )

        assert result == "Plain prompt text"
        mock_prompt.render_plain.assert_called_once()


class TestParsingProxyDelegation:
    """Tests for parsing-related proxy method delegation."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_extract_findings_delegates(self, mock_config, mock_tracker):
        """Test _extract_findings_from_response delegates to ParsingService."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_parsing = MagicMock(spec=ParsingService)
        mock_parsing.extract_findings.return_value = [{"id": "abc", "file": "test.py", "line": 10}]
        ctx = WorkflowContext(parsing=mock_parsing)

        wf = DummyWorkflow(ctx=ctx)
        findings = wf._extract_findings_from_response(
            "test.py:10: issue found",
            ["test.py"],
        )

        assert len(findings) == 1
        assert findings[0]["file"] == "test.py"
        mock_parsing.extract_findings.assert_called_once()


# --- WorkflowBuilder with_context tests ---


class TestWorkflowBuilderWithContext:
    """Tests for WorkflowBuilder.with_context()."""

    def test_with_context_returns_self(self):
        """Test that with_context returns the builder for chaining."""
        builder = WorkflowBuilder(MagicMock)
        ctx = WorkflowContext()
        result = builder.with_context(ctx)
        assert result is builder

    def test_with_context_stores_ctx(self):
        """Test that with_context stores the context."""
        builder = WorkflowBuilder(MagicMock)
        ctx = WorkflowContext(cost=CostService())
        builder.with_context(ctx)
        assert builder._ctx is ctx

    def test_build_passes_ctx_to_workflow(self):
        """Test that build() passes ctx to the workflow constructor."""

        class MockWorkflow:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        builder = WorkflowBuilder(MockWorkflow)
        ctx = WorkflowContext(cost=CostService())
        wf = builder.with_context(ctx).build()

        assert "ctx" in wf.kwargs
        assert wf.kwargs["ctx"] is ctx

    def test_build_without_ctx_does_not_pass_ctx(self):
        """Test that build() without with_context() doesn't pass ctx."""

        class MockWorkflow:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        builder = WorkflowBuilder(MockWorkflow)
        wf = builder.build()

        assert "ctx" not in wf.kwargs

    def test_chaining_with_context_and_other_options(self):
        """Test chaining with_context alongside other builder methods."""

        class MockWorkflow:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        ctx = WorkflowContext(cost=CostService())
        wf = (
            WorkflowBuilder(MockWorkflow)
            .with_cache_enabled(False)
            .with_context(ctx)
            .with_telemetry_enabled(False)
            .build()
        )

        assert wf.kwargs["ctx"] is ctx
        assert wf.kwargs["enable_cache"] is False
        assert wf.kwargs["enable_telemetry"] is False


# --- Phase 2D: Concrete workflow migration tests ---


class TestIsXmlEnabledProxy:
    """Tests for the _is_xml_enabled proxy (added in Phase 2D)."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_is_xml_enabled_delegates_to_prompt_service(self, mock_config, mock_tracker):
        """Test _is_xml_enabled delegates to PromptService.xml_enabled."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_prompt = MagicMock(spec=PromptService)
        mock_prompt.xml_enabled = True
        ctx = WorkflowContext(prompt=mock_prompt)

        wf = DummyWorkflow(ctx=ctx)
        assert wf._is_xml_enabled() is True

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_is_xml_enabled_returns_false_when_service_says_false(self, mock_config, mock_tracker):
        """Test _is_xml_enabled returns False when PromptService says False."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_prompt = MagicMock(spec=PromptService)
        mock_prompt.xml_enabled = False
        ctx = WorkflowContext(prompt=mock_prompt)

        wf = DummyWorkflow(ctx=ctx)
        assert wf._is_xml_enabled() is False

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_is_xml_enabled_falls_back_without_prompt_service(self, mock_config, mock_tracker):
        """Test _is_xml_enabled falls back to mixin when no prompt service."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"
        mock_config.return_value.get_xml_config_for_workflow.return_value = {}

        wf = DummyWorkflow()
        # Default mixin returns True (XML enabled by default on Claude 4.x)
        assert wf._is_xml_enabled() is True

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_is_xml_disabled_when_explicitly_set(self, mock_config, mock_tracker):
        """Test _is_xml_enabled returns False when explicitly disabled."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"
        mock_config.return_value.get_xml_config_for_workflow.return_value = {
            "enabled": False,
        }

        wf = DummyWorkflow()
        assert wf._is_xml_enabled() is False


class TestBugPredictDefaultContext:
    """Tests for BugPredictionWorkflow.default_context()."""

    def test_default_context_has_prompt_and_parsing(self):
        """Test default_context returns ctx with prompt and parsing services."""
        from attune.workflows.bug_predict import BugPredictionWorkflow

        ctx = BugPredictionWorkflow.default_context()
        assert ctx.prompt is not None
        assert ctx.parsing is not None
        assert ctx.cache is None
        assert ctx.cost is None

    def test_default_context_prompt_uses_workflow_name(self):
        """Test that prompt service is configured with correct workflow name."""
        from attune.workflows.bug_predict import BugPredictionWorkflow

        ctx = BugPredictionWorkflow.default_context()
        assert ctx.prompt._workflow_name == "bug-predict"

    def test_default_context_with_xml_config(self):
        """Test default_context passes xml_config to services."""
        from attune.workflows.bug_predict import BugPredictionWorkflow

        xml_cfg = {"enabled": True, "template_name": "bug-predict"}
        ctx = BugPredictionWorkflow.default_context(xml_config=xml_cfg)
        assert ctx.prompt.xml_enabled is True

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_constructed_with_default_context(self, mock_config, mock_tracker):
        """Test BugPredictionWorkflow can be constructed with default_context."""
        from attune.workflows.bug_predict import BugPredictionWorkflow

        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        ctx = BugPredictionWorkflow.default_context()
        wf = BugPredictionWorkflow(ctx=ctx)
        assert wf._ctx is ctx
        assert wf._ctx.prompt is not None


class TestDependencyCheckDefaultContext:
    """Tests for DependencyCheckWorkflow.default_context()."""

    def test_default_context_has_prompt_and_parsing(self):
        """Test default_context returns ctx with prompt and parsing services."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        ctx = DependencyCheckWorkflow.default_context()
        assert ctx.prompt is not None
        assert ctx.parsing is not None
        assert ctx.prompt._workflow_name == "dependency-check"

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_constructed_with_default_context(self, mock_config, mock_tracker):
        """Test DependencyCheckWorkflow can be constructed with default_context."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        ctx = DependencyCheckWorkflow.default_context()
        wf = DependencyCheckWorkflow(ctx=ctx)
        assert wf._ctx is ctx


class TestResearchSynthesisDefaultContext:
    """Tests for ResearchSynthesisWorkflow.default_context()."""

    def test_default_context_has_prompt_and_parsing(self):
        """Test default_context returns ctx with prompt and parsing services."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        ctx = ResearchSynthesisWorkflow.default_context()
        assert ctx.prompt is not None
        assert ctx.parsing is not None
        assert ctx.prompt._workflow_name == "research"

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_constructed_with_default_context(self, mock_config, mock_tracker):
        """Test ResearchSynthesisWorkflow can be constructed with default_context."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        ctx = ResearchSynthesisWorkflow.default_context()
        wf = ResearchSynthesisWorkflow(ctx=ctx)
        assert wf._ctx is ctx


class TestCompositionEndToEnd:
    """End-to-end tests: construct workflow with context and verify delegation."""

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_xml_enabled_routes_through_context(self, mock_config, mock_tracker):
        """Test that _is_xml_enabled uses PromptService when ctx is set."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        xml_cfg = {"enabled": True}
        ctx = WorkflowContext(
            prompt=PromptService("dummy", xml_config=xml_cfg),
            parsing=ParsingService(xml_config=xml_cfg),
        )
        wf = DummyWorkflow(ctx=ctx)
        assert wf._is_xml_enabled() is True

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_render_xml_prompt_routes_through_context(self, mock_config, mock_tracker):
        """Test that _render_xml_prompt uses PromptService when ctx is set."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_prompt = MagicMock(spec=PromptService)
        mock_prompt.xml_enabled = True
        mock_prompt.render_xml.return_value = "<prompt>test</prompt>"
        ctx = WorkflowContext(prompt=mock_prompt)

        wf = DummyWorkflow(ctx=ctx)
        result = wf._render_xml_prompt(
            "analyst",
            "find bugs",
            ["step1"],
            ["rule1"],
            "code",
            "def foo(): pass",
        )
        assert result == "<prompt>test</prompt>"
        mock_prompt.render_xml.assert_called_once()

    @patch("attune.workflows.base.CostTracker")
    @patch("attune.workflows.config.WorkflowConfig.load")
    def test_parse_xml_response_routes_through_context(self, mock_config, mock_tracker):
        """Test that _parse_xml_response uses ParsingService when ctx is set."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.get_provider_for_workflow.return_value = "anthropic"

        mock_parsing = MagicMock(spec=ParsingService)
        mock_parsing.parse_xml_response.return_value = {
            "_parsed_response": None,
            "_raw": "test",
            "xml_parsed": False,
        }
        ctx = WorkflowContext(parsing=mock_parsing)

        wf = DummyWorkflow(ctx=ctx)
        result = wf._parse_xml_response("some LLM response")
        assert result["_raw"] == "test"
        mock_parsing.parse_xml_response.assert_called_once_with("some LLM response")

    def test_builder_with_default_context(self):
        """Test WorkflowBuilder.with_context passes ctx through to workflow."""

        class KwargsCapture:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        ctx = WorkflowContext(
            prompt=PromptService("test-wf"),
            parsing=ParsingService(),
        )
        wf = WorkflowBuilder(KwargsCapture).with_context(ctx).build()

        assert wf.kwargs["ctx"] is ctx
        assert wf.kwargs["ctx"].prompt._workflow_name == "test-wf"
