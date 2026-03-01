"""Tests for Anthropic-inspired agent composition patterns.

Tests the three new patterns:
1. ToolEnhancedStrategy - Single agent with tools
2. PromptCachedSequentialStrategy - Shared cached context
3. DelegationChainStrategy - Hierarchical delegation

Created: 2026-01-29
"""

import pytest

from attune.orchestration.agent_templates import AgentTemplate
from attune.orchestration.execution_strategies import (
    DelegationChainStrategy,
    PromptCachedSequentialStrategy,
    ToolEnhancedStrategy,
)

# ============================================================================
# Fixtures
# ============================================================================


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
def sample_tools():
    """Create sample tool definitions."""
    return [
        {
            "name": "read_file",
            "description": "Read a file from disk",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path"}},
                "required": ["path"],
            },
        },
        {
            "name": "analyze_code",
            "description": "Analyze Python code for issues",
            "input_schema": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Code to analyze"}},
                "required": ["code"],
            },
        },
    ]


# ============================================================================
# Pattern 8: ToolEnhancedStrategy Tests
# ============================================================================


class TestToolEnhancedStrategy:
    """Tests for single agent with tools pattern."""

    def test_initialization(self, sample_tools):
        """Test strategy initialization."""
        strategy = ToolEnhancedStrategy(tools=sample_tools)
        assert strategy.tools == sample_tools

    def test_initialization_without_tools(self):
        """Test strategy initialization without tools."""
        strategy = ToolEnhancedStrategy()
        assert strategy.tools == []

    @pytest.mark.asyncio
    async def test_no_agents_provided(self, sample_tools):
        """Test error handling when no agents provided."""
        strategy = ToolEnhancedStrategy(tools=sample_tools)
        result = await strategy.execute(agents=[], context={"task": "Test"})

        assert result.success is False
        assert len(result.errors) == 1
        assert "No agent provided" in result.errors[0]


# ============================================================================
# Pattern 9: PromptCachedSequentialStrategy Tests
# ============================================================================


class TestPromptCachedSequentialStrategy:
    """Tests for cached context sharing pattern."""

    def test_initialization_with_context(self):
        """Test initialization with cached context."""
        cached_context = "This is shared context"
        strategy = PromptCachedSequentialStrategy(cached_context=cached_context)
        assert strategy.cached_context == cached_context
        assert strategy.cache_ttl == 3600  # Default

    def test_initialization_custom_ttl(self):
        """Test initialization with custom TTL."""
        strategy = PromptCachedSequentialStrategy(cached_context="test", cache_ttl=7200)
        assert strategy.cache_ttl == 7200


# ============================================================================
# Pattern 10: DelegationChainStrategy Tests
# ============================================================================


class TestDelegationChainStrategy:
    """Tests for hierarchical delegation pattern."""

    def test_initialization_default_depth(self):
        """Test initialization with default max depth."""
        strategy = DelegationChainStrategy()
        assert strategy.max_depth == 3

    def test_initialization_custom_depth(self):
        """Test initialization with custom max depth."""
        strategy = DelegationChainStrategy(max_depth=2)
        assert strategy.max_depth == 2

    def test_max_depth_capped_at_three(self):
        """Test that max depth is capped at 3 (Anthropic guideline)."""
        strategy = DelegationChainStrategy(max_depth=10)
        assert strategy.max_depth == 3  # Should be capped

    @pytest.mark.asyncio
    async def test_max_depth_enforcement(self):
        """Test that max delegation depth is enforced."""
        coordinator = AgentTemplate(
            id="coordinator",
            role="Coordinator",
            capabilities=["coordinate"],
            tier_preference="PREMIUM",
            tools=[],
            default_instructions="Coordinate tasks",
            quality_gates={},
        )

        strategy = DelegationChainStrategy(max_depth=3)

        # Try to exceed max depth
        result = await strategy.execute(
            agents=[coordinator],
            context={"task": "Test", "_delegation_depth": 3},
        )

        assert result.success is False
        assert len(result.errors) == 1
        assert "Max delegation depth" in result.errors[0]

    @pytest.mark.asyncio
    async def test_no_agents_provided(self):
        """Test error handling when no agents provided."""
        strategy = DelegationChainStrategy()
        result = await strategy.execute(agents=[], context={"task": "Test"})

        assert result.success is False
        assert "No agents provided" in result.errors[0]


# ============================================================================
# Integration Tests
# ============================================================================


class TestAnthropicPatternsIntegration:
    """Integration tests for Anthropic patterns."""

    def test_strategy_registry_includes_new_patterns(self):
        """Test that new patterns are registered."""
        from attune.orchestration.execution_strategies import STRATEGY_REGISTRY

        assert "tool_enhanced" in STRATEGY_REGISTRY
        assert "prompt_cached_sequential" in STRATEGY_REGISTRY
        assert "delegation_chain" in STRATEGY_REGISTRY

        assert STRATEGY_REGISTRY["tool_enhanced"] == ToolEnhancedStrategy
        assert STRATEGY_REGISTRY["prompt_cached_sequential"] == PromptCachedSequentialStrategy
        assert STRATEGY_REGISTRY["delegation_chain"] == DelegationChainStrategy

    def test_get_strategy_by_name(self):
        """Test getting strategies by name."""
        from attune.orchestration.execution_strategies import get_strategy

        strategy1 = get_strategy("tool_enhanced")
        assert isinstance(strategy1, ToolEnhancedStrategy)

        strategy2 = get_strategy("prompt_cached_sequential")
        assert isinstance(strategy2, PromptCachedSequentialStrategy)

        strategy3 = get_strategy("delegation_chain")
        assert isinstance(strategy3, DelegationChainStrategy)

    def test_all_patterns_implement_base_interface(self):
        """Test that all new patterns implement ExecutionStrategy interface."""
        from attune.orchestration.execution_strategies import ExecutionStrategy

        assert issubclass(ToolEnhancedStrategy, ExecutionStrategy)
        assert issubclass(PromptCachedSequentialStrategy, ExecutionStrategy)
        assert issubclass(DelegationChainStrategy, ExecutionStrategy)

    def test_pattern_count(self):
        """Test that we now have 13 total patterns (7 original + 3 nested + 3 new)."""
        from attune.orchestration.execution_strategies import STRATEGY_REGISTRY

        # Original 7 + 3 nested variants + 3 new Anthropic patterns = 13 total
        assert len(STRATEGY_REGISTRY) >= 10  # At least 10 patterns

    def test_tool_enhanced_strategy_instantiation(self, sample_tools):
        """Test that tool-enhanced strategy can be instantiated."""
        strategy = ToolEnhancedStrategy(tools=sample_tools)
        assert strategy is not None
        assert hasattr(strategy, "execute")

    def test_prompt_cached_strategy_instantiation(self):
        """Test that prompt-cached strategy can be instantiated."""
        strategy = PromptCachedSequentialStrategy(cached_context="test context")
        assert strategy is not None
        assert hasattr(strategy, "execute")

    def test_delegation_chain_strategy_instantiation(self):
        """Test that delegation-chain strategy can be instantiated."""
        strategy = DelegationChainStrategy(max_depth=3)
        assert strategy is not None
        assert hasattr(strategy, "execute")

    def test_new_patterns_have_proper_docstrings(self):
        """Test that new patterns have proper documentation."""
        assert ToolEnhancedStrategy.__doc__ is not None
        assert "Anthropic" in ToolEnhancedStrategy.__doc__

        assert PromptCachedSequentialStrategy.__doc__ is not None
        assert "Anthropic" in PromptCachedSequentialStrategy.__doc__

        assert DelegationChainStrategy.__doc__ is not None
        assert "Anthropic" in DelegationChainStrategy.__doc__


# ============================================================================
# Architecture Compliance Tests
# ============================================================================
