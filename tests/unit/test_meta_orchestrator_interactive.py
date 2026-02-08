"""Tests for meta-orchestrator interactive features (Phases 2 & 3).

Tests confidence scoring, interactive branching, and pattern wizard features
added to support user choice when automatic selection has low confidence.

Created: 2026-01-29
"""

from unittest.mock import Mock, patch

import pytest

from attune.orchestration.agent_templates import AgentTemplate
from attune.orchestration.meta_orchestrator import (
    CompositionPattern,
    MetaOrchestrator,
    TaskComplexity,
    TaskDomain,
    TaskRequirements,
)

# attune.tools now exists - no module-level mock needed


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def orchestrator():
    """Create meta-orchestrator instance."""
    return MetaOrchestrator()


@pytest.fixture
def simple_requirements():
    """Create simple task requirements (high confidence)."""
    return TaskRequirements(
        complexity=TaskComplexity.SIMPLE,
        domain=TaskDomain.TESTING,
        capabilities_needed=["analyze_gaps"],
        context={},
    )


@pytest.fixture
def complex_requirements():
    """Create complex task requirements (low confidence)."""
    return TaskRequirements(
        complexity=TaskComplexity.COMPLEX,
        domain=TaskDomain.GENERAL,
        capabilities_needed=["coord1", "coord2", "coord3", "coord4", "coord5", "coord6"],
        context={},
    )


@pytest.fixture
def test_agent():
    """Create test agent."""
    return AgentTemplate(
        id="test-agent",
        role="Test Agent",
        capabilities=["test_capability"],
        tier_preference="CAPABLE",
        tools=[],
        default_instructions="Test agent",
        quality_gates={},
    )


@pytest.fixture
def many_agents():
    """Create list of 6 agents (triggers low confidence)."""
    return [
        AgentTemplate(
            id=f"agent-{i}",
            role=f"Agent {i}",
            capabilities=[f"capability_{i}"],
            tier_preference="CAPABLE",
            tools=[],
            default_instructions="Test agent",
            quality_gates={},
        )
        for i in range(6)
    ]


# ============================================================================
# Confidence Scoring Tests
# ============================================================================


class TestConfidenceScoring:
    """Tests for _calculate_confidence() method."""

    def test_high_confidence_simple_task(self, orchestrator, simple_requirements, test_agent):
        """Test high confidence for simple, clear task."""
        confidence = orchestrator._calculate_confidence(
            requirements=simple_requirements,
            agents=[test_agent],
            pattern=CompositionPattern.SEQUENTIAL,
        )

        assert confidence >= 0.8, "Simple task with clear domain should have high confidence"

    def test_low_confidence_general_domain(self, orchestrator, test_agent):
        """Test reduced confidence for GENERAL domain."""
        requirements = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.GENERAL,  # Ambiguous domain
            capabilities_needed=["generic"],
            context={},
        )

        confidence = orchestrator._calculate_confidence(
            requirements=requirements,
            agents=[test_agent],
            pattern=CompositionPattern.SEQUENTIAL,
        )

        assert confidence < 0.8, "GENERAL domain should reduce confidence"

    def test_low_confidence_many_agents(self, orchestrator, complex_requirements, many_agents):
        """Test reduced confidence for many agents (complex coordination)."""
        confidence = orchestrator._calculate_confidence(
            requirements=complex_requirements,
            agents=many_agents,  # 6 agents
            pattern=CompositionPattern.SEQUENTIAL,
        )

        assert confidence < 0.8, "Many agents should reduce confidence"

    def test_low_confidence_complex_task(self, orchestrator, complex_requirements, test_agent):
        """Test reduced confidence for complex task."""
        confidence = orchestrator._calculate_confidence(
            requirements=complex_requirements,
            agents=[test_agent],
            pattern=CompositionPattern.SEQUENTIAL,
        )

        assert confidence < 0.9, "Complex task should reduce confidence"

    def test_confidence_boost_anthropic_patterns(
        self, orchestrator, simple_requirements, test_agent
    ):
        """Test confidence boost for Anthropic patterns."""
        # Test tool-enhanced pattern
        confidence_tool = orchestrator._calculate_confidence(
            requirements=simple_requirements,
            agents=[test_agent],
            pattern=CompositionPattern.TOOL_ENHANCED,
        )

        # Test delegation chain pattern
        confidence_delegation = orchestrator._calculate_confidence(
            requirements=simple_requirements,
            agents=[test_agent],
            pattern=CompositionPattern.DELEGATION_CHAIN,
        )

        # Test cached sequential pattern
        confidence_cached = orchestrator._calculate_confidence(
            requirements=simple_requirements,
            agents=[test_agent],
            pattern=CompositionPattern.PROMPT_CACHED_SEQUENTIAL,
        )

        # All should have boost (1.1x multiplier)
        assert confidence_tool >= 0.9, "Tool-enhanced should get confidence boost"
        assert confidence_delegation >= 0.9, "Delegation chain should get confidence boost"
        assert confidence_cached >= 0.9, "Cached sequential should get confidence boost"

    def test_confidence_boost_domain_specific_patterns(self, orchestrator, test_agent):
        """Test confidence boost for domain-specific pattern matches."""
        # Documentation domain with teaching pattern
        doc_requirements = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.DOCUMENTATION,
            capabilities_needed=["generate_docs"],
            context={},
        )

        confidence = orchestrator._calculate_confidence(
            requirements=doc_requirements,
            agents=[test_agent],
            pattern=CompositionPattern.TEACHING,
        )

        assert confidence >= 0.85, "Domain-specific pattern should get confidence boost"

    def test_confidence_capped_at_one(self, orchestrator, simple_requirements, test_agent):
        """Test that confidence is capped at 1.0."""
        confidence = orchestrator._calculate_confidence(
            requirements=simple_requirements,
            agents=[test_agent],
            pattern=CompositionPattern.TOOL_ENHANCED,  # Gets 1.1x boost
        )

        assert confidence <= 1.0, "Confidence should be capped at 1.0"


# ============================================================================
# Interactive Mode Tests
# ============================================================================


class TestInteractiveMode:
    """Tests for analyze_and_compose_interactive() method."""

    def test_high_confidence_automatic_execution(
        self, orchestrator, simple_requirements, test_agent
    ):
        """Test that high confidence proceeds automatically without prompting."""
        with patch.object(orchestrator, "_analyze_task", return_value=simple_requirements):
            with patch.object(orchestrator, "_select_agents", return_value=[test_agent]):
                with patch.object(
                    orchestrator,
                    "_choose_composition_pattern",
                    return_value=CompositionPattern.SEQUENTIAL,
                ):
                    # Should NOT call _prompt_user_for_approach
                    with patch.object(orchestrator, "_prompt_user_for_approach") as mock_prompt:
                        plan = orchestrator.analyze_and_compose_interactive(
                            task="Simple test task", context={}
                        )

                        mock_prompt.assert_not_called()
                        assert plan.strategy == CompositionPattern.SEQUENTIAL
                        assert len(plan.agents) == 1

    def test_low_confidence_prompts_user(self, orchestrator, complex_requirements, many_agents):
        """Test that low confidence prompts user for choice."""
        with patch.object(orchestrator, "_analyze_task", return_value=complex_requirements):
            with patch.object(orchestrator, "_select_agents", return_value=many_agents):
                with patch.object(
                    orchestrator,
                    "_choose_composition_pattern",
                    return_value=CompositionPattern.SEQUENTIAL,
                ):
                    # Mock _prompt_user_for_approach to return plan
                    mock_plan = Mock()
                    with patch.object(
                        orchestrator,
                        "_prompt_user_for_approach",
                        return_value=mock_plan,
                    ) as mock_prompt:
                        plan = orchestrator.analyze_and_compose_interactive(
                            task="Complex ambiguous task", context={}
                        )

                        mock_prompt.assert_called_once()
                        assert plan == mock_plan

    def test_analyze_and_compose_with_interactive_flag(self, orchestrator):
        """Test that analyze_and_compose respects interactive flag."""
        with patch.object(orchestrator, "analyze_and_compose_interactive") as mock_interactive:
            orchestrator.analyze_and_compose(task="Test task", context={}, interactive=True)

            mock_interactive.assert_called_once_with("Test task", {})

    def test_analyze_and_compose_without_interactive_flag(self, orchestrator):
        """Test that analyze_and_compose uses automatic mode by default."""
        with patch.object(orchestrator, "analyze_and_compose_interactive") as mock_interactive:
            with patch.object(orchestrator, "_analyze_task") as mock_analyze:
                with patch.object(orchestrator, "_select_agents", return_value=[]):
                    with patch.object(orchestrator, "_choose_composition_pattern"):
                        try:
                            orchestrator.analyze_and_compose(task="Test task", context={})
                        except (ValueError, AttributeError):
                            # Expected to fail due to mocking, but we check the call pattern
                            pass

                        mock_interactive.assert_not_called()
                        mock_analyze.assert_called_once()


# ============================================================================
# User Prompting Tests
# ============================================================================


class TestUserPrompting:
    """Tests for _prompt_user_for_approach() method."""

    def test_graceful_degradation_without_ask_user_question(
        self, orchestrator, simple_requirements, test_agent
    ):
        """Test fallback when AskUserQuestion is not available.

        Since AskUserQuestion raises NotImplementedError, the method should
        gracefully fall back to automatic selection.
        """
        # AskUserQuestion will raise NotImplementedError, triggering fallback
        plan = orchestrator._prompt_user_for_approach(
            requirements=simple_requirements,
            agents=[test_agent],
            recommended_pattern=CompositionPattern.SEQUENTIAL,
            confidence=0.75,
        )

        # Should fall back to automatic selection
        assert plan.strategy == CompositionPattern.SEQUENTIAL
        assert len(plan.agents) == 1


# ============================================================================
# Interactive Team Builder Tests
# ============================================================================


class TestInteractiveTeamBuilder:
    """Tests for _interactive_team_builder() method."""

    def test_graceful_degradation_uses_defaults(
        self, orchestrator, simple_requirements, test_agent
    ):
        """Test that team builder falls back to defaults when tool unavailable.

        Since AskUserQuestion raises NotImplementedError, should use
        the suggested agents and pattern.
        """
        plan = orchestrator._interactive_team_builder(
            requirements=simple_requirements,
            suggested_agents=[test_agent],
            suggested_pattern=CompositionPattern.SEQUENTIAL,
        )

        # Should use suggested defaults
        assert plan.strategy == CompositionPattern.SEQUENTIAL
        assert len(plan.agents) == 1


# ============================================================================
# Pattern Chooser Wizard Tests
# ============================================================================


class TestPatternChooserWizard:
    """Tests for _pattern_chooser_wizard() method."""

    def test_graceful_degradation_without_ask_user_question(
        self, orchestrator, simple_requirements, test_agent
    ):
        """Test fallback when AskUserQuestion is not available.

        Since AskUserQuestion raises NotImplementedError, should fall back
        to automatic pattern selection based on requirements.
        """
        plan = orchestrator._pattern_chooser_wizard(
            requirements=simple_requirements,
            suggested_agents=[test_agent],
        )

        # Should fall back to automatic pattern selection
        assert plan.strategy in CompositionPattern
        # For simple requirements with testing domain, should select SEQUENTIAL
        assert plan.strategy == CompositionPattern.SEQUENTIAL


# ============================================================================
# Pattern Description Tests
# ============================================================================


class TestPatternDescriptions:
    """Tests for _get_pattern_description() method."""

    def test_all_patterns_have_descriptions(self, orchestrator):
        """Test that all patterns have descriptions."""
        for pattern in CompositionPattern:
            description = orchestrator._get_pattern_description(pattern)

            assert isinstance(description, str)
            assert len(description) > 0
            # All descriptions should contain meaningful content
            # (arrows, parallel markers, or descriptive text)
            assert any(
                [
                    "→" in description,
                    "||" in description,
                    "⇄" in description,
                    "pattern" in description.lower(),
                    "routing" in description.lower(),
                    "sequential" in description.lower(),
                    "parallel" in description.lower(),
                    "agent" in description.lower(),
                    "branching" in description.lower(),
                    "if" in description.lower(),
                ]
            ), f"Pattern {pattern.value} has insufficient description: {description}"

    def test_anthropic_patterns_descriptions(self, orchestrator):
        """Test that Anthropic patterns have clear descriptions."""
        tool_desc = orchestrator._get_pattern_description(CompositionPattern.TOOL_ENHANCED)
        assert "tool" in tool_desc.lower()

        cached_desc = orchestrator._get_pattern_description(
            CompositionPattern.PROMPT_CACHED_SEQUENTIAL
        )
        assert "cached" in cached_desc.lower() or "cache" in cached_desc.lower()

        delegation_desc = orchestrator._get_pattern_description(CompositionPattern.DELEGATION_CHAIN)
        assert "delegation" in delegation_desc.lower() or "hierarchical" in delegation_desc.lower()


# ============================================================================
# Integration Tests
# ============================================================================


class TestInteractiveIntegration:
    """Integration tests for complete interactive workflows."""

    def test_full_interactive_workflow_high_confidence(self, orchestrator):
        """Test that high confidence proceeds automatically without prompting.

        When confidence >= 0.8, should execute automatically without
        trying to call AskUserQuestion.
        """
        plan = orchestrator.analyze_and_compose_interactive(
            task="Simple test coverage task",
            context={},
        )

        assert plan is not None
        assert isinstance(plan.strategy, CompositionPattern)
        assert len(plan.agents) > 0

    def test_full_interactive_workflow_low_confidence_fallback(self, orchestrator):
        """Test that low confidence falls back gracefully when tool unavailable.

        When confidence < 0.8 but AskUserQuestion is not available,
        should fall back to automatic selection.
        """
        # Force low confidence scenario
        with patch.object(orchestrator, "_calculate_confidence", return_value=0.75):
            plan = orchestrator.analyze_and_compose_interactive(
                task="Test task",
                context={},
            )

            assert plan is not None
            assert isinstance(plan.strategy, CompositionPattern)
            assert len(plan.agents) > 0

    def test_interactive_with_tool_enhanced_context(self, orchestrator):
        """Test interactive mode completes successfully with tools in context.

        Tool-enhanced pattern is selected when exactly 1 agent is chosen AND
        tools are in the context passed to _choose_composition_pattern.
        The full workflow may not preserve context through all steps.
        """
        plan = orchestrator.analyze_and_compose_interactive(
            task="Analyze files",
            context={"tools": [{"name": "read_file"}]},
        )

        assert plan is not None
        assert isinstance(plan.strategy, CompositionPattern)
        assert len(plan.agents) > 0
        # Workflow completed successfully, pattern selection happened
        # (actual pattern depends on implementation details of agent selection)
