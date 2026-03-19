"""Adapter to convert Agent SDK output into WorkflowResult.

Bridges the Agent SDK world (ResultMessage text) with attune's
workflow system (WorkflowResult, WorkflowStage, CostReport).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import claude_agent_sdk

from .base import ModelTier
from .data_classes import CostReport, NextAction, WorkflowResult, WorkflowStage

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    """Data extracted from Agent SDK execution.

    Carries cost, usage, and timing data from ResultMessage
    alongside the text output. Passed to
    ``AgentSDKResultAdapter.from_agent_output()`` so it can
    populate CostReport and WorkflowStage fields.
    """

    result_text: str
    structured_output: Any = None
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None
    duration_ms: int = 0
    duration_api_ms: int = 0
    num_turns: int = 0
    session_id: str | None = None
    is_error: bool = False


def collect_agent_output(
    message: Any,
    assistant_parts: list[str],
    result_parts: list[str],
) -> AgentRunResult | None:
    """Extract text and metadata from a single SDK message.

    Call this inside ``async for message in claude_agent_sdk.query()``.
    It collects text from both ``AssistantMessage`` (the actual agent
    analysis) and ``ResultMessage`` (final metadata + optional summary).

    Args:
        message: A message yielded by ``claude_agent_sdk.query()``.
        assistant_parts: Mutable list accumulating AssistantMessage text.
        result_parts: Mutable list accumulating ResultMessage text.

    Returns:
        An AgentRunResult with metadata when a ResultMessage is received,
        or None for other message types. The caller should set
        ``run_result.result_text`` after the loop completes using
        ``build_result_text(assistant_parts, result_parts)``.
    """
    if isinstance(message, claude_agent_sdk.AssistantMessage):
        # Only collect top-level messages (not subagent tool calls)
        if message.parent_tool_use_id is None:
            for block in message.content:
                if isinstance(block, claude_agent_sdk.types.TextBlock):
                    assistant_parts.append(block.text)
        return None

    if isinstance(message, claude_agent_sdk.ResultMessage):
        if message.result:
            result_parts.append(message.result)
        return AgentRunResult(
            result_text="",
            structured_output=message.structured_output,
            total_cost_usd=message.total_cost_usd,
            usage=message.usage,
            duration_ms=message.duration_ms,
            duration_api_ms=message.duration_api_ms,
            num_turns=message.num_turns,
            session_id=message.session_id,
            is_error=message.is_error,
        )

    return None


def build_result_text(
    assistant_parts: list[str],
    result_parts: list[str],
) -> str:
    """Combine collected text into the final result string.

    Prefers ``ResultMessage.result`` when available (explicit summary).
    Falls back to ``AssistantMessage`` text blocks (the full analysis).

    Args:
        assistant_parts: Text from AssistantMessage TextBlocks.
        result_parts: Text from ResultMessage.result fields.

    Returns:
        Combined result text, or a default message if both are empty.
    """
    # Prefer ResultMessage.result if it has content
    result_text = "\n".join(result_parts).strip()
    if result_text:
        return result_text

    # Fall back to AssistantMessage text blocks
    assistant_text = "\n\n".join(assistant_parts).strip()
    if assistant_text:
        return assistant_text

    return "No results returned."


# Budget defaults by depth level
_DEFAULT_BUDGET_USD: dict[str, float] = {
    "quick": 0.50,
    "standard": 2.00,
    "deep": 5.00,
}


def get_max_budget_usd(depth: str = "standard") -> float | None:
    """Get budget cap for a workflow depth.

    Acts as a cost cap for API-key users and a complexity
    bound for subscription users. Priority:

    1. ``ATTUNE_MAX_BUDGET_USD`` env var (set to 0 to disable)
    2. Depth-based default from ``_DEFAULT_BUDGET_USD``

    Args:
        depth: Analysis depth — "quick", "standard", or "deep".

    Returns:
        Budget cap in USD, or None if caps are disabled.
    """
    override = os.environ.get("ATTUNE_MAX_BUDGET_USD")
    if override is not None:
        val = float(override)
        return val if val > 0 else None
    return _DEFAULT_BUDGET_USD.get(depth, 2.00)


# Role-keyword to model mapping for subagents
_SUBAGENT_MODEL_MAP: dict[str, str] = {
    # Deep reasoning agents → opus
    "security": "opus",
    "vuln": "opus",
    "architect": "opus",
    # Synthesis/planning agents → sonnet (balanced)
    "quality": "sonnet",
    "plan": "sonnet",
    "research": "sonnet",
    # Scanning/detection agents → haiku (fast, cheap)
    "complexity": "haiku",
    "lint": "haiku",
    "coverage": "haiku",
    "dep": "haiku",
}


def get_subagent_model(agent_name: str) -> str | None:
    """Get model for a subagent based on role keywords.

    Priority:

    1. ``ATTUNE_AGENT_MODEL_<KEYWORD>`` env var (exact keyword match)
    2. ``ATTUNE_AGENT_MODEL_DEFAULT`` env var (global override)
    3. ``_SUBAGENT_MODEL_MAP`` dict (built-in defaults)
    4. ``None`` (inherit parent model)

    Valid model values: ``"opus"``, ``"sonnet"``, ``"haiku"``,
    ``"inherit"``.

    Args:
        agent_name: Name of the subagent (e.g. ``"security-reviewer"``).

    Returns:
        Model name string, or None to inherit the parent model.
    """
    name_lower = agent_name.lower()

    # Check keyword-specific env var override
    for keyword in _SUBAGENT_MODEL_MAP:
        if keyword in name_lower:
            env_key = f"ATTUNE_AGENT_MODEL_{keyword.upper()}"
            env_val = os.environ.get(env_key)
            if env_val:
                return env_val if env_val != "inherit" else None
            return _SUBAGENT_MODEL_MAP[keyword]

    # Check global default override
    default = os.environ.get("ATTUNE_AGENT_MODEL_DEFAULT")
    if default:
        return default if default != "inherit" else None

    return None


# Section headers mapped to finding categories
_CATEGORY_PATTERNS: dict[str, re.Pattern[str]] = {
    "security": re.compile(r"##\s*security", re.IGNORECASE),
    "quality": re.compile(r"##\s*(?:code\s+)?quality", re.IGNORECASE),
    "performance": re.compile(r"##\s*performance", re.IGNORECASE),
    "architecture": re.compile(r"##\s*architecture", re.IGNORECASE),
    "test_gaps": re.compile(r"##\s*test\s*gaps?", re.IGNORECASE),
    "dependencies": re.compile(r"##\s*dependenc(?:y|ies)", re.IGNORECASE),
    "coverage": re.compile(r"##\s*(?:test\s+)?coverage", re.IGNORECASE),
    "refactoring": re.compile(r"##\s*refactor(?:ing)?", re.IGNORECASE),
    "bugs": re.compile(r"##\s*bugs?(?:\s+predict)?", re.IGNORECASE),
    "documentation": re.compile(r"##\s*documentation", re.IGNORECASE),
    "changelog": re.compile(r"##\s*changelog", re.IGNORECASE),
    "health": re.compile(r"##\s*health", re.IGNORECASE),
    "optimization": re.compile(r"##\s*optimiz(?:ation|e)", re.IGNORECASE),
    "complexity": re.compile(r"##\s*complexity", re.IGNORECASE),
    "outline": re.compile(r"##\s*outline", re.IGNORECASE),
    "research": re.compile(r"##\s*research", re.IGNORECASE),
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
        agent_run_result: AgentRunResult | None = None,
    ) -> WorkflowResult:
        """Build a WorkflowResult from raw agent text output.

        Args:
            result_text: The agent's full text response.
            subagent_names: Names of subagents that participated.
            started_at: When the agent execution began.
            completed_at: When the agent execution finished.
            metadata: Optional extra metadata to attach to the result.
            agent_run_result: Optional rich result data from the SDK
                including cost, usage, and timing. When provided,
                populates CostReport and WorkflowStage fields.

        Returns:
            A WorkflowResult populated with parsed findings,
            suggestions, stages, and cost/usage data.
        """
        if not result_text:
            logger.warning("Empty result_text passed to AgentSDKResultAdapter")

        text = result_text or ""
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Extract cost and usage from AgentRunResult if available
        total_cost: float | None = None
        usage: dict[str, Any] | None = None
        if agent_run_result:
            total_cost = agent_run_result.total_cost_usd
            usage = agent_run_result.usage

        stages = cls._build_stages(subagent_names, duration_ms, usage=usage)
        cost_report = cls._build_cost_report(
            subagent_names,
            total_cost_usd=total_cost,
        )

        # Prefer structured output when available; fall back to text parsing
        if (
            agent_run_result
            and agent_run_result.structured_output
            and isinstance(agent_run_result.structured_output, dict)
        ):
            findings, suggestions, summary = cls._from_structured_output(
                agent_run_result.structured_output,
            )
        else:
            findings = cls._parse_findings(text)
            suggestions = cls._extract_suggestions(text)
            summary = cls._extract_summary(text)

        result_metadata: dict[str, Any] = {
            "source": "agent_sdk",
            "subagent_count": len(subagent_names),
            "findings": findings,
        }
        if agent_run_result:
            result_metadata["num_turns"] = agent_run_result.num_turns
            result_metadata["session_id"] = agent_run_result.session_id
            result_metadata["duration_api_ms"] = agent_run_result.duration_api_ms
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
        usage: dict[str, Any] | None = None,
    ) -> list[WorkflowStage]:
        """Create a WorkflowStage for each subagent.

        Splits total duration and token counts evenly across
        subagents as a rough approximation (actual per-agent
        timing is not available).
        """
        if not subagent_names:
            return []

        count = len(subagent_names)
        per_agent_ms = total_duration_ms // count

        # Distribute tokens evenly if usage data is available
        per_input = 0
        per_output = 0
        if usage:
            per_input = usage.get("input_tokens", 0) // count
            per_output = usage.get("output_tokens", 0) // count

        return [
            WorkflowStage(
                name=name,
                tier=ModelTier.CAPABLE,
                description=f"Agent SDK subagent: {name}",
                duration_ms=per_agent_ms,
                input_tokens=per_input,
                output_tokens=per_output,
            )
            for name in subagent_names
        ]

    @classmethod
    def _build_cost_report(
        cls,
        subagent_names: list[str],
        total_cost_usd: float | None = None,
    ) -> CostReport:
        """Build a cost report from SDK execution data.

        Uses actual cost when available (API-key users).
        Falls back to zero for subscription users (None).
        """
        cost = total_cost_usd if total_cost_usd is not None else 0.0
        by_stage = dict.fromkeys(subagent_names, 0.0)
        return CostReport(
            total_cost=cost,
            baseline_cost=cost,
            savings=0.0,
            savings_percent=0.0,
            by_stage=by_stage,
            by_tier={"capable": cost},
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

    @classmethod
    def _from_structured_output(
        cls,
        data: dict[str, Any],
    ) -> tuple[dict[str, Any], list[NextAction], str]:
        """Extract findings, suggestions, and summary from structured JSON.

        Called when the SDK returns ``structured_output`` instead of
        free-form markdown. Produces the same triple that the text-
        parsing path yields so the caller can use either transparently.

        Args:
            data: Parsed JSON dict from ``ResultMessage.structured_output``.

        Returns:
            Tuple of (findings dict, suggestions list, summary string).
        """
        findings: dict[str, Any] = data.get("findings", {})
        summary_data = data.get("summary", {})
        summary = summary_data.get("text", "") if isinstance(summary_data, dict) else ""

        suggestions = [
            NextAction(
                workflow_name="agent-followup",
                description=item.get("description", ""),
                reasoning="Structured agent output",
                priority=item.get("priority", "medium"),
                confidence=0.9,
            )
            for item in data.get("suggestions", [])
            if isinstance(item, dict) and item.get("description")
        ]
        return findings, suggestions, summary
