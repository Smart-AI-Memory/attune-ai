"""DiscoverySweepWorkflow — the orchestrator.

Runs N FindingSources against a bounded scope, filters their
output through the verification rule engine, tags ACCEPTed
findings with resolution complexity, and writes three artifacts:

- ``<sweep_id>.jsonl``           — ACCEPTed findings (queue)
- ``<sweep_id>.rejected.jsonl``  — REJECTed findings (audit log)
- ``<sweep_id>.questions.md``    — UNSURE findings (human review)

The orchestrator is read-only: it does not modify source code.
Patrick triages the queue at his pace; promoted items flow to
``docs/COVERAGE_BUG_LOG.md`` for fixing via the existing
interactive workflow.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from .budget import BudgetTracker, SweepBudgetExceeded
from .complexity import ComplexityClassifier
from .rules import default_rules
from .schema import (
    Finding,
    ResolutionComplexity,
    VerificationStatus,
    _new_sweep_id,
)
from .serialization import write_jsonl, write_questions_markdown
from .verification import VerificationEngine

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(".claude") / "discovery-queue"


@runtime_checkable
class FindingSource(Protocol):
    """A pluggable discovery adapter.

    Implementations wrap a single sub-workflow (bug_predict,
    security_audit, etc.) and translate its output into Finding
    objects with ``verification_status = UNSURE`` (the verifier
    will classify).

    ``discover`` MUST be side-effect free and respect the
    ``budget_usd`` ceiling. ``estimated_spend_usd`` reports the
    actual spend for budget accounting.
    """

    name: str

    def discover(
        self,
        scope: Path,
        budget_usd: float,
        sweep_id: str,
    ) -> Iterable[Finding]:  # pragma: no cover - protocol
        ...

    @property
    def estimated_spend_usd(self) -> float:  # pragma: no cover - protocol
        ...


@dataclass
class SweepResult:
    """Result of a discovery sweep run."""

    sweep_id: str
    scope: str
    started_at: str
    completed_at: str
    accept_count: int
    reject_count: int
    unsure_count: int
    queue_path: str | None
    rejected_path: str | None
    questions_path: str | None
    total_spend_usd: float
    sub_workflow_spend: dict[str, float]
    sub_workflow_errors: dict[str, str] = field(default_factory=dict)
    budget_halted: bool = False


class DiscoverySweepEngine:
    """Engine for the discovery-sweep pipeline.

    Not a ``BaseWorkflow`` subclass — the engine doesn't need the
    multi-tier LLM routing machinery in ``BaseWorkflow``. It
    orchestrates ``FindingSource`` adapters, and the LLM cost (if
    any) is owned by each adapter, not by the engine.

    Phase 2A wraps this engine in a thin ``BaseWorkflow`` subclass
    (``DiscoverySweepWorkflow`` in ``cli_workflow.py``) so that
    ``attune workflow run discovery-sweep`` dispatches to it.
    """

    name = "discovery-sweep"
    description = (
        "Read-only discovery sweep: runs N sub-workflows on a "
        "bounded path, filters findings through verification "
        "rules grounded in CLAUDE.md lessons, produces a curated "
        "queue tagged by resolution complexity."
    )
    stages = ["discover", "verify", "classify", "serialize"]

    def __init__(
        self,
        sources: list[FindingSource],
        *,
        verification_engine: VerificationEngine | None = None,
        complexity_classifier: ComplexityClassifier | None = None,
        budget: BudgetTracker | None = None,
        output_dir: str | Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        if not sources:
            raise ValueError("DiscoverySweepEngine requires at least one source")
        self._sources = sources
        self._project_root = (project_root or Path.cwd()).resolve()
        self._verification = verification_engine or VerificationEngine(
            default_rules(), project_root=self._project_root
        )
        self._complexity = complexity_classifier or ComplexityClassifier()
        self._budget = budget or BudgetTracker.from_env()
        self._output_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    def run(self, scope: str | Path) -> SweepResult:
        """Run the sweep against ``scope`` and write all three files.

        Synchronous. Sub-workflow failures are recorded but do not
        abort the sweep. The budget ceiling DOES abort the sweep
        (no further sub-workflows invoked once exceeded).
        """
        scope_path = Path(scope).resolve()
        sweep_id = _new_sweep_id()
        started_at = datetime.now(timezone.utc).isoformat()

        raw_findings: list[Finding] = []
        sub_workflow_errors: dict[str, str] = {}
        budget_halted = False

        for source in self._sources:
            if not self._budget.can_run(source.name):
                logger.info(
                    "skipping %s — sweep budget exhausted (sweep=%s)",
                    source.name,
                    sweep_id,
                )
                budget_halted = True
                break

            allowance = self._budget.budget_for(source.name)
            try:
                produced = list(source.discover(scope_path, allowance, sweep_id))
            except Exception as exc:  # noqa: BLE001
                # INTENTIONAL: one bad adapter must not abort the sweep.
                # Capture the error in the result; continue with the
                # next source.
                logger.exception("discovery source %s failed (sweep=%s)", source.name, sweep_id)
                sub_workflow_errors[source.name] = f"{type(exc).__name__}: {exc}"
                continue

            raw_findings.extend(produced)

            try:
                self._budget.record(source.name, source.estimated_spend_usd)
            except SweepBudgetExceeded as exc:
                logger.warning("sweep halted: %s", exc)
                budget_halted = True
                break

        verified = self._verification.classify_many(raw_findings)
        classified = self._complexity.classify_many(verified)

        accepted = [f for f in classified if f.verification_status == VerificationStatus.ACCEPT]
        rejected = [f for f in classified if f.verification_status == VerificationStatus.REJECT]
        unsure = [f for f in classified if f.verification_status == VerificationStatus.UNSURE]

        scope_str = str(scope_path)
        queue_path, rejected_path, questions_path = self._write_outputs(
            sweep_id=sweep_id,
            scope=scope_str,
            accepted=accepted,
            rejected=rejected,
            unsure=unsure,
        )

        completed_at = datetime.now(timezone.utc).isoformat()
        return SweepResult(
            sweep_id=sweep_id,
            scope=scope_str,
            started_at=started_at,
            completed_at=completed_at,
            accept_count=len(accepted),
            reject_count=len(rejected),
            unsure_count=len(unsure),
            queue_path=str(queue_path) if queue_path else None,
            rejected_path=str(rejected_path) if rejected_path else None,
            questions_path=str(questions_path) if questions_path else None,
            total_spend_usd=self._budget.total_spend_usd,
            sub_workflow_spend=dict(self._budget.spend_by_subworkflow),
            sub_workflow_errors=sub_workflow_errors,
            budget_halted=budget_halted,
        )

    def _write_outputs(
        self,
        *,
        sweep_id: str,
        scope: str,
        accepted: list[Finding],
        rejected: list[Finding],
        unsure: list[Finding],
    ) -> tuple[Path | None, Path | None, Path | None]:
        output_dir = self._resolve_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        queue_path = output_dir / f"{sweep_id}.jsonl"
        rejected_path = output_dir / f"{sweep_id}.rejected.jsonl"
        questions_path = output_dir / f"{sweep_id}.questions.md"

        write_jsonl(queue_path, accepted)
        write_jsonl(rejected_path, rejected)
        write_questions_markdown(questions_path, unsure, sweep_id=sweep_id, scope=scope)
        return queue_path, rejected_path, questions_path

    def _resolve_output_dir(self) -> Path:
        if self._output_dir.is_absolute():
            return self._output_dir
        return self._project_root / self._output_dir


def split_findings_by_complexity(
    findings: Iterable[Finding],
) -> tuple[list[Finding], list[Finding]]:
    """Split ACCEPTed findings into (routine, needs_patrick) lists."""
    routine: list[Finding] = []
    needs_patrick: list[Finding] = []
    for finding in findings:
        if finding.verification_status != VerificationStatus.ACCEPT:
            continue
        if finding.resolution_complexity == ResolutionComplexity.NEEDS_PATRICK:
            needs_patrick.append(finding)
        else:
            routine.append(finding)
    return routine, needs_patrick


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "DiscoverySweepEngine",
    "FindingSource",
    "SweepResult",
    "split_findings_by_complexity",
]
