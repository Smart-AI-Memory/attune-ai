"""Tests for NestedStrategy - Phase 2: Sentences within sentences.

Tests cover:
- Workflow reference resolution (by ID and inline)
- Nesting depth limits
- Cycle detection
- Context inheritance
- Mixed agent/workflow steps
"""

from unittest.mock import AsyncMock, patch

import pytest

from attune.orchestration.agent_templates import AgentTemplate
from attune.orchestration.execution_strategies import (
    WORKFLOW_REGISTRY,
    InlineWorkflow,
    NestedStrategy,
    NestingContext,
    StepDefinition,
    StrategyResult,
    WorkflowDefinition,
    WorkflowReference,
    get_workflow,
    register_workflow,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_agent():
    """Create a mock agent template."""
    return AgentTemplate(
        id="test_agent",
        role="Test Agent",
        capabilities=["test"],
        tier_preference="CHEAP",
        tools=["test_tool"],
        default_instructions="Test instructions",
        quality_gates={"min_score": 0.5},
    )


@pytest.fixture
def mock_workflow(mock_agent):
    """Create and register a mock workflow."""
    workflow = WorkflowDefinition(
        id="test-workflow",
        agents=[mock_agent],
        strategy="sequential",
        description="Test workflow",
    )
    register_workflow(workflow)
    yield workflow
    # Cleanup
    WORKFLOW_REGISTRY.pop("test-workflow", None)


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up workflow registry after each test."""
    yield
    WORKFLOW_REGISTRY.clear()


# =============================================================================
# WorkflowReference Tests
# =============================================================================


class TestWorkflowReference:
    """Tests for WorkflowReference dataclass."""

    def test_valid_id_reference(self):
        """Test creating reference by workflow ID."""
        ref = WorkflowReference(workflow_id="security-audit")
        assert ref.workflow_id == "security-audit"
        assert ref.inline is None

    def test_valid_inline_reference(self, mock_agent):
        """Test creating inline workflow reference."""
        inline = InlineWorkflow(
            agents=[mock_agent],
            strategy="parallel",
            description="Inline workflow",
        )
        ref = WorkflowReference(inline=inline)
        assert ref.workflow_id == ""
        assert ref.inline is inline

    def test_invalid_both_specified(self, mock_agent):
        """Test that both ID and inline is rejected."""
        inline = InlineWorkflow(agents=[mock_agent])
        with pytest.raises(ValueError, match="exactly one of"):
            WorkflowReference(workflow_id="test", inline=inline)

    def test_invalid_neither_specified(self):
        """Test that neither ID nor inline is rejected."""
        with pytest.raises(ValueError, match="exactly one of"):
            WorkflowReference()


# =============================================================================
# NestingContext Tests
# =============================================================================


class TestNestingContext:
    """Tests for NestingContext depth tracking."""

    def test_initial_state(self):
        """Test initial nesting context state."""
        ctx = NestingContext()
        assert ctx.current_depth == 0
        assert ctx.max_depth == 3
        assert ctx.workflow_stack == []

    def test_custom_max_depth(self):
        """Test custom max depth configuration."""
        ctx = NestingContext(max_depth=5)
        assert ctx.max_depth == 5

    def test_can_nest_within_limit(self):
        """Test nesting allowed within depth limit."""
        ctx = NestingContext(max_depth=3)
        assert ctx.can_nest() is True

    def test_cannot_nest_at_limit(self):
        """Test nesting blocked at depth limit."""
        ctx = NestingContext(max_depth=3)
        ctx.current_depth = 3
        assert ctx.can_nest() is False

    def test_cycle_detection(self):
        """Test that cycles are detected."""
        ctx = NestingContext()
        ctx.workflow_stack = ["workflow-a", "workflow-b"]
        assert ctx.can_nest("workflow-a") is False  # Cycle!
        assert ctx.can_nest("workflow-c") is True  # No cycle

    def test_enter_increments_depth(self):
        """Test that entering a workflow increments depth."""
        parent = NestingContext()
        child = parent.enter("workflow-a")

        assert child.current_depth == 1
        assert child.workflow_stack == ["workflow-a"]
        assert parent.current_depth == 0  # Parent unchanged

    def test_enter_preserves_stack(self):
        """Test that entering preserves parent stack."""
        parent = NestingContext()
        parent.workflow_stack = ["a", "b"]

        child = parent.enter("c")
        assert child.workflow_stack == ["a", "b", "c"]

    def test_from_context_creates_new(self):
        """Test from_context creates new context if not present."""
        context = {"some_key": "value"}
        nesting = NestingContext.from_context(context)
        assert nesting.current_depth == 0

    def test_from_context_extracts_existing(self):
        """Test from_context extracts existing context."""
        existing = NestingContext(max_depth=5)
        existing.current_depth = 2
        context = {NestingContext.CONTEXT_KEY: existing}

        nesting = NestingContext.from_context(context)
        assert nesting.current_depth == 2
        assert nesting.max_depth == 5

    def test_to_context_adds_nesting(self):
        """Test to_context adds nesting info."""
        nesting = NestingContext()
        context = {"existing": "value"}

        updated = nesting.to_context(context)
        assert NestingContext.CONTEXT_KEY in updated
        assert updated["existing"] == "value"  # Preserved


# =============================================================================
# Workflow Registry Tests
# =============================================================================


class TestWorkflowRegistry:
    """Tests for workflow registration and lookup."""

    def test_register_workflow(self, mock_agent):
        """Test registering a workflow."""
        workflow = WorkflowDefinition(
            id="my-workflow",
            agents=[mock_agent],
            strategy="parallel",
        )
        register_workflow(workflow)

        assert "my-workflow" in WORKFLOW_REGISTRY
        assert WORKFLOW_REGISTRY["my-workflow"] == workflow

    def test_get_workflow_success(self, mock_workflow):
        """Test getting a registered workflow."""
        result = get_workflow("test-workflow")
        assert result.id == "test-workflow"

    def test_get_workflow_not_found(self):
        """Test getting non-existent workflow raises error."""
        with pytest.raises(ValueError, match="Unknown workflow"):
            get_workflow("nonexistent")


# =============================================================================
# NestedStrategy Tests
# =============================================================================


class TestNestedStrategy:
    """Tests for NestedStrategy execution."""

    @pytest.mark.asyncio
    async def test_execute_by_id(self, mock_workflow, mock_agent):
        """Test executing workflow by ID reference."""
        ref = WorkflowReference(workflow_id="test-workflow")
        strategy = NestedStrategy(workflow_ref=ref)

        with patch("attune.orchestration._strategies.get_strategy") as mock_get:
            mock_inner = AsyncMock()
            mock_inner.execute.return_value = StrategyResult(
                success=True,
                outputs=[],
                aggregated_output={"result": "from_nested"},
                total_duration=1.0,
            )
            mock_get.return_value = mock_inner

            result = await strategy.execute([], {})

            assert result.success is True
            assert "_nested" in result.aggregated_output
            assert result.aggregated_output["_nested"]["workflow_id"] == "test-workflow"

    @pytest.mark.asyncio
    async def test_execute_inline(self, mock_agent):
        """Test executing inline workflow."""
        inline = InlineWorkflow(
            agents=[mock_agent],
            strategy="parallel",
        )
        ref = WorkflowReference(inline=inline)
        strategy = NestedStrategy(workflow_ref=ref)

        with patch("attune.orchestration._strategies.get_strategy") as mock_get:
            mock_inner = AsyncMock()
            mock_inner.execute.return_value = StrategyResult(
                success=True,
                outputs=[],
                aggregated_output={},
                total_duration=0.5,
            )
            mock_get.return_value = mock_inner

            result = await strategy.execute([], {})

            assert result.success is True
            mock_get.assert_called_once_with("parallel")

    @pytest.mark.asyncio
    async def test_depth_limit_exceeded(self, mock_workflow):
        """Test that exceeding depth limit raises error."""
        ref = WorkflowReference(workflow_id="test-workflow")
        strategy = NestedStrategy(workflow_ref=ref, max_depth=2)

        # Create context at depth 2 (limit)
        nesting = NestingContext(max_depth=2)
        nesting.current_depth = 2
        context = nesting.to_context({})

        with pytest.raises(RecursionError, match="Maximum nesting depth"):
            await strategy.execute([], context)

    @pytest.mark.asyncio
    async def test_cycle_detection(self, mock_workflow):
        """Test that cycles are detected and blocked."""
        ref = WorkflowReference(workflow_id="test-workflow")
        strategy = NestedStrategy(workflow_ref=ref)

        # Create context with test-workflow already in stack
        nesting = NestingContext()
        nesting.workflow_stack = ["test-workflow"]
        context = nesting.to_context({})

        with pytest.raises(RecursionError, match="Cycle detected"):
            await strategy.execute([], context)

    @pytest.mark.asyncio
    async def test_context_inheritance(self, mock_workflow):
        """Test that child inherits parent context."""
        ref = WorkflowReference(workflow_id="test-workflow")
        strategy = NestedStrategy(workflow_ref=ref)

        parent_context = {
            "parent_data": "inherited",
            "config": {"setting": True},
        }

        with patch("attune.orchestration._strategies.get_strategy") as mock_get:
            mock_inner = AsyncMock()
            mock_inner.execute.return_value = StrategyResult(
                success=True,
                outputs=[],
                aggregated_output={},
                total_duration=0.5,
            )
            mock_get.return_value = mock_inner

            await strategy.execute([], parent_context)

            # Verify child received parent context
            call_args = mock_inner.execute.call_args
            child_context = call_args[0][1]  # Second positional arg
            assert child_context["parent_data"] == "inherited"
            assert child_context["config"]["setting"] is True


# =============================================================================
# StepDefinition Tests
# =============================================================================


class TestStepDefinition:
    """Tests for StepDefinition dataclass."""

    def test_valid_agent_step(self, mock_agent):
        """Test creating agent step."""
        step = StepDefinition(agent=mock_agent)
        assert step.agent == mock_agent
        assert step.workflow_ref is None

    def test_valid_workflow_step(self):
        """Test creating workflow step."""
        ref = WorkflowReference(workflow_id="test")
        step = StepDefinition(workflow_ref=ref)
        assert step.agent is None
        assert step.workflow_ref == ref

    def test_invalid_both(self, mock_agent):
        """Test that both agent and workflow_ref is rejected."""
        ref = WorkflowReference(workflow_id="test")
        with pytest.raises(ValueError, match="exactly one of"):
            StepDefinition(agent=mock_agent, workflow_ref=ref)

    def test_invalid_neither(self):
        """Test that neither agent nor workflow_ref is rejected."""
        with pytest.raises(ValueError, match="exactly one of"):
            StepDefinition()


# =============================================================================
# Integration Tests
# =============================================================================


class TestNestedIntegration:
    """Integration tests for nested composition."""

    def test_strategy_registry_includes_nested(self):
        """Test that nested strategies are in registry."""
        from attune.orchestration.execution_strategies import STRATEGY_REGISTRY

        assert "nested" in STRATEGY_REGISTRY
        assert "nested_sequential" in STRATEGY_REGISTRY

    @pytest.mark.asyncio
    async def test_three_level_nesting(self, mock_agent):
        """Test that three levels of nesting works."""
        # Register workflows for each level
        level3 = WorkflowDefinition(
            id="level-3",
            agents=[mock_agent],
            strategy="sequential",
        )
        register_workflow(level3)

        level2 = WorkflowDefinition(
            id="level-2",
            agents=[mock_agent],
            strategy="sequential",
        )
        register_workflow(level2)

        # This test verifies the depth tracking works correctly
        nesting = NestingContext(max_depth=3)
        assert nesting.can_nest("level-1") is True

        child1 = nesting.enter("level-1")
        assert child1.can_nest("level-2") is True

        child2 = child1.enter("level-2")
        assert child2.can_nest("level-3") is True

        child3 = child2.enter("level-3")
        assert child3.can_nest("level-4") is False  # At limit
