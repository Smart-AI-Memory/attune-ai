"""Security Audit Crew

Multi-agent crew that performs comprehensive security audits.
Demonstrates CrewAI's hierarchical collaboration patterns with:
- 5 specialized agents with distinct roles
- Hierarchical task delegation from Security Lead
- Memory Graph integration for cross-analysis learning
- Structured output with severity scoring

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging

from attune.agent_factory.crews.base import CrewBase

from .config import SecurityAuditConfig
from .models import SecurityFinding, SecurityReport
from .parsers import (
    dict_to_finding,
    generate_summary,
    parse_findings,
    parse_text_findings,
)
from .prompts import XML_PROMPT_TEMPLATES

logger = logging.getLogger(__name__)


class SecurityAuditCrew(CrewBase):
    """Multi-agent crew for comprehensive security audits.

    The crew consists of 5 specialized agents:

    1. **Security Lead** (Coordinator)
    2. **Vulnerability Hunter** (Security Analyst)
    3. **Risk Assessor** (Risk Analyst)
    4. **Remediation Expert** (Security Engineer)
    5. **Compliance Mapper** (Compliance Officer)

    Example:
        crew = SecurityAuditCrew(api_key="...")
        report = await crew.audit("./src")

        for finding in report.critical_findings:
            print(f"{finding.title}: {finding.remediation}")

        print(f"Risk Score: {report.risk_score}/100")

    """

    config_class = SecurityAuditConfig
    XML_PROMPT_TEMPLATES = XML_PROMPT_TEMPLATES

    async def _create_agents(self) -> None:
        """Create the 5 specialized security agents."""
        # 1. Security Lead (Coordinator)
        lead_fallback = """You are the Security Lead, a senior security architect.

Your responsibilities:
1. Coordinate the security audit team
2. Prioritize findings based on business impact
3. Deduplicate overlapping findings
4. Generate executive summaries
5. Ensure comprehensive coverage

You delegate tasks to your team:
- Vulnerability Hunter: Initial scanning and detection
- Risk Assessor: Severity scoring and impact analysis
- Remediation Expert: Fix strategies and code samples
- Compliance Mapper: Regulatory and standards mapping

Always think strategically about the overall security posture."""

        self._agents["lead"] = self._factory.create_agent(
            name="security_lead",
            role="coordinator",
            description="Senior security architect who orchestrates the security audit team",
            system_prompt=self._get_system_prompt("security_lead", lead_fallback),
            model_tier=self.config.lead_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
            resilience_enabled=self.config.resilience_enabled,
        )

        # 2. Vulnerability Hunter (Security Analyst)
        hunter_fallback = """You are the Vulnerability Hunter, an expert security analyst.

Your focus areas:
1. OWASP Top 10 vulnerabilities
2. Injection attacks (SQL, NoSQL, OS command, LDAP)
3. Cross-Site Scripting (XSS) - stored, reflected, DOM
4. Authentication and session management flaws
5. Sensitive data exposure
6. Security misconfigurations
7. Insecure deserialization
8. Known vulnerable components

For each finding, provide:
- Clear description of the vulnerability
- Exact file and line number
- Code snippet showing the issue
- Confidence level (0.0-1.0)

Be thorough but avoid false positives. When uncertain, note the confidence level."""

        self._agents["hunter"] = self._factory.create_agent(
            name="vulnerability_hunter",
            role="security",
            description="Expert at finding OWASP Top 10 and common vulnerabilities",
            system_prompt=self._get_system_prompt("vulnerability_hunter", hunter_fallback),
            model_tier=self.config.hunter_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 3. Risk Assessor (Risk Analyst)
        assessor_fallback = """You are the Risk Assessor, a security risk analyst.

Your methodology:
1. Apply CVSS v3.1 scoring methodology
2. Consider attack vector (Network, Adjacent, Local, Physical)
3. Assess attack complexity (Low, High)
4. Evaluate privileges required (None, Low, High)
5. Determine user interaction requirements
6. Calculate impact on Confidentiality, Integrity, Availability

For each vulnerability:
- Assign CVSS base score (0.0-10.0)
- Map to severity level (Critical: 9.0-10.0, High: 7.0-8.9, Medium: 4.0-6.9, Low: 0.1-3.9)
- Assess blast radius (single component, service, system-wide)
- Evaluate exploitability (known exploits, proof of concept, theoretical)
- Consider business context impact

Be precise and consistent in your scoring methodology."""

        self._agents["assessor"] = self._factory.create_agent(
            name="risk_assessor",
            role="analyst",
            description="Scores vulnerability severity and assesses blast radius",
            system_prompt=self._get_system_prompt("risk_assessor", assessor_fallback),
            model_tier=self.config.assessor_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 4. Remediation Expert (Security Engineer)
        remediation_fallback = """You are the Remediation Expert, a senior security engineer.

For each vulnerability, provide:

1. **Immediate Fix**
   - Specific code changes required
   - Before/after code examples
   - Step-by-step implementation guide

2. **Defense in Depth**
   - Additional protective measures
   - Monitoring and alerting recommendations
   - Related hardening suggestions

3. **Effort Estimation**
   - Time to implement (hours/days)
   - Required expertise level
   - Dependencies or prerequisites

4. **Verification**
   - How to test the fix
   - Regression test suggestions
   - Security test cases

Prioritize fixes by:
- Severity x Exploitability x Effort
- Quick wins (high impact, low effort) first
- Group related fixes for efficiency"""

        self._agents["remediation"] = self._factory.create_agent(
            name="remediation_expert",
            role="debugger",
            description="Generates fix strategies with code examples",
            system_prompt=self._get_system_prompt("remediation_expert", remediation_fallback),
            model_tier=self.config.remediation_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 5. Compliance Mapper (Compliance Officer)
        compliance_fallback = """You are the Compliance Mapper, a security compliance specialist.

Your responsibilities:

1. **CWE Mapping**
   - Map each finding to relevant CWE IDs
   - Provide CWE category and description
   - Link to mitre.org references

2. **CVE Correlation**
   - Check if vulnerability matches known CVEs
   - Note CVE IDs when applicable
   - Reference NVD entries

3. **OWASP Classification**
   - Map to OWASP Top 10 categories
   - Reference OWASP testing guides
   - Note ASVS requirements

4. **Compliance Impact**
   - PCI-DSS requirements affected
   - HIPAA considerations (if healthcare)
   - GDPR implications (if personal data)
   - SOC2 control mappings

5. **Reporting Format**
   - Structured output for compliance reports
   - Evidence gathering suggestions
   - Audit trail recommendations

Be precise with ID references. Verify CWE/CVE mappings are accurate."""

        self._agents["compliance"] = self._factory.create_agent(
            name="compliance_mapper",
            role="analyst",
            description="Maps findings to CWE, CVE, and compliance standards",
            system_prompt=self._get_system_prompt("compliance_mapper", compliance_fallback),
            model_tier=self.config.compliance_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

    async def _create_workflow(self) -> None:
        """Create hierarchical workflow with Security Lead as manager."""
        agents = list(self._agents.values())

        self._workflow = self._factory.create_workflow(
            name="security_audit_workflow",
            agents=agents,
            mode="hierarchical",  # Security Lead delegates to others
            description="Comprehensive security audit with coordinated analysis",
        )

    async def audit(
        self,
        target: str,
        context: dict | None = None,
    ) -> SecurityReport:
        """Perform a comprehensive security audit.

        Args:
            target: Path to codebase or repository URL
            context: Optional context (previous findings, focus areas, etc.)

        Returns:
            SecurityReport with all findings and recommendations

        """
        import time

        start_time = time.time()

        # Initialize if needed
        await self._initialize()

        context = context or {}
        findings: list[SecurityFinding] = []
        memory_hits = 0

        # Check Memory Graph for similar past findings
        if self._graph and self.config.memory_graph_enabled:
            try:
                similar = self._graph.find_similar(
                    {"name": f"security_audit:{target}", "description": target},
                    threshold=0.4,
                    limit=10,
                )
                if similar:
                    memory_hits = len(similar)
                    context["similar_audits"] = [
                        {
                            "name": node.name,
                            "findings_count": node.metadata.get("findings_count", 0),
                            "risk_score": node.metadata.get("risk_score", 0),
                        }
                        for node, score in similar
                    ]
                    logger.info(f"Found {memory_hits} similar past audits in Memory Graph")
            except Exception as e:
                logger.warning(f"Error querying Memory Graph: {e}")

        # Build audit task for the crew
        audit_task = self._build_audit_task(target, context)

        # Execute the workflow
        try:
            result = await self._workflow.run(audit_task, initial_state=context)

            # Parse findings from result
            findings = parse_findings(result)

        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            # Return partial report with error
            return SecurityReport(
                target=target,
                findings=findings,
                summary=f"Audit failed with error: {e}",
                audit_duration_seconds=time.time() - start_time,
                agents_used=list(self._agents.keys()),
                memory_graph_hits=memory_hits,
                metadata={"error": str(e)},
            )

        # Build the report
        duration = time.time() - start_time
        report = SecurityReport(
            target=target,
            findings=findings,
            summary=generate_summary(findings),
            audit_duration_seconds=duration,
            agents_used=list(self._agents.keys()),
            memory_graph_hits=memory_hits,
            metadata={
                "scan_depth": self.config.scan_depth,
                "framework": str(self._factory.framework.value),
            },
        )

        # Store findings in Memory Graph
        if self._graph and self.config.memory_graph_enabled and findings:
            try:
                self._graph.add_finding(
                    "security_audit_crew",
                    {
                        "type": "security_audit",
                        "name": f"audit:{target}",
                        "description": report.summary,
                        "findings_count": len(findings),
                        "risk_score": report.risk_score,
                        "critical_count": len(report.critical_findings),
                    },
                )
                self._graph._save()
            except Exception as e:
                logger.warning(f"Error storing audit in Memory Graph: {e}")

        return report

    def _build_audit_task(self, target: str, context: dict) -> str:
        """Build the audit task description for the crew.

        Args:
            target: Path or URL being audited.
            context: Audit context including similar audits and focus areas.

        Returns:
            Formatted task string for the workflow.

        """
        depth_instructions = {
            "quick": "Focus on critical and high severity issues only. Skip detailed analysis.",
            "standard": "Cover all OWASP Top 10 categories with moderate depth.",
            "thorough": "Perform deep analysis including edge cases and complex attack chains.",
        }

        task = f"""Perform a comprehensive security audit of: {target}

Scan Depth: {self.config.scan_depth}
Instructions: {depth_instructions.get(self.config.scan_depth, depth_instructions["standard"])}

File Patterns to Include: {", ".join(self.config.include_patterns)}
File Patterns to Exclude: {", ".join(self.config.exclude_patterns)}

Workflow:
1. Security Lead coordinates the overall audit strategy
2. Vulnerability Hunter scans for security issues
3. Risk Assessor scores each finding by severity
4. Remediation Expert provides fix strategies
5. Compliance Mapper adds CWE/CVE references

For each finding, provide:
- Title and description
- Severity (critical/high/medium/low/info)
- Category (OWASP classification)
- File path and line number
- Code snippet
- Remediation steps
- CWE ID if applicable
- CVSS score

"""
        if context.get("similar_audits"):
            task += f"""
Previous Similar Audits Found: {len(context["similar_audits"])}
Consider patterns from past audits when analyzing.
"""

        if context.get("focus_areas"):
            task += f"""
Focus Areas Requested: {", ".join(context["focus_areas"])}
"""

        return task

    # ------------------------------------------------------------------
    # Backward-compatible delegation methods
    # These were previously inline methods; now they delegate to the
    # standalone functions in parsers.py.
    # ------------------------------------------------------------------

    def _parse_findings(self, result: dict) -> list[SecurityFinding]:
        """Parse findings from workflow result.

        Args:
            result: Workflow result dict.

        Returns:
            List of SecurityFinding objects.

        """
        return parse_findings(result)

    def _dict_to_finding(self, data: dict) -> SecurityFinding:
        """Convert dictionary to SecurityFinding.

        Args:
            data: Dictionary with finding fields.

        Returns:
            A SecurityFinding instance.

        """
        return dict_to_finding(data)

    def _parse_text_findings(self, text: str) -> list[SecurityFinding]:
        """Parse findings from unstructured text output.

        Args:
            text: Raw text output from the audit workflow.

        Returns:
            List of SecurityFinding objects.

        """
        return parse_text_findings(text)

    def _generate_summary(self, findings: list[SecurityFinding]) -> str:
        """Generate executive summary of findings.

        Args:
            findings: List of SecurityFinding objects.

        Returns:
            Human-readable summary string.

        """
        return generate_summary(findings)
