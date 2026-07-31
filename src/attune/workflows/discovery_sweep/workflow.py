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
import glob as _glob
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol, runtime_checkable

from attune.models import ModelTier
from attune.workflows.base import BaseWorkflow
from attune.workflows.data_classes import CostReport, WorkflowResult, WorkflowStage

from ..validation import InputSchema
from . import ds_stdout, verification

logger = logging.getLogger(__name__)

Severity = Literal["critical", "high", "medium", "low", "info"]

DEFAULT_BUDGET_USD: float = 10.00


# ---------------------------------------------------------------------------
# Per-source telemetry (Phase 1 of discovery-sweep-ops-integration)
# ---------------------------------------------------------------------------
#
# The engine emits source_started / source_finished / source_failed events
# via an optional `event_sink` callback. Defaults to None — CLI callers
# get exactly today's behavior; daemon callers (Phase 2) pass a sink that
# bridges to the ops dashboard's SSE stream.
#
# Fire-and-forget delivery: a slow or raising sink must not stall the
# sweep (NFR-2 in the spec). `_safe_emit` wraps the sink so exceptions
# are logged, not propagated.

EventSink = Callable[[dict[str, Any]], Awaitable[None]]


def _iso_now() -> str:
    """Timezone-aware ISO-8601 timestamp used for every event."""
    return datetime.now(timezone.utc).isoformat()


async def _safe_emit(sink: EventSink, event: dict[str, Any]) -> None:
    """Await ``sink(event)`` and swallow + log any exception.

    Run as a fire-and-forget task via :func:`asyncio.create_task`, so
    the sweep never waits on the sink. A raising sink logs at
    exception level and is silently dropped — observability never
    breaks correctness.
    """
    try:
        await sink(event)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: event delivery is best-effort observability;
        # sink failures must not propagate into the sweep.
        logger.exception(
            "event_sink failed for event %s source %s",
            event.get("event"),
            event.get("source"),
        )


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

    Three attributes plus one async method:

    - ``name`` — surfaced in finding metadata and CLI output.
    - ``is_llm`` — lets the engine filter sources for ``--no-llm``.
      Non-LLM adapters (e.g. :class:`PatternScanSource`) set it False.
    - ``budget_multiplier`` — proportional share of the total sweep
      budget this source claims. The engine sums multipliers across
      active sources and allocates ``budget_usd * (mult / total)`` to
      each. Non-LLM sources set ``0.0`` (they ignore budget anyway);
      LLM sources scale by their expected spend (1.0 default,
      4.0 for multi-subagent security-audit, 0.5 for CVE-feed-heavy
      dependency-check, etc.).

    The engine glob-expands the user's ``--path`` upstream and passes
    every source the same concrete ``paths`` list; sources never see
    raw glob syntax.
    """

    name: str
    is_llm: bool
    budget_multiplier: float

    async def discover(
        self,
        paths: list[str],
        budget_usd: float,
    ) -> list[Finding]:
        """Discover findings under ``paths``.

        ``paths`` is a list of concrete files or directories (glob
        expansion happens in the engine). Implementations must respect
        ``budget_usd``: return partial findings (with an ``info``-
        severity Finding noting the cap) rather than overspending or
        raising.
        """
        ...


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


# ANSI severity color map. Aligned with the project's existing
# `attune.workflows.output` pattern (high=red / medium=yellow /
# low=blue / info=dim) with critical bumped to bold-red to
# differentiate from high.
_SEVERITY_ANSI: dict[str, str] = {
    "critical": "\x1b[1;31m",  # bold red
    "high": "\x1b[31m",  # red
    "medium": "\x1b[33m",  # yellow
    "low": "\x1b[34m",  # blue
    "info": "\x1b[2m",  # dim
}
_ANSI_RESET = "\x1b[0m"


def _should_color() -> bool:
    """True when ANSI escape codes should be injected into output.

    Follows the ``NO_COLOR`` env convention (no-color.org) — any
    non-empty value disables color. ``FORCE_COLOR=1`` overrides TTY
    detection for tests and piped invocations that want color.
    Otherwise, attaches color only when stdout is an interactive
    terminal.
    """
    import os
    import sys

    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


def _severity_badge(severity: str, *, colored: bool) -> str:
    """Return the bracketed ``[severity]`` badge, optionally colored."""
    label = f"[{severity}]"
    if not colored:
        return label
    code = _SEVERITY_ANSI.get(severity, "")
    if not code:
        return label
    return f"{code}{label}{_ANSI_RESET}"


def _render_finding_line(f: Finding, *, colored: bool = False) -> str:
    location = f.file or "(no file)"
    if f.line is not None:
        location = f"{location}:{f.line}"
    return f"{_severity_badge(f.severity, colored=colored)} {location}\n  {f.title}\n  Source: {f.source}"


def _render_markdown(result: SweepResult, *, verbose: bool = False) -> str:
    """Human-readable rendering used in ``WorkflowResult.final_output``.

    Severity badges (``[critical]``, ``[high]``, ``[medium]``,
    ``[low]``, ``[info]``) are colored via ANSI escape codes when
    stdout is a TTY (and ``NO_COLOR`` is unset). Non-TTY output —
    pipes, CI logs, file redirects — gets plain brackets so logs
    stay grep-friendly.

    The check happens once per render via :func:`_should_color`
    rather than per-finding, so a single tty-detection cost amortizes
    across the whole report.
    """
    colored = _should_color()
    out: list[str] = []
    if result.metadata.failures:
        n_failed = len(result.metadata.failures)
        n_sources = len(result.metadata.sources)
        out.append(
            f"⚠ PARTIAL SWEEP: {n_failed} of {n_sources} source(s) failed "
            f"({', '.join(result.metadata.failures)}) — findings below "
            f"may be incomplete.\n"
        )
    out.append(f"## Queue ({len(result.queue)} findings)\n")
    if result.queue:
        for f in result.queue:
            out.append(_render_finding_line(f, colored=colored))
            if f.evidence:
                out.append(f"  Evidence: {f.evidence}")
            out.append("")
    else:
        out.append("_(empty)_\n")

    out.append(f"## Questions ({len(result.questions)} findings)\n")
    if result.questions:
        for q in result.questions:
            out.append(_render_finding_line(q.finding, colored=colored))
            out.append(f"  Why a question: {q.reason}")
            out.append(f"  Next step: {q.next_step}")
            out.append("")
    else:
        out.append("_(none)_\n")

    if verbose:
        out.append(f"## Rejected ({len(result.rejected)} findings)\n")
        for r in result.rejected:
            out.append(_render_finding_line(r.finding, colored=colored))
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


def _render_json(result: SweepResult) -> str:
    """JSON rendering of a sweep result matching ``design.md`` § Data model.

    Uses :func:`dataclasses.asdict` which recursively converts the
    frozen Finding / QuestionFinding / RejectedFinding dataclasses
    into plain dicts; tuple fields (notably ``Finding.tags``) become
    JSON arrays. Top-level shape is
    ``{"queue": [...], "questions": [...], "rejected": [...],
    "metadata": {...}}`` — directly consumable by CI tooling and
    the ops dashboard.

    Imports are function-scoped so the existing markdown-only call
    path doesn't pay for ``json`` / ``asdict`` at module import.
    """
    import json
    from dataclasses import asdict

    return json.dumps(asdict(result), indent=2, default=str)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


async def _run_source(
    source: FindingSource,
    paths: list[str],
    budget_usd: float,
    *,
    event_sink: EventSink | None = None,
    sweep_id: str | None = None,
) -> tuple[str, list[Finding] | BaseException]:
    """Wrap a single source.discover() so the gather() never raises.

    Returns a ``(source_name, payload)`` tuple where ``payload`` is
    either the source's findings list or the exception it raised.
    Centralizing this here keeps the engine's gather call clean and
    keeps source-failure rendering in one place.

    When ``event_sink`` is provided, emits ``source_started`` before
    ``source.discover()``, then ``source_finished`` (with
    ``findings_count``) or ``source_failed`` (with ``error`` =
    exception class name). Events are delivered fire-and-forget via
    :func:`asyncio.create_task` so sink latency never stalls the
    sweep; sink exceptions are caught + logged by :func:`_safe_emit`.
    """
    _emit_event(
        event_sink,
        {
            "event": "source_started",
            "source": source.name,
            "sweep_id": sweep_id,
            "ts": _iso_now(),
        },
    )
    try:
        findings = await source.discover(paths, budget_usd)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: per spec NFR-1, source failures must not abort
        # the sweep; convert them to a questions entry downstream.
        _emit_event(
            event_sink,
            {
                "event": "source_failed",
                "source": source.name,
                "sweep_id": sweep_id,
                "ts": _iso_now(),
                "error": type(exc).__name__,
            },
        )
        return source.name, exc
    _emit_event(
        event_sink,
        {
            "event": "source_finished",
            "source": source.name,
            "sweep_id": sweep_id,
            "ts": _iso_now(),
            "findings_count": len(findings),
        },
    )
    return source.name, findings


def _emit_event(sink: EventSink | None, event: dict[str, Any]) -> None:
    """Fire-and-forget event emission to the in-process sink, with an
    optional daemon-parseable stdout side-channel (Phase 1b).

    Stdout emission is gated by ``ATTUNE_DS_EMIT=1`` (see
    :mod:`.ds_stdout`); the daemon sets that when spawning the
    subprocess. Other invocations (CLI users piping to a file, tests,
    in-process callers) see no extra output.
    """
    if ds_stdout.is_emission_enabled():
        ds_stdout.emit_event_line(event)
    if sink is None:
        return
    asyncio.create_task(_safe_emit(sink, event))


_GLOB_CHARS: frozenset[str] = frozenset("*?[")


def _expand_path(path: str) -> list[str]:
    """Glob-expand ``path`` into a concrete list for fan-out.

    The engine expands once and passes the same list to every source so
    LLM and non-LLM adapters share an identical scope. If ``path``
    contains no glob characters it is returned as a single-element list.
    Recursive ``**`` is supported. Returns ``[path]`` when expansion
    yields nothing so sources can still emit a "no files matched"
    finding.
    """
    if not any(c in path for c in _GLOB_CHARS):
        return [path]
    matches = sorted(_glob.glob(path, recursive=True))
    return matches if matches else [path]


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

    Phase 2B: ``default_sources()`` returns all seven adapters — the
    non-LLM ``PatternScanSource`` plus six LLM adapters (bug-predict,
    security-audit, dependency-check, perf-audit, doc-audit, test-audit).
    ``--no-llm`` filters to the non-LLM sources (``is_llm = False``).

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

    input_schema = InputSchema(
        optional_fields={
            "path": str,
            "depth": str,
            "budget_usd": (int, float),
            "no_llm": bool,
            "output_format": str,
            "source": str,
            "sources": list,
        },
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Run the sweep.

        Kwargs:
            path: Scope to sweep. Required for meaningful output.
            budget_usd: Total spend cap. Defaults to
                :data:`DEFAULT_BUDGET_USD` ($10.00).
            sources: Optional explicit list of :class:`FindingSource`
                adapters; defaults to :func:`default_sources`.
            no_llm: If True, filter to non-LLM sources only
                (``is_llm = False`` adapters survive the filter).
            source: Optional source-name filter — only the named
                source runs. Mutually exclusive with ``no_llm``;
                if both are passed, ``no_llm`` applies first then
                ``source`` filters within the survivors.
            verbose: If True, include the rejected bucket in the
                rendered ``final_output`` markdown.
            output_format: ``"markdown"`` (default, human-readable)
                or ``"json"`` (machine-readable, matches design.md
                § Data model). ``verbose`` is implied for ``"json"``
                — JSON output always carries all three buckets.
            event_sink: Optional async callback receiving per-source
                ``source_started`` / ``source_finished`` /
                ``source_failed`` events as plain dicts. Fire-and-
                forget delivery — a slow or raising sink never
                stalls the sweep. Defaults to None (no emission).
                See ``docs/specs/discovery-sweep-ops-integration/
                design.md`` for the event shape.
            sweep_id: Optional correlation id propagated into every
                event. Engine does not generate it; callers supply
                one if they need to correlate events across runs
                (the ops daemon passes its ``run_id``; CLI leaves
                it None).
        """
        self.validate_input(kwargs)
        path: str = kwargs.get("path", "")
        budget_usd: float = float(kwargs.get("budget_usd", DEFAULT_BUDGET_USD))
        sources: list[FindingSource] | None = kwargs.get("sources")
        no_llm: bool = bool(kwargs.get("no_llm", False))
        source_filter: str | None = kwargs.get("source")
        verbose: bool = bool(kwargs.get("verbose", False))
        output_format: str = str(kwargs.get("output_format", "markdown"))
        depth: str | None = kwargs.get("depth")
        event_sink: EventSink | None = kwargs.get("event_sink")
        sweep_id: str | None = kwargs.get("sweep_id")

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

        if source_filter:
            sources = [s for s in sources if s.name == source_filter]

        if depth is not None:
            # Apply user-requested depth to every adapter that carries
            # one (all LLMSource subclasses have ``depth: str``;
            # PatternScanSource doesn't and gets skipped). Mutating
            # plain dataclass fields in place is the smallest hop —
            # adapters are constructed per-sweep by default_sources()
            # so the change doesn't leak across calls.
            for s in sources:
                if hasattr(s, "depth"):
                    s.depth = depth

        if not sources:
            return self._error_result(
                "no sources to run (check --source name, drop --no-llm, or both)"
            )

        allocations = self._allocate_budget(sources, budget_usd)
        paths = _expand_path(path)

        # Phase 1b: write the daemon-parseable schema-version line as
        # the first thing on stdout when emission is enabled. The
        # daemon's parser refuses unknown versions, so the version
        # line must precede any event line.
        if ds_stdout.is_emission_enabled():
            ds_stdout.emit_version_line()

        started_at = datetime.now()
        t0 = time.perf_counter()

        gathered = await asyncio.gather(
            *(
                _run_source(
                    s,
                    paths,
                    allocations[s.name],
                    event_sink=event_sink,
                    sweep_id=sweep_id,
                )
                for s in sources
            ),
            return_exceptions=False,
        )

        duration_ms = int((time.perf_counter() - t0) * 1000)
        completed_at = datetime.now()

        # Sum the API spend each LLM source accumulated during the
        # fan-out (LLMSource._record_cost). Non-LLM / deterministic
        # sources carry no spent_usd attribute and default to 0.0.
        # Without this the wrapped workflows' real cost is discarded
        # and the sweep always reports $0.00 spent.
        spent_usd = sum(getattr(s, "spent_usd", 0.0) for s in sources)

        sweep = self._build_sweep_result(
            gathered=gathered,
            budget_usd=budget_usd,
            duration_ms=duration_ms,
            spent_usd=spent_usd,
        )

        # Phase 1b: emit the final SweepResult JSON as the last
        # ATTUNE_DS line when emission is enabled. Always one line
        # (newlines stripped by emit_final_line); always the same
        # JSON shape ``--json`` / ``output_format="json"`` produces.
        if ds_stdout.is_emission_enabled():
            ds_stdout.emit_final_line(_render_json(sweep))

        # A sweep where source failures are a strict majority is a
        # failed sweep, not a clean one with quiet footnotes (NFR-1
        # says failures must not ABORT the sweep — it never promised
        # they render as success). At half or fewer failed, success
        # stays True with the failures named in metadata + the
        # markdown banner.
        n_failed = len(sweep.metadata.failures)
        sweep_ok = n_failed * 2 <= len(sources)

        return WorkflowResult(
            success=sweep_ok,
            error=(
                None
                if sweep_ok
                else (
                    f"{n_failed} of {len(sources)} sources failed: "
                    f"{', '.join(sweep.metadata.failures)}"
                )
            ),
            stages=[
                WorkflowStage(
                    name="sweep",
                    tier=ModelTier.CAPABLE,
                    description=self.description,
                )
            ],
            final_output=(
                _render_json(sweep)
                if output_format == "json"
                else _render_markdown(sweep, verbose=verbose)
            ),
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
    ) -> dict[str, float]:
        """Allocate ``budget_usd`` proportionally by ``budget_multiplier``.

        Each source receives
        ``budget_usd * (its_multiplier / sum_of_multipliers)``. Non-LLM
        adapters set ``budget_multiplier=0.0`` and receive ``$0`` (they
        ignore budget anyway). When no source claims a positive
        multiplier the engine passes the full budget through to every
        source as a no-op signal so pattern-only sweeps still work.
        """
        total_mult = sum(getattr(s, "budget_multiplier", 0.0) for s in sources)
        if total_mult <= 0.0:
            return {s.name: budget_usd for s in sources}
        return {
            s.name: budget_usd * (getattr(s, "budget_multiplier", 0.0) / total_mult)
            for s in sources
        }

    @staticmethod
    def _build_sweep_result(
        *,
        gathered: list[tuple[str, list[Finding] | BaseException]],
        budget_usd: float,
        duration_ms: int,
        spent_usd: float = 0.0,
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
            # A source whose EVERY finding is a failure marker produced
            # nothing usable — count it as failed alongside crashed
            # sources so metadata.failures (and the caller's success
            # flag) reflect reality. Before this, six dead LLM sources
            # rendered as a clean sweep (2026-07-14 health report).
            if payload and all("source-failure" in f.tags for f in payload):
                failures.append(f"{source_name}: returned only failure markers")

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
            # Real API spend summed from each LLM source's cost_report
            # by the engine (see execute()). 0.0 only when no LLM source
            # ran (--no-llm, error/empty path) or all costs were zero.
            spent_usd=spent_usd,
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
