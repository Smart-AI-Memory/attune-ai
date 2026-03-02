#!/usr/bin/env python3
"""Demo script for Test Creation and Management Workflow.

Shows the full workflow execution with simulated user responses.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from attune.meta_workflows import FormResponse, MetaWorkflow, TemplateRegistry


def main():
    """Run the test creation workflow demo."""
    print("=" * 80)
    print("TEST CREATION AND MANAGEMENT WORKFLOW - DEMO")
    print("=" * 80)
    print()

    # Load template
    print("📋 Loading template...")
    # Use built-in test-coverage-boost template (similar to test creation workflow)
    templates_dir = Path(__file__).parent / ".empathy" / "meta_workflows" / "templates"
    registry = TemplateRegistry(storage_dir=str(templates_dir))
    template = registry.load_template("test-coverage-boost")  # Built-in template
    print(f"✅ Loaded: {template.name}")
    print(f"   Questions: {len(template.form_schema.questions)}")
    print(f"   Agents: {len(template.agent_composition_rules)}")
    print(
        f"   Cost Range: ${template.estimated_cost_range[0]:.2f}-${template.estimated_cost_range[1]:.2f}"
    )
    print()

    # Show questions that would be asked
    print("❓ Questions (what would be asked interactively):")
    print()
    for i, question in enumerate(template.form_schema.questions, 1):
        print(f"{i}. {question.text}")
        print(f"   Type: {question.type.value}")
        if question.options:
            print(
                f"   Options: {', '.join(question.options[:3])}{'...' if len(question.options) > 3 else ''}"
            )
        print()

    # Simulated user responses (what a real user would provide)
    # Using test-coverage-boost template's expected format
    print("💭 Simulating user responses...")
    print()

    responses = {
        "target_coverage": "80%",
        "test_style": "pytest",
        "prioritize_high_impact": "Yes",
        "include_edge_cases": "Yes",
    }

    for key, value in responses.items():
        question = next((q for q in template.form_schema.questions if q.id == key), None)
        if question:
            print(f"   {question.text}")
            if isinstance(value, list):
                for item in value:
                    print(f"      ✓ {item}")
            elif isinstance(value, bool):
                print(f"      → {'Yes' if value else 'No'}")
            else:
                print(f"      → {value}")
            print()

    # Create form response
    form_response = FormResponse(
        template_id="test-coverage-boost",  # Match loaded template
        responses=responses,
    )

    # Create and execute workflow
    print("🚀 Executing workflow...")
    print()

    workflow = MetaWorkflow(template=template)

    try:
        result = workflow.execute(
            form_response=form_response,
            mock_execution=True,  # Use mock execution for demo
        )

        print("=" * 80)
        print("✅ WORKFLOW EXECUTION COMPLETE")
        print("=" * 80)
        print()

        # Show results
        print(f"Run ID: {result.run_id}")
        print(f"Success: {result.success}")
        print(f"Timestamp: {result.timestamp}")
        print()

        print("📊 Agent Team Created:")
        for agent in result.agents_created:
            print(f"   • {agent.role}")
            print(f"     - Tier Strategy: {agent.tier_strategy.value}")
            print(
                f"     - Tools: {', '.join(agent.tools[:3])}{'...' if len(agent.tools) > 3 else ''}"
            )

            # Show execution result if available
            if result.agent_results:
                agent_result = next((r for r in result.agent_results if r.role == agent.role), None)
                if agent_result:
                    print(f"     - Executed: {agent_result.tier_used} tier")
                    print(f"     - Cost: ${agent_result.cost:.2f}")
                    print(f"     - Duration: {agent_result.duration:.1f}s")
            print()

        print("💰 Cost Summary:")
        print(f"   Total Cost: ${result.total_cost:.2f}")
        print(f"   Total Duration: {result.total_duration:.2f}s")
        print()

        print("📁 Results Saved To:")
        print(f"   .attune/meta_workflows/executions/{result.run_id}/")
        print()

        print("🔍 View Details:")
        print(f"   empathy meta-workflow show-run {result.run_id}")
        print()

        print("=" * 80)
        print("WHAT THIS WORKFLOW WOULD DO (in production):")
        print("=" * 80)
        print()

        print("1. 📊 Analyze existing tests")
        print("   - Scan entire project for test files")
        print("   - Calculate current coverage (e.g., 65%)")
        print("   - Identify gaps and missing tests")
        print()

        print("2. 🧪 Generate new tests")
        print("   - Create unit tests for uncovered functions")
        print("   - Generate integration tests for module interactions")
        print("   - Design E2E tests for user workflows")
        print()

        print("3. ✅ Validate test quality")
        print("   - Check assertion depth (min 2+ assertions)")
        print("   - Validate edge case coverage")
        print("   - Ensure error handling tests exist")
        print()

        print("4. 🔧 Update outdated tests")
        print("   - Fix broken tests")
        print("   - Modernize test syntax")
        print("   - Improve test quality")
        print()

        print("5. 🏭 Create fixtures")
        print("   - Generate realistic test data with Faker")
        print("   - Create reusable fixtures")
        print("   - Set up cleanup strategies")
        print()

        print("6. ⚡ Performance tests")
        print("   - Create benchmarks for critical paths")
        print("   - Set up load tests")
        print("   - Establish performance baselines")
        print()

        print("7. 📈 Generate reports")
        print("   - Coverage report (HTML + terminal)")
        print("   - JUnit XML for CI/CD")
        print("   - Performance metrics report")
        print()

        print("8. 🔄 CI/CD integration")
        print("   - Generate GitHub Actions workflow")
        print("   - Configure parallel test execution")
        print("   - Set up coverage upload to Codecov")
        print()

        print("9. 📚 Create documentation")
        print("   - Write test plan documentation")
        print("   - Document fixtures and factories")
        print("   - Create testing best practices guide")
        print()

        print("=" * 80)
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
