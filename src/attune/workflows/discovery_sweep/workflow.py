"""Discovery sweep engine, Protocol, and data model.

This module is intentionally LLM-free — every routing decision is
deterministic code that takes a list of :class:`Finding` objects and
returns a triaged :class:`SweepResult`.

The async :meth:`DiscoverySweepWorkflow.execute` fans out across the
registered :class:`FindingSource` adapters via
``asyncio.gather(..., return_exceptions=True)`` so a single source
crashing surfaces as one ``questions`` entry rather than a failed
sweep.

Spec: ``docs/specs/discovery-sweep/{decisions,design,requirements}.md``.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from attune.models import ModelTier
from attune.workflows.base import BaseWorkflow
from attune.workflows.data_classes import CostReport, WorkflowResult, WorkflowStage

from . import verification

logger = logging.getLogger(__name__)

Severity = Literal["critical", "high", "medium", "low", "info"]

DEFAULT_BUDGET_USD: float = 10.00


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A single discovery finding emitted by a :class:`FindingSource`.

    Frozen so verification rules can treat findings as immutable inputs
    and so adapters can build them once and share them across the
    routing layer without copy-on-write concerns.
    """

    source: str
    severity: Severity
    title: str
    description: str
    file: str | None
    line: int | None
    evidence: str | None
    confidence: float
    tags: tuple[str, ...] = ()
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class QuestionFinding:
    """A finding the engine could not auto-route to queue/rejected.

    The ``reason`` is an enumerated constant from
    :mod:`.verification` (e.g. ``LOCATION_MISSING``,
    ``LOW_CONFIDENCE``, ``SEVERITY_CONFLICT``, ``SOURCE_FAILED``).
    """

    finding: Finding
    reason: str
    next_step: str


@dataclass(frozen=True)
class RejectedFinding:
    """A finding filtered out of the queue by a deterministic rule.

    The ``rule`` field is the same enumerated constant the user sees
    in ``--verbose`` output, e.g. ``SEVERITY_BELOW_THRESHOLD`` or
    ``DUPLICATE_OF:bug-predict``.
    """

    finding: Finding
    rule: str


@dataclass
class SweepMetadata:
    """Top-level metadata for one sweep run.

    Surfaced verbatim in the JSON output footer; lets CI trend cost,
    coverage, and per-source failure rate over time.
    """

    spent_usd: float
    budget_usd: float
    sources: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class SweepResult:
    """Final output of :meth:`DiscoverySweepWorkflow.execute`."""

    queue: list[Finding]
    questions: list[QuestionFinding]
    rejected: list[RejectedFinding]
    metadata: SweepMetadata


# ---------------------------------------------------------------------------
# FindingSource Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class FindingSource(Protocol):
    """Contract every discovery-sweep source adapter implements.

    Two attributes plus one async method. ``name`` is used in finding
    metadata and CLI output; ``is_llm`` lets the engine filter sources
    for the ``--no-llm`` flag (defaults to True for adapters that
    spend API budget; non-LLM adapters like ``PatternScanSource`` set
    it to False).
    """

    name: str
    is_llm: bool

    async def discover(
        self,
        path: str,
        budget_usd: float,
    ) -> list[Finding]:
        """Discover findings in ``path``.

        Implementations must respect ``budget_usd``: return partial
        findings (with an ``info``-severity Finding noting the cap)
        rather than overspending or raising.
        """
        ...


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_finding_line(f: Finding) -> str:
    location = f.file or "(no file)"
    if f.line is not None:
        location = f"{location}:{f.line}"
    return f"[{f.severity}] {location}\n  {f.title}\n  Source: {f.source}"


def _render_markdown(result: SweepResult, *, verbose: bool = False) -> str:
    """Human-readable rendering used in ``WorkflowResult.final_output``.

    The CLI surface in Phase 3 will replace this with rich formatting;
    Phase 1 ships plain markdown so the engine works end-to-end before
    polish work begins.
    """
    out: list[str] = []
    out.append(f"## Queue ({len(result.queue)} findings)\n")
    if result.queue:
        for f in result.queue:
            out.append(_render_finding_line(f))
            if f.evidence:
                out.append(f"  Evidence: {f.evidence}")
            out.append("")
    else:
        out.append("_(empty)_\n")

    out.append(f"## Questions ({len(result.questions)} findings)\n")
    if result.questions:
        for q in result.questions:
            out.append(_render_finding_line(q.finding))
            out.append(f"  Why a question: {q.reason}")
            out.append(f"  Next step: {q.next_step}")
            out.append("")
    else:
        out.append("_(none)_\n")

    if verbose:
        out.append(f"## Rejected ({len(result.rejected)} findings)\n")
        for r in result.rejected:
            out.append(_render_finding_line(r.finding))
            out.append(f"  Rule: {r.rule}")
            out.append("")
    else:
        out.append(f"## Rejected ({len(result.rejected)} findings, " "use --verbose to see)\n")

    meta = result.metadata
    out.append(f"Spent: ${meta.spent_usd:.2f} / ${meta.budget_usd:.2f} budget")
    out.append(f"Sources: {', '.join(meta.sources) if meta.sources else '(none)'}")
    if meta.failures:
        out.append(f"Failures: {', '.join(meta.failures)}")
    out.append(f"Duration: {meta.duration_ms} ms")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


async def _run_source(
    source: FindingSource,
    path: str,
    budget_usd: float,
) -> tuple[str, list[Finding] | BaseException]:
    """Wrap a single source.discover() so the gather() never raises.

    Returns a ``(source_name, payload)`` tuple where ``payload`` is
    either the source's findings list or the exception it raised.
    Centralizing this here keeps the engine's gather call clean and
    keeps source-failure rendering in one place.
    """
    try:
        findings = await source.discover(path, budget_usd)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: per spec NFR-1, source failures must not abort
        # the sweep; convert them to a questions entry downstream.
        return source.name, exc
    return source.name, findings


def _failure_to_question(source_name: str, exc: BaseException) -> QuestionFinding:
    """Build the QuestionFinding entry for a crashed source."""
    return QuestionFinding(
        finding=Finding(
            source=source_name,
            severity="info",
            title=f"Source `{source_name}` failed: {type(exc).__name__}",
            description=(f"Re-run individually to investigate. Error: {exc}"),
            file=None,
            line=None,
            evidence=None,
            confidence=1.0,
            tags=("source-failure",),
        ),
        reason=verification.REASON_SOURCE_FAILED,
        next_step=(
            f"Run `attune workflow run discovery-sweep --path X --source "
            f"{source_name}` to reproduce."
        ),
    )


class DiscoverySweepWorkflow(BaseWorkflow):
    """Meta-workflow that fans out across audit sources and triages.

    Phase 1 wires the engine, the PatternScanSource, and CLI
    registration. LLM source adapters land in Phase 2A+; until they
    do, ``default_sources()`` returns the pattern source only and
    ``--no-llm`` is effectively a no-op (no LLM sources to filter).

    See ``docs/specs/discovery-sweep/`` for the approved spec.
    """

    name = "discovery-sweep"
    description = (
        "Fan-out audit meta-workflow — pattern + LLM sources, " "triage to queue/questions/rejected"
    )
    stages = ["sweep"]
    tier_map = {"sweep": ModelTier.CAPABLE}

    def __init__(self, **kwargs: Any) -> None:
        """Pass through to BaseWorkflow."""
        super().__init__(**kwargs)

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Run the sweep.

        Kwargs:
            path: Scope to sweep. Required for meaningful output.
            budget_usd: Total spend cap. Defaults to
                :data:`DEFAULT_BUDGET_USD` ($10.00).
            sources: Optional explicit list of :class:`FindingSource`
                adapters; defaults to :func:`default_sources`.
            no_llm: If True, filter to non-LLM sources only.
            verbose: If True, include the rejected bucket in the
                rendered ``final_output`` markdown.
        """
        path: str = kwargs.get("path", "")
        budget_usd: float = float(kwargs.get("budget_usd", DEFAULT_BUDGET_USD))
        sources: list[FindingSource] | None = kwargs.get("sources")
        no_llm: bool = bool(kwargs.get("no_llm", False))
        verbose: bool = bool(kwargs.get("verbose", False))

        if not path:
            return self._error_result("path argument is required")

        if sources is None:
            # Late import keeps the dependency from the workflow.py
            # module to cli_workflow.py one-way; matters for tests
            # that construct the engine with explicit fake sources.
            from .cli_workflow import default_sources

            sources = default_sources()

        if no_llm:
            sources = [s for s in sources if not getattr(s, "is_llm", True)]

        if not sources:
            return self._error_result("no sources to run (use --source or drop --no-llm)")

        per_source_budget = self._allocate_budget(sources, budget_usd)

        started_at = datetime.now()
        t0 = time.perf_counter()

        gathered = await asyncio.gather(
            *(_run_source(s, path, per_source_budget) for s in sources),
            return_exceptions=False,
        )

        duration_ms = int((time.perf_counter() - t0) * 1000)
        completed_at = datetime.now()

        sweep = self._build_sweep_result(
            gathered=gathered,
            budget_usd=budget_usd,
            duration_ms=duration_ms,
        )

        return WorkflowResult(
            success=True,
            stages=[
                WorkflowStage(
                    name="sweep",
                    tier=ModelTier.CAPABLE,
                    description=self.description,
                )
            ],
            final_output=_render_markdown(sweep, verbose=verbose),
            cost_report=CostReport(
                total_cost=sweep.metadata.spent_usd,
                baseline_cost=sweep.metadata.budget_usd,
                savings=max(sweep.metadata.budget_usd - sweep.metadata.spent_usd, 0.0),
                savings_percent=0.0,
            ),
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
            provider="meta",
            metadata={
                "sweep": sweep,
                "path": path,
                "budget_usd": budget_usd,
                "sources": [s.name for s in sources],
            },
        )

    @staticmethod
    def _allocate_budget(
        sources: list[FindingSource],
        budget_usd: float,
    ) -> float:
        """Per-source budget = total / number of LLM sources.

        Non-LLM sources don't consume budget, so dividing by all
        sources would under-allocate to the LLM ones. Falling back to
        the full budget when there are zero LLM sources keeps the
        signal simple (PatternScanSource ignores it anyway).
        """
        llm_count = sum(1 for s in sources if getattr(s, "is_llm", True))
        if llm_count == 0:
            return budget_usd
        return budget_usd / llm_count

    @staticmethod
    def _build_sweep_result(
        *,
        gathered: list[tuple[str, list[Finding] | BaseException]],
        budget_usd: float,
        duration_ms: int,
    ) -> SweepResult:
        all_findings: list[Finding] = []
        failures: list[str] = []
        questions: list[QuestionFinding] = []
        ran: list[str] = []

        for source_name, payload in gathered:
            ran.append(source_name)
            if isinstance(payload, BaseException):
                failures.append(f"{source_name}: {type(payload).__name__}")
                questions.append(_failure_to_question(source_name, payload))
                continue
            all_findings.extend(payload)

        queue: list[Finding] = []
        rejected: list[RejectedFinding] = []
        for finding in all_findings:
            decision = verification.route(finding, all_findings)
            if isinstance(decision, verification.Queue):
                queue.append(finding)
            elif isinstance(decision, verification.Questions):
                questions.append(
                    QuestionFinding(
                        finding=finding,
                        reason=decision.reason,
                        next_step=decision.next_step,
                    )
                )
            elif isinstance(decision, verification.Rejected):
                rejected.append(RejectedFinding(finding=finding, rule=decision.rule))

        metadata = SweepMetadata(
            spent_usd=0.0,  # Phase 1: pattern source only, no spend.
            budget_usd=budget_usd,
            sources=ran,
            failures=failures,
            duration_ms=duration_ms,
        )
        return SweepResult(
            queue=queue,
            questions=questions,
            rejected=rejected,
            metadata=metadata,
        )
