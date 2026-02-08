"""Workflow Chaining Demo

Demonstrates automatic workflow chaining based on results.

Usage:
    python examples/workflow_chaining_demo.py

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from attune.routing import ChainExecutor


def demo_chain_config():
    """Demo 1: Show loaded chain configuration."""
    print("=" * 70)
    print("DEMO 1: Chain Configuration")
    print("=" * 70)

    executor = ChainExecutor()

    print("\n✅ Chain configuration loaded successfully!")
    print(f"\n📋 Available templates: {len(executor.list_templates())}")

    for template_name, workflows in executor.list_templates().items():
        print(f"\n  📦 {template_name}:")
        print(f"     Workflows: {' → '.join(workflows)}")


def demo_trigger_evaluation():
    """Demo 2: Evaluate triggers for sample results."""
    print("\n" + "=" * 70)
    print("DEMO 2: Trigger Evaluation")
    print("=" * 70)

    executor = ChainExecutor()

    # Scenario 1: Security audit finds critical issues
    print("\n🔍 Scenario 1: Security audit finds 5 high-severity issues")
    result = {
        "high_severity_count": 5,
        "critical_issues": 1,
        "vulnerability_types": ["sql_injection", "xss"],
    }

    triggered = executor.get_triggered_chains("security-audit", result)

    if triggered:
        print(f"\n  ✅ Triggered {len(triggered)} chain(s):")
        for trigger in triggered:
            approval = "⚠️ Approval required" if trigger.approval_required else "✓ Auto"
            print(f"    → {trigger.next_workflow}")
            print(f"      {approval}")
            print(f"      Reason: {trigger.reason}")
    else:
        print("  ℹ️  No chains triggered")

    # Scenario 2: Code review detects large changes
    print("\n\n🔍 Scenario 2: Code review detects 15 file changes with low coverage")
    result = {
        "files_changed": 15,
        "test_coverage": 0.45,
        "high_complexity_count": 3,
    }

    triggered = executor.get_triggered_chains("code-review", result)

    if triggered:
        print(f"\n  ✅ Triggered {len(triggered)} chain(s):")
        for trigger in triggered:
            approval = "⚠️ Approval required" if trigger.approval_required else "✓ Auto"
            print(f"    → {trigger.next_workflow}")
            print(f"      {approval}")
            print(f"      Reason: {trigger.reason}")
    else:
        print("  ℹ️  No chains triggered")

    # Scenario 3: Performance audit finds memory issues
    print("\n\n🔍 Scenario 3: Performance audit finds memory issues")
    result = {
        "critical_perf_issues": 2,
        "memory_issues": 5,
        "optimization_score": 35,
    }

    triggered = executor.get_triggered_chains("perf-audit", result)

    if triggered:
        print(f"\n  ✅ Triggered {len(triggered)} chain(s):")
        for trigger in triggered:
            approval = "⚠️ Approval required" if trigger.approval_required else "✓ Auto"
            print(f"    → {trigger.next_workflow}")
            print(f"      {approval}")
            print(f"      Reason: {trigger.reason}")
    else:
        print("  ℹ️  No chains triggered")


def demo_template_execution():
    """Demo 3: Show how to execute templates."""
    print("\n" + "=" * 70)
    print("DEMO 3: Template Execution")
    print("=" * 70)

    executor = ChainExecutor()

    print("\n📦 Available templates:")
    for template_name, workflows in executor.list_templates().items():
        print(f"\n  {template_name}:")
        print(f"    {' → '.join(workflows)}")

    print("\n\n💡 To execute a template:")
    print("   await executor.execute_template('full-security-review', input_data)")


def demo_configuration_tips():
    """Demo 4: Configuration tips."""
    print("\n" + "=" * 70)
    print("DEMO 4: Configuration Tips")
    print("=" * 70)

    print(
        """
✅ Chain Configuration Loaded: .attune/workflow_chains.yaml

📝 Key Features:

1. **Automatic Triggers**
   - Chains run based on workflow results
   - Example: security-audit → bug-predict (if issues > 3)

2. **Approval Control**
   - auto_approve: false (default) = Ask user
   - auto_approve: true = Fully automatic
   - Per-chain approval settings available

3. **Pre-defined Templates**
   - full-security-review: Complete security pipeline
   - qa-pipeline: Quality assurance workflow
   - pre-release: Validation before release

4. **Safety Features**
   - max_chain_depth: 4 (prevents infinite loops)
   - cost_optimization: Skip expensive chains if budget low
   - rate_limits: Maximum 20 chains/hour

🔧 Configuration File:
   .attune/workflow_chains.yaml

📊 Usage:
   # Run workflow - chains trigger automatically
   empathy workflow run security-audit

   # Execute template
   empathy workflow template full-security-review

   # Enable auto-approval (edit .attune/workflow_chains.yaml)
   global:
     auto_approve: true  # Set to true for fully automatic

💡 Best Practices:
   1. Start with auto_approve: false (safer)
   2. Test chains with small codebases first
   3. Monitor chain_history.jsonl for patterns
   4. Adjust triggers based on your workflow
    """
    )


def demo_real_world_scenario():
    """Demo 5: Real-world scenario walkthrough."""
    print("\n" + "=" * 70)
    print("DEMO 5: Real-World Scenario")
    print("=" * 70)

    print(
        """
📖 Scenario: Developer commits security-sensitive code

1. Developer runs:
   $ empathy workflow run security-audit

2. Security scan finds:
   ✓ 6 high-severity issues
   ✓ 1 SQL injection vulnerability
   ✓ 2 XSS vulnerabilities

3. Framework evaluates triggers:
   ✓ high_severity_count (6) > 3 → Trigger bug-predict
   ✓ 'sql_injection' in types → Trigger code-review (needs approval)

4. Terminal output:
   🔗 Chain triggered: bug-predict
      ✓ Auto-approved (reason: Many security issues found)
      ⏳ Running bug-predict...

   🔗 Chain suggested: code-review
      ⚠️  Approval required (reason: SQL injection detected)
      ❓ Run code-review? [y/N]:

5. User types 'y':
   ⏳ Running code-review...
   ✅ Full security review complete!

6. Results saved:
   📊 .attune/chain_history.jsonl
   📁 Individual workflow outputs

💰 Cost Impact:
   - Without chaining: $0.015 (single workflow)
   - With chaining: $0.032 (3 workflows)
   - Value: Comprehensive security review ✨
    """
    )


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("WORKFLOW CHAINING DEMO")
    print("Empathy Framework - Automatic Workflow Chains")
    print("=" * 70)

    try:
        demo_chain_config()
        demo_trigger_evaluation()
        demo_template_execution()
        demo_configuration_tips()
        demo_real_world_scenario()

        print("\n" + "=" * 70)
        print("✅ DEMO COMPLETE")
        print("=" * 70)
        print("\nNext Steps:")
        print("1. Review: .attune/workflow_chains.yaml")
        print("2. Try: empathy workflow run security-audit")
        print("3. Watch: Chains trigger automatically based on results")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
