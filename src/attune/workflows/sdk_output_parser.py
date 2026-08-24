"""Markdown output parser — agent report text to ``WorkflowResult``.

Split out of ``agent_sdk_adapter`` (#2240). ``agent_sdk_adapter``
re-exports ``AgentSDKResultAdapter``, so existing imports keep working.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .base import ModelTier
from .data_classes import CostReport, NextAction, WorkflowResult, WorkflowStage
from .output import (
    CalloutSection,
    Finding,
    FindingsSection,
    ListSection,
    Section,
    WorkflowReport,
    next_steps_section_from_suggestions,
)

if TYPE_CHECKING:
    from .agent_sdk_adapter import AgentRunResult

logger = logging.getLogger(__name__)


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
        report_title: str | None = None,
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
            report_title: Human title for the rendered WorkflowReport
                (e.g. ``"Code review"``). Used when findings parse and
                ``final_output`` becomes a serialized report.

        Returns:
            A WorkflowResult populated with parsed findings,
            suggestions, stages, and cost/usage data. When findings
            parse (text categories or structured output),
            ``final_output`` carries a serialized
            :class:`~attune.workflows.output.WorkflowReport` (design
            D2 of workflow-result-formatting) that the voice / CLI
            layers render with tiered disclosure and the
            ``show_cost`` gate; otherwise the raw markdown text
            passes through unchanged.
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
            findings, suggestions, summary, score = cls._from_structured_output(
                agent_run_result.structured_output,
            )
        else:
            findings = cls._parse_findings(text)
            suggestions = cls._extract_suggestions(text)
            summary = cls._extract_summary(text)
            score = cls._extract_score(text)

        result_metadata: dict[str, Any] = {
            "source": "agent_sdk",
            "subagent_count": len(subagent_names),
            "findings": findings,
            # The UNMODIFIED agent text. final_output below may be
            # REWRITTEN as formatted markdown when _parse_findings
            # fires, which drops content the raw text carried — e.g.
            # the ```json block discovery-sweep's STRUCTURED_EMIT_FOOTER
            # requests (its adapters parse this field first; see
            # llm_source_base.findings_from_workflow_result).
            "raw_result_text": text,
        }
        if agent_run_result:
            result_metadata["num_turns"] = agent_run_result.num_turns
            result_metadata["session_id"] = agent_run_result.session_id
            result_metadata["duration_api_ms"] = agent_run_result.duration_api_ms
            # SDK ResultMessage error signals — surfaced so a failed run
            # records *why* (stop_reason/subtype/errors) instead of only a
            # boolean is_error. Speeds diagnosis of the "Command failed with
            # exit code 1" class of SDK failures.
            result_metadata["is_error"] = agent_run_result.is_error
            result_metadata["stop_reason"] = agent_run_result.stop_reason
            result_metadata["subtype"] = agent_run_result.subtype
            result_metadata["errors"] = agent_run_result.errors
        if metadata:
            result_metadata.update(metadata)

        # Build final_output: when findings parsed, serialize a
        # WorkflowReport (the voice/CLI renderers own formatting +
        # the show_cost gate — design D2/D3); otherwise the raw SDK
        # markdown passes through unchanged.
        final_output: str | dict[str, Any] = text
        if findings:
            final_output = cls._to_workflow_report(
                title=report_title or "Workflow report",
                summary=summary,
                score=score,
                findings=findings,
                suggestions=suggestions,
                total_cost=total_cost,
                duration_ms=duration_ms,
            ).to_dict()

        # A cleanly-completed stream can still carry an error-shaped
        # ResultMessage (budget cut, max-turns, in-run error). Deriving
        # success from the SDK's own signal keeps those runs from
        # reporting green — the CLI exit-code contract and the ops
        # dashboard chip both key off WorkflowResult.success. subtype
        # is the primary signal (sdk-teardown-exit-guard D1: is_error
        # was wrongly True on success in the CLI 2.1.178 window);
        # is_error is the fallback for SDKs that don't expose subtype.
        success = True
        error: str | None = None
        if agent_run_result is not None:
            if agent_run_result.subtype is not None:
                success = agent_run_result.subtype == "success"
            else:
                success = not agent_run_result.is_error
            if not success:
                detail = "; ".join(agent_run_result.errors or [])
                error = (
                    "SDK run ended unsuccessfully "
                    f"(subtype={agent_run_result.subtype!r}, "
                    f"is_error={agent_run_result.is_error}, "
                    f"stop_reason={agent_run_result.stop_reason!r})"
                    + (f": {detail}" if detail else "")
                )

        return WorkflowResult(
            success=success,
            error=error,
            stages=stages,
            final_output=final_output,
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

            # Any other h2 header ends the current category. Deeper
            # headers (``### HIGH`` severity groups under ``## Bugs``)
            # stay INSIDE it — treating them as terminators dropped
            # every bullet beneath them and yielded ``{"bugs": []}``:
            # a truthy findings dict that built a scored report with
            # zero sections (bug-predict, 6/6 runs, 2026-08-22).
            if stripped.startswith("##") and not stripped.startswith("###"):
                current_category = None
                continue
            if stripped.startswith("###"):
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
    def _to_workflow_report(
        cls,
        *,
        title: str,
        summary: str,
        score: int | None,
        findings: dict[str, Any],
        suggestions: list[NextAction],
        total_cost: float | None,
        duration_ms: int,
    ) -> WorkflowReport:
        """Build the universal WorkflowReport from parsed agent output.

        The adapter is the shared converter for every SDK-native
        workflow (workflow-result-formatting T8): per category, dict
        items (structured output) become a :class:`FindingsSection`;
        plain-string bullets (text parsing) become a
        :class:`ListSection`. Suggestions become the trailing
        NextStepsSection. Cost/duration land in ``metadata`` where the
        renderer's ``show_cost`` gate reads them — ``cost_usd`` is
        omitted for subscription runs (``total_cost is None``).
        """
        sections: list[Section] = []
        for category, items in findings.items():
            if not items:
                continue
            heading = category.replace("_", " ").title()
            if isinstance(items, list) and all(isinstance(i, dict) for i in items):
                sections.append(
                    FindingsSection(
                        title=heading,
                        tier="essential",
                        findings=[
                            Finding(
                                severity=str(i.get("severity", "info")),
                                file=str(i.get("file") or "unknown"),
                                line=i.get("line"),
                                message=str(i.get("description", "")),
                            )
                            for i in items
                        ],
                    )
                )
            else:
                str_items = [
                    str(i.get("description", i)) if isinstance(i, dict) else str(i)
                    for i in (items if isinstance(items, list) else [items])
                ]
                sections.append(ListSection(title=heading, tier="essential", items=str_items))

        # Attach a re-runnable slash command to each suggestion so the report
        # panel can render one-click next-step buttons (closes the
        # workflow -> report -> next-step loop). The adapter's text-extracted
        # suggestions flatten to the non-runnable ``agent-followup``, so these
        # render as static text until the richer ``generate_suggestions``
        # pipeline refreshes them post-execution (see execution_mixin).
        next_steps = next_steps_section_from_suggestions(suggestions)
        if next_steps is not None:
            sections.append(next_steps)

        # A SCORED report with no sections analysed the code, graded it,
        # and then handed back nothing structured. That renders as a blank
        # panel and reports completed/exit 0, so it looks healthy from
        # every angle — bug-predict did exactly this in 6 of 6 recorded
        # runs across three weeks and nobody noticed. Say so in the report
        # rather than rendering blank; the run still records, and the
        # prose summary is still there to read.
        #
        # The scored-vs-unscored split is the discriminator, measured over
        # the recorded run corpus (2026-08-22): an ABORTED run is also
        # section-less but carries no score, and flagging those would make
        # the marker noise. Do not widen this to "any empty report".
        if score is not None and not sections:
            logger.warning(
                "%s produced a scored report with no structured sections; "
                "findings exist only in the summary prose",
                title,
            )
            sections.append(
                CalloutSection(
                    title="No structured findings",
                    tier="essential",
                    emphasis="warn",
                    text=(
                        "This workflow returned a score but no structured "
                        "findings, so there is nothing to list here. Any "
                        "findings are in the summary above. This is a "
                        "reporting defect, not a clean result."
                    ),
                )
            )

        report_metadata: dict[str, object] = {"duration_s": duration_ms / 1000}
        if total_cost is not None:
            report_metadata["cost_usd"] = total_cost

        return WorkflowReport(
            title=title,
            summary=summary,
            score=score,
            metadata=report_metadata,
            sections=sections,
        )

    @classmethod
    def _extract_score(cls, result_text: str) -> int | None:
        """Pull a 0-100 score from text like ``score: 85/100``.

        SDK workflows prompt for "Overall code health score (0-100)"
        in the summary; the structured-output path carries it as
        ``summary.score`` instead. Returns None when absent.
        """
        match = re.search(r"\bscore:?\s*(\d{1,3})\s*/\s*100", result_text, re.IGNORECASE)
        if not match:
            return None
        value = int(match.group(1))
        return value if 0 <= value <= 100 else None

    @classmethod
    def _from_structured_output(
        cls,
        data: dict[str, Any],
    ) -> tuple[dict[str, Any], list[NextAction], str, int | None]:
        """Extract findings, suggestions, summary, and score from JSON.

        Called when the SDK returns ``structured_output`` instead of
        free-form markdown. Produces the same shape that the text-
        parsing path yields so the caller can use either transparently.

        Args:
            data: Parsed JSON dict from ``ResultMessage.structured_output``.

        Returns:
            Tuple of (findings dict, suggestions list, summary string,
            score or None).
        """
        findings: dict[str, Any] = data.get("findings", {})
        summary_data = data.get("summary", {})
        summary = summary_data.get("text", "") if isinstance(summary_data, dict) else ""
        score_raw = summary_data.get("score") if isinstance(summary_data, dict) else None
        score = score_raw if isinstance(score_raw, int) else None

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
        return findings, suggestions, summary, score
