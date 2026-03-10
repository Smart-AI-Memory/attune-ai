"""Release Preparation Workflow - Approve Stage

Final release readiness assessment using LLM synthesis of all
preceding stage results.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from typing import Any

from .base import ModelTier
from .release_prep_report import format_release_prep_report
from .step_config import WorkflowStepConfig

# Define step configurations for executor-based execution
RELEASE_PREP_STEPS = {
    "approve": WorkflowStepConfig(
        name="approve",
        task_type="final_review",  # Premium tier task
        tier_hint="premium",
        description="Assess release readiness and provide go/no-go recommendation",
        max_tokens=2000,
    ),
}


class ReleasePrepApproveMixin:
    """Mixin providing the ``_approve`` stage for release preparation.

    Expects the host class to expose:
        - ``_has_blockers: bool``
        - ``_auth_mode_used: str | None``
        - ``_executor`` / ``_api_key`` (from BaseWorkflow)
        - ``_is_xml_enabled()`` (from BaseWorkflow)
        - ``_render_xml_prompt(...)`` (from BaseWorkflow)
        - ``_parse_xml_response(...)`` (from BaseWorkflow)
        - ``run_step_with_executor(...)`` (from BaseWorkflow)
        - ``_call_llm(...)`` (from BaseWorkflow)
    """

    _has_blockers: bool
    _auth_mode_used: str | None

    async def _approve(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Final release readiness assessment using LLM.

        Synthesizes all checks into go/no-go recommendation.

        Supports XML-enhanced prompts when enabled in workflow config.
        """
        health = input_data.get("health", {})
        security = input_data.get("security", {})
        changelog = input_data.get("changelog", {})
        target = input_data.get("path", "")

        # Gather blockers
        blockers: list[str] = []

        if not health.get("passed", False):
            for check in health.get("failed_checks", []):
                blockers.append(f"Health check failed: {check}")

        if not security.get("passed", False):
            blockers.append(f"Security issues: {security.get('high_severity', 0)} high severity")

        if changelog.get("total_commits", 0) == 0:
            blockers.append("No commits in release period")

        # Gather warnings
        warnings: list[str] = []

        if security.get("medium_severity", 0) > 0:
            warnings.append(f"{security.get('medium_severity')} medium security issues")

        test_count = health.get("checks", {}).get("tests", {}).get("test_count", 0)
        if test_count < 10:
            warnings.append(f"Low test count: {test_count}")

        # Build input payload for LLM
        input_payload = f"""Target: {target or "codebase"}

Health Score: {health.get("health_score", 0)}/100
Health Checks: {json.dumps(health.get("checks", {}), indent=2)}

Security Issues: {security.get("total_issues", 0)}
High Severity: {security.get("high_severity", 0)}
Medium Severity: {security.get("medium_severity", 0)}

Commit Count: {changelog.get("total_commits", 0)}
Changes by Category: {json.dumps(changelog.get("by_category", {}), indent=2)}

Blockers: {json.dumps(blockers, indent=2)}
Warnings: {json.dumps(warnings, indent=2)}"""

        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            # Use XML-enhanced prompt
            from attune.prompts.examples import RELEASE_PREP_EXAMPLES

            user_message = self._render_xml_prompt(
                role="release manager assessing release readiness",
                goal="Provide a comprehensive release readiness assessment",
                instructions=[
                    "Evaluate all health checks and their implications",
                    "Assess security findings and their risk level",
                    "Review the changelog for completeness",
                    "Identify any blockers that must be resolved",
                    "Provide a clear go/no-go recommendation",
                    "Suggest remediation steps for any issues",
                ],
                constraints=[
                    "Be conservative - flag potential issues",
                    "Provide clear, actionable feedback",
                    "Include confidence level in recommendation",
                ],
                input_type="release_checks",
                input_payload=input_payload,
                examples=RELEASE_PREP_EXAMPLES,
                extra={
                    "blocker_count": len(blockers),
                    "warning_count": len(warnings),
                },
            )
            system = None  # XML prompt includes all context
        else:
            # Use legacy plain text prompts
            system = """You are a release manager assessing release readiness.
Analyze the health checks, security findings, and changelog to provide
a clear go/no-go recommendation.

Be thorough and flag any potential issues."""

            user_message = f"""Assess release readiness:

{input_payload}

Provide a comprehensive release readiness assessment."""

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = RELEASE_PREP_STEPS["approve"]
                response, input_tokens, output_tokens, cost = await self.run_step_with_executor(
                    step=step,
                    prompt=user_message,
                    system=system,
                )
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Fall back to legacy _call_llm if executor fails
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system or "",
                    user_message,
                    max_tokens=2000,
                )
        else:
            # Legacy path for backward compatibility
            response, input_tokens, output_tokens = await self._call_llm(
                tier,
                system or "",
                user_message,
                max_tokens=2000,
            )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        # Make decision
        approved = len(blockers) == 0
        confidence = "high" if approved and len(warnings) == 0 else "medium" if approved else "low"

        result: dict[str, Any] = {
            "approved": approved,
            "confidence": confidence,
            "blockers": blockers,
            "warnings": warnings,
            "health_score": health.get("health_score", 0),
            "commit_count": changelog.get("total_commits", 0),
            "assessment": response,
            "recommendation": (
                "Ready for release" if approved else "Address blockers before release"
            ),
            "model_tier_used": tier.value,
        }

        # Include auth mode used for telemetry
        if self._auth_mode_used:
            result["auth_mode_used"] = self._auth_mode_used

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

        # Add formatted report for human readability
        result["formatted_report"] = format_release_prep_report(result, input_data)

        return (result, input_tokens, output_tokens)
