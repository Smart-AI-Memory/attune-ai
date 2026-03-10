"""Performance Audit Optimize Stage (Mixin)

Mixin class containing the optimize stage and its helpers
for the performance audit workflow.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import heapq
import json
from typing import Any

from .base import ModelTier
from .perf_audit_patterns import PERF_AUDIT_STEPS
from .perf_audit_report import (
    create_perf_audit_workflow_report,
    format_perf_audit_report,
)


class PerfAuditOptimizeMixin:
    """Mixin providing the optimize stage for PerformanceAuditWorkflow.

    This mixin expects the host class to provide:
    - ``_auth_mode_used``: str | None
    - ``_is_xml_enabled()``: method
    - ``_render_xml_prompt()``: method
    - ``_parse_xml_response()``: method
    - ``_executor``: executor or None
    - ``_api_key``: API key or None
    - ``run_step_with_executor()``: method
    - ``_call_llm()``: method
    """

    async def _optimize(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate optimization recommendations using LLM.

        Creates actionable recommendations for performance
        improvements. Supports XML-enhanced prompts when
        enabled in workflow config.

        Args:
            input_data: Dict with hotspot_result and findings
            tier: Model tier for this stage

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens)

        """
        hotspot_result = input_data.get("hotspot_result", {})
        hotspots = hotspot_result.get("hotspots", [])
        findings = input_data.get("findings", [])
        target = input_data.get("target", "")

        # Build hotspots summary for LLM
        hotspots_summary = []
        for h in hotspots[:10]:
            hotspots_summary.append(
                f"- {h.get('file')}: "
                f"score={h.get('complexity_score', 0)}, "
                f"concerns={', '.join(h.get('concerns', []))}",
            )

        # Summary of most common issues
        issue_counts: dict[str, int] = {}
        for f in findings:
            t = f.get("type", "unknown")
            issue_counts[t] = issue_counts.get(t, 0) + 1
        top_issues = heapq.nlargest(5, issue_counts.items(), key=lambda x: x[1])

        # Build input payload for prompt
        hotspots_text = (
            chr(10).join(hotspots_summary) if hotspots_summary else "No hotspots identified"
        )
        issues_json = json.dumps(
            [{"type": t, "count": c} for t, c in top_issues],
            indent=2,
        )
        input_payload = (
            f"Target: {target or 'codebase'}\n\n"
            f"Performance Score: "
            f"{hotspot_result.get('perf_score', 0)}/100\n"
            f"Performance Level: "
            f"{hotspot_result.get('perf_level', 'unknown')}"
            f"\n\nHotspots:\n{hotspots_text}"
            f"\n\nTop Issues:\n{issues_json}"
        )

        # Build prompt (XML or legacy)
        system, user_message = _build_optimize_prompt(self, input_payload, hotspot_result, hotspots)

        # Execute LLM call
        response, input_tokens, output_tokens = await _execute_optimize_llm(
            self,
            tier,
            system,
            user_message,
        )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        result = {
            "optimization_plan": response,
            "recommendation_count": len(hotspots),
            "top_issues": [{"type": t, "count": c} for t, c in top_issues],
            "perf_score": hotspot_result.get("perf_score", 0),
            "perf_level": hotspot_result.get("perf_level", "unknown"),
            "model_tier_used": tier.value,
            "auth_mode_used": self._auth_mode_used,
        }

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
        result["formatted_report"] = format_perf_audit_report(result, input_data)

        # Add structured WorkflowReport for Rich rendering
        result["workflow_report"] = create_perf_audit_workflow_report(result, input_data)

        return (result, input_tokens, output_tokens)


def _build_optimize_prompt(
    workflow: Any,
    input_payload: str,
    hotspot_result: dict,
    hotspots: list,
) -> tuple[str | None, str]:
    """Build the prompt for the optimize stage.

    Args:
        workflow: The workflow instance
        input_payload: Formatted input text
        hotspot_result: Hotspot analysis results
        hotspots: List of hotspot dicts

    Returns:
        Tuple of (system_prompt, user_message)

    """
    if workflow._is_xml_enabled():
        from attune.prompts.examples import PERF_AUDIT_EXAMPLES

        user_message = workflow._render_xml_prompt(
            role="performance engineer specializing in optimization",
            goal=("Generate comprehensive optimization recommendations for performance issues"),
            instructions=[
                "Analyze each performance hotspot and its concerns",
                "Provide specific optimization strategies with code examples",
                "Estimate the impact of each optimization (high/medium/low)",
                "Prioritize recommendations by potential performance gain",
                "Include before/after code patterns where helpful",
            ],
            constraints=[
                "Be specific about which files and patterns to optimize",
                "Include actionable code changes",
                "Focus on high-impact optimizations first",
            ],
            input_type="performance_hotspots",
            input_payload=input_payload,
            examples=PERF_AUDIT_EXAMPLES,
            extra={
                "perf_score": hotspot_result.get("perf_score", 0),
                "hotspot_count": len(hotspots),
            },
        )
        system = None
    else:
        system = (
            "You are a performance engineer specializing in "
            "code optimization.\n"
            "Analyze the identified performance hotspots and "
            "generate actionable recommendations.\n\n"
            "For each hotspot:\n"
            "1. Explain why the pattern causes performance issues\n"
            "2. Provide specific optimization strategies "
            "with code examples\n"
            "3. Estimate the impact of the optimization\n\n"
            "Prioritize by potential performance gain."
        )

        user_message = (
            "Generate optimization recommendations "
            "for these performance issues:\n\n"
            f"{input_payload}\n\n"
            "Provide detailed optimization strategies."
        )

    return system, user_message


async def _execute_optimize_llm(
    workflow: Any,
    tier: ModelTier,
    system: str | None,
    user_message: str,
) -> tuple[Any, int, int]:
    """Execute the LLM call for the optimize stage.

    Tries executor-based execution first, falls back to legacy _call_llm.

    Args:
        workflow: The workflow instance
        tier: Model tier for this call
        system: System prompt (or None for XML)
        user_message: User message/prompt

    Returns:
        Tuple of (response, input_tokens, output_tokens)

    """
    if workflow._executor is not None or workflow._api_key:
        try:
            step = PERF_AUDIT_STEPS["optimize"]
            response, input_tokens, output_tokens, cost = await workflow.run_step_with_executor(
                step=step,
                prompt=user_message,
                system=system,
            )
            return response, input_tokens, output_tokens
        except Exception:  # noqa: BLE001
            # Fall back to legacy _call_llm if executor fails
            return await workflow._call_llm(
                tier,
                system or "",
                user_message,
                max_tokens=3000,
            )
    else:
        # Legacy path for backward compatibility
        return await workflow._call_llm(
            tier,
            system or "",
            user_message,
            max_tokens=3000,
        )
