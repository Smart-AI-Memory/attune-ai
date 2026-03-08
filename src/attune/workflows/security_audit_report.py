"""Security Audit Report Formatting.

Human-readable report formatter and CLI entry point for security audits.
Extracted from security_audit.py for maintainability.

Contains:
- format_security_report: Formats security audit output as a readable report
- main: CLI entry point

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations


def format_security_report(output: dict) -> str:
    """Format security audit output as a human-readable report.

    This format is designed to be:
    - Easy for humans to read and understand
    - Easy to copy/paste to an AI assistant for remediation help
    - Actionable with clear severity levels and file locations

    Args:
        output: The workflow output dictionary

    Returns:
        Formatted report string

    """
    lines = []

    # Header
    assessment = output.get("assessment", {})
    risk_level = assessment.get("risk_level", "unknown").upper()
    risk_score = assessment.get("risk_score", 0)

    lines.append("=" * 60)
    lines.append("SECURITY AUDIT REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Risk Level: {risk_level}")
    lines.append(f"Risk Score: {risk_score}/100")
    lines.append("")

    # Severity breakdown
    breakdown = assessment.get("severity_breakdown", {})
    lines.append("Severity Summary:")
    for sev in ["critical", "high", "medium", "low"]:
        count = breakdown.get(sev, 0)
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
        lines.append(f"  {icon} {sev.capitalize()}: {count}")
    lines.append("")

    # Files scanned
    files_scanned = output.get("files_scanned", 0)
    lines.append(f"Files Scanned: {files_scanned}")
    lines.append("")

    # Findings requiring review
    needs_review = output.get("needs_review", [])
    if needs_review:
        lines.append("-" * 60)
        lines.append("FINDINGS REQUIRING REVIEW")
        lines.append("-" * 60)
        lines.append("")

        for i, finding in enumerate(needs_review, 1):
            severity = finding.get("severity", "unknown").upper()
            vuln_type = finding.get("type", "unknown")
            file_path = finding.get("file", "").split("Empathy-framework/")[-1]
            line_num = finding.get("line", 0)
            match = finding.get("match", "")[:50]
            owasp = finding.get("owasp", "")
            is_test = finding.get("is_test", False)
            analysis = finding.get("analysis", "")

            test_marker = " [TEST FILE]" if is_test else ""
            lines.append(f"{i}. [{severity}]{test_marker} {vuln_type}")
            lines.append(f"   File: {file_path}:{line_num}")
            lines.append(f"   Match: {match}")
            lines.append(f"   OWASP: {owasp}")
            if analysis:
                lines.append(f"   Analysis: {analysis}")
            lines.append("")

    # Accepted risks
    accepted = output.get("accepted_risks", [])
    if accepted:
        lines.append("-" * 60)
        lines.append("ACCEPTED RISKS (No Action Required)")
        lines.append("-" * 60)
        lines.append("")

        for finding in accepted:
            vuln_type = finding.get("type", "unknown")
            file_path = finding.get("file", "").split("Empathy-framework/")[-1]
            line_num = finding.get("line", 0)
            reason = finding.get("decision_reason", "")

            lines.append(f"  - {vuln_type} in {file_path}:{line_num}")
            if reason:
                lines.append(f"    Reason: {reason}")
        lines.append("")

    # Remediation plan if present
    remediation = output.get("remediation_plan", "")
    if remediation and remediation.strip():
        lines.append("-" * 60)
        lines.append("REMEDIATION PLAN")
        lines.append("-" * 60)
        lines.append("")
        lines.append(remediation)
        lines.append("")

    # Footer with action items
    lines.append("=" * 60)
    if needs_review:
        lines.append("ACTION REQUIRED:")
        lines.append(f"  Review {len(needs_review)} finding(s) above")
        lines.append("  Copy this report to Claude Code for remediation help")
    else:
        lines.append("STATUS: All clear - no critical or high findings")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    """CLI entry point for security audit workflow."""
    import asyncio

    from .security_audit import SecurityAuditWorkflow

    async def run():
        """Run the security audit analysis stage."""
        workflow = SecurityAuditWorkflow()
        result = await workflow.execute(path=".", file_types=[".py"])

        # Use the new formatted report
        report = format_security_report(result.final_output)
        print(report)

        print("\nCost Report:")
        print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
        savings = result.cost_report.savings
        pct = result.cost_report.savings_percent
        print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())
