"""Render a :class:`~attune.workflows.output.WorkflowReport` as markdown.

The ONLY place that knows markdown (workflow-result-formatting design
D1): workflows own content (`WorkflowReport` sections), this module
owns formatting. Consumers feed the output onward — the CLI through
``rich.markdown.Markdown``, the dashboard parses to HTML, MCP returns
it verbatim.

Disclosure contract (proposal §3):

- ``disclosure="summary"`` — essential + useful sections inline;
  detail-tier sections wrapped in native ``<details>`` collapsibles.
- ``disclosure="full"`` — every section inline, no ``<details>``.

``show_cost`` gates cost/duration/model metadata lines (proposal §4 —
cost figures don't apply for subscription users; the data stays in
``WorkflowReport.metadata`` either way).

:func:`render_safe` is the crash-visible wrapper (proposal §5): a
renderer bug emits a one-line error banner plus a generic pretty-print
of the report, never a silent swallow and never a bare repr.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Literal

from attune.workflows.output import (
    CalloutSection,
    FindingsSection,
    ListSection,
    NextAction,
    NextStepsSection,
    ProseSection,
    Section,
    TableSection,
    WorkflowReport,
)

logger = logging.getLogger(__name__)

Disclosure = Literal["summary", "full"]

_EMPHASIS_ICON = {"info": "ℹ️", "ok": "✅", "warn": "⚠️", "danger": "🚨"}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}

#: metadata keys the cost line knows how to label (proposal §4)
_COST_KEYS = (
    ("cost_usd", lambda v: f"${float(v):.2f}"),
    ("duration_s", lambda v: f"{float(v):.1f}s"),
    ("model", str),
    ("tier", str),
    ("confidence", lambda v: f"confidence {float(v):.2f}"),
)


def render(
    report: WorkflowReport,
    *,
    disclosure: Disclosure = "summary",
    show_cost: bool = False,
) -> str:
    """Render ``report`` as markdown per the disclosure contract."""
    blocks: list[str] = [f"# {report.title}".rstrip()]
    if report.summary:
        blocks.append(report.summary.strip())
    if report.score is not None:
        blocks.append(f"**Score:** {report.score}/100")
    if show_cost:
        cost_line = _render_cost_line(report.metadata)
        if cost_line:
            blocks.append(cost_line)

    # NextStepsSection always renders last (tasks.md T2); empty → omitted.
    ordinary = [s for s in report.sections if not isinstance(s, NextStepsSection)]
    next_steps = [s for s in report.sections if isinstance(s, NextStepsSection) and s.items]

    for section in [*ordinary, *next_steps]:
        body = _render_section(section)
        if not body:
            continue
        if disclosure == "summary" and section.tier == "detail":
            blocks.append(f"<details><summary>{section.title}</summary>\n\n{body}\n\n</details>")
        else:
            blocks.append(body)

    return "\n\n".join(blocks) + "\n"


def render_safe(
    report: WorkflowReport,
    *,
    disclosure: Disclosure = "summary",
    show_cost: bool = False,
) -> str:
    """:func:`render`, but a renderer crash stays visible (proposal §5).

    On any exception: log it, emit a one-line error banner, and fall
    back to a generic pretty-print so the user still sees the content.
    """
    try:
        return render(report, disclosure=disclosure, show_cost=show_cost)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a rendering bug must never hide the report —
        # banner + fallback instead of a crash or a silent repr.
        logger.exception("Report renderer error")
        banner = f"⚠ Report renderer error: {type(exc).__name__}: {exc}"
        return f"{banner}\n\n{_fallback_pretty(report)}"


# =============================================================================
# Per-section emitters (one isinstance dispatch — proposal §3)
# =============================================================================


def _render_section(section: Section) -> str:
    if isinstance(section, CalloutSection):
        return _render_callout(section)
    if isinstance(section, ProseSection):
        return _render_prose(section)
    if isinstance(section, TableSection):
        return _render_table(section)
    if isinstance(section, ListSection):
        return _render_list(section)
    if isinstance(section, FindingsSection):
        return _render_findings(section)
    if isinstance(section, NextStepsSection):
        return _render_next_steps(section)
    # Unknown subclass: fail soft with its title so content isn't lost.
    logger.warning("Unknown section kind %r — rendering title only", type(section).__name__)
    return f"## {section.title}" if section.title else ""


def _render_callout(s: CalloutSection) -> str:
    icon = _EMPHASIS_ICON.get(s.emphasis, _EMPHASIS_ICON["info"])
    head = f"> {icon} **{s.title}**" if s.title else f"> {icon}"
    if not s.text:
        return head
    quoted = "\n".join(f"> {line}".rstrip() for line in s.text.strip().splitlines())
    return f"{head}\n>\n{quoted}"


def _render_prose(s: ProseSection) -> str:
    parts = [f"## {s.title}"] if s.title else []
    if s.text:
        parts.append(s.text.strip())
    return "\n\n".join(parts)


def _render_table(s: TableSection) -> str:
    if not s.columns or not s.rows:
        return f"## {s.title}" if s.title else ""
    head = "| " + " | ".join(s.columns) + " |"
    sep = "| " + " | ".join("---" for _ in s.columns) + " |"
    lines = [head, sep]
    for row in s.rows:
        lines.append("| " + " | ".join(_cell(row.get(c, "")) for c in s.columns) + " |")
    table = "\n".join(lines)
    return f"## {s.title}\n\n{table}" if s.title else table


def _render_list(s: ListSection) -> str:
    if not s.items:
        return f"## {s.title}" if s.title else ""
    items = "\n".join(f"- {item}" for item in s.items)
    return f"## {s.title}\n\n{items}" if s.title else items


def _render_findings(s: FindingsSection) -> str:
    if not s.findings:
        return f"## {s.title}" if s.title else ""
    ordered = sorted(
        s.findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, len(_SEVERITY_ORDER))
    )
    lines = ["| Severity | Location | Message |", "| --- | --- | --- |"]
    for f in ordered:
        lines.append(f"| {_cell(f.severity)} | `{f.location}` | {_cell(f.message)} |")
    table = "\n".join(lines)
    return f"## {s.title}\n\n{table}" if s.title else table


def _render_next_steps(s: NextStepsSection) -> str:
    if not s.items:
        return ""
    parts: list[str] = [f"## {s.title or 'Next steps'}"]
    bullets: list[str] = []
    for action in s.items:
        bullets.append(_render_next_action(action))
    parts.append("\n".join(bullets))
    return "\n\n".join(parts)


def _render_next_action(a: NextAction) -> str:
    text = a.text or ""
    if a.file:
        text = f"{text} (`{a.file}`)" if text else f"`{a.file}`"
    bullet = f"- {text}".rstrip()
    if a.command:
        # Fenced one-liner under the bullet so the CLI can highlight it
        # and the dashboard can grow a Run button (proposal §3).
        bullet += f"\n\n  ```\n  {a.command}\n  ```"
    return bullet


# =============================================================================
# Helpers
# =============================================================================


def _cell(value: object) -> str:
    """One table cell: stringify and keep the row on one line."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _render_cost_line(metadata: dict[str, object]) -> str:
    parts = []
    for key, fmt in _COST_KEYS:
        if key in metadata and metadata[key] is not None:
            try:
                parts.append(fmt(metadata[key]))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
    return f"*Cost & time:* {' · '.join(parts)}" if parts else ""


def _fallback_pretty(report: WorkflowReport) -> str:
    """Generic pretty-print used when :func:`render` crashes.

    Deliberately repr-free: titles and counts only, so the safety net
    never leaks dataclass reprs to a reader (proposal §6).
    """
    lines = [f"# {getattr(report, 'title', 'Workflow report')}"]
    summary = getattr(report, "summary", "")
    if summary:
        lines.append(str(summary))
    for section in getattr(report, "sections", []) or []:
        title = getattr(section, "title", "") or type(section).__name__
        lines.append(f"- {title}")
    return "\n\n".join(lines)
