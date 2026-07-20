"""
Anthropic Agent Patterns - Simple Demo

Demonstrates the three new Anthropic-inspired composition patterns
without requiring actual LLM API calls.

Usage:
    python examples/anthropic_patterns_simple_demo.py

Requirements:
    pip install attune-ai
"""

import asyncio

from attune.orchestration import (
    DelegationChainStrategy,
    PromptCachedSequentialStrategy,
    ToolEnhancedStrategy,
    get_strategy,
)
from attune.orchestration.agent_templates import AgentTemplate

# ============================================================================
# Demo: Pattern 8 - Tool-Enhanced Strategy
# ============================================================================


async def demo_tool_enhanced():
    """Demonstrate tool-enhanced pattern (single agent with tools)."""
    print("\n" + "=" * 60)
    print("PATTERN 8: TOOL-ENHANCED STRATEGY")
    print("=" * 60)
    print("\nPrinciple: Use tools over multiple agents when possible")

    # Create single agent
    agent = AgentTemplate(
        id="code-analyzer",
        role="Code Analyzer",
        capabilities=["code_analysis", "file_operations"],
        tier_preference="CAPABLE",
        tools=[],
        default_instructions="Analyze code files and report findings.",
        quality_gates={},
    )

    # Define tools for the agent
    tools = [
        {
            "name": "read_file",
            "description": "Read file contents",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        {
            "name": "analyze_ast",
            "description": "Parse and analyze Python AST",
            "input_schema": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    ]

    # Create strategy
    strategy = ToolEnhancedStrategy(tools=tools)

    print(f"\n✓ Created strategy: {strategy.__class__.__name__}")
    print(f"✓ Agent: {agent.role}")
    print(f"✓ Tools: {len(tools)} tools available")
    print("\nThis pattern is more efficient than using:")
    print("  - Agent 1: File reader")
    print("  - Agent 2: AST analyzer")
    print("  - Agent 3: Report generator")


# ============================================================================
# Demo: Pattern 9 - Prompt-Cached Sequential Strategy
# ============================================================================


async def demo_prompt_cached_sequential():
    """Demonstrate prompt-cached sequential pattern."""
    print("\n" + "=" * 60)
    print("PATTERN 9: PROMPT-CACHED SEQUENTIAL STRATEGY")
    print("=" * 60)
    print("\nPrinciple: Cache large unchanging contexts across agent calls")

    # Create three agents that will share context
    agents = [
        AgentTemplate(
            id="security-reviewer",
            role="Security Reviewer",
            capabilities=["security_analysis"],
            tier_preference="CAPABLE",
            tools=[],
            default_instructions="Review code for security issues.",
            quality_gates={},
        ),
        AgentTemplate(
            id="quality-validator",
            role="Quality Validator",
            capabilities=["quality_assessment"],
            tier_preference="CAPABLE",
            tools=[],
            default_instructions="Assess code quality.",
            quality_gates={},
        ),
        AgentTemplate(
            id="performance-analyst",
            role="Performance Analyst",
            capabilities=["performance_analysis"],
            tier_preference="CAPABLE",
            tools=[],
            default_instructions="Analyze performance.",
            quality_gates={},
        ),
    ]

    # Large cached context (shared across all agents)
    cached_context = """
    # Codebase Architecture Documentation
    [Imagine 10,000 lines of architecture docs, API specs, coding standards here]

    This context is cached once and shared across all 3 agents,
    reducing token costs by ~60% on cache hits.
    """

    # Create strategy with cached context
    strategy = PromptCachedSequentialStrategy(cached_context=cached_context, cache_ttl=3600)

    print(f"\n✓ Created strategy: {strategy.__class__.__name__}")
    print(f"✓ Agents: {len(agents)} agents will share cached context")
    print(f"✓ Cache TTL: {strategy.cache_ttl} seconds")
    print(f"✓ Context size: {len(cached_context)} characters")
    print("\nBenefit: ~60% token cost reduction with cache hits")


# ============================================================================
# Demo: Pattern 10 - Delegation Chain Strategy
# ============================================================================


async def demo_delegation_chain():
    """Demonstrate delegation chain pattern."""
    print("\n" + "=" * 60)
    print("PATTERN 10: DELEGATION CHAIN STRATEGY")
    print("=" * 60)
    print("\nPrinciple: Keep hierarchies shallow (≤3 levels)")

    # Create coordinator and specialists
    coordinator = AgentTemplate(
        id="task-coordinator",
        role="Task Coordinator",
        capabilities=["coordination", "planning"],
        tier_preference="PREMIUM",
        tools=[],
        default_instructions="Coordinate complex tasks and delegate to specialists.",
        quality_gates={},
    )

    specialist1 = AgentTemplate(
        id="architecture-specialist",
        role="Architecture Specialist",
        capabilities=["architecture_analysis"],
        tier_preference="CAPABLE",
        tools=[],
        default_instructions="Analyze system architecture.",
        quality_gates={},
    )

    specialist2 = AgentTemplate(
        id="implementation-specialist",
        role="Implementation Specialist",
        capabilities=["code_implementation"],
        tier_preference="CAPABLE",
        tools=[],
        default_instructions="Implement code changes.",
        quality_gates={},
    )

    # Create strategy with max depth enforcement
    strategy = DelegationChainStrategy(max_depth=3)

    print(f"\n✓ Created strategy: {strategy.__class__.__name__}")
    print(f"✓ Max delegation depth: {strategy.max_depth} levels (enforced)")
    print(f"✓ Coordinator: {coordinator.role}")
    print(f"✓ Specialists: {specialist1.role}, {specialist2.role}")
    print("\nHierarchy:")
    print("  Level 0: Task Coordinator (analyzes, delegates)")
    print("    └─> Level 1: Architecture Specialist (designs)")
    print("    └─> Level 1: Implementation Specialist (implements)")


# ============================================================================
# Demo: Strategy Registry and Factory Pattern
# ============================================================================


async def demo_registry_and_factory():
    """Demonstrate strategy registry and factory pattern."""
    print("\n" + "=" * 60)
    print("STRATEGY REGISTRY & FACTORY PATTERN")
    print("=" * 60)
    print("\nAll 10 patterns accessible via get_strategy():")

    # Patterns that can be instantiated without arguments
    no_arg_patterns = [
        "sequential",
        "parallel",
        "debate",
        "teaching",
        "refinement",
        "adaptive",
        "tool_enhanced",
        "prompt_cached_sequential",
        "delegation_chain",
    ]

    # Patterns that require arguments (show but don't instantiate)
    arg_patterns = [
        "conditional",  # Requires condition and branches
    ]

    for pattern_name in no_arg_patterns:
        strategy = get_strategy(pattern_name)
        is_new = pattern_name in ["tool_enhanced", "prompt_cached_sequential", "delegation_chain"]
        marker = " (NEW)" if is_new else ""
        print(f"  ✓ {pattern_name:30s} → {strategy.__class__.__name__}{marker}")

    for pattern_name in arg_patterns:
        print(f"  ✓ {pattern_name:30s} → ConditionalStrategy (requires args)")


# ============================================================================
# Main Demo Runner
# ============================================================================


async def main():
    """Run all pattern demonstrations."""
    print("\n🚀 ANTHROPIC AGENT PATTERNS - SIMPLE DEMO")
    print("Demonstrating 3 new patterns in Attune AI v5.1.4+\n")

    try:
        # Pattern 8: Tool-Enhanced
        await demo_tool_enhanced()

        # Pattern 9: Prompt-Cached Sequential
        await demo_prompt_cached_sequential()

        # Pattern 10: Delegation Chain
        await demo_delegation_chain()

        # Registry and Factory
        await demo_registry_and_factory()

        print("\n" + "=" * 60)
        print("✅ ALL PATTERNS DEMONSTRATED SUCCESSFULLY")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Read docs/architecture/anthropic-agent-patterns.md")
        print(
            "  2. Try: python -c 'from attune.orchestration import get_strategy; print(get_strategy(\"tool_enhanced\"))'"
        )
        print("  3. Run tests: pytest tests/unit/test_anthropic_patterns.py -v")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
