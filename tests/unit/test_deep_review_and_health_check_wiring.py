"""Wiring tests for deep_review MCP tool, architecture_analyst dispatch,
and health-check registry mapping.

These verify the new features added in the plugin reliability session
are properly connected end-to-end.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.orchestration.agent_templates import AgentTemplate, ResourceRequirements

# -------------------------------------------------------------------
# 1. MCP deep_review dispatch
# -------------------------------------------------------------------


class TestDeepReviewMCPDispatch:
    """Verify deep_review MCP tool is registered and dispatches."""

    def test_deep_review_tool_registered(self):
        """deep_review appears in the registered tool definitions."""
        from attune.mcp.server import AttuneMCPServer

        server = AttuneMCPServer()
        tool_names = {t["name"] for t in server.get_tool_list()}
        assert "deep_review" in tool_names

    def test_deep_review_tool_has_required_path(self):
        """deep_review tool schema requires a path parameter."""
        from attune.mcp.server import AttuneMCPServer

        server = AttuneMCPServer()
        tools = {t["name"]: t for t in server.get_tool_list()}
        schema = tools["deep_review"]["input_schema"]
        assert "path" in schema["properties"]
        assert "path" in schema.get("required", [])

    def test_deep_review_in_dispatch_table(self):
        """deep_review has a handler in the dispatch table."""
        from attune.mcp.server import AttuneMCPServer

        server = AttuneMCPServer()
        table = server._build_dispatch_table()
        assert "deep_review" in table

    @pytest.mark.asyncio
    async def test_deep_review_handler_calls_workflow(self):
        """_run_deep_review validates path and calls the workflow."""
        from attune.mcp.workflow_handlers import WorkflowHandlersMixin

        mixin = WorkflowHandlersMixin.__new__(WorkflowHandlersMixin)
        mixin._workspace_root = "/tmp"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = "Review findings"
        mock_result.cost_report = MagicMock(total_cost=0.05)

        with (
            patch(
                "attune.mcp.workflow_handlers.WorkflowHandlersMixin._validated_path",
                return_value="/tmp/src",
            ),
            patch("attune.workflows.deep_review.DeepReviewAgentSDKWorkflow") as mock_cls,
        ):
            mock_wf = AsyncMock()
            mock_wf.execute.return_value = mock_result
            mock_cls.return_value = mock_wf

            result = await mixin._run_deep_review({"path": "src/"})

        assert result["success"] is True
        assert result["output"] == "Review findings"
        assert result["cost"] == 0.05


# -------------------------------------------------------------------
# 2. architecture_analyst strategy dispatch
# -------------------------------------------------------------------


class TestArchitectureAnalystDispatch:
    """Verify architecture_analyst agent dispatches to RealArchitectureAnalyzer."""

    @pytest.mark.asyncio
    async def test_architecture_analyst_dispatches(self, tmp_path):
        """Given architecture_analyst agent, executes RealArchitectureAnalyzer."""
        from attune.orchestration.execution_strategies import ParallelStrategy

        agent = AgentTemplate(
            id="architecture_analyst",
            role="Architecture Analyst",
            capabilities=["analyze_architecture"],
            tier_preference="PREMIUM",
            tools=["mock"],
            default_instructions="Analyze architecture",
            quality_gates={},
            resource_requirements=ResourceRequirements(timeout_seconds=30),
        )

        strategy = ParallelStrategy()
        result = await strategy.execute(
            [agent],
            {"project_root": str(tmp_path), "target_path": "."},
        )

        assert len(result.outputs) == 1
        agent_result = result.outputs[0]
        assert agent_result.agent_id == "architecture_analyst"
        assert agent_result.success is True
        assert "score" in agent_result.output
        assert "total_modules" in agent_result.output
        assert "circular_imports" in agent_result.output

    @pytest.mark.asyncio
    async def test_architecture_role_fallback_dispatches(self, tmp_path):
        """Agent with 'architecture' in role also dispatches correctly."""
        from attune.orchestration.execution_strategies import ParallelStrategy

        agent = AgentTemplate(
            id="custom_arch_agent",
            role="Custom Architecture Reviewer",
            capabilities=["review"],
            tier_preference="CAPABLE",
            tools=["mock"],
            default_instructions="Review architecture",
            quality_gates={},
            resource_requirements=ResourceRequirements(timeout_seconds=30),
        )

        strategy = ParallelStrategy()
        result = await strategy.execute(
            [agent],
            {"project_root": str(tmp_path), "target_path": "."},
        )

        agent_result = result.outputs[0]
        assert agent_result.success is True
        assert "score" in agent_result.output


# -------------------------------------------------------------------
# 3. health-check registry mapping
# -------------------------------------------------------------------


class TestHealthCheckRegistryMapping:
    """Verify health-check resolves to OrchestratedHealthCheckWorkflow."""

    def test_health_check_maps_to_orchestrated(self):
        """health-check in _DEFAULT_WORKFLOW_NAMES points to Orchestrated."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        assert "health-check" in _DEFAULT_WORKFLOW_NAMES
        assert _DEFAULT_WORKFLOW_NAMES["health-check"] == "OrchestratedHealthCheckWorkflow"

    def test_orchestrated_health_check_also_mapped(self):
        """orchestrated-health-check alias also exists."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        assert "orchestrated-health-check" in _DEFAULT_WORKFLOW_NAMES
        assert (
            _DEFAULT_WORKFLOW_NAMES["orchestrated-health-check"]
            == "OrchestratedHealthCheckWorkflow"
        )

    def test_get_workflow_returns_orchestrated_class(self):
        """get_workflow('health-check') returns OrchestratedHealthCheckWorkflow."""
        from attune.workflows import get_workflow

        cls = get_workflow("health-check")
        assert cls.__name__ == "OrchestratedHealthCheckWorkflow"

    def test_health_check_sdk_class_removed(self):
        """HealthCheckAgentSDKWorkflow no longer importable from workflows."""
        from attune import workflows

        assert not hasattr(workflows, "HealthCheckAgentSDKWorkflow")
