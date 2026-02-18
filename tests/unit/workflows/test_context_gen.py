"""Unit tests for src/attune/workflows/context.py

Tests cover WorkflowContext dataclass:
- Construction (positional and keyword)
- Default values (all service slots default to None)
- extras dict
- services property (returns only non-None services)
- minimal() classmethod (creates context with only CostService)
- standard() classmethod (creates context with cache, cost, telemetry, prompt, parsing)

Key corrections vs naive generation:
- Service slots are typed as concrete service classes (CacheService,
  CostService, TelemetryService, PromptService, ParsingService,
  TierService, CoordinationService), NOT generic 'Any'
- Use MagicMock() for service slots in unit tests — avoids pulling in
  real service deps
- minimal(workflow_name) and standard(workflow_name, provider, enable_cache)
  are the only factory classmethods — no 'full()' classmethod
- extras is a dict[str, Any], not a list or set
- services property iterates the 7 named service fields only
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from attune.workflows.context import WorkflowContext

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_ctx(**kwargs: Any) -> WorkflowContext:
    """Return a WorkflowContext with all-None services, overridable per-test."""
    return WorkflowContext(**kwargs)


# ---------------------------------------------------------------------------
# 1. Construction
# ---------------------------------------------------------------------------


class TestWorkflowContextConstruction:
    def test_default_construction_succeeds(self):
        ctx = WorkflowContext()
        assert ctx is not None

    def test_all_service_slots_default_to_none(self):
        ctx = WorkflowContext()
        assert ctx.cache is None
        assert ctx.cost is None
        assert ctx.telemetry is None
        assert ctx.prompt is None
        assert ctx.parsing is None
        assert ctx.tier is None
        assert ctx.coordination is None

    def test_extras_defaults_to_empty_dict(self):
        ctx = WorkflowContext()
        assert ctx.extras == {}

    def test_accepts_mock_cache_service(self):
        cache = MagicMock()
        ctx = WorkflowContext(cache=cache)
        assert ctx.cache is cache

    def test_accepts_mock_cost_service(self):
        cost = MagicMock()
        ctx = WorkflowContext(cost=cost)
        assert ctx.cost is cost

    def test_accepts_mock_telemetry_service(self):
        tel = MagicMock()
        ctx = WorkflowContext(telemetry=tel)
        assert ctx.telemetry is tel

    def test_accepts_mock_prompt_service(self):
        prompt = MagicMock()
        ctx = WorkflowContext(prompt=prompt)
        assert ctx.prompt is prompt

    def test_accepts_mock_parsing_service(self):
        parsing = MagicMock()
        ctx = WorkflowContext(parsing=parsing)
        assert ctx.parsing is parsing

    def test_accepts_mock_tier_service(self):
        tier = MagicMock()
        ctx = WorkflowContext(tier=tier)
        assert ctx.tier is tier

    def test_accepts_mock_coordination_service(self):
        coord = MagicMock()
        ctx = WorkflowContext(coordination=coord)
        assert ctx.coordination is coord

    def test_accepts_extras_dict(self):
        extras = {"key": "value", "count": 42}
        ctx = WorkflowContext(extras=extras)
        assert ctx.extras["key"] == "value"
        assert ctx.extras["count"] == 42

    def test_all_services_set_simultaneously(self):
        cache = MagicMock()
        cost = MagicMock()
        telemetry = MagicMock()
        ctx = WorkflowContext(cache=cache, cost=cost, telemetry=telemetry)
        assert ctx.cache is cache
        assert ctx.cost is cost
        assert ctx.telemetry is telemetry


# ---------------------------------------------------------------------------
# 2. services property
# ---------------------------------------------------------------------------


class TestServicesProperty:
    def test_empty_context_services_is_empty_dict(self):
        ctx = WorkflowContext()
        assert ctx.services == {}

    def test_services_returns_dict(self):
        ctx = WorkflowContext(cost=MagicMock())
        assert isinstance(ctx.services, dict)

    def test_services_includes_cache_when_set(self):
        cache = MagicMock()
        ctx = WorkflowContext(cache=cache)
        assert "cache" in ctx.services
        assert ctx.services["cache"] is cache

    def test_services_includes_cost_when_set(self):
        cost = MagicMock()
        ctx = WorkflowContext(cost=cost)
        assert "cost" in ctx.services

    def test_services_includes_telemetry_when_set(self):
        tel = MagicMock()
        ctx = WorkflowContext(telemetry=tel)
        assert "telemetry" in ctx.services

    def test_services_includes_prompt_when_set(self):
        ctx = WorkflowContext(prompt=MagicMock())
        assert "prompt" in ctx.services

    def test_services_includes_parsing_when_set(self):
        ctx = WorkflowContext(parsing=MagicMock())
        assert "parsing" in ctx.services

    def test_services_includes_tier_when_set(self):
        ctx = WorkflowContext(tier=MagicMock())
        assert "tier" in ctx.services

    def test_services_includes_coordination_when_set(self):
        ctx = WorkflowContext(coordination=MagicMock())
        assert "coordination" in ctx.services

    def test_services_excludes_none_slots(self):
        ctx = WorkflowContext(cache=MagicMock())
        assert "cost" not in ctx.services
        assert "telemetry" not in ctx.services

    def test_services_count_matches_non_none_slots(self):
        ctx = WorkflowContext(cache=MagicMock(), cost=MagicMock())
        assert len(ctx.services) == 2

    def test_services_does_not_include_extras(self):
        ctx = WorkflowContext(extras={"foo": "bar"})
        assert "extras" not in ctx.services
        assert "foo" not in ctx.services

    def test_all_services_set_services_has_all_seven(self):
        ctx = WorkflowContext(
            cache=MagicMock(),
            cost=MagicMock(),
            telemetry=MagicMock(),
            prompt=MagicMock(),
            parsing=MagicMock(),
            tier=MagicMock(),
            coordination=MagicMock(),
        )
        assert len(ctx.services) == 7

    def test_services_returns_correct_objects(self):
        cache = MagicMock()
        cost = MagicMock()
        ctx = WorkflowContext(cache=cache, cost=cost)
        assert ctx.services["cache"] is cache
        assert ctx.services["cost"] is cost


# ---------------------------------------------------------------------------
# 3. extras dict
# ---------------------------------------------------------------------------


class TestExtrasDict:
    def test_extras_is_mutable(self):
        ctx = WorkflowContext()
        ctx.extras["new_key"] = 99
        assert ctx.extras["new_key"] == 99

    def test_extras_instances_are_independent(self):
        ctx1 = WorkflowContext()
        ctx2 = WorkflowContext()
        ctx1.extras["x"] = 1
        assert "x" not in ctx2.extras

    def test_extras_accepts_any_values(self):
        ctx = WorkflowContext(extras={"list": [1, 2], "nested": {"a": 1}})
        assert ctx.extras["list"] == [1, 2]
        assert ctx.extras["nested"]["a"] == 1


# ---------------------------------------------------------------------------
# 4. minimal() classmethod
# ---------------------------------------------------------------------------


class TestMinimalClassmethod:
    def test_minimal_returns_workflow_context(self):
        ctx = WorkflowContext.minimal()
        assert isinstance(ctx, WorkflowContext)

    def test_minimal_has_cost_service(self):
        ctx = WorkflowContext.minimal()
        assert ctx.cost is not None

    def test_minimal_has_no_cache(self):
        ctx = WorkflowContext.minimal()
        assert ctx.cache is None

    def test_minimal_has_no_telemetry(self):
        ctx = WorkflowContext.minimal()
        assert ctx.telemetry is None

    def test_minimal_has_no_prompt(self):
        ctx = WorkflowContext.minimal()
        assert ctx.prompt is None

    def test_minimal_has_no_parsing(self):
        ctx = WorkflowContext.minimal()
        assert ctx.parsing is None

    def test_minimal_has_no_tier(self):
        ctx = WorkflowContext.minimal()
        assert ctx.tier is None

    def test_minimal_has_no_coordination(self):
        ctx = WorkflowContext.minimal()
        assert ctx.coordination is None

    def test_minimal_accepts_optional_workflow_name(self):
        ctx = WorkflowContext.minimal(workflow_name="my-wf")
        assert isinstance(ctx, WorkflowContext)

    def test_minimal_services_dict_has_only_cost(self):
        ctx = WorkflowContext.minimal()
        assert set(ctx.services.keys()) == {"cost"}


# ---------------------------------------------------------------------------
# 5. standard() classmethod
# ---------------------------------------------------------------------------


class TestStandardClassmethod:
    def test_standard_returns_workflow_context(self):
        ctx = WorkflowContext.standard("test-wf")
        assert isinstance(ctx, WorkflowContext)

    def test_standard_has_cache(self):
        ctx = WorkflowContext.standard("test-wf")
        assert ctx.cache is not None

    def test_standard_has_cost(self):
        ctx = WorkflowContext.standard("test-wf")
        assert ctx.cost is not None

    def test_standard_has_telemetry(self):
        ctx = WorkflowContext.standard("test-wf")
        assert ctx.telemetry is not None

    def test_standard_has_prompt(self):
        ctx = WorkflowContext.standard("test-wf")
        assert ctx.prompt is not None

    def test_standard_has_parsing(self):
        ctx = WorkflowContext.standard("test-wf")
        assert ctx.parsing is not None

    def test_standard_has_no_tier(self):
        """standard() does not set TierService."""
        ctx = WorkflowContext.standard("test-wf")
        assert ctx.tier is None

    def test_standard_has_no_coordination(self):
        """standard() does not set CoordinationService."""
        ctx = WorkflowContext.standard("test-wf")
        assert ctx.coordination is None

    def test_standard_accepts_provider(self):
        ctx = WorkflowContext.standard("test-wf", provider="openai")
        assert isinstance(ctx, WorkflowContext)

    def test_standard_accepts_enable_cache_false(self):
        ctx = WorkflowContext.standard("test-wf", enable_cache=False)
        # Cache service exists but caching is disabled
        assert isinstance(ctx, WorkflowContext)

    def test_standard_services_dict_has_expected_keys(self):
        ctx = WorkflowContext.standard("test-wf")
        services = ctx.services
        assert "cache" in services
        assert "cost" in services
        assert "telemetry" in services
        assert "prompt" in services
        assert "parsing" in services

    def test_no_full_classmethod_exists(self):
        """There is no full() classmethod."""
        assert not hasattr(WorkflowContext, "full")


# ---------------------------------------------------------------------------
# 6. Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_repr_does_not_raise(self):
        ctx = WorkflowContext()
        _ = repr(ctx)

    def test_context_with_all_mocks_repr_does_not_raise(self):
        ctx = WorkflowContext(
            cache=MagicMock(),
            cost=MagicMock(),
            telemetry=MagicMock(),
        )
        _ = repr(ctx)

    def test_two_default_contexts_are_equal(self):
        ctx1 = WorkflowContext()
        ctx2 = WorkflowContext()
        assert ctx1 == ctx2

    def test_contexts_with_different_extras_are_not_equal(self):
        ctx1 = WorkflowContext(extras={"a": 1})
        ctx2 = WorkflowContext(extras={"a": 2})
        assert ctx1 != ctx2

    def test_services_property_is_not_cached_across_mutations(self):
        """services reflects current state, not a snapshot at init time."""
        ctx = WorkflowContext()
        assert ctx.services == {}
        ctx.cache = MagicMock()
        assert "cache" in ctx.services
