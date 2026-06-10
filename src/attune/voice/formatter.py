"""Unified output formatter for Attune AI.

This is the single bottleneck all user-facing output passes
through. It takes raw workflow results, MCP responses, or
error data and returns consistently voiced, formatted text.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import os
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from enum import Enum
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
) -> str:
    """Format a workflow result in the attune voice.

    This is the primary public API. All output surfaces should
    call this instead of printing directly.

    Args:
        workflow_name: Name of the workflow that produced this result.
        result: WorkflowResult, dict, or string to format.
        compact: If True, produce shorter output (for MCP responses).

    Returns:
        Voiced, formatted output string ready for display.

    """
    lines: list[str] = []

    # --- Detect result type and extract data ---
    success, score, report_text, cost_line, error_msg = _extract_result_data(
        result,
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
    if score is not None:
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
    steps = get_next_steps(
        workflow_name,
        result,
        max_steps=2 if compact else 3,
        compact=compact,
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

    # Add a one-line voice summary
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


def _extract_result_data(
    result: Any,
) -> tuple[bool, int | None, str | None, str | None, str | None]:
    """Extract display data from various result types.

    Args:
        result: WorkflowResult, dict, or string.

    Returns:
        Tuple of (success, score, report_text, cost_line, error_msg).

    """
    try:
        from attune.workflows.data_classes import WorkflowResult
    except ImportError:
        WorkflowResult = None  # type: ignore[misc,assignment]

    if WorkflowResult is not None and isinstance(result, WorkflowResult):
        try:
            return _extract_from_workflow_result(result)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Degrade gracefully if result fields are unexpected
            logger.debug("Failed to extract from WorkflowResult", exc_info=True)

    if isinstance(result, dict):
        return _extract_from_dict(result)

    if isinstance(result, str):
        return (True, None, result, None, None)

    return (True, None, str(result) if result else None, None, None)


def resolve_show_cost(config: Any | None = None) -> bool:
    """Resolve whether human-facing output should include cost metrics.

    Design D3 (workflow-result-formatting): an explicit
    ``config.show_cost_metrics`` wins; ``None`` means auto — on for
    API-key users, off for subscription users (cost figures don't
    apply to them). Metadata stays in ``WorkflowReport.metadata`` and
    ``--json`` either way; only human rendering is gated.

    Args:
        config: Optional ``AttuneConfig``. Loaded via ``load_config()``
            when omitted.

    Returns:
        True if cost/duration/model lines should be rendered.

    """
    if config is None:
        try:
            from attune.config import load_config

            config = load_config()
        except Exception:  # noqa: BLE001
            # INTENTIONAL: config loading must never break output formatting
            logger.debug("Could not load config for show_cost", exc_info=True)
            config = None

    explicit = getattr(config, "show_cost_metrics", None)
    if explicit is not None:
        return bool(explicit)
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _extract_from_workflow_result(
    result: Any,
) -> tuple[bool, int | None, str | None, str | None, str | None]:
    """Extract data from a WorkflowResult dataclass.

    Args:
        result: WorkflowResult instance.

    Returns:
        Tuple of (success, score, report_text, cost_line, error_msg).

    """
    from attune.workflows.output import WorkflowReport

    from . import report_renderer

    report_text = None
    score = None
    rendered_report = False

    # Extract formatted report from final_output
    fo = result.final_output
    if WorkflowReport.is_report_dict(fo):
        # Migrated workflow: reconstruct + render (design D2).
        try:
            report = WorkflowReport.from_dict(fo)
            report_text = report_renderer.render_safe(
                report,
                disclosure="summary",
                show_cost=resolve_show_cost(),
            )
            score = report.score
            rendered_report = True
        except Exception:  # noqa: BLE001
            # INTENTIONAL: a malformed payload must not crash output —
            # fall through to the plain-dict handling below.
            logger.exception("WorkflowReport reconstruction failed")

    if not rendered_report:
        if isinstance(fo, dict):
            report_text = fo.get("formatted_report")
            score = fo.get("score")
        elif isinstance(fo, str):
            report_text = fo
        elif fo is not None:
            # Safety net (proposal §6): bespoke result object with no
            # converter yet — banner + generic pretty-print, never a repr.
            report_text = _safety_net_text(fo)

    # Fallback: use summary + metadata findings if report_text is sparse
    # (a rendered WorkflowReport is authoritative — never overridden).
    if not rendered_report and (not report_text or len(report_text.strip()) < 50):
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
            report_text = "\n".join(fallback_parts)

    # Build cost line (guard against None cost_report). A rendered
    # WorkflowReport owns its own cost line (gated by resolve_show_cost),
    # so skip the formatter's to avoid double display.
    cost_line = None
    cr = result.cost_report
    if cr is not None and not rendered_report:
        cost_parts = [f"${cr.total_cost:.4f}"]
        if cr.savings_percent > 0:
            cost_parts.append(f"(saved {cr.savings_percent:.0f}% vs premium)")
        cost_parts.append(f"| {result.total_duration_ms / 1000:.1f}s")
        cost_line = " ".join(cost_parts)

    error_msg = result.error if not result.success else None

    return (result.success, score, report_text, cost_line, error_msg)


def _safety_net_text(obj: Any) -> str:
    """Generic pretty-printer for unmigrated bespoke result objects.

    Proposal §6: intentionally not pretty — it satisfies "no repr ever"
    without satisfying "designed output." The visible banner makes the
    missing converter obvious so it gets addressed.

    Args:
        obj: A bespoke result object (dataclass or otherwise) found in
            ``final_output`` with no ``WorkflowReport`` converter.

    Returns:
        Banner plus an indented field listing.

    """
    type_name = type(obj).__name__
    if is_dataclass(obj) and not isinstance(obj, type):
        items = [(f.name, getattr(obj, f.name, None)) for f in dataclass_fields(obj)]
    elif hasattr(obj, "__dict__"):
        items = [(k, v) for k, v in vars(obj).items() if not k.startswith("_")]
    else:
        return f"⚠ Renderer not yet migrated for {type_name}.\n\n  {obj}"

    lines = [f"⚠ Renderer not yet migrated for {type_name}. Raw fields:", ""]
    for name, value in items:
        lines.append(f"  {name}: {_safety_net_value(value)}")
    return "\n".join(lines)


def _safety_net_value(value: Any) -> str:
    """One safety-net field value: counts for containers, no reprs."""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, list | tuple | set):
        return f"[{len(value)} items]" if value else "(empty)"
    if isinstance(value, dict):
        return f"[{len(value)} keys]" if value else "(empty)"
    if is_dataclass(value) and not isinstance(value, type):
        return type(value).__name__
    return str(value)


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
