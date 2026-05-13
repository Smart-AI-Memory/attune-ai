"""Discovery Sweep engine, Finding dataclasses, and FindingSource Protocol.

The engine fans out across a list of sources (``FindingSource``
adapters), collects ``Finding`` objects from each, runs the
verification rules in :mod:`.verification`, and packs the
result into a ``WorkflowResult`` whose ``final_output`` is a
human-readable markdown render and whose ``metadata`` carries
the structured ``SweepResult`` for JSON / dashboard consumers.

Sources are dispatched via ``asyncio.gather(...,
return_exceptions=True)``. A source that raises becomes a
single ``questions`` entry with ``reason="SOURCE_CRASHED"``,
not a sweep failure — see ``decisions.md`` § Output contract.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from .verification import route_finding

logger = logging.getLogger(__name__)

Severity = Literal["critical", "high", "medium", "low", "info"]


@dataclass(frozen=True)
class Finding:
    """A single discovery-sweep finding emitted by a FindingSource."""

    source: str
    severity: Severity
    title: str
    description: str
    file: str | None = None
    line: int | None = None
    evidence: str | None = None
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class QuestionFinding:
    """A finding the engine couldn't auto-classify into queue or rejected."""

    finding: Finding
    reason: str
    next_step: str


@dataclass(frozen=True)
class RejectedFinding:
    """A finding filtered out by a verification rule."""

    finding: Finding
    rule: str


@dataclass
class SweepMetadata:
    """Run-level metadata for a sweep."""

    spent_usd: float
    budget_usd: float
    sources: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class SweepResult:
    """Structured output of one discovery-sweep run."""

    queue: list[Finding] = field(default_factory=list)
    questions: list[QuestionFinding] = field(default_factory=list)
    rejected: list[RejectedFinding] = field(default_factory=list)
    metadata: SweepMetadata = field(
        default_factory=lambda: SweepMetadata(spent_usd=0.0, budget_usd=0.0),
    )


@runtime_checkable
class FindingSource(Protocol):
    """Adapter contract for sources the engine fans out across.

    Implementations may be LLM-backed or deterministic. They
    must:

    - Have a stable, kebab-case ``name`` attribute.
    - Implement ``async def discover(path, budget_usd) ->
      list[Finding]``.
    - Never raise on budget exhaustion — emit a low-confidence
      info Finding instead so the engine can route it.
    - Never exceed ``budget_usd``. The engine trusts the
      source on this.

    ``is_llm`` is an optional marker attribute (defaults to
    True if absent). The ``--no-llm`` CLI flag filters to
    ``is_llm = False`` sources only.
    """

    name: str

    async def discover(
        self,
        path: str,
        budget_usd: float,
    ) -> list[Finding]: ...


_DEFAULT_BUDGET_USD = 10.00


def _resolve_path(path: str) -> str:
    """Resolve a user-supplied path for source dispatch."""
    return os.path.abspath(path)


def _build_markdown(result: SweepResult, verbose: bool) -> str:
    """Render a SweepResult as the markdown shown in `final_output`."""
    lines: list[str] = []
    lines.append(f"## Queue ({len(result.queue)} findings)\n")
    if result.queue:
        for f in result.queue:
            loc = f"{f.file}:{f.line}" if f.file and f.line else (f.file or "(no location)")
            lines.append(f"[{f.severity}] {loc}")
            lines.append(f"  {f.title}")
            lines.append(f"  Source: {f.source}")
            if f.evidence:
                lines.append(f"  Evidence: {f.evidence}")
            lines.append("")
    else:
        lines.append("(none)\n")

    lines.append(f"## Questions ({len(result.questions)} findings)\n")
    for q in result.questions:
        f = q.finding
        loc = f"{f.file}:{f.line}" if f.file and f.line else (f.file or "(no location)")
        lines.append(f"[?] {loc}")
        lines.append(f"  {f.title} (source: {f.source})")
        lines.append(f"  Why a question: {q.reason}")
        lines.append(f"  Next step: {q.next_step}")
        lines.append("")

    if verbose:
        lines.append(f"## Rejected ({len(result.rejected)} findings)\n")
        for r in result.rejected:
            f = r.finding
            loc = f"{f.file}:{f.line}" if f.file and f.line else (f.file or "(no location)")
            lines.append(f"[{f.severity}] {loc} — rule: {r.rule} (source: {f.source})")
        lines.append("")
    else:
        lines.append(f"## Rejected ({len(result.rejected)} findings, use --verbose to see)\n")

    m = result.metadata
    lines.append(f"Spent: ${m.spent_usd:.2f} / ${m.budget_usd:.2f} budget")
    lines.append(f"Sources: {', '.join(m.sources) if m.sources else '(none)'}")
    if m.failures:
        lines.append(f"Failures: {', '.join(m.failures)}")
    lines.append(f"Duration: {m.duration_ms}ms")
    return "\n".join(lines)


def _bucket_findings(findings: list[Finding]) -> SweepResult:
    """Route every finding through the verification rules into a SweepResult."""
    result = SweepResult()
    for f in findings:
        decision = route_finding(f, findings)
        if decision.bucket == "queue":
            result.queue.append(f)
        elif decision.bucket == "questions":
            result.questions.append(
                QuestionFinding(
                    finding=f,
                    reason=decision.reason or "",
                    next_step=decision.next_step or "",
                )
            )
        else:  # rejected
            result.rejected.append(RejectedFinding(finding=f, rule=decision.rule or "REJECTED"))
    return result


def _source_crashed_finding(source_name: str, error: BaseException) -> Finding:
    """Build the single questions-bound finding for a crashed source."""
    return Finding(
        source=source_name,
        severity="info",
        title=f"Source `{source_name}` failed",
        description=(
            f"Source raised {type(error).__name__}: {error}. " "Re-run individually to investigate."
        ),
        file=None,
        line=None,
        evidence=None,
        confidence=0.0,
        tags=("source-crashed",),
    )


def _allocate_budget(sources: list[FindingSource], total_budget_usd: float) -> dict[str, float]:
    """Split the total budget evenly across LLM sources.

    Sources marked ``is_llm = False`` get $0.00 — pattern
    scanning is effectively free per ``decisions.md`` §
    Cost discipline.
    """
    llm_sources = [s for s in sources if getattr(s, "is_llm", True)]
    if not llm_sources or total_budget_usd <= 0:
        return {s.name: 0.0 for s in sources}
    per_llm = total_budget_usd / len(llm_sources)
    return {s.name: (per_llm if getattr(s, "is_llm", True) else 0.0) for s in sources}


class DiscoverySweepWorkflow:
    """Engine that fans out audit sources and triages findings.

    Phase 1: register with the workflow registry; consumes
    ``path`` and an optional ``budget_usd``. Phase 3 adds the
    JSON-mode rendering and ``--verbose`` plumbing.

    The engine does NOT inherit ``BaseWorkflow`` — it has no
    LLM stages of its own. ``execute()`` returns a
    ``WorkflowResult`` shaped to satisfy the registry / CLI,
    while keeping the engine itself dependency-light.
    """

    name = "discovery-sweep"
    description = (
        "Fan out audits, dedupe, and triage findings into " "queue / questions / rejected buckets."
    )

    def __init__(
        self,
        sources: list[FindingSource] | None = None,
        **_kwargs: Any,
    ) -> None:
        # ``sources`` is injected for tests; production callers
        # rely on ``default_sources()`` via ``execute()``.
        self._injected_sources = sources

    async def execute(self, **kwargs: Any) -> Any:
        """Run a sweep against ``path`` with ``budget_usd``.

        Returns a ``WorkflowResult`` whose ``final_output`` is
        the markdown rendering of the queue/questions/rejected
        buckets and whose ``metadata['sweep_result']`` carries
        the structured ``SweepResult`` for downstream tooling.
        """
        path: str = kwargs.get("path") or "."
        budget_usd: float = float(kwargs.get("budget_usd", _DEFAULT_BUDGET_USD))
        no_llm: bool = bool(kwargs.get("no_llm", False))
        verbose: bool = bool(kwargs.get("verbose", False))
        sources = kwargs.get("sources") or self._injected_sources
        if sources is None:
            # Import lazily to avoid a circular at module load.
            from .cli_workflow import default_sources

            sources = default_sources()

        if no_llm:
            sources = [s for s in sources if not getattr(s, "is_llm", True)]

        started_at = datetime.now()
        wall_start = time.perf_counter()

        resolved = _resolve_path(path)
        allocation = _allocate_budget(sources, budget_usd)

        findings, failures = await self._fan_out(sources, resolved, allocation)
        for source_name, exc in failures:
            findings.append(_source_crashed_finding(source_name, exc))

        result = _bucket_findings(findings)
        result.metadata = SweepMetadata(
            spent_usd=sum(allocation.values()),
            budget_usd=budget_usd,
            sources=[s.name for s in sources],
            failures=[name for name, _ in failures],
            duration_ms=int((time.perf_counter() - wall_start) * 1000),
        )

        markdown = _build_markdown(result, verbose=verbose)

        completed_at = datetime.now()
        return self._wrap_workflow_result(
            markdown=markdown,
            sweep_result=result,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _fan_out(
        self,
        sources: list[FindingSource],
        path: str,
        allocation: dict[str, float],
    ) -> tuple[list[Finding], list[tuple[str, BaseException]]]:
        """Run every source.discover() concurrently via asyncio.gather."""
        tasks = [
            asyncio.create_task(source.discover(path, allocation.get(source.name, 0.0)))
            for source in sources
        ]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)

        findings: list[Finding] = []
        failures: list[tuple[str, BaseException]] = []
        for source, outcome in zip(sources, gathered, strict=True):
            if isinstance(outcome, BaseException):
                logger.warning(
                    "discovery-sweep source %s raised %s: %s",
                    source.name,
                    type(outcome).__name__,
                    outcome,
                )
                failures.append((source.name, outcome))
            else:
                findings.extend(outcome)
        return findings, failures

    def _wrap_workflow_result(
        self,
        *,
        markdown: str,
        sweep_result: SweepResult,
        started_at: datetime,
        completed_at: datetime,
    ) -> Any:
        """Build a ``WorkflowResult`` carrying both markdown and structured output."""
        from ..data_classes import CostReport, WorkflowResult

        cost_report = CostReport(
            total_cost=sweep_result.metadata.spent_usd,
            baseline_cost=sweep_result.metadata.spent_usd,
            savings=0.0,
            savings_percent=0.0,
        )
        duration_ms = max(
            sweep_result.metadata.duration_ms,
            int((completed_at - started_at).total_seconds() * 1000),
        )
        return WorkflowResult(
            success=True,
            stages=[],
            final_output=markdown,
            cost_report=cost_report,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
            provider="discovery-sweep",
            metadata={
                "sweep_result": sweep_result,
                "queue_count": len(sweep_result.queue),
                "questions_count": len(sweep_result.questions),
                "rejected_count": len(sweep_result.rejected),
            },
        )


__all__ = [
    "DiscoverySweepWorkflow",
    "Finding",
    "FindingSource",
    "QuestionFinding",
    "RejectedFinding",
    "Severity",
    "SweepMetadata",
    "SweepResult",
]
