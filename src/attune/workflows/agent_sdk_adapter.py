"""Adapter to convert Agent SDK output into WorkflowResult.

Bridges the Agent SDK world (ResultMessage text) with attune's
workflow system (WorkflowResult, WorkflowStage, CostReport).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from .base import ModelTier
from .data_classes import CostReport, NextAction, WorkflowResult, WorkflowStage

logger = logging.getLogger(__name__)

# Section headers mapped to finding categories
_CATEGORY_PATTERNS: dict[str, re.Pattern[str]] = {
    "security": re.compile(r"##\s*security", re.IGNORECASE),
    "quality": re.compile(r"##\s*(?:code\s+)?quality", re.IGNORECASE),
    "performance": re.compile(r"##\s*performance", re.IGNORECASE),
    "architecture": re.compile(r"##\s*architecture", re.IGNORECASE),
    "test_gaps": re.compile(r"##\s*test\s*gaps?", re.IGNORECASE),
}

# Pattern for suggestion-like bullet points
_SUGGESTION_RE = re.compile(
    r"^[\s]*[-*]\s+(?:(?:consider|suggest|recommend|should|could|try)\w*\s+)?(.+)",
    re.IGNORECASE,
)


class AgentSDKResultAdapter:
    """Converts Agent SDK ResultMessage text into a WorkflowResult.

    This adapter parses unstructured agent output text, extracts
    structured findings and suggestions, and packages everything
    into the standard WorkflowResult dataclass that downstream
    consumers (quality gates, telemetry, CLI) expect.
    """

    @classmethod
    def from_agent_output(
        cls,
        result_text: str,
        subagent_names: list[str],
        started_at: datetime,
        completed_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Build a WorkflowResult from raw agent text output.

        Args:
            result_text: The agent's full text response.
            subagent_names: Names of subagents that participated.
            started_at: When the agent execution began.
            completed_at: When the agent execution finished.
            metadata: Optional extra metadata to attach to the result.

        Returns:
            A WorkflowResult populated with parsed findings,
            suggestions, stages, and a zero-cost report.
        """
        if not result_text:
            logger.warning("Empty result_text passed to AgentSDKResultAdapter")

        text = result_text or ""
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        stages = cls._build_stages(subagent_names, duration_ms)
        cost_report = cls._build_cost_report(subagent_names)
        findings = cls._parse_findings(text)
        suggestions = cls._extract_suggestions(text)
        summary = cls._extract_summary(text)

        result_metadata: dict[str, Any] = {
            "source": "agent_sdk",
            "subagent_count": len(subagent_names),
            "findings": findings,
        }
        if metadata:
            result_metadata.update(metadata)

        return WorkflowResult(
            success=True,
            stages=stages,
            final_output=text,
            cost_report=cost_report,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
            provider="anthropic",
            metadata=result_metadata,
            summary=summary,
            suggestions=suggestions,
        )

    @classmethod
    def _build_stages(
        cls,
        subagent_names: list[str],
        total_duration_ms: int,
    ) -> list[WorkflowStage]:
        """Create a WorkflowStage for each subagent.

        Splits total duration evenly across subagents as a rough
        approximation (actual per-agent timing is not available).
        """
        if not subagent_names:
            return []

        per_agent_ms = total_duration_ms // len(subagent_names)
        return [
            WorkflowStage(
                name=name,
                tier=ModelTier.CAPABLE,
                description=f"Agent SDK subagent: {name}",
                duration_ms=per_agent_ms,
            )
            for name in subagent_names
        ]

    @classmethod
    def _build_cost_report(cls, subagent_names: list[str]) -> CostReport:
        """Build a zero-cost report (subscription-based execution)."""
        by_stage = dict.fromkeys(subagent_names, 0.0)
        return CostReport(
            total_cost=0.0,
            baseline_cost=0.0,
            savings=0.0,
            savings_percent=0.0,
            by_stage=by_stage,
            by_tier={"capable": 0.0},
        )

    @classmethod
    def _extract_summary(cls, result_text: str) -> str:
        """Extract a summary from the agent's output.

        Looks for an explicit ``## Summary`` section first. Falls
        back to the first non-empty paragraph of text.
        """
        if not result_text.strip():
            return ""

        # Try explicit summary section
        summary_match = re.search(
            r"##\s*Summary\s*\n(.*?)(?=\n##|\Z)",
            result_text,
            re.DOTALL | re.IGNORECASE,
        )
        if summary_match:
            return summary_match.group(1).strip()

        # Fall back to first paragraph
        for paragraph in result_text.split("\n\n"):
            stripped = paragraph.strip()
            if stripped and not stripped.startswith("#"):
                return stripped

        # Last resort: first non-empty line
        for line in result_text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped

        return ""

    @classmethod
    def _parse_findings(cls, result_text: str) -> dict[str, Any]:
        """Extract structured findings by category from agent output.

        Looks for markdown section headers matching known categories
        (security, quality, performance, architecture) and collects
        the bullet points underneath each one.

        Args:
            result_text: The full agent response text.

        Returns:
            Dict mapping category names to lists of finding strings.
        """
        findings: dict[str, Any] = {}
        if not result_text.strip():
            return findings

        lines = result_text.splitlines()
        current_category: str | None = None

        for line in lines:
            stripped = line.strip()

            # Check if this line is a category header
            matched_category = False
            for category, pattern in _CATEGORY_PATTERNS.items():
                if pattern.search(stripped):
                    current_category = category
                    findings.setdefault(category, [])
                    matched_category = True
                    break

            if matched_category:
                continue

            # Any other h2/h3 header ends the current category
            if stripped.startswith("##"):
                current_category = None
                continue

            # Collect bullet points under the current category
            if current_category and re.match(r"^[-*]\s+", stripped):
                item = re.sub(r"^[-*]\s+", "", stripped)
                if item:
                    findings[current_category].append(item)

        return findings

    @classmethod
    def _extract_suggestions(cls, result_text: str) -> list[NextAction]:
        """Extract actionable suggestions as NextAction items.

        Scans for a ``## Suggestions`` or ``## Recommendations``
        section and converts each bullet into a NextAction. Falls
        back to scanning the entire text for suggestion-phrased
        bullets if no dedicated section exists.

        Args:
            result_text: The full agent response text.

        Returns:
            List of NextAction items parsed from the text.
        """
        if not result_text.strip():
            return []

        suggestions: list[NextAction] = []

        # Try dedicated section first
        section_match = re.search(
            r"##\s*(?:Suggestions?|Recommendations?|Next\s*Steps?)\s*\n(.*?)(?=\n##|\Z)",
            result_text,
            re.DOTALL | re.IGNORECASE,
        )

        if section_match:
            section_text = section_match.group(1)
            for line in section_text.splitlines():
                stripped = line.strip()
                bullet_match = re.match(r"^[-*]\s+(.+)", stripped)
                if bullet_match:
                    desc = bullet_match.group(1).strip()
                    if desc:
                        suggestions.append(
                            NextAction(
                                workflow_name="agent-followup",
                                description=desc,
                                reasoning="Extracted from agent SDK output",
                                priority="medium",
                                confidence=0.7,
                            )
                        )
            return suggestions

        # Fallback: scan entire text for suggestion-phrased bullets
        keywords = ("consider", "suggest", "recommend", "should", "could", "try")
        for line in result_text.splitlines():
            stripped = line.strip()
            bullet_match = re.match(r"^[-*]\s+(.+)", stripped)
            if bullet_match:
                content = bullet_match.group(1)
                lower = content.lower()
                if any(lower.startswith(kw) or f" {kw} " in lower for kw in keywords):
                    suggestions.append(
                        NextAction(
                            workflow_name="agent-followup",
                            description=content.strip(),
                            reasoning="Suggestion-phrased bullet in agent output",
                            priority="low",
                            confidence=0.5,
                        )
                    )

        return suggestions
