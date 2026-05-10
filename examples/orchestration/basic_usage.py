"""Basic Meta-Orchestration Examples

This file demonstrates simple usage patterns for the meta-orchestration system.

Perfect for getting started - shows the most common use cases without complexity.

Run these examples:
    python basic_usage.py

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio

from attune.agents.release import ReleasePrepTeamWorkflow
from attune.orchestration.agent_templates import (
    get_all_templates,
    get_template,
    get_templates_by_capability,
)
from attune.orchestration.execution_strategies import get_strategy
from attune.orchestration.meta_orchestrator import MetaOrchestrator

# =============================================================================
# Example 1: Release Preparation with Default Settings
# =============================================================================


async def example1_basic_release_prep():
    """Simplest possible usage - release prep with defaults."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Release Preparation")
    print("=" * 60)

    # Create workflow
    workflow = ReleasePrepTeamWorkflow()

    # Execute on current directory
    report = await workflow.execute(path=".")

    # Check results
    if report.approved:
        print(f"\n✅ Release APPROVED (confidence: {report.confidence})")
    else:
        print(f"\n❌ Release BLOCKED (confidence: {report.confidence})")
        print("\nBlockers:")
        for blocker in report.blockers:
            print(f"  • {blocker}")

    # Print formatted report
    print("\n" + report.format_console_output())


# =============================================================================
# Example 2: Release Prep with Custom Quality Gates
# =============================================================================


async def example2_custom_quality_gates():
    """Release prep with stricter quality requirements."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Quality Gates")
    print("=" * 60)

    # Define custom quality gates
    quality_gates = {
        "min_coverage": 90.0,  # Raise from 80% to 90%
        "min_quality_score": 8.5,  # Raise from 7.0 to 8.5
        "max_critical_issues": 0,  # Still zero tolerance
        "min_doc_coverage": 100.0,  # Full documentation required
    }

    print("\nQuality Gates:")
    for gate, threshold in quality_gates.items():
        print(f"  • {gate}: {threshold}")

    # Create workflow with custom gates
    workflow = ReleasePrepTeamWorkflow(quality_gates=quality_gates)

    # Execute
    report = await workflow.execute(path=".")

    # Display summary
    print(f"\nResult: {'APPROVED' if report.approved else 'BLOCKED'}")
    print(
        f"Quality Gates Passed: {sum(1 for g in report.quality_gates if g.passed)}/{len(report.quality_gates)}"
    )


# =============================================================================
# Example 4: Exploring Available Agent Templates
# =============================================================================
# (Example 3 retired with TestCoverageBoostWorkflow in v7.0.0;
# numbering preserved so example identifiers remain stable.)


def example4_explore_templates():
    """Discover available agent templates and capabilities."""
    print("\n" + "=" * 60)
    print("Example 4: Available Agent Templates")
    print("=" * 60)

    # Get all templates
    templates = get_all_templates()
    print(f"\n📋 {len(templates)} agent templates available:\n")

    for template in templates:
        print(f"  {template.id}")
        print(f"    Role: {template.role}")
        print(f"    Tier: {template.tier_preference}")
        print(f"    Capabilities: {', '.join(template.capabilities)}")
        print(f"    Tools: {', '.join(template.tools)}")
        print()

    # Find templates by capability
    print("\n🔍 Templates with 'vulnerability_scan' capability:")
    security_templates = get_templates_by_capability("vulnerability_scan")
    for template in security_templates:
        print(f"  • {template.id}: {template.role}")

    # Get specific template
    print("\n📖 Detailed view of 'test_coverage_analyzer':")
    template = get_template("test_coverage_analyzer")
    if template:
        print(f"  Role: {template.role}")
        print(f"  Tier: {template.tier_preference}")
        print(f"  Min Tokens: {template.resource_requirements.min_tokens}")
        print(f"  Max Tokens: {template.resource_requirements.max_tokens}")
        print(f"  Timeout: {template.resource_requirements.timeout_seconds}s")
        print(f"  Quality Gates: {template.quality_gates}")


# =============================================================================
# Example 5: Direct Meta-Orchestrator Usage
# =============================================================================


async def example5_direct_orchestrator():
    """Use meta-orchestrator directly to analyze tasks."""
    print("\n" + "=" * 60)
    print("Example 5: Direct Meta-Orchestrator Usage")
    print("=" * 60)

    # Create orchestrator
    orchestrator = MetaOrchestrator()

    # Analyze different tasks
    tasks = [
        "Improve test coverage to 90%",
        "Perform security audit for production deployment",
        "Optimize database query performance",
        "Generate API documentation for all endpoints",
    ]

    for task in tasks:
        print(f"\n📝 Task: {task}")

        # Analyze and create execution plan
        plan = orchestrator.analyze_and_compose(task=task, context={"priority": "high"})

        print(f"  Strategy: {plan.strategy.value}")
        print(f"  Agents: {[a.id for a in plan.agents]}")
        print(f"  Estimated Cost: {plan.estimated_cost:.2f} units")
        print(f"  Estimated Duration: {plan.estimated_duration}s")


# =============================================================================
# Example 6: Executing with Specific Strategy
# =============================================================================


async def example6_specific_strategy():
    """Execute agents with a specific composition pattern."""
    print("\n" + "=" * 60)
    print("Example 6: Using Specific Strategy")
    print("=" * 60)

    # Get agents
    security = get_template("security_auditor")
    coverage = get_template("test_coverage_analyzer")
    quality = get_template("code_reviewer")

    agents = [security, coverage, quality]

    print("\n🤖 Selected Agents:")
    for agent in agents:
        print(f"  • {agent.role}")

    # Execute with parallel strategy
    print("\n⚡ Executing with PARALLEL strategy...")

    strategy = get_strategy("parallel")
    result = await strategy.execute(agents=agents, context={"path": ".", "strict_mode": True})

    print("\n✅ Execution Complete!")
    print(f"  Success: {result.success}")
    print(f"  Duration: {result.total_duration:.2f}s")
    print(f"  Agents: {len(result.outputs)}")

    # Show individual agent results
    print("\n📊 Individual Results:")
    for agent_result in result.outputs:
        status = "✅" if agent_result.success else "❌"
        print(f"  {status} {agent_result.agent_id}: {agent_result.duration_seconds:.2f}s")


# =============================================================================
# Example 7: Comparing Strategies
# =============================================================================


async def example7_compare_strategies():
    """Compare different composition strategies."""
    print("\n" + "=" * 60)
    print("Example 7: Strategy Comparison")
    print("=" * 60)

    # Get agents
    agents = [
        get_template("test_coverage_analyzer"),
        get_template("code_reviewer"),
        get_template("documentation_writer"),
    ]

    context = {"project_root": "."}

    strategies = ["sequential", "parallel"]

    print(f"\n🤖 Agents: {[a.id for a in agents]}\n")

    for strategy_name in strategies:
        print(f"⚡ {strategy_name.upper()} Strategy:")

        strategy = get_strategy(strategy_name)
        result = await strategy.execute(agents, context)

        print(f"  Duration: {result.total_duration:.2f}s")
        print(f"  Success: {result.success}")
        print()


# =============================================================================
# Example 8: Error Handling
# =============================================================================


async def example8_error_handling():
    """Demonstrate proper error handling."""
    print("\n" + "=" * 60)
    print("Example 8: Error Handling")
    print("=" * 60)

    # Example 1: Invalid quality gates
    print("\n1. Handling invalid quality gates:")
    try:
        workflow = ReleasePrepTeamWorkflow(quality_gates={"min_coverage": 150.0})  # Invalid: >100
    except ValueError as e:
        print(f"  ❌ Caught ValueError: {e}")

    # Example 2: Invalid path
    print("\n2. Handling invalid path:")
    try:
        workflow = ReleasePrepTeamWorkflow()
        report = await workflow.execute(path="")  # Empty path
    except ValueError as e:
        print(f"  ❌ Caught ValueError: {e}")

    # Example 3: Invalid strategy name
    print("\n3. Handling invalid strategy:")
    try:
        strategy = get_strategy("invalid_strategy")
    except ValueError as e:
        print(f"  ❌ Caught ValueError: {e}")

    # Example 4: Empty agents list
    print("\n4. Handling empty agents list:")
    try:
        strategy = get_strategy("sequential")
        result = await strategy.execute([], {})
    except ValueError as e:
        print(f"  ❌ Caught ValueError: {e}")

    print("\n✅ All errors handled gracefully!")


# =============================================================================
# Main Runner
# =============================================================================


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Meta-Orchestration Basic Examples")
    print("=" * 60)

    # Run examples
    await example1_basic_release_prep()
    await example2_custom_quality_gates()
    example4_explore_templates()
    await example5_direct_orchestrator()
    await example6_specific_strategy()
    await example7_compare_strategies()
    await example8_error_handling()

    print("\n" + "=" * 60)
    print("All Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Run async examples
    asyncio.run(main())
