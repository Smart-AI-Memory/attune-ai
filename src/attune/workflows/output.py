"""Workflow result data model.

The universal result type every workflow returns at the boundary into
the voice / CLI / dashboard / MCP surfaces. This module is **pure data**
— it knows nothing about rendering. Rendering markdown from a
``WorkflowReport`` is the job of ``attune.voice.report_renderer``
(workflow-result-formatting spec, T2).

Content model:

- ``WorkflowReport`` carries ordered ``sections``; each ``Section`` is a
  typed subclass (callout / prose / table / list / findings / next-steps)
  with a ``tier`` (``"essential"`` / ``"useful"`` / ``"detail"``) that
  drives progressive disclosure at render time.
- ``to_dict()`` / ``from_dict()`` round-trip through a plain dict (with a
  ``_type`` discriminator and a per-section ``kind``) so a report
  survives the SDK / MCP / JSON boundary that ``WorkflowResult.final_output``
  crosses; the voice layer detects the discriminator and reconstructs.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Literal

Tier = Literal["essential", "useful", "detail"]
Emphasis = Literal["info", "ok", "warn", "danger"]


# =============================================================================
# Leaf content types
# =============================================================================


@dataclass
class Finding:
    """Individual finding from a workflow."""

    severity: str  # "high", "medium", "low", "info"
    file: str
    line: int | None = None
    message: str = ""
    code: str | None = None

    @property
    def location(self) -> str:
        """Get ``file:line`` location string (``file`` alone if no line)."""
        if self.line:
            return f"{self.file}:{self.line}"
        return self.file

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict."""
        return {
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "code": self.code,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Finding:
        """Reconstruct from a plain dict (ignores unknown keys)."""
        return cls(
            severity=str(d.get("severity", "info")),
            file=str(d.get("file", "unknown")),
            line=d.get("line"),  # type: ignore[arg-type]
            message=str(d.get("message", "")),
            code=d.get("code"),  # type: ignore[arg-type]
        )


@dataclass
class NextAction:
    """A single forward-looking step the user can take after a report.

    ``text`` is the bullet's main line. ``command`` is an optional shell
    command a surface can wire to a one-click run button (CLI prints it
    syntax-highlighted). ``file`` is an optional ``path[:line]`` reference
    a surface can turn into a link.
    """

    text: str
    command: str | None = None
    file: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict."""
        return {"text": self.text, "command": self.command, "file": self.file}

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> NextAction:
        """Reconstruct from a plain dict."""
        return cls(
            text=str(d.get("text", "")),
            command=d.get("command"),  # type: ignore[arg-type]
            file=d.get("file"),  # type: ignore[arg-type]
        )


# =============================================================================
# Sections
# =============================================================================


@dataclass
class Section:
    """Base class for report sections. Subclasses carry kind-specific
    content and set ``kind`` for serialization."""

    title: str
    tier: Tier
    kind: ClassVar[str] = "section"

    def _payload(self) -> dict[str, object]:
        """Kind-specific fields (overridden by subclasses)."""
        return {}

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict with a ``kind`` discriminator."""
        return {"kind": self.kind, "title": self.title, "tier": self.tier, **self._payload()}


@dataclass
class CalloutSection(Section):
    """A short highlighted statement (verdict, headline)."""

    text: str = ""
    emphasis: Emphasis = "info"
    kind: ClassVar[str] = "callout"

    def _payload(self) -> dict[str, object]:
        return {"text": self.text, "emphasis": self.emphasis}


@dataclass
class ProseSection(Section):
    """A paragraph of free text."""

    text: str = ""
    kind: ClassVar[str] = "prose"

    def _payload(self) -> dict[str, object]:
        return {"text": self.text}


@dataclass
class TableSection(Section):
    """A table with named columns and row dicts."""

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, object]] = field(default_factory=list)
    kind: ClassVar[str] = "table"

    def _payload(self) -> dict[str, object]:
        return {"columns": list(self.columns), "rows": [dict(r) for r in self.rows]}


@dataclass
class ListSection(Section):
    """An unordered list of strings."""

    items: list[str] = field(default_factory=list)
    kind: ClassVar[str] = "list"

    def _payload(self) -> dict[str, object]:
        return {"items": list(self.items)}


@dataclass
class FindingsSection(Section):
    """A collection of :class:`Finding` objects."""

    findings: list[Finding] = field(default_factory=list)
    kind: ClassVar[str] = "findings"

    def _payload(self) -> dict[str, object]:
        return {"findings": [f.to_dict() for f in self.findings]}


@dataclass
class NextStepsSection(Section):
    """Forward-momentum section, rendered last in summary mode and
    omitted entirely when ``items`` is empty. Tier is ``"essential"`` by
    convention."""

    items: list[NextAction] = field(default_factory=list)
    kind: ClassVar[str] = "next-steps"

    def _payload(self) -> dict[str, object]:
        return {"items": [a.to_dict() for a in self.items]}


# kind -> subclass, for from_dict dispatch.
_SECTION_REGISTRY: dict[str, type[Section]] = {
    CalloutSection.kind: CalloutSection,
    ProseSection.kind: ProseSection,
    TableSection.kind: TableSection,
    ListSection.kind: ListSection,
    FindingsSection.kind: FindingsSection,
    NextStepsSection.kind: NextStepsSection,
}


def _section_from_dict(d: dict[str, object]) -> Section:
    """Reconstruct the right :class:`Section` subclass from its dict."""
    kind = str(d.get("kind", ""))
    cls = _SECTION_REGISTRY.get(kind)
    if cls is None:
        raise ValueError(f"Unknown section kind: {kind!r}")
    title = str(d.get("title", ""))
    tier: Tier = d.get("tier", "useful")  # type: ignore[assignment]
    if cls is CalloutSection:
        return CalloutSection(
            title=title,
            tier=tier,
            text=str(d.get("text", "")),
            emphasis=d.get("emphasis", "info"),  # type: ignore[arg-type]
        )
    if cls is ProseSection:
        return ProseSection(title=title, tier=tier, text=str(d.get("text", "")))
    if cls is TableSection:
        return TableSection(
            title=title,
            tier=tier,
            columns=list(d.get("columns", [])),  # type: ignore[arg-type]
            rows=list(d.get("rows", [])),  # type: ignore[arg-type]
        )
    if cls is ListSection:
        return ListSection(title=title, tier=tier, items=list(d.get("items", [])))  # type: ignore[arg-type]
    if cls is FindingsSection:
        raw = d.get("findings", []) or []
        return FindingsSection(
            title=title,
            tier=tier,
            findings=[Finding.from_dict(f) for f in raw],  # type: ignore[union-attr]
        )
    # NextStepsSection
    raw_items = d.get("items", []) or []
    return NextStepsSection(
        title=title,
        tier=tier,
        items=[NextAction.from_dict(a) for a in raw_items],  # type: ignore[union-attr]
    )


# =============================================================================
# Report
# =============================================================================


@dataclass
class WorkflowReport:
    """The universal workflow result type. Pure data; rendering lives in
    ``attune.voice.report_renderer``."""

    title: str
    summary: str = ""
    score: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    suggestions: list = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        """Back-compat read: all findings across any FindingsSection."""
        out: list[Finding] = []
        for s in self.sections:
            if isinstance(s, FindingsSection):
                out.extend(s.findings)
        return out

    @classmethod
    def from_findings(
        cls,
        title: str,
        findings: list[Finding],
        *,
        tier: Tier = "essential",
        **kwargs: object,
    ) -> WorkflowReport:
        """Convenience: build a one-section report for findings-only workflows."""
        return cls(
            title=title,
            sections=[FindingsSection(title=title, tier=tier, findings=findings)],
            **kwargs,  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict with a ``_type`` discriminator.

        Suitable for ``WorkflowResult.final_output`` — survives the
        SDK / MCP / JSON boundary; the voice layer detects ``_type`` and
        reconstructs via :meth:`from_dict`.
        """
        return {
            "_type": "WorkflowReport",
            "title": self.title,
            "summary": self.summary,
            "score": self.score,
            "metadata": dict(self.metadata),
            "suggestions": list(self.suggestions),
            "sections": [s.to_dict() for s in self.sections],
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> WorkflowReport:
        """Reconstruct from a :meth:`to_dict` payload."""
        raw_sections = d.get("sections", []) or []
        return cls(
            title=str(d.get("title", "")),
            summary=str(d.get("summary", "")),
            score=d.get("score"),  # type: ignore[arg-type]
            metadata=dict(d.get("metadata", {}) or {}),  # type: ignore[arg-type]
            suggestions=list(d.get("suggestions", []) or []),  # type: ignore[arg-type]
            sections=[_section_from_dict(s) for s in raw_sections],  # type: ignore[union-attr]
        )

    @staticmethod
    def is_report_dict(value: object) -> bool:
        """True if ``value`` is a serialized WorkflowReport (voice detection)."""
        return isinstance(value, dict) and value.get("_type") == "WorkflowReport"


def next_steps_section_from_suggestions(
    suggestions: list[object],
) -> NextStepsSection | None:
    """Build a ``NextStepsSection`` from suggestion objects, attaching a
    re-runnable slash command to each.

    The command turns the panel's next-step into a one-click "run" button that
    posts the command back through ``sendPrompt`` — closing the
    ``workflow -> report -> next-step -> next workflow`` loop. Each suggestion
    is anything exposing ``description`` and ``workflow_name`` (a
    ``attune.workflows.data_classes.NextAction``). The command is resolved via
    :func:`attune.cli_router.workflow_to_slash_command`; a suggestion whose
    ``workflow_name`` names no concrete workflow (``agent-followup``) gets a
    ``None`` command and renders as static text, not a button.

    Args:
        suggestions: Suggestion objects to render as forward actions.

    Returns:
        A populated ``NextStepsSection``, or ``None`` when there are no
        suggestions (the caller appends nothing).
    """
    if not suggestions:
        return None
    from attune.cli_router import workflow_to_slash_command

    return NextStepsSection(
        title="Next steps",
        tier="essential",
        items=[
            NextAction(
                text=str(getattr(s, "description", "") or ""),
                command=workflow_to_slash_command(str(getattr(s, "workflow_name", "") or "")),
            )
            for s in suggestions
        ],
    )


def report_dict_with_next_steps(report: object, suggestions: list[object]) -> object:
    """Return ``report`` with its next-steps section rebuilt from ``suggestions``.

    Applied after the richer, project-aware suggestion pipeline
    (``generate_suggestions``) runs post-execution: the report inside
    ``WorkflowResult.final_output`` was serialized earlier from the adapter's
    text-extracted suggestions (which flatten to the non-runnable
    ``agent-followup``), so its next-step buttons would be inert. This swaps in
    the rich suggestions' real workflow commands.

    Non-report values (raw markdown, prose) pass through untouched, as does a
    report when ``suggestions`` is empty (its existing section is preserved).

    Args:
        report: ``WorkflowResult.final_output`` — a serialized report dict or
            raw markdown.
        suggestions: The rich suggestions to source next-step commands from.

    Returns:
        The report dict with its next-steps section replaced, or ``report``
        unchanged when it is not a report dict or there is nothing to add.
    """
    if not suggestions or not WorkflowReport.is_report_dict(report):
        return report
    assert isinstance(report, dict)
    section = next_steps_section_from_suggestions(suggestions)
    if section is None:
        return report
    kept = [
        s
        for s in (report.get("sections") or [])
        if not (isinstance(s, dict) and s.get("kind") == NextStepsSection.kind)
    ]
    return {**report, "sections": [*kept, section.to_dict()]}
