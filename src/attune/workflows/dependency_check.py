"""Dependency Check Workflow

Audits dependencies for vulnerabilities, updates, and licensing issues.
Parses lockfiles and checks against known vulnerability patterns.

Stages:
1. inventory (CHEAP) - Parse requirements.txt, package.json, pyproject.toml, lockfiles
2. assess (CAPABLE) - Check for known vulnerabilities using pip-audit/npm audit
3. report (CAPABLE) - Generate risk assessment and recommendations

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from pathlib import Path
from typing import Any

from .base import BaseWorkflow, ModelTier
from .context import WorkflowContext
from .dependency_check_audit import (  # noqa: F401
    CACHE_DIR,
    _get_cache_path,
    _load_cached_advisories,
    _run_npm_audit,
    _run_pip_audit,
    _save_advisory_cache,
)
from .dependency_check_parsers import DependencyParserMixin
from .dependency_check_report import (
    format_dependency_check_report,
    main,
)
from .services import ParsingService, PromptService
from .step_config import WorkflowStepConfig

logger = logging.getLogger(__name__)

# Define step configurations for executor-based execution
DEPENDENCY_CHECK_STEPS = {
    "report": WorkflowStepConfig(
        name="report",
        task_type="analyze",  # Capable tier task
        tier_hint="capable",
        description="Generate dependency security report with remediation steps",
        max_tokens=3000,
    ),
}


class DependencyCheckWorkflow(DependencyParserMixin, BaseWorkflow):
    """Audit dependencies for security and updates.

    Scans dependency files to identify vulnerable, outdated,
    or potentially problematic packages.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.
    """

    name = "dependency-check"
    description = "Audit dependencies for vulnerabilities and updates"
    stages = ["inventory", "assess", "report"]
    tier_map = {
        "inventory": ModelTier.CHEAP,
        "assess": ModelTier.CAPABLE,
        "report": ModelTier.CAPABLE,
    }

    def __init__(self, **kwargs: Any):
        """Initialize dependency check workflow.

        Args:
            **kwargs: Additional arguments passed to BaseWorkflow

        """
        super().__init__(**kwargs)

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for dependency checking.

        Args:
            xml_config: Optional XML prompt configuration dict.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        return WorkflowContext(
            prompt=PromptService("dependency-check", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to specific stage implementation."""
        if stage_name == "inventory":
            return await self._inventory(input_data, tier)
        if stage_name == "assess":
            return await self._assess(input_data, tier)
        if stage_name == "report":
            return await self._report(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _inventory(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Parse dependency files to build inventory.

        Supports requirements.txt, pyproject.toml, package.json,
        and their lockfiles.
        """
        target_path = input_data.get("path", ".")
        target = Path(target_path)

        dependencies: dict[str, list[dict]] = {
            "python": [],
            "node": [],
        }
        files_found: list[str] = []

        # Parse Python dependencies
        req_files = ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]
        for req_file in req_files:
            req_path = target / req_file
            if req_path.exists():
                files_found.append(str(req_path))
                deps = self._parse_requirements(req_path)
                dependencies["python"].extend(deps)

        # Parse pyproject.toml
        pyproject_path = target / "pyproject.toml"
        if pyproject_path.exists():
            files_found.append(str(pyproject_path))
            deps = self._parse_pyproject(pyproject_path)
            dependencies["python"].extend(deps)

        # Parse package.json
        package_json = target / "package.json"
        if package_json.exists():
            files_found.append(str(package_json))
            deps = self._parse_package_json(package_json)
            dependencies["node"].extend(deps)

        # Parse lockfiles for exact versions (more reliable for vuln checking)
        poetry_lock = target / "poetry.lock"
        if poetry_lock.exists():
            files_found.append(str(poetry_lock))
            lockfile_deps = self._parse_poetry_lock(poetry_lock)
            # Lockfile deps have pinned=True and override manifest versions
            dependencies["python"].extend(lockfile_deps)

        package_lock = target / "package-lock.json"
        if package_lock.exists():
            files_found.append(str(package_lock))
            lockfile_deps = self._parse_package_lock_json(package_lock)
            dependencies["node"].extend(lockfile_deps)

        # Deduplicate
        for ecosystem in dependencies:
            seen = set()
            unique = []
            for dep in dependencies[ecosystem]:
                name = dep["name"].lower()
                if name not in seen:
                    seen.add(name)
                    unique.append(dep)
            dependencies[ecosystem] = unique

        total_count = sum(len(deps) for deps in dependencies.values())

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(dependencies)) // 4

        return (
            {
                "dependencies": dependencies,
                "files_found": files_found,
                "total_dependencies": total_count,
                "python_count": len(dependencies["python"]),
                "node_count": len(dependencies["node"]),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _assess(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Check dependencies for vulnerabilities using real advisory sources.

        Uses pip-audit for Python and npm audit for Node.js packages.
        Falls back to cached advisories if tools are unavailable.
        """
        target_path = Path(input_data.get("path", "."))
        dependencies = input_data.get("dependencies", {})

        vulnerabilities: list[dict] = []
        outdated: list[dict] = []
        data_source = "none"

        # Run pip-audit for Python vulnerabilities
        pip_audit_results = _run_pip_audit(target_path)
        if pip_audit_results:
            data_source = "pip-audit"
            for result in pip_audit_results:
                for vuln in result.get("vulns", []):
                    vulnerabilities.append(
                        {
                            "package": result.get("name", "unknown"),
                            "current_version": result.get("version", "unknown"),
                            "fixed_versions": vuln.get("fix_versions", []),
                            "severity": self._map_severity(vuln.get("id", "")),
                            "cve": vuln.get("id", ""),
                            "description": vuln.get("description", "")[:200],
                            "ecosystem": "python",
                            "source": "pip-audit",
                        },
                    )

        # Run npm audit for Node.js vulnerabilities
        npm_audit_results = _run_npm_audit(target_path)
        if npm_audit_results:
            data_source = "pip-audit+npm" if data_source == "pip-audit" else "npm-audit"
            for vuln in npm_audit_results:
                severity = vuln.get("severity", "unknown")
                vulnerabilities.append(
                    {
                        "package": vuln.get("name", "unknown"),
                        "current_version": vuln.get("range", "unknown"),
                        "fixed_versions": [],
                        "severity": severity,
                        "cve": "",
                        "description": str(vuln.get("via", []))[:200],
                        "ecosystem": "node",
                        "source": "npm-audit",
                        "fixAvailable": vuln.get("fixAvailable", False),
                    },
                )

        # If no real audit data, try cached advisories
        if not vulnerabilities:
            cached = _load_cached_advisories()
            if cached:
                data_source = "cached"
                for ecosystem, deps in dependencies.items():
                    for dep in deps:
                        name_lower = dep["name"].lower()
                        if name_lower in cached:
                            for vuln in cached[name_lower]:
                                vulnerabilities.append(
                                    {
                                        "package": dep["name"],
                                        "current_version": dep["version"],
                                        "severity": self._map_severity(vuln.get("id", "")),
                                        "cve": vuln.get("id", ""),
                                        "ecosystem": ecosystem,
                                        "source": "cached",
                                    },
                                )

        # Check for potentially outdated packages (heuristic)
        for ecosystem, deps in dependencies.items():
            for dep in deps:
                version = dep.get("version", "")
                # Flag pre-release and very old-looking versions
                if version.startswith("^0.") or version.startswith("~0."):
                    outdated.append(
                        {
                            "package": dep["name"],
                            "current_version": version,
                            "status": "potentially_outdated",
                            "ecosystem": ecosystem,
                        },
                    )

        # Categorize by severity
        critical = [v for v in vulnerabilities if v.get("severity") == "critical"]
        high = [v for v in vulnerabilities if v.get("severity") == "high"]
        medium = [v for v in vulnerabilities if v.get("severity") == "medium"]
        low = [v for v in vulnerabilities if v.get("severity") == "low"]

        assessment = {
            "vulnerabilities": vulnerabilities,
            "outdated": outdated,
            "vulnerability_count": len(vulnerabilities),
            "critical_count": len(critical),
            "high_count": len(high),
            "medium_count": len(medium),
            "low_count": len(low),
            "outdated_count": len(outdated),
            "data_source": data_source,
        }

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(assessment)) // 4

        return (
            {
                "assessment": assessment,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    def _map_severity(self, vuln_id: str) -> str:
        """Map vulnerability ID to severity level.

        Uses heuristics based on CVE/GHSA patterns.
        """
        vuln_id_lower = vuln_id.lower()

        # GHSA typically includes severity in metadata, but we can't get it from ID alone
        # CVEs don't encode severity in the ID
        # Default to "medium" as a conservative estimate
        # In practice, pip-audit provides severity in the response

        if "critical" in vuln_id_lower:
            return "critical"
        if "high" in vuln_id_lower:
            return "high"

        # Default to medium - actual severity should come from the audit tool
        return "medium"

    async def _report(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate risk assessment and recommendations using LLM.

        Creates actionable report with remediation steps.

        Supports XML-enhanced prompts when enabled in workflow config.
        """
        assessment = input_data.get("assessment", {})
        vulnerabilities = assessment.get("vulnerabilities", [])
        outdated = assessment.get("outdated", [])
        target = input_data.get("path", "")

        # Calculate risk score
        risk_score = (
            assessment.get("critical_count", 0) * 25
            + assessment.get("high_count", 0) * 10
            + assessment.get("medium_count", 0) * 3
            + assessment.get("outdated_count", 0) * 1
        )
        risk_score = min(100, risk_score)

        risk_level = (
            "critical"
            if risk_score >= 75
            else "high" if risk_score >= 50 else "medium" if risk_score >= 25 else "low"
        )

        # Build vulnerability summary for LLM
        vuln_summary = []
        for v in vulnerabilities[:15]:
            vuln_summary.append(
                f"- {v.get('package')}@{v.get('current_version')}: "
                f"{v.get('cve')} ({v.get('severity')})",
            )

        # Build input payload for prompt
        input_payload = f"""Target: {target or "codebase"}

Total Dependencies: {input_data.get("total_dependencies", 0)}
Risk Score: {risk_score}/100
Risk Level: {risk_level}

Vulnerabilities ({len(vulnerabilities)}):
{chr(10).join(vuln_summary) if vuln_summary else "None found"}

Outdated Packages: {len(outdated)}

Severity Summary:
- Critical: {assessment.get("critical_count", 0)}
- High: {assessment.get("high_count", 0)}
- Medium: {assessment.get("medium_count", 0)}"""

        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            # Use XML-enhanced prompt
            from attune.prompts.examples import DEPENDENCY_CHECK_EXAMPLES

            user_message = self._render_xml_prompt(
                role="security engineer specializing in dependency management",
                goal="Generate a comprehensive dependency security report with remediation steps",
                instructions=[
                    "Analyze the vulnerability findings and their severity",
                    "Prioritize remediation actions by risk level",
                    "Provide specific upgrade recommendations",
                    "Identify potential breaking changes from upgrades",
                    "Suggest a remediation timeline",
                ],
                constraints=[
                    "Focus on actionable recommendations",
                    "Prioritize critical and high severity issues",
                    "Include version upgrade targets where possible",
                ],
                input_type="dependency_vulnerabilities",
                input_payload=input_payload,
                examples=DEPENDENCY_CHECK_EXAMPLES,
                extra={
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                },
            )
            system = None  # XML prompt includes all context
        else:
            # Use legacy plain text prompts
            system = """You are a security engineer specializing in dependency management.
Analyze the vulnerability findings and generate a comprehensive remediation report.

Focus on:
1. Prioritizing by severity
2. Specific upgrade recommendations
3. Potential breaking changes
4. Remediation timeline"""

            user_message = f"""Generate a dependency security report:

{input_payload}

Provide actionable remediation recommendations."""

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = DEPENDENCY_CHECK_STEPS["report"]
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

        # Generate basic recommendations for backwards compatibility
        recommendations: list[dict] = []

        for vuln in vulnerabilities:
            recommendations.append(
                {
                    "priority": 1 if vuln["severity"] == "critical" else 2,
                    "action": "upgrade",
                    "package": vuln["package"],
                    "reason": f"Fix {vuln['cve']} ({vuln['severity']} severity)",
                    "suggestion": f"Upgrade {vuln['package']} to latest version",
                },
            )

        for dep in outdated[:10]:  # Top 10 outdated
            recommendations.append(
                {
                    "priority": 3,
                    "action": "review",
                    "package": dep["package"],
                    "reason": "Potentially outdated version",
                    "suggestion": f"Review and update {dep['package']}",
                },
            )

        # Sort by priority
        recommendations.sort(key=lambda x: x["priority"])

        result = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "total_dependencies": input_data.get("total_dependencies", 0),
            "vulnerability_count": len(vulnerabilities),
            "outdated_count": len(outdated),
            "recommendations": recommendations[:20],
            "security_report": response,
            "summary": {
                "critical": assessment.get("critical_count", 0),
                "high": assessment.get("high_count", 0),
                "medium": assessment.get("medium_count", 0),
            },
            "model_tier_used": tier.value,
        }

        # Merge parsed XML data if available
        if parsed_data.get("xml_parsed"):
            result.update(
                {
                    "xml_parsed": True,
                    "report_summary": parsed_data.get("summary"),
                    "findings": parsed_data.get("findings", []),
                    "checklist": parsed_data.get("checklist", []),
                },
            )

        # Add formatted report for human readability
        result["formatted_report"] = format_dependency_check_report(result, input_data)

        return (result, input_tokens, output_tokens)


if __name__ == "__main__":
    main()
