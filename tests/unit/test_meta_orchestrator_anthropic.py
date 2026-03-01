"""Tests for meta-orchestrator integration with Anthropic patterns.

Tests that the meta-orchestrator correctly selects the three new
Anthropic-inspired patterns when appropriate conditions are met.

Created: 2026-01-29
"""

import pytest

from attune.orchestration.agent_templates import AgentTemplate
from attune.orchestration.meta_orchestrator import (
    CompositionPattern,
    MetaOrchestrator,
    TaskComplexity,
    TaskDomain,
    TaskRequirements,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def orchestrator():
    """Create meta-orchestrator instance."""
    return MetaOrchestrator()


@pytest.fixture
def sample_agent():
    """Create sample agent for testing."""
    return AgentTemplate(
        id="test-agent",
        role="Test Agent",
        capabilities=["test_capability"],
        tier_preference="CAPABLE",
        tools=[],
        default_instructions="You are a helpful assistant.",
        quality_gates={},
    )


@pytest.fixture
def coordinator_agent():
    """Create coordinator agent for delegation pattern."""
    return AgentTemplate(
        id="coordinator-agent",
        role="Task Coordinator",
        capabilities=["coordinate", "delegate"],
        tier_preference="PREMIUM",
        tools=[],
        default_instructions="You coordinate tasks and delegate to specialists.",
        quality_gates={},
    )


@pytest.fixture
def specialist_agent():
    """Create specialist agent for delegation pattern."""
    return AgentTemplate(
        id="specialist-agent",
        role="Code Specialist",
        capabilities=["code_analysis"],
        tier_preference="CAPABLE",
        tools=[],
        default_instructions="You analyze code in detail.",
        quality_gates={},
    )


# ============================================================================
# Pattern 8: Tool-Enhanced Strategy Selection Tests
# ============================================================================


class TestToolEnhancedPatternSelection:
    """Tests for tool-enhanced pattern selection."""

    def test_selects_tool_enhanced_for_single_agent_with_tools(self, orchestrator, sample_agent):
        """Test that tool-enhanced pattern is selected when tools are provided."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.GENERAL,
            capabilities_needed=["test_capability"],
            context={"tools": [{"name": "read_file", "description": "Read files"}]},
        )

        pattern = orchestrator._choose_composition_pattern(requirements, [sample_agent])

        assert pattern == CompositionPattern.TOOL_ENHANCED

    def test_does_not_select_tool_enhanced_without_tools(self, orchestrator, sample_agent):
        """Test that tool-enhanced is NOT selected without tools in context."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.GENERAL,
            capabilities_needed=["test_capability"],
            context={},  # No tools
        )

        pattern = orchestrator._choose_composition_pattern(requirements, [sample_agent])

        # Should fall back to sequential for single agent
        assert pattern == CompositionPattern.SEQUENTIAL

    def test_does_not_select_tool_enhanced_for_multiple_agents(self, orchestrator, sample_agent):
        """Test that tool-enhanced is NOT selected with multiple agents."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.GENERAL,
            capabilities_needed=["test_capability"],
            context={"tools": [{"name": "read_file"}]},
        )

        # Even with tools, if multiple agents, don't use tool-enhanced
        pattern = orchestrator._choose_composition_pattern(
            requirements,
            [sample_agent, sample_agent],
        )

        assert pattern != CompositionPattern.TOOL_ENHANCED


# ============================================================================
# Pattern 9: Prompt-Cached Sequential Strategy Selection Tests
# ============================================================================


class TestPromptCachedSequentialPatternSelection:
    """Tests for prompt-cached sequential pattern selection."""

    def test_selects_cached_for_multiple_agents_with_large_context(
        self,
        orchestrator,
        sample_agent,
    ):
        """Test cached pattern selected for 3+ agents with large context."""
        large_context = "x" * 3000  # > 2000 characters
        requirements = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.TESTING,
            capabilities_needed=["test_capability"],
            context={"cached_context": large_context},
        )

        agents = [sample_agent, sample_agent, sample_agent]  # 3 agents
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        assert pattern == CompositionPattern.PROMPT_CACHED_SEQUENTIAL

    def test_does_not_select_cached_for_small_context(self, orchestrator):
        """Test cached pattern NOT selected for small context."""
        small_context = "small"  # < 2000 characters
        requirements = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.TESTING,
            capabilities_needed=["test_capability"],
            context={"cached_context": small_context},
        )

        # Create 3 distinct agents to avoid DEBATE pattern
        agents = [
            AgentTemplate(
                id=f"agent-{i}",
                role=f"Agent {i}",
                capabilities=[f"capability_{i}"],
                tier_preference="CAPABLE",
                tools=[],
                default_instructions="Test agent",
                quality_gates={},
            )
            for i in range(3)
        ]
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        # Should use testing domain default (sequential)
        assert pattern == CompositionPattern.SEQUENTIAL

    def test_does_not_select_cached_for_few_agents(self, orchestrator, sample_agent):
        """Test cached pattern NOT selected with fewer than 3 agents."""
        large_context = "x" * 3000
        requirements = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.GENERAL,
            capabilities_needed=["test_capability"],
            context={"cached_context": large_context},
        )

        agents = [sample_agent, sample_agent]  # Only 2 agents
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        assert pattern != CompositionPattern.PROMPT_CACHED_SEQUENTIAL


# ============================================================================
# Pattern 10: Delegation Chain Strategy Selection Tests
# ============================================================================


class TestDelegationChainPatternSelection:
    """Tests for delegation chain pattern selection."""

    def test_selects_delegation_for_complex_with_coordinator(
        self,
        orchestrator,
        coordinator_agent,
        specialist_agent,
    ):
        """Test delegation pattern selected for complex task with coordinator."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.COMPLEX,
            domain=TaskDomain.ARCHITECTURE,
            capabilities_needed=["coordinate", "code_analysis"],
            context={},
        )

        agents = [coordinator_agent, specialist_agent]
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        assert pattern == CompositionPattern.DELEGATION_CHAIN

    def test_does_not_select_delegation_without_coordinator(self, orchestrator):
        """Test delegation NOT selected without coordinator agent."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.COMPLEX,
            domain=TaskDomain.GENERAL,
            capabilities_needed=["code_analysis"],
            context={},
        )

        # Create 2 distinct specialist agents (no coordinator)
        agents = [
            AgentTemplate(
                id="specialist-1",
                role="Code Specialist",
                capabilities=["code_analysis"],
                tier_preference="CAPABLE",
                tools=[],
                default_instructions="Analyze code",
                quality_gates={},
            ),
            AgentTemplate(
                id="specialist-2",
                role="Test Specialist",
                capabilities=["test_analysis"],
                tier_preference="CAPABLE",
                tools=[],
                default_instructions="Analyze tests",
                quality_gates={},
            ),
        ]
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        # Should fall back to adaptive for complex tasks
        assert pattern == CompositionPattern.ADAPTIVE

    def test_does_not_select_delegation_for_simple_tasks(
        self,
        orchestrator,
        coordinator_agent,
        specialist_agent,
    ):
        """Test delegation NOT selected for simple tasks."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.SIMPLE,  # Not complex
            domain=TaskDomain.GENERAL,
            capabilities_needed=["coordinate", "code_analysis"],
            context={},
        )

        agents = [coordinator_agent, specialist_agent]
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        # Simple tasks don't need delegation chain
        assert pattern != CompositionPattern.DELEGATION_CHAIN


# ============================================================================
# Integration Tests
# ============================================================================


class TestAnthropicPatternsMetaOrchestratorIntegration:
    """Integration tests for Anthropic patterns in meta-orchestrator."""

    def test_composition_pattern_enum_includes_new_patterns(self):
        """Test that CompositionPattern enum includes all 10 patterns."""
        patterns = [p.value for p in CompositionPattern]

        # Original 7 + CONDITIONAL + 3 Anthropic = 11 total
        assert "sequential" in patterns
        assert "parallel" in patterns
        assert "debate" in patterns
        assert "teaching" in patterns
        assert "refinement" in patterns
        assert "adaptive" in patterns
        assert "conditional" in patterns

        # New Anthropic patterns
        assert "tool_enhanced" in patterns
        assert "prompt_cached_sequential" in patterns
        assert "delegation_chain" in patterns

        # Should have at least 10 patterns
        assert len(patterns) >= 10

    def test_all_patterns_have_duration_estimates(self, orchestrator, sample_agent):
        """Test that _estimate_duration handles all patterns."""
        # Test each pattern doesn't raise an error
        for pattern in CompositionPattern:
            duration = orchestrator._estimate_duration([sample_agent], pattern)
            assert duration > 0, f"Pattern {pattern.value} should have positive duration"

    def test_tool_enhanced_pattern_in_full_workflow(self, orchestrator):
        """Test tool-enhanced pattern selected in analyze_and_compose workflow."""
        plan = orchestrator.analyze_and_compose(
            task="Read and analyze file",
            context={"tools": [{"name": "read_file", "description": "Read files"}]},
        )

        # Should select tool-enhanced for simple task with tools
        assert plan.strategy == CompositionPattern.TOOL_ENHANCED

    def test_delegation_pattern_in_full_workflow(self, orchestrator):
        """Test delegation pattern selected in analyze_and_compose workflow."""
        # Create a complex architectural task that would need coordination
        plan = orchestrator.analyze_and_compose(
            task="Prepare comprehensive architecture redesign",
            context={},
        )

        # For complex architecture tasks, should select appropriate pattern
        # (May be PARALLEL or DELEGATION_CHAIN depending on agents selected)
        assert plan.strategy in [
            CompositionPattern.PARALLEL,
            CompositionPattern.DELEGATION_CHAIN,
            CompositionPattern.ADAPTIVE,
        ]

    def test_execution_plan_created_with_new_patterns(
        self,
        orchestrator,
        coordinator_agent,
        specialist_agent,
    ):
        """Test that execution plans can be created with new patterns."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.COMPLEX,
            domain=TaskDomain.ARCHITECTURE,
            capabilities_needed=["coordinate", "code_analysis"],
            quality_gates={"min_quality": 80},
        )

        # Test each new pattern
        for pattern in [
            CompositionPattern.TOOL_ENHANCED,
            CompositionPattern.PROMPT_CACHED_SEQUENTIAL,
            CompositionPattern.DELEGATION_CHAIN,
        ]:
            plan = orchestrator.create_execution_plan(
                requirements=requirements,
                agents=[coordinator_agent, specialist_agent],
                strategy=pattern,
            )

            assert plan.strategy == pattern
            assert len(plan.agents) == 2
            assert plan.estimated_duration > 0
            assert plan.estimated_cost > 0


# ============================================================================
# Pattern Selection Logic Tests
# ============================================================================


class TestPatternSelectionPriority:
    """Tests for pattern selection priority and fallback logic."""

    def test_tool_enhanced_takes_priority_over_sequential(self, orchestrator, sample_agent):
        """Test that tool-enhanced is chosen over sequential when tools present."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.GENERAL,
            capabilities_needed=["test_capability"],
            context={"tools": [{"name": "test_tool"}]},
        )

        pattern = orchestrator._choose_composition_pattern(requirements, [sample_agent])

        # Should prefer tool-enhanced over sequential
        assert pattern == CompositionPattern.TOOL_ENHANCED

    def test_delegation_takes_priority_over_adaptive(
        self,
        orchestrator,
        coordinator_agent,
        specialist_agent,
    ):
        """Test that delegation is chosen over adaptive for complex with coordinator."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.COMPLEX,
            domain=TaskDomain.GENERAL,
            capabilities_needed=["coordinate", "analyze"],
            context={},
        )

        agents = [coordinator_agent, specialist_agent]
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        # Should prefer delegation over adaptive when coordinator present
        assert pattern == CompositionPattern.DELEGATION_CHAIN

    def test_cached_takes_priority_over_sequential(self, orchestrator, sample_agent):
        """Test that cached sequential chosen over regular sequential with large context."""
        large_context = "x" * 3000
        requirements = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.TESTING,
            capabilities_needed=["test_capability"],
            context={"cached_context": large_context},
        )

        agents = [sample_agent, sample_agent, sample_agent]
        pattern = orchestrator._choose_composition_pattern(requirements, agents)

        # Should prefer cached sequential over regular sequential
        assert pattern == CompositionPattern.PROMPT_CACHED_SEQUENTIAL
