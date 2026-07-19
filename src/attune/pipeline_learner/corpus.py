"""Corpus loading and the RR-1 readiness gate (pipeline-learner v1).

Reads the canonical run stream (`~/.attune/telemetry/workflow_runs.jsonl`
plus rotated archives — run-record-corpus RC-1/RC-5) into normalized,
eligibility-filtered records, and computes the RR-1 readiness report.
The learner NEVER mines an unready corpus: readiness is operationally
defined (RR-1), not proxied by a single number.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from attune.models.telemetry.storage import _canonical_runs_file

logger = logging.getLogger(__name__)

#: Start-clean cutover (pipeline-learner decisions.md D3, chair-ruled
#: 2026-07-19): records predating the run-record-corpus merge are
#: ineligible — the pre-cutover archive is pytest-polluted with no
#: verifiable purity filter.
CUTOVER = datetime(2026, 7, 19, 17, 41, 26, tzinfo=timezone.utc)

#: Known pytest fixture workflow names (run-record-corpus RC-4 purity
#: rule): excluded outright even post-cutover, belt-and-suspenders on
#: top of suite isolation.
FIXTURE_NAMES: frozenset[str] = frozenset(
    {
        "stub-workflow",
        "test-workflow",
        "test-tier-fallback",
        "success-workflow",
        "successful-workflow",
        "failing-workflow",
        "failing-stub",
        "simple-test-workflow",
        "complete-test-workflow",
        "complex-workflow",
        "test-runner",
    }
)


@dataclass(frozen=True)
class RunRecord:
    """One eligible, normalized run record (the RR-2 fixture schema)."""

    workflow: str
    started_at: datetime  # always timezone-aware UTC
    trigger: str | None  # "manual" | "attune-rec" | None (unknown → auto)
    project: str
    run_id: str


@dataclass
class LoadStats:
    """Counted drops — RR-2 requires drops to be counted, not silent."""

    total_lines: int = 0
    eligible: int = 0
    dropped_malformed: int = 0
    dropped_pre_cutover: int = 0
    dropped_fixture: int = 0
    dropped_no_project: int = 0
    dropped_other_project: int = 0
    dropped_duplicate: int = 0


def default_stream_paths() -> list[Path]:
    """The canonical stream plus its rotated archives, oldest-last."""
    stream = _canonical_runs_file()
    archives = sorted((stream.parent / "archive").glob("workflow_runs*.jsonl"))
    return [*archives, stream]


def _parse_started_at(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    # Timezone-naive timestamps are normalized to UTC (RR-2: normalize
    # or drop, counted either way — we normalize).
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _classify_line(line: str, project: str, cutover: datetime) -> RunRecord | str:
    """Parse one JSONL line into a RunRecord, or a drop-counter name.

    The string return value is the ``LoadStats`` field to increment —
    RR-2 requires drops to be counted, never silent.
    """
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return "dropped_malformed"
    if not isinstance(data, dict):
        return "dropped_malformed"
    name = data.get("workflow_name")
    started = _parse_started_at(data.get("started_at"))
    if not isinstance(name, str) or not name or started is None:
        return "dropped_malformed"
    if name in FIXTURE_NAMES:
        return "dropped_fixture"
    if started < cutover:
        return "dropped_pre_cutover"
    rec_project = data.get("project")
    if not isinstance(rec_project, str) or not rec_project:
        return "dropped_no_project"
    if rec_project != project:
        return "dropped_other_project"
    run_id = data.get("run_id")
    trigger = data.get("trigger")
    return RunRecord(
        workflow=name,
        started_at=started,
        trigger=trigger if trigger in ("manual", "attune-rec") else None,
        project=rec_project,
        run_id=run_id if isinstance(run_id, str) and run_id else f"{name}@{started.isoformat()}",
    )


def _read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("pipeline_learner: unreadable corpus file %s: %s", path, exc)
        return []


def load_corpus(
    project: str,
    paths: list[Path] | None = None,
    *,
    cutover: datetime = CUTOVER,
) -> tuple[list[RunRecord], LoadStats]:
    """Load eligible records for ONE project (RR-4 single-project scope).

    Eligibility: schema-valid, timestamp-parseable, post-cutover,
    non-fixture, carrying a ``project`` field that matches. Records
    without a project are ineligible — never silently mined across
    mixed projects (RR-4). Duplicates (same ``run_id``) are dropped
    and counted.
    """
    stats = LoadStats()
    records: list[RunRecord] = []
    seen_ids: set[str] = set()
    for path in paths if paths is not None else default_stream_paths():
        for line in _read_lines(path):
            line = line.strip()
            if not line:
                continue
            stats.total_lines += 1
            outcome = _classify_line(line, project, cutover)
            if isinstance(outcome, str):
                setattr(stats, outcome, getattr(stats, outcome) + 1)
                continue
            if outcome.run_id in seen_ids:
                stats.dropped_duplicate += 1
                continue
            seen_ids.add(outcome.run_id)
            records.append(outcome)
            stats.eligible += 1
    records.sort(key=lambda r: (r.started_at, r.workflow, r.run_id))
    return records, stats


@dataclass
class Readiness:
    """The RR-1 readiness report — the four numbers plus the verdict."""

    eligible_records: int
    distinct_workflows: int
    distinct_active_days: int
    date_span_days: int
    min_support: int
    pairs_at_min_support: int
    stats: LoadStats = field(repr=False, default_factory=LoadStats)

    @property
    def viable(self) -> bool:
        """RR-1: ≥ 2×min-support eligible records across ≥ 7 distinct
        active days AND at least one candidate pair at min-support."""
        return (
            self.eligible_records >= 2 * self.min_support
            and self.distinct_active_days >= 7
            and self.pairs_at_min_support >= 1
        )

    def shortfall(self) -> str:
        """Human-readable 'insufficient corpus' detail (RR-1)."""
        if self.viable:
            return "corpus viable"
        needs: list[str] = []
        if self.eligible_records < 2 * self.min_support:
            needs.append(f"eligible records {self.eligible_records}/{2 * self.min_support}")
        if self.distinct_active_days < 7:
            needs.append(f"distinct active days {self.distinct_active_days}/7")
        if self.pairs_at_min_support < 1:
            needs.append(f"no candidate pair at min-support {self.min_support}")
        return "insufficient corpus — not yet viable: " + "; ".join(needs)


def assess_readiness(
    records: list[RunRecord],
    stats: LoadStats,
    *,
    min_support: int,
    pairs_at_min_support: int,
) -> Readiness:
    """Build the RR-1 report from an already-loaded corpus."""
    days = {r.started_at.date() for r in records}
    span = (max(days) - min(days)).days + 1 if days else 0
    return Readiness(
        eligible_records=len(records),
        distinct_workflows=len({r.workflow for r in records}),
        distinct_active_days=len(days),
        date_span_days=span,
        min_support=min_support,
        pairs_at_min_support=pairs_at_min_support,
        stats=stats,
    )
