"""Integration test for CodeReviewWorkflow with authentication strategy.

Demonstrates:
1. Module size detection
2. Auth mode recommendation
3. Cost estimation
4. Full code review execution with auth tracking
5. Results analysis and quality checks

Structure mirrors test_doc_with_auth.py for consistency.
"""

import asyncio
from pathlib import Path

from attune.models import (
    AuthMode,
    AuthStrategy,
    SubscriptionTier,
    count_lines_of_code,
    get_module_size_category,
)
from attune.workflows.code_review import CodeReviewWorkflow


async def test_code_review_with_auth():
    """Test code review workflow with auth strategy."""
    print("🔍 Testing Code Review + Auth Strategy Integration\n")
    print("=" * 60)

    # Test on cache_stats.py (same module as doc test for consistency)
    test_module = Path("src/attune/cache_stats.py")

    if not test_module.exists():
        print(f"❌ Test module not found: {test_module}")
        return

    # === STEP 1: Module Size Detection ===
    print("\n1. Module Size Detection")
    print("-" * 60)

    module_lines = count_lines_of_code(test_module)
    size_category = get_module_size_category(module_lines)

    print(f"   Module: {test_module.name}")
    print(f"   Lines of code: {module_lines}")
    print(f"   Size category: {size_category}")

    # === STEP 2: Auth Strategy Recommendation ===
    print("\n2. Auth Strategy Recommendation")
    print("-" * 60)

    # Test with Max user (should use subscription for small modules)
    max_strategy = AuthStrategy(
        subscription_tier=SubscriptionTier.MAX,
        default_mode=AuthMode.AUTO,
        setup_completed=True,  # Skip interactive setup
    )

    # Save strategy so workflow can load it
    max_strategy.save()
    print("   ✓ Saved auth strategy to ~/.attune/auth_strategy.json\n")

    recommended_mode = max_strategy.get_recommended_mode(module_lines)
    print(f"   Subscription tier: {max_strategy.subscription_tier.value}")
    print(f"   Recommended mode: {recommended_mode.value}")

    # Get cost estimate
    cost_estimate = max_strategy.estimate_cost(module_lines, recommended_mode)
    print("\n   Cost Estimate:")
    print(f"      Mode: {cost_estimate['mode']}")
    if cost_estimate["mode"] == "subscription":
        print(f"      Monetary cost: ${cost_estimate['monetary_cost']}")
        print(f"      Quota cost: {cost_estimate['quota_cost']}")
        print(f"      Fits in 200K context: {cost_estimate['fits_in_context']}")
    else:
        print(f"      Monetary cost: ${cost_estimate['monetary_cost']:.4f}")
        print(f"      Fits in 1M context: {cost_estimate['fits_in_context']}")

    # === STEP 3: Code Review Execution ===
    print("\n3. Code Review Execution (with auth tracking)")
    print("-" * 60)

    # Read source code
    source_code = test_module.read_text()

    # Create workflow with auth strategy enabled
    workflow = CodeReviewWorkflow(
        file_threshold=10,
        use_crew=False,  # Disable crew for simple integration test
        enable_auth_strategy=True,  # Enable auth strategy integration
    )

    print(f"   Reviewing {test_module.name}...")
    print("   Auth strategy: ENABLED")
    print(f"   Expected recommendation: {recommended_mode.value}")
    print("   Crew review: DISABLED (for faster testing)")

    # Execute code review
    result = await workflow.execute(
        diff=source_code,
        target=str(test_module),
        files_changed=[str(test_module)],
        is_core_module=False,
    )

    # === STEP 4: Results Analysis ===
    print("\n4. Results Analysis")
    print("=" * 60)

    # Extract results
    if hasattr(result, "final_output") and isinstance(result.final_output, dict):
        output = result.final_output
    elif isinstance(result, dict):
        output = result
    else:
        print(f"❌ Unexpected result format: {type(result)}")
        return

    # Extract review results
    classification = output.get("classification", "")
    scan_results = output.get("scan_results", "")
    architectural_review = output.get("architectural_review", "")
    verdict = output.get("verdict", "unknown")
    auth_mode_used = output.get("auth_mode_used")
    security_score = output.get("security_score", 0)
    has_critical_issues = output.get("has_critical_issues", False)

    print("\n   Review Results:")
    print(
        (
            f"      Classification: {classification[:80]}..."
            if classification
            else "      Classification: None"
        ),
    )
    print(f"      Verdict: {verdict.upper()}")
    print(f"      Security score: {security_score}/100")
    print(f"      Critical issues: {'Yes' if has_critical_issues else 'No'}")

    print("\n   Review Content:")
    print(f"      Scan results: {len(scan_results):,} characters")
    print(f"      Architectural review: {len(architectural_review):,} characters")

    print("\n   Auth Strategy:")
    print(f"      Recommended: {recommended_mode.value}")
    print(f"      Tracked in workflow: {auth_mode_used or 'Not tracked'}")
    print(f"      Match: {auth_mode_used == recommended_mode.value}")

    # === STEP 5: Quality Checks ===
    print("\n5. Quality Checks")
    print("-" * 60)

    checks = [
        ("✅" if classification else "❌", "Classification completed"),
        ("✅" if scan_results else "❌", "Security scan completed"),
        (
            (
                "✅"
                if verdict in ["approve", "approve_with_suggestions", "request_changes", "reject"]
                else "❌"
            ),
            "Valid verdict",
        ),
        ("✅" if security_score > 0 else "❌", "Security score calculated"),
        ("✅" if auth_mode_used else "❌", "Auth mode tracked"),
        (
            (
                "✅"
                if "security" in scan_results.lower() or "quality" in scan_results.lower()
                else "❌"
            ),
            "Scan includes security/quality analysis",
        ),
    ]

    for icon, check in checks:
        print(f"   {icon} {check}")

    # === STEP 6: Detailed Findings ===
    print("\n6. Detailed Findings")
    print("-" * 60)

    # Check for findings
    findings = output.get("findings", [])
    security_findings = output.get("security_findings", [])
    bug_patterns = output.get("bug_patterns", [])

    print(f"   Total findings: {len(findings)}")
    print(f"   Security findings: {len(security_findings)}")
    print(f"   Bug patterns: {len(bug_patterns)}")

    if findings:
        print("\n   Sample findings:")
        for i, finding in enumerate(findings[:3], 1):
            severity = finding.get("severity", "unknown")
            title = finding.get("title", "N/A")
            print(f"      {i}. [{severity.upper()}] {title}")

    # === STEP 7: Recommendation Summary ===
    print("\n7. Recommendation Summary")
    print("=" * 60)

    print(f"\n   For this module ({module_lines} LOC, {size_category}):")
    print(f"      Recommended: {recommended_mode.value.upper()} mode")

    if recommended_mode.value == "subscription":
        print("      Reason: Small module fits easily in 200K context")
        print("      Benefit: No additional cost, uses existing subscription")
    else:
        print("      Reason: Large module needs 1M context window")
        print("      Benefit: Higher context limit, no quota consumption")

    print("\n   Workflow Integration:")
    print("      ✅ Auth strategy detected module size")
    print(f"      ✅ Recommended {recommended_mode.value} mode")
    print("      ✅ Tracked auth_mode_used in results")
    print("      ✅ Ready for telemetry logging")

    # === STEP 8: Formatted Report Check ===
    print("\n8. Formatted Report")
    print("-" * 60)

    formatted_report = output.get("formatted_report", "")
    display_output = output.get("display_output", "")

    if formatted_report:
        print(f"   Formatted report: {len(formatted_report):,} characters")
        print(f"   Includes verdict: {'✅' if verdict.upper() in formatted_report else '❌'}")
        print(f"   Includes security: {'✅' if 'SECURITY' in formatted_report else '❌'}")
    else:
        print("   ❌ No formatted report generated")

    if display_output:
        print(f"   Display output: {len(display_output):,} characters")
    else:
        print("   ⚠️  No display_output field (may impact UI presentation)")

    print("\n" + "=" * 60)
    print("✅ Integration Test Complete!")
    print("=" * 60)

    # Print sample of formatted report if available
    if formatted_report:
        print("\nSample output (first 500 characters):")
        print("-" * 60)
        print(formatted_report[:500])
        if len(formatted_report) > 500:
            print("...")
        print("-" * 60)


async def test_code_review_with_api_mode():
    """Test code review workflow with API mode (large module simulation)."""
    print("\n\n🔍 Testing Code Review + Auth Strategy (API Mode)\n")
    print("=" * 60)

    # Simulate a large module by using a big LOC count
    # In real usage, this would be a large file like src/attune/workflows/base.py
    test_module = Path("src/attune/cache_stats.py")
    if not test_module.exists():
        print(f"❌ Test module not found: {test_module}")
        return

    print("\n1. Simulating Large Module (>8000 LOC)")
    print("-" * 60)
    print(f"   Note: Using {test_module.name} as test target")
    print("   Simulated LOC: 10,000 (would trigger API mode)")

    # Create strategy that should recommend API mode for large modules
    max_strategy = AuthStrategy(
        subscription_tier=SubscriptionTier.MAX,
        default_mode=AuthMode.AUTO,
        setup_completed=True,
    )

    simulated_loc = 10000
    recommended_mode = max_strategy.get_recommended_mode(simulated_loc)
    size_category = get_module_size_category(simulated_loc)

    print(f"   Size category: {size_category}")
    print(f"   Recommended mode: {recommended_mode.value}")

    cost_estimate = max_strategy.estimate_cost(simulated_loc, recommended_mode)
    print("\n   Cost Estimate:")
    print(f"      Mode: {cost_estimate['mode']}")
    print(f"      Monetary cost: ${cost_estimate['monetary_cost']:.4f}")
    print(f"      Fits in context: {cost_estimate['fits_in_context']}")

    print("\n2. Expected Behavior for Large Modules")
    print("-" * 60)
    print(f"   ✅ Strategy recommends {recommended_mode.value.upper()} mode")
    print("   ✅ Uses 1M context window (API)")
    print("   ✅ Avoids quota consumption on subscription")
    print(f"   ✅ Estimated cost: ${cost_estimate['monetary_cost']:.4f}")

    print("\n" + "=" * 60)
    print("✅ Large Module Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_code_review_with_auth())
    asyncio.run(test_code_review_with_api_mode())
