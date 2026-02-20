"""Code review security scan mixin.

Extracted from code_review.py for maintainability.

Contains:
    ScanMixin:
        _scan                — CAPABLE security scan and bug pattern matching
        _merge_external_audit — merge SecurityAuditCrew results into scan output

Expected host attributes (provided by BaseWorkflow / its mixins):
    _call_llm                       : async method (from LLMMixin)
    _extract_findings_from_response : method (from ResponseParsingMixin)
    _auth_mode_used                 : str | None

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from .base import ModelTier
from .code_review_report import format_code_review_report

logger = logging.getLogger(__name__)


class ScanMixin:
    """Mixin providing the security scan stage for code review."""

    async def _scan(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Security scan and bug pattern matching.

        When external_audit_results is provided in input_data (e.g., from
        SecurityAuditCrew), these findings are merged with the LLM analysis
        and can trigger architect_review if critical issues are found.
        """
        code_to_review = input_data.get("code_to_review", input_data.get("diff", ""))
        classification = input_data.get("classification", "")
        files_changed = input_data.get("files_changed", input_data.get("files", []))

        # Check for external audit results (e.g., from SecurityAuditCrew)
        external_audit = input_data.get("external_audit_results")

        system = """You are a security and code quality expert. Analyze the code for:

1. SECURITY ISSUES (OWASP Top 10):
   - SQL Injection, XSS, Command Injection
   - Hardcoded secrets, API keys, passwords
   - Insecure deserialization
   - Authentication/authorization flaws

2. BUG PATTERNS:
   - Null/undefined references
   - Resource leaks
   - Race conditions
   - Error handling issues

3. CODE QUALITY:
   - Code smells
   - Maintainability issues
   - Performance concerns

For each issue found, provide:
- Severity (critical/high/medium/low)
- Location (if identifiable)
- Description
- Recommendation

Be thorough but focused on actionable findings."""

        # If external audit provided, include it in the prompt for context
        external_context = ""
        if external_audit:
            external_summary = external_audit.get("summary", "")
            external_findings = external_audit.get("findings", [])
            if external_summary or external_findings:
                # Build findings list efficiently (avoid O(n**2) string concat)
                finding_lines = []
                for finding in external_findings[:10]:  # Top 10
                    sev = finding.get("severity", "unknown").upper()
                    title = finding.get("title", "N/A")
                    desc = finding.get("description", "")[:100]
                    finding_lines.append(f"- [{sev}] {title}: {desc}")

                external_context = f"""

## External Security Audit Results
Summary: {external_summary}

Findings ({len(external_findings)} total):
{chr(10).join(finding_lines)}

Verify these findings and identify additional issues."""

        user_message = f"""Review this code for security and quality issues:

Previous classification: {classification}
{external_context}
Code to review:
{code_to_review[:6000]}"""

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=2048,
        )

        # Extract structured findings from LLM response
        llm_findings = self._extract_findings_from_response(
            response=response,
            files_changed=files_changed or [],
            code_context=code_to_review[:1000],  # First 1000 chars for context
        )

        # Check if critical issues found in LLM response
        has_critical = "critical" in response.lower() or "high" in response.lower()

        # Merge external audit findings if provided
        security_findings: list[dict] = []
        external_has_critical = False

        if external_audit:
            merged_response, security_findings, external_has_critical = self._merge_external_audit(
                response,
                external_audit,
            )
            response = merged_response
            has_critical = has_critical or external_has_critical

        # Combine LLM findings with security findings
        all_findings = llm_findings + security_findings

        # Calculate summary statistics
        summary: dict[str, Any] = {
            "total_findings": len(all_findings),
            "by_severity": {},
            "by_category": {},
            "files_affected": list({f.get("file", "") for f in all_findings if f.get("file")}),
        }

        # Count by severity
        for finding in all_findings:
            sev = finding.get("severity", "info")
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1

        # Count by category
        for finding in all_findings:
            cat = finding.get("category", "other")
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

        # Add helpful message if no findings
        if len(all_findings) == 0:
            summary["message"] = (
                "No security or quality issues found in scan. "
                "Code will proceed to architectural review."
            )

        # Calculate security score
        security_score = 70 if has_critical else 90

        # Determine preliminary verdict based on scan
        if has_critical:
            preliminary_verdict = "request_changes"
        elif security_score >= 90:
            preliminary_verdict = "approve"
        else:
            preliminary_verdict = "approve_with_suggestions"

        result = {
            "scan_results": response,
            "findings": all_findings,  # NEW: structured findings for UI
            "summary": summary,  # NEW: summary statistics
            "security_findings": security_findings,  # Keep for backward compat
            "bug_patterns": [],
            "quality_issues": [],
            "has_critical_issues": has_critical,
            "security_score": security_score,
            "verdict": preliminary_verdict,  # Add verdict for when architect_review is skipped
            "needs_architect_review": input_data.get("needs_architect_review", False)
            or has_critical,
            "code_to_review": code_to_review,
            "classification": classification,
            "external_audit_included": external_audit is not None,
            "external_audit_risk_score": (
                external_audit.get("risk_score", 0) if external_audit else 0
            ),
            "auth_mode_used": self._auth_mode_used,  # Track auth mode
            "model_tier_used": tier.value,  # Track model tier
        }

        # Generate formatted report (for when architect_review is skipped)
        formatted_report = format_code_review_report(result, input_data)
        result["formatted_report"] = formatted_report
        result["display_output"] = formatted_report

        return (result, input_tokens, output_tokens)

    def _merge_external_audit(
        self,
        llm_response: str,
        external_audit: dict,
    ) -> tuple[str, list, bool]:
        """Merge external SecurityAuditCrew results into scan output.

        Args:
            llm_response: Response from LLM security scan
            external_audit: External audit dict (from SecurityAuditCrew.to_dict())

        Returns:
            Tuple of (merged_response, security_findings, has_critical)

        """
        findings = external_audit.get("findings", [])
        summary = external_audit.get("summary", "")
        risk_score = external_audit.get("risk_score", 0)

        # Check for critical/high findings
        has_critical = any(f.get("severity") in ("critical", "high") for f in findings)

        # Build merged response
        merged_sections = [llm_response]

        if summary or findings:
            # Build crew section efficiently (avoid O(n**2) string concat)
            parts = ["\n\n## SecurityAuditCrew Analysis\n"]
            if summary:
                parts.append(f"\n{summary}\n")

            parts.append(f"\n**Risk Score**: {risk_score}/100\n")

            if findings:
                critical = [f for f in findings if f.get("severity") == "critical"]
                high = [f for f in findings if f.get("severity") == "high"]

                if critical:
                    parts.append("\n### Critical Findings\n")
                    for f in critical:
                        title = f"- **{f.get('title', 'N/A')}**"
                        if f.get("file"):
                            title += f" ({f.get('file')}:{f.get('line', '?')})"
                        parts.append(title)
                        parts.append(f"\n  {f.get('description', '')[:200]}\n")
                        if f.get("remediation"):
                            parts.append(f"  *Fix*: {f.get('remediation')[:150]}\n")

                if high:
                    parts.append("\n### High Severity Findings\n")
                    for f in high[:5]:  # Top 5
                        title = f"- **{f.get('title', 'N/A')}**"
                        if f.get("file"):
                            title += f" ({f.get('file')}:{f.get('line', '?')})"
                        parts.append(title)
                        parts.append(f"\n  {f.get('description', '')[:150]}\n")

            merged_sections.append("".join(parts))

        return "\n".join(merged_sections), findings, has_critical
