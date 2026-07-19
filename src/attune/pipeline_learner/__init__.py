"""Pipeline learner v1 — mine workflow-run pairs, rank, propose.

Fixture-buildable core per RR-8's lifecycle: the readiness gate (RR-1),
pair miner (RR-2), deterministic ranker (RR-3), decision ledger (RR-6),
and acceptance scaffold (RR-7) — with NO production surfacing: the
curator source (RR-5) stays gated until RR-1's readiness passes on the
live corpus. `learn()` is the orchestrator: on an unready corpus it
returns the explicit "insufficient corpus" report and proposes nothing.

Spec: docs/specs/pipeline-learner/ (table-refreshed, chair-ruled
2026-07-19; source amended to the canonical run stream per
docs/specs/run-record-corpus/).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .corpus import (
    CUTOVER,
    LoadStats,
    Readiness,
    RunRecord,
    assess_readiness,
    default_stream_paths,
    load_corpus,
)
from .decisions import (
    REOPEN_DELTA,
    Decision,
    filter_proposable,
    ledger_path,
    load_decisions,
    record_decision,
)
from .mining import (
    MIN_RATIO,
    MIN_SUPPORT,
    WINDOW,
    Candidate,
    filter_candidates,
    mine_pairs,
    rank,
)
from .scaffold import ScaffoldError, scaffold_acceptance

__all__ = [
    "CUTOVER",
    "MIN_RATIO",
    "MIN_SUPPORT",
    "REOPEN_DELTA",
    "WINDOW",
    "Candidate",
    "Decision",
    "LearnerReport",
    "LoadStats",
    "Readiness",
    "RunRecord",
    "ScaffoldError",
    "assess_readiness",
    "default_stream_paths",
    "filter_candidates",
    "filter_proposable",
    "learn",
    "ledger_path",
    "load_corpus",
    "load_decisions",
    "mine_pairs",
    "rank",
    "record_decision",
    "scaffold_acceptance",
]


@dataclass
class LearnerReport:
    """One `learn()` run's outcome: readiness verdict + proposals."""

    readiness: Readiness
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def status(self) -> str:
        """ "proposing", or the explicit RR-1 insufficiency statement."""
        if not self.readiness.viable:
            return self.readiness.shortfall()
        if not self.candidates:
            return "corpus viable — no unruled candidates above thresholds"
        return f"proposing {len(self.candidates)} candidate(s)"


def learn(
    project: str,
    *,
    paths: list[Path] | None = None,
    ledger: Path | None = None,
    now: datetime | None = None,
    min_support: int = MIN_SUPPORT,
    min_ratio: float = MIN_RATIO,
) -> LearnerReport:
    """Run the fixture-safe learner pipeline: load → gate → mine → rank.

    Produces ZERO writes (RR-6 asserts this): proposing is read-only;
    only the explicit `record_decision`/`scaffold_acceptance` calls
    write, and only the latter touches the pipeline-artifact path.
    On an unready corpus the report carries the explicit
    "insufficient corpus" status and an EMPTY candidate list — the
    learner never proposes over the gate (RR-1).
    """
    records, stats = load_corpus(project, paths)
    mined = mine_pairs(records)
    surviving = filter_candidates(mined, min_support=min_support, min_ratio=min_ratio)
    readiness = assess_readiness(
        records,
        stats,
        min_support=min_support,
        pairs_at_min_support=len(surviving),
    )
    if not readiness.viable:
        return LearnerReport(readiness=readiness)
    ranked = rank(surviving, now=now or datetime.now(timezone.utc))
    proposable = filter_proposable(ranked, load_decisions(ledger))
    return LearnerReport(readiness=readiness, candidates=proposable)
