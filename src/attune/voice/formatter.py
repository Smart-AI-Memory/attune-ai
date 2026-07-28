"""Unified output formatter for Attune AI.

This is the single bottleneck all user-facing output passes
through. It takes raw workflow results, MCP responses, or
error data and returns consistently voiced, formatted text.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import dataclasses
import enum
import logging
from types import SimpleNamespace
from typing import Any

from . import personality
from .next_steps import get_next_steps

logger = logging.getLogger(__name__)


def format_output(
    workflow_name: str,
    result: Any,
    *,
    compact: bool = False,
    disclosure: str = "summary",
) -> str:
    """Format a workflow result in the attune voice.

    This is the primary public API. All output surfaces should
    call this instead of printing directly.

    Args:
        workflow_name: Name of the workflow that produced this result.
        result: WorkflowResult, dict, or string to format.
        compact: If True, produce shorter output (for MCP responses).
        disclosure: ``"summary"`` (default) collapses detail-tier report
            sections; ``"full"`` inlines everything. Only affects results
            carrying a serialized ``WorkflowReport``.

    Returns:
        Voiced, formatted output string ready for display.

    """
    lines: list[str] = []

    # A rendered WorkflowReport owns its own score line and next-steps
    # section — the voice wrapper must not duplicate them around it.
    rendered_report = _is_report_result(result)

    # --- Detect result type and extract data ---
    success, score, report_text, cost_line, error_msg = _extract_result_data(
        result,
        disclosure=disclosure,
    )

    # --- Opening line ---
    if success:
        if score is not None:
            lines.append(f"\n{personality.score_commentary(score)}")
        else:
            lines.append(f"\n{personality.GREETING_SUCCESS}")
    elif error_msg:
        lines.append(f"\n{personality.GREETING_FAILURE}")
    else:
        lines.append(f"\n{personality.GREETING_PARTIAL}")

    # --- Main content ---
    if report_text:
        lines.append("")
        lines.append(report_text)

    # --- Score ---
    if score is not None and not rendered_report:
        lines.append(f"\nScore: {score}/100")

    # --- Cost & duration ---
    if cost_line:
        lines.append("")
        lines.append(f"  {personality.HEADER_COST}")
        lines.append(f"  {cost_line}")

    # --- Error ---
    if error_msg:
        lines.append("")
        lines.append(f"  {personality.HEADER_ERROR}")
        error_type = getattr(result, "error_type", None)
        if error_type is None and isinstance(result, dict):
            error_type = result.get("error_type")
        lines.append(f"  {personality.phrase_error(error_type)}")
        lines.append(f"  {error_msg}")

    # --- Next steps ---
    steps = (
        []
        if rendered_report
        else get_next_steps(
            workflow_name,
            result,
            max_steps=2 if compact else 3,
            compact=compact,
        )
    )
    if steps:
        lines.append("")
        lines.append(f"  {personality.HEADER_NEXT_STEPS}")
        for step in steps:
            lines.append(f"  {step}")

    lines.append("")
    return "\n".join(lines)


def format_error(
    message: str,
    *,
    error_type: str | None = None,
    workflow_name: str | None = None,
) -> str:
    """Format an error message in the attune voice.

    Args:
        message: The raw error message.
        error_type: Structured error type if available.
        workflow_name: Workflow name if applicable.

    Returns:
        Voiced error string.

    """
    lines: list[str] = []

    lines.append(f"\n{personality.ERROR_PREFIX}.")
    lines.append(f"  {personality.phrase_error(error_type)}")
    lines.append(f"  {message}")

    # Add recovery suggestion if we know the workflow
    if workflow_name and error_type == "transient":
        lines.append("")
        lines.append(
            f"  Try running `attune workflow run {workflow_name}` again.",
        )

    lines.append("")
    return "\n".join(lines)


def format_mcp_response(
    workflow_name: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    """Add voiced next steps to an MCP tool response dict.

    MCP responses stay as structured JSON but get a ``next_steps``
    field with voiced suggestions and a ``voice_summary`` field
    with a one-line human summary.

    Args:
        workflow_name: Name of the MCP tool/workflow.
        response: Raw response dict from the handler.

    Returns:
        Response dict with added voice fields.

    """
    result_proxy = SimpleNamespace(
        success=response.get("success", True),
        final_output=response,
        error=response.get("error"),
        error_type=response.get("error_type"),
        transient=response.get("transient", False),
    )

    steps = get_next_steps(workflow_name, result_proxy, max_steps=2, compact=True)

    # Add voice fields without modifying the original structure
    voiced = dict(response)
    if steps:
        voiced["next_steps"] = steps

    # Add a one-line voice summary — a handler-supplied summary wins
    # (adapters phrase their own verbs; the generic greeting is a fallback)
    if not voiced.get("voice_summary"):
        success = response.get("success", True)
        score = response.get("score")
        if score is not None:
            voiced["voice_summary"] = personality.score_commentary(score)
        elif success:
            voiced["voice_summary"] = personality.GREETING_SUCCESS
        else:
            voiced["voice_summary"] = personality.GREETING_FAILURE

    return voiced


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------


def _is_report_result(result: Any) -> bool:
    """True when ``result.final_output`` is a serialized WorkflowReport."""
    try:
        from attune.workflows.output import WorkflowReport
    except ImportError:
        return False
    return WorkflowReport.is_report_dict(getattr(result, "final_output", None))


def _extract_result_data(
    result: Any,
    *,
    disclosure: str = "summary",
) -> tuple[bool, int | None, str | None, str | None, str | None]:
    """Extract display data from various result types.

    Args:
        result: WorkflowResult, dict, or string.
        disclosure: Report disclosure mode (see :func:`format_output`).

    Returns:
        Tuple of (success, score, report_text, cost_line, error_msg).

    """
    try:
        from attune.workflows.data_classes import WorkflowResult
    except ImportError:
        WorkflowResult = None  # type: ignore[misc,assignment]

    if WorkflowResult is not None and isinstance(result, WorkflowResult):
        try:
            return _extract_from_workflow_result(result, disclosure=disclosure)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Degrade gracefully if result fields are unexpected
            logger.debug("Failed to extract from WorkflowResult", exc_info=True)

    if isinstance(result, dict):
        return _extract_from_dict(result)

    if isinstance(result, str):
        return (True, None, result, None, None)

    return (True, None, str(result) if result else None, None, None)


def _render_report_dict(fo: dict, disclosure: str) -> tuple[str | None, int | None]:
    """Render a serialized WorkflowReport dict (design D2).

    Returns ``(report_text, score)``, or ``(None, None)`` when
    reconstruction fails — the caller degrades to the legacy dict
    handling; never a crash, never a repr leak of the WorkflowResult.
    """
    try:
        from attune.config import resolve_show_cost
        from attune.voice import report_renderer
        from attune.workflows.output import WorkflowReport

        report = WorkflowReport.from_dict(fo)
        report_text = report_renderer.render_safe(
            report,
            disclosure="full" if disclosure == "full" else "summary",
            show_cost=resolve_show_cost(),
        )
        return report_text, report.score
    except Exception:  # noqa: BLE001
        # INTENTIONAL: a malformed report payload degrades to the
        # legacy dict handling in the caller.
        logger.exception("WorkflowReport reconstruction failed")
        return None, None


def _sparse_fallback_text(result: Any) -> str | None:
    """Summary + metadata-findings fallback for sparse report text.

    Returns the joined fallback string, or ``None`` when there is
    nothing to fall back to (caller keeps the original report_text).
    """
    fallback_parts: list[str] = []
    summary = getattr(result, "summary", None)
    if summary:
        fallback_parts.append(summary)
    metadata = getattr(result, "metadata", None) or {}
    findings = metadata.get("findings")
    if isinstance(findings, dict) and findings:
        for cat, items in findings.items():
            heading = cat.replace("_", " ").title()
            fallback_parts.append(f"\n## {heading}")
            if isinstance(items, list):
                for item in items:
                    fallback_parts.append(f"- {item}")
    if fallback_parts:
        return "\n".join(fallback_parts)
    return None


def _build_cost_line(result: Any) -> str | None:
    """Cost/duration line for unrendered results (None cost_report → None)."""
    cr = result.cost_report
    if cr is None:
        return None
    cost_parts = [f"${cr.total_cost:.4f}"]
    if cr.savings_percent > 0:
        cost_parts.append(f"(saved {cr.savings_percent:.0f}% vs premium)")
    cost_parts.append(f"| {result.total_duration_ms / 1000:.1f}s")
    return " ".join(cost_parts)


def _extract_from_workflow_result(
    result: Any,
    *,
    disclosure: str = "summary",
) -> tuple[bool, int | None, str | None, str | None, str | None]:
    """Extract data from a WorkflowResult dataclass.

    Args:
        result: WorkflowResult instance.
        disclosure: Report disclosure mode (see :func:`format_output`).

    Returns:
        Tuple of (success, score, report_text, cost_line, error_msg).

    """
    report_text = None
    score = None
    # True when report_text is designed output (rendered WorkflowReport or
    # the safety-net pretty-print) — exempt from the sparse fallback below.
    rendered = False

    # True only when a WorkflowReport actually rendered — the renderer
    # then owns the cost display (show_cost gate), not the voice wrapper.
    report_rendered = False

    # Extract formatted report from final_output
    fo = result.final_output
    if isinstance(fo, dict):
        from attune.workflows.output import WorkflowReport

        if WorkflowReport.is_report_dict(fo):
            # Migrated workflow: reconstruct + render (design D2).
            report_text, score = _render_report_dict(fo, disclosure)
            if report_text is not None:
                rendered = True
                report_rendered = True
        if not report_rendered:
            report_text = fo.get("formatted_report")
            score = fo.get("score")
    elif isinstance(fo, str):
        # SDK workflows emit markdown text directly — pass through.
        report_text = fo
    elif fo is not None:
        # Unmigrated bespoke result object: safety net instead of a raw
        # repr (proposal §6) — banner + generic field pretty-print.
        report_text = _format_unmigrated(fo)
        rendered = True

    # Fallback: use summary + metadata findings if report_text is sparse
    if not rendered and (not report_text or len(report_text.strip()) < 50):
        report_text = _sparse_fallback_text(result) or report_text

    # A rendered report's show_cost gate owns cost display — no wrapper
    # duplicate, and no inapplicable cost line for subscription users
    # (design D3).
    cost_line = None if report_rendered else _build_cost_line(result)

    error_msg = result.error if not result.success else None

    return (result.success, score, report_text, cost_line, error_msg)


def _format_unmigrated(value: Any) -> str:
    """Safety net for bespoke result objects with no renderer yet.

    Emits a visible "renderer not yet migrated" banner plus a generic
    field pretty-print (proposal §6): enums become ``.value``, nested
    dataclasses indent one level, collections show counts, empties show
    ``(empty)``. Intentionally not pretty — it satisfies "no repr ever"
    while making the migration gap obvious.

    Args:
        value: The unmigrated ``final_output`` object.

    Returns:
        Banner + indented field summary text.

    """
    type_name = type(value).__name__
    lines = [f"⚠ Renderer not yet migrated for {type_name}. Raw fields:", ""]
    lines.extend(_pretty_fields(value, indent="  ", depth=0))
    return "\n".join(lines)


def _pretty_fields(value: Any, *, indent: str, depth: int) -> list[str]:
    """One line per field of ``value``; nested dataclasses indent once."""
    pairs: list[tuple[str, Any]]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        pairs = [(f.name, getattr(value, f.name, None)) for f in dataclasses.fields(value)]
    elif hasattr(value, "__dict__"):
        pairs = [(k, v) for k, v in vars(value).items() if not k.startswith("_")]
    else:
        return [f"{indent}{value}"]

    lines: list[str] = []
    for name, val in pairs:
        if dataclasses.is_dataclass(val) and not isinstance(val, type) and depth < 1:
            lines.append(f"{indent}{name}: {type(val).__name__}")
            lines.extend(_pretty_fields(val, indent=indent + "  ", depth=depth + 1))
        else:
            lines.append(f"{indent}{name}: {_summarize_field(val)}")
    return lines


def _summarize_field(val: Any) -> str:
    """Scalar summary for one field value — counts, not contents."""
    if isinstance(val, enum.Enum):
        return str(val.value)
    if dataclasses.is_dataclass(val) and not isinstance(val, type):
        return type(val).__name__
    if isinstance(val, list | tuple | set):
        return f"[{len(val)} items]" if val else "(empty)"
    if isinstance(val, dict):
        return f"[{len(val)} keys]" if val else "(empty)"
    text = str(val)
    return text if len(text) <= 120 else text[:117] + "..."


def _extract_from_dict(
    result: dict[str, Any],
) -> tuple[bool, int | None, str | None, str | None, str | None]:
    """Extract data from a plain dict result.

    Args:
        result: Dict result.

    Returns:
        Tuple of (success, score, report_text, cost_line, error_msg).

    """
    success = result.get("success", True)
    score = result.get("score")
    report_text = result.get("formatted_report")
    error_msg = result.get("error") if not success else None

    if report_text is None:
        # Build text from dict fields, skipping internal/meta keys
        _skip = {"success", "score", "error", "error_type", "transient"}
        text_parts = []
        for key, value in result.items():
            if key in _skip or key.startswith("_"):
                continue
            if not isinstance(value, dict | list):
                text_parts.append(f"  {key}: {value}")
        report_text = "\n".join(text_parts) if text_parts else None

    return (success, score, report_text, None, error_msg)
