"""Security Audit Analysis, Assessment, and Remediation Stages.

Mixins providing analyze, assess, and remediate stages for
SecurityAuditWorkflow. Extracted from security_audit.py for
maintainability.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging

from .base import ModelTier
from .security_audit_report import format_security_report
from .step_config import WorkflowStepConfig

logger = logging.getLogger(__name__)

# Define step configurations for executor-based execution
SECURITY_STEPS = {
    "remediate": WorkflowStepConfig(
        name="remediate",
        task_type="final_review",  # Premium tier task
        tier_hint="premium",
        description="Generate remediation plan for security vulnerabilities",
        max_tokens=3000,
    ),
}


class AnalyzeStageMixin:
    """Mixin providing the analyze stage for security audit workflows."""

    async def _analyze(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Deep analysis of flagged areas.

        Filters findings against team decisions and performs
        deeper analysis of genuine security concerns.
        """
        findings = input_data.get("findings", [])
        analyzed: list[dict] = []

        for finding in findings:
            finding_key = finding.get("type", "")

            # Check team decisions
            decision = self._team_decisions.get(finding_key)
            if decision:
                if decision.get("decision") == "false_positive":
                    finding["status"] = "false_positive"
                    finding["decision_reason"] = decision.get("reason", "")
                    finding["decided_by"] = decision.get("decided_by", "")
                elif decision.get("decision") == "accepted":
                    finding["status"] = "accepted_risk"
                    finding["decision_reason"] = decision.get("reason", "")
                elif decision.get("decision") == "deferred":
                    finding["status"] = "deferred"
                    finding["decision_reason"] = decision.get("reason", "")
                else:
                    finding["status"] = "needs_review"
            else:
                finding["status"] = "needs_review"

            # Add context analysis
            if finding["status"] == "needs_review":
                finding["analysis"] = self._analyze_finding(finding)

            analyzed.append(finding)

        # Separate by status
        needs_review = [f for f in analyzed if f["status"] == "needs_review"]
        false_positives = [f for f in analyzed if f["status"] == "false_positive"]
        accepted = [f for f in analyzed if f["status"] == "accepted_risk"]

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(analyzed)) // 4

        return (
            {
                "analyzed_findings": analyzed,
                "needs_review": needs_review,
                "false_positives": false_positives,
                "accepted_risks": accepted,
                "review_count": len(needs_review),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )


class AssessStageMixin:
    """Mixin providing the assess stage for security audit workflows."""

    async def _assess(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Risk scoring and severity classification.

        Calculates overall security risk score and identifies
        critical issues requiring immediate attention.

        When use_crew_for_assessment=True, uses SecurityAuditCrew's
        comprehensive analysis for enhanced vulnerability detection.
        """
        await self._initialize_crew()

        needs_review = input_data.get("needs_review", [])

        # Count by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in needs_review:
            sev = finding.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # Calculate risk score (0-100)
        risk_score = (
            severity_counts["critical"] * 25
            + severity_counts["high"] * 10
            + severity_counts["medium"] * 3
            + severity_counts["low"] * 1
        )
        risk_score = min(100, risk_score)

        # Set flag for skip logic
        self._has_critical = severity_counts["critical"] > 0 or severity_counts["high"] > 0

        # Group findings by OWASP category
        by_owasp: dict[str, list] = {}
        for finding in needs_review:
            owasp = finding.get("owasp", "Unknown")
            if owasp not in by_owasp:
                by_owasp[owasp] = []
            by_owasp[owasp].append(finding)

        # Use crew for enhanced assessment if available
        crew_enhanced = False
        crew_findings = []
        if self.use_crew_for_assessment and self._crew_available:
            target = input_data.get("path", ".")
            try:
                crew_report = await self._crew.audit(target=target)
                if crew_report and crew_report.findings:
                    crew_enhanced = True
                    # Convert crew findings to workflow format
                    for finding in crew_report.findings:
                        crew_findings.append(
                            {
                                "type": finding.category.value,
                                "title": finding.title,
                                "description": finding.description,
                                "severity": finding.severity.value,
                                "file": finding.file_path or "",
                                "line": finding.line_number or 0,
                                "owasp": finding.category.value,
                                "remediation": finding.remediation or "",
                                "cwe_id": finding.cwe_id or "",
                                "cvss_score": finding.cvss_score or 0.0,
                                "source": "crew",
                            }
                        )
                    # Update severity counts with crew findings
                    for finding in crew_findings:
                        sev = finding.get("severity", "low")
                        severity_counts[sev] = severity_counts.get(sev, 0) + 1
                    # Recalculate risk score with crew findings
                    risk_score = (
                        severity_counts["critical"] * 25
                        + severity_counts["high"] * 10
                        + severity_counts["medium"] * 3
                        + severity_counts["low"] * 1
                    )
                    risk_score = min(100, risk_score)
            except Exception as e:
                logger.warning(f"Crew assessment failed: {e}")

        # Merge crew findings with pattern-based findings
        all_critical = [f for f in needs_review if f.get("severity") == "critical"]
        all_high = [f for f in needs_review if f.get("severity") == "high"]
        if crew_enhanced:
            all_critical.extend([f for f in crew_findings if f.get("severity") == "critical"])
            all_high.extend([f for f in crew_findings if f.get("severity") == "high"])

        assessment = {
            "risk_score": risk_score,
            "risk_level": (
                "critical"
                if risk_score >= 75
                else "high" if risk_score >= 50 else "medium" if risk_score >= 25 else "low"
            ),
            "severity_breakdown": severity_counts,
            "by_owasp_category": {k: len(v) for k, v in by_owasp.items()},
            "critical_findings": all_critical,
            "high_findings": all_high,
            "crew_enhanced": crew_enhanced,
            "crew_findings_count": len(crew_findings) if crew_enhanced else 0,
        }

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(assessment)) // 4

        # Build output with assessment
        output = {
            "assessment": assessment,
            **input_data,
        }

        # Add formatted report for human readability
        output["formatted_report"] = format_security_report(output)

        return (
            output,
            input_tokens,
            output_tokens,
        )


class RemediateStageMixin:
    """Mixin providing the remediate stage for security audit workflows."""

    async def _remediate(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate remediation plan for security issues.

        Creates actionable remediation steps prioritized by
        severity and grouped by OWASP category.

        When use_crew_for_remediation=True, uses SecurityAuditCrew's
        Remediation Expert agent for enhanced recommendations.

        Supports XML-enhanced prompts when enabled in workflow config.
        """
        try:
            from .security_adapters import _check_crew_available

            adapters_available = True
        except ImportError:
            adapters_available = False

            def _check_crew_available():
                return False

        assessment = input_data.get("assessment", {})
        critical = assessment.get("critical_findings", [])
        high = assessment.get("high_findings", [])
        target = input_data.get("target", input_data.get("path", ""))

        crew_remediation = None
        crew_enhanced = False

        # Try crew-based remediation first if enabled
        if self.use_crew_for_remediation and adapters_available and _check_crew_available():
            crew_remediation = await self._get_crew_remediation(target, critical + high, assessment)
            if crew_remediation:
                crew_enhanced = True

        # Build findings summary for LLM
        findings_summary = []
        for f in critical:
            findings_summary.append(
                f"CRITICAL: {f.get('type')} in {f.get('file')}:{f.get('line')} - {f.get('owasp')}",
            )
        for f in high:
            findings_summary.append(
                f"HIGH: {f.get('type')} in {f.get('file')}:{f.get('line')} - {f.get('owasp')}",
            )

        # Build input payload for prompt
        input_payload = f"""Target: {target or "codebase"}

Findings:
{chr(10).join(findings_summary) if findings_summary else "No critical or high findings"}

Risk Score: {assessment.get("risk_score", 0)}/100
Risk Level: {assessment.get("risk_level", "unknown")}

Severity Breakdown: {json.dumps(assessment.get("severity_breakdown", {}), indent=2)}"""

        # Build prompt (XML or legacy)
        system, user_message = self._build_remediation_prompt(input_payload, assessment)

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = SECURITY_STEPS["remediate"]
                response, input_tokens, output_tokens, cost = await self.run_step_with_executor(
                    step=step,
                    prompt=user_message,
                    system=system,
                )
            except Exception:
                # Fall back to legacy _call_llm if executor fails
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system or "",
                    user_message,
                    max_tokens=3000,
                )
        else:
            # Legacy path for backward compatibility
            response, input_tokens, output_tokens = await self._call_llm(
                tier,
                system or "",
                user_message,
                max_tokens=3000,
            )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        # Merge crew remediation if available
        if crew_enhanced and crew_remediation:
            response = self._merge_crew_remediation(response, crew_remediation)

        result = {
            "remediation_plan": response,
            "remediation_count": len(critical) + len(high),
            "risk_score": assessment.get("risk_score", 0),
            "risk_level": assessment.get("risk_level", "unknown"),
            "model_tier_used": tier.value,
            "crew_enhanced": crew_enhanced,
            "auth_mode_used": self._auth_mode_used,  # Track recommended auth mode
            **input_data,  # Merge all previous stage data
        }

        # Add crew-specific fields if enhanced
        if crew_enhanced and crew_remediation:
            result["crew_findings"] = crew_remediation.get("findings", [])
            result["crew_agents_used"] = crew_remediation.get("agents_used", [])

        # Merge parsed XML data if available
        if parsed_data.get("xml_parsed"):
            result.update(
                {
                    "xml_parsed": True,
                    "summary": parsed_data.get("summary"),
                    "findings": parsed_data.get("findings", []),
                    "checklist": parsed_data.get("checklist", []),
                },
            )

        return (result, input_tokens, output_tokens)

    def _build_remediation_prompt(
        self, input_payload: str, assessment: dict
    ) -> tuple[str | None, str]:
        """Build the remediation prompt (XML-enhanced or legacy).

        Args:
            input_payload: Formatted findings summary string.
            assessment: Assessment dict with risk score and level.

        Returns:
            Tuple of (system_message, user_message).
        """
        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            # Use XML-enhanced prompt
            from attune.prompts.examples import SECURITY_AUDIT_EXAMPLES

            user_message = self._render_xml_prompt(
                role="application security engineer",
                goal="Generate a comprehensive remediation plan for security vulnerabilities",
                instructions=[
                    "Explain each vulnerability and its potential impact",
                    "Provide specific remediation steps with code examples",
                    "Suggest preventive measures to avoid similar issues",
                    "Reference relevant OWASP guidelines",
                    "Prioritize by severity (critical first, then high)",
                ],
                constraints=[
                    "Be specific and actionable",
                    "Include code examples where helpful",
                    "Group fixes by severity",
                ],
                input_type="security_findings",
                input_payload=input_payload,
                examples=SECURITY_AUDIT_EXAMPLES,
                extra={
                    "risk_score": assessment.get("risk_score", 0),
                    "risk_level": assessment.get("risk_level", "unknown"),
                },
            )
            system = None  # XML prompt includes all context
        else:
            # Use legacy plain text prompts
            system = """You are a security expert in application security and OWASP.
Generate a comprehensive remediation plan for the security findings.

For each finding:
1. Explain the vulnerability and its potential impact
2. Provide specific remediation steps with code examples
3. Suggest preventive measures to avoid similar issues
4. Reference relevant OWASP guidelines

Prioritize by severity (critical first, then high).
Be specific and actionable."""

            user_message = f"""Generate a remediation plan for these security findings:

{input_payload}

Provide a detailed remediation plan with specific fixes."""

        return system, user_message

    async def _get_crew_remediation(
        self,
        target: str,
        findings: list,
        assessment: dict,
    ) -> dict | None:
        """Get remediation recommendations from SecurityAuditCrew.

        Args:
            target: Path to codebase
            findings: List of findings needing remediation
            assessment: Current assessment dict

        Returns:
            Crew results dict or None if failed
        """
        try:
            from attune.agent_factory.crews import (
                SecurityAuditConfig,
                SecurityAuditCrew,
            )

            from .security_adapters import (
                crew_report_to_workflow_format,
                workflow_findings_to_crew_format,
            )

            # Configure crew for focused remediation
            config = SecurityAuditConfig(
                scan_depth="quick",  # Skip deep scan, focus on remediation
                **self.crew_config,
            )
            crew = SecurityAuditCrew(config=config)

            # Convert findings to crew format for context
            crew_findings = workflow_findings_to_crew_format(findings)

            # Run audit with remediation focus
            context = {
                "focus_areas": ["remediation"],
                "existing_findings": crew_findings,
                "skip_detection": True,  # We already have findings
                "risk_score": assessment.get("risk_score", 0),
            }

            report = await crew.audit(target, context=context)

            if report:
                return crew_report_to_workflow_format(report)
            return None

        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Crew remediation failed: {e}")
            return None

    def _merge_crew_remediation(self, llm_response: str, crew_remediation: dict) -> str:
        """Merge crew remediation recommendations with LLM response.

        Args:
            llm_response: LLM-generated remediation plan
            crew_remediation: Crew results in workflow format

        Returns:
            Merged response with crew enhancements
        """
        crew_findings = crew_remediation.get("findings", [])

        if not crew_findings:
            return llm_response

        # Build crew section efficiently (avoid O(n^2) string concat)
        parts = [
            "\n\n## Enhanced Remediation (SecurityAuditCrew)\n\n",
            f"**Agents Used**: {', '.join(crew_remediation.get('agents_used', []))}\n\n",
        ]

        for finding in crew_findings:
            if finding.get("remediation"):
                parts.append(f"### {finding.get('title', 'Finding')}\n")
                parts.append(f"**Severity**: {finding.get('severity', 'unknown').upper()}\n")
                if finding.get("cwe_id"):
                    parts.append(f"**CWE**: {finding.get('cwe_id')}\n")
                if finding.get("cvss_score"):
                    parts.append(f"**CVSS Score**: {finding.get('cvss_score')}\n")
                parts.append(f"\n**Remediation**:\n{finding.get('remediation')}\n\n")

        return llm_response + "".join(parts)
