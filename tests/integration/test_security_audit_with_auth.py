"""Test security audit with authentication strategy integration.

Demonstrates:
1. Codebase size detection
2. Auth mode recommendation
3. Cost estimation
4. Full security audit with auth tracking
5. Security findings analysis
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
from attune.workflows.security_audit import SecurityAuditWorkflow


async def test_security_audit_with_auth():
    """Test security audit with auth strategy."""
    print("🔒 Testing Security Audit + Auth Strategy Integration\n")
    print("=" * 60)

    # Test on src/attune directory
    test_target = Path("src/attune")

    if not test_target.exists():
        print(f"❌ Test target not found: {test_target}")
        return

    # === STEP 1: Codebase Size Detection ===
    print("\n1. Codebase Size Detection")
    print("-" * 60)

    # Count lines across all Python files in directory
    codebase_lines = 0
    if test_target.is_dir():
        for py_file in test_target.rglob("*.py"):
            codebase_lines += count_lines_of_code(py_file)
    else:
        codebase_lines = count_lines_of_code(test_target)

    size_category = get_module_size_category(codebase_lines)

    print(f"   Target: {test_target}")
    print(f"   Lines of code: {codebase_lines:,}")
    print(f"   Size category: {size_category}")

    # === STEP 2: Auth Strategy Recommendation ===
    print("\n2. Auth Strategy Recommendation")
    print("-" * 60)

    # Use MAX tier for testing (most capable tier)
    max_strategy = AuthStrategy(
        subscription_tier=SubscriptionTier.MAX,
        default_mode=AuthMode.AUTO,
        setup_completed=True,
    )
    max_strategy.save()
    print("   ✓ Saved auth strategy to ~/.attune/auth_strategy.json\n")

    recommended_mode = max_strategy.get_recommended_mode(codebase_lines)
    print(f"   Subscription tier: {max_strategy.subscription_tier.value}")
    print(f"   Recommended mode: {recommended_mode.value}")

    cost_estimate = max_strategy.estimate_cost(codebase_lines, recommended_mode)
    print("\n   Cost Estimate:")
    print(f"      Mode: {cost_estimate['mode']}")
    if cost_estimate["mode"] == "subscription":
        print(f"      Monetary cost: ${cost_estimate['monetary_cost']}")
        print(f"      Quota cost: {cost_estimate['quota_cost']}")
        print(f"      Fits in 200K context: {cost_estimate['fits_in_context']}")
    else:
        print(f"      Monetary cost: ${cost_estimate['monetary_cost']:.4f}")
        print(f"      Fits in 1M context: {cost_estimate['fits_in_context']}")

    # === STEP 3: Security Audit Execution ===
    print("\n3. Security Audit (with auth tracking)")
    print("-" * 60)

    workflow = SecurityAuditWorkflow(
        enable_auth_strategy=True,
        skip_remediate_if_clean=True,  # Skip remediation for clean scans
        use_crew_for_assessment=False,  # Disable crew for faster test
        use_crew_for_remediation=False,
    )

    print(f"   Scanning {test_target}...")
    print("   Auth strategy: ENABLED")
    print(f"   Expected recommendation: {recommended_mode.value}")
    print("   File types: [.py, .ts, .tsx, .js, .jsx]")

    # Run workflow
    result = await workflow.execute(
        path=str(test_target),
        file_types=[".py", ".ts", ".tsx", ".js", ".jsx"],
    )

    # === STEP 4: Results Analysis ===
    print("\n4. Results Analysis")
    print("=" * 60)

    if hasattr(result, "final_output") and isinstance(result.final_output, dict):
        output = result.final_output
    elif isinstance(result, dict):
        output = result
    else:
        print(f"❌ Unexpected result format: {type(result)}")
        return

    auth_mode_used = output.get("auth_mode_used")
    files_scanned = output.get("files_scanned", 0)
    finding_count = output.get("finding_count", 0)
    needs_review = output.get("needs_review", [])
    false_positives = output.get("false_positives", [])
    accepted_risks = output.get("accepted_risks", [])
    assessment = output.get("assessment", {})

    print("\n   Security Audit Results:")
    print(f"      Files scanned: {files_scanned}")
    print(f"      Total findings: {finding_count}")
    print(f"      Needs review: {len(needs_review)}")
    print(f"      False positives: {len(false_positives)}")
    print(f"      Accepted risks: {len(accepted_risks)}")

    if assessment:
        risk_level = assessment.get("risk_level", "unknown")
        risk_score = assessment.get("risk_score", 0)
        severity_breakdown = assessment.get("severity_breakdown", {})

        print("\n   Risk Assessment:")
        print(f"      Risk level: {risk_level.upper()}")
        print(f"      Risk score: {risk_score}/100")
        print(f"      Critical: {severity_breakdown.get('critical', 0)}")
        print(f"      High: {severity_breakdown.get('high', 0)}")
        print(f"      Medium: {severity_breakdown.get('medium', 0)}")
        print(f"      Low: {severity_breakdown.get('low', 0)}")

    print("\n   Auth Strategy:")
    print(f"      Recommended: {recommended_mode.value}")
    print(f"      Tracked in workflow: {auth_mode_used or 'Not tracked'}")
    print(f"      Match: {auth_mode_used == recommended_mode.value}")

    # === STEP 5: Findings Samples ===
    if needs_review:
        print("\n5. Sample Findings Requiring Review")
        print("-" * 60)

        for i, finding in enumerate(needs_review[:3], 1):  # Show first 3
            vuln_type = finding.get("type", "unknown")
            severity = finding.get("severity", "unknown")
            file_path = finding.get("file", "").split("empathy-framework/")[-1]
            line = finding.get("line", 0)
            owasp = finding.get("owasp", "")

            print(f"\n   Finding {i}:")
            print(f"      Type: {vuln_type}")
            print(f"      Severity: {severity.upper()}")
            print(f"      File: {file_path}:{line}")
            print(f"      OWASP: {owasp}")

        if len(needs_review) > 3:
            print(f"\n   ... and {len(needs_review) - 3} more findings")

    # === STEP 6: Quality Checks ===
    print("\n6. Quality Checks")
    print("-" * 60)

    checks = [
        ("✅" if files_scanned > 0 else "❌", "Files were scanned"),
        ("✅" if auth_mode_used else "❌", "Auth mode tracked"),
        (
            "✅" if auth_mode_used == recommended_mode.value else "❌",
            "Auth mode matches recommendation",
        ),
        ("✅" if assessment else "❌", "Assessment generated"),
        ("✅" if "risk_score" in assessment else "❌", "Risk score calculated"),
        ("✅" if "severity_breakdown" in assessment else "❌", "Severity breakdown included"),
    ]

    for icon, check in checks:
        print(f"   {icon} {check}")

    # === STEP 7: Cost Analysis ===
    if hasattr(result, "cost_report"):
        print("\n7. Cost Report")
        print("-" * 60)

        print(f"   Total cost: ${result.cost_report.total_cost:.4f}")
        print(
            f"   Savings: ${result.cost_report.savings:.4f} ({result.cost_report.savings_percent:.1f}%)",
        )
        print(f"   Stages with costs: {len(result.cost_report.by_stage)}")

        if result.cost_report.by_stage:
            print("   Stage breakdown:")
            for stage, cost in result.cost_report.by_stage.items():
                print(f"      {stage}: ${cost:.4f}")

    print("\n" + "=" * 60)
    print("✅ Integration Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_security_audit_with_auth())
