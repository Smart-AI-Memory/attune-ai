"""Dependency Check Report Formatting and CLI Entry Point.

Extracted from dependency_check.py for maintainability.

Functions:
    format_dependency_check_report: Format check output as human-readable report
    main: CLI entry point for dependency check workflow

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations


def format_dependency_check_report(result: dict, input_data: dict) -> str:
    """Format dependency check output as a human-readable report.

    Args:
        result: The report stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string

    """
    lines = []

    # Header with risk level
    risk_score = result.get("risk_score", 0)

    if risk_score >= 75:
        risk_icon = "🔴"
        risk_text = "CRITICAL"
    elif risk_score >= 50:
        risk_icon = "🟠"
        risk_text = "HIGH RISK"
    elif risk_score >= 25:
        risk_icon = "🟡"
        risk_text = "MEDIUM RISK"
    else:
        risk_icon = "🟢"
        risk_text = "LOW RISK"

    lines.append("=" * 60)
    lines.append("DEPENDENCY SECURITY REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Risk Level: {risk_icon} {risk_text}")
    lines.append(f"Risk Score: {risk_score}/100")
    lines.append("")

    # Inventory summary
    total_deps = result.get("total_dependencies", 0)
    python_count = input_data.get("python_count", 0)
    node_count = input_data.get("node_count", 0)
    files_found = input_data.get("files_found", [])

    lines.append("-" * 60)
    lines.append("DEPENDENCY INVENTORY")
    lines.append("-" * 60)
    lines.append(f"Total Dependencies: {total_deps}")
    if python_count:
        lines.append(f"  Python: {python_count}")
    if node_count:
        lines.append(f"  Node.js: {node_count}")
    if files_found:
        lines.append(f"Files Scanned: {len(files_found)}")
        for f in files_found[:5]:
            lines.append(f"  • {f}")
    lines.append("")

    # Vulnerability summary
    summary = result.get("summary", {})
    vuln_count = result.get("vulnerability_count", 0)
    outdated_count = result.get("outdated_count", 0)

    lines.append("-" * 60)
    lines.append("SECURITY FINDINGS")
    lines.append("-" * 60)
    lines.append(f"Vulnerabilities: {vuln_count}")
    lines.append(f"  🔴 Critical: {summary.get('critical', 0)}")
    lines.append(f"  🟠 High: {summary.get('high', 0)}")
    lines.append(f"  🟡 Medium: {summary.get('medium', 0)}")
    lines.append(f"Outdated Packages: {outdated_count}")
    lines.append("")

    # Vulnerabilities detail
    assessment = input_data.get("assessment", {})
    vulnerabilities = assessment.get("vulnerabilities", [])
    if vulnerabilities:
        lines.append("-" * 60)
        lines.append("VULNERABLE PACKAGES")
        lines.append("-" * 60)
        for vuln in vulnerabilities[:10]:
            severity = vuln.get("severity", "unknown").upper()
            pkg = vuln.get("package", "unknown")
            version = vuln.get("current_version", "?")
            cve = vuln.get("cve", "N/A")
            sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(severity, "⚪")
            lines.append(f"  {sev_icon} {pkg}@{version}")
            lines.append(f"      CVE: {cve} | Severity: {severity}")
        if len(vulnerabilities) > 10:
            lines.append(f"  ... and {len(vulnerabilities) - 10} more")
        lines.append("")

    # Recommendations
    recommendations = result.get("recommendations", [])
    if recommendations:
        lines.append("-" * 60)
        lines.append("REMEDIATION ACTIONS")
        lines.append("-" * 60)
        priority_labels = {1: "🔴 URGENT", 2: "🟠 HIGH", 3: "🟡 REVIEW"}
        for rec in recommendations[:10]:
            priority = rec.get("priority", 3)
            pkg = rec.get("package", "unknown")
            suggestion = rec.get("suggestion", "")
            label = priority_labels.get(priority, "⚪ LOW")
            lines.append(f"  {label}: {pkg}")
            lines.append(f"      {suggestion}")
        lines.append("")

    # Security report from LLM (if available)
    security_report = result.get("security_report", "")
    if security_report and not security_report.startswith("[Simulated"):
        lines.append("-" * 60)
        lines.append("DETAILED ANALYSIS")
        lines.append("-" * 60)
        # Truncate if very long
        if len(security_report) > 1500:
            lines.append(security_report[:1500] + "...")
        else:
            lines.append(security_report)
        lines.append("")

    # Footer
    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    lines.append(f"Scanned {total_deps} dependencies using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    """CLI entry point for dependency check workflow."""
    import asyncio

    async def run():
        from .dependency_check import DependencyCheckWorkflow

        workflow = DependencyCheckWorkflow()
        result = await workflow.execute(path=".")

        print("\nDependency Check Results")
        print("=" * 50)
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")

        report = result.final_output.get("report", {})
        print(f"Risk Level: {report.get('risk_level', 'N/A')}")
        print(f"Risk Score: {report.get('risk_score', 0)}/100")
        print(f"Total Dependencies: {report.get('total_dependencies', 0)}")
        print(f"Vulnerabilities: {report.get('vulnerability_count', 0)}")
        print(f"Outdated: {report.get('outdated_count', 0)}")

        print("\nCost Report:")
        print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
        savings = result.cost_report.savings
        pct = result.cost_report.savings_percent
        print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())
