"""Pair mining and deterministic ranking (pipeline-learner RR-2/RR-3).

Pair semantics (RR-2, pinned so a fixture cannot pass two incompatible
algorithms): records are ordered by start timestamp; for each occurrence
of workflow A, each DISTINCT workflow B ≠ A whose first subsequent run
starts within the window contributes ONE co-occurrence to A→B —
intervening unrelated workflows do not break the pair, A→A
self-sequences are excluded, and the ratio denominator is the count of
A occurrences.

Ranking (RR-3, the stated formula — deterministic, reproducible)::

    score = 0.35 * freq_norm        # support / max support in batch
          + 0.25 * ratio            # support / count(A)
          + 0.25 * recency          # exp(-ln 2 · age_days / 30)
          + 0.15 * manual_fraction  # manual-triggered pairs / support

``recency`` decays from the MOST RECENT contributing pair with a fixed
30-day half-life against an injected ``now`` (never wall-clock inside
the ranker — two runs over the same corpus produce identical ordering).
A pair's provenance is the trigger of its A record; unknown provenance
weighs as auto (RR-3). Tie-breaker: higher support, then lexical
(a, b).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .corpus import RunRecord

#: RR-2 defaults (30-min window, min-support ~5, ratio ~0.5).
WINDOW = timedelta(minutes=30)
MIN_SUPPORT = 5
MIN_RATIO = 0.5
HALF_LIFE_DAYS = 30.0

_WEIGHT_FREQ = 0.35
_WEIGHT_RATIO = 0.25
_WEIGHT_RECENCY = 0.25
_WEIGHT_MANUAL = 0.15


@dataclass
class Candidate:
    """A mined A→B pair with the evidence the chair needs (RR-5 shape)."""

    a: str
    b: str
    support: int
    a_occurrences: int
    manual_pairs: int
    last_pair_at: datetime
    sample_run_ids: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def ratio(self) -> float:
        """support / count(A) — the RR-2 denominator."""
        return self.support / self.a_occurrences if self.a_occurrences else 0.0

    @property
    def manual_fraction(self) -> float:
        """Manual-triggered pairs / support; unknown provenance = auto."""
        return self.manual_pairs / self.support if self.support else 0.0

    def fingerprint(self, window: timedelta = WINDOW) -> str:
        """Candidate identity (RR-6): ordered members + window class."""
        return f"{self.a}->{self.b}@w{int(window.total_seconds() // 60)}"


def mine_pairs(records: list[RunRecord], *, window: timedelta = WINDOW) -> list[Candidate]:
    """Mine A→B co-occurrences from a time-ordered corpus (RR-2)."""
    ordered = sorted(records, key=lambda r: (r.started_at, r.workflow, r.run_id))
    occurrences: dict[str, int] = {}
    for rec in ordered:
        occurrences[rec.workflow] = occurrences.get(rec.workflow, 0) + 1

    pairs: dict[tuple[str, str], Candidate] = {}
    for i, a_rec in enumerate(ordered):
        seen_b: set[str] = set()
        for b_rec in ordered[i + 1 :]:
            gap = b_rec.started_at - a_rec.started_at
            if gap > window:
                break
            if gap <= timedelta(0):
                # Same-instant records carry no temporal order — "A then
                # B" requires strictly-later (deterministic under the
                # name tie-broken sort).
                continue
            b = b_rec.workflow
            if b == a_rec.workflow or b in seen_b:
                continue
            seen_b.add(b)
            key = (a_rec.workflow, b)
            cand = pairs.get(key)
            if cand is None:
                cand = Candidate(
                    a=a_rec.workflow,
                    b=b,
                    support=0,
                    a_occurrences=occurrences[a_rec.workflow],
                    manual_pairs=0,
                    last_pair_at=b_rec.started_at,
                )
                pairs[key] = cand
            cand.support += 1
            if a_rec.trigger == "manual":
                cand.manual_pairs += 1
            if b_rec.started_at > cand.last_pair_at:
                cand.last_pair_at = b_rec.started_at
            if len(cand.sample_run_ids) < 5:
                cand.sample_run_ids.append(a_rec.run_id)
    return list(pairs.values())


def filter_candidates(
    candidates: list[Candidate],
    *,
    min_support: int = MIN_SUPPORT,
    min_ratio: float = MIN_RATIO,
) -> list[Candidate]:
    """Apply the RR-2 support/ratio thresholds."""
    return [c for c in candidates if c.support >= min_support and c.ratio >= min_ratio]


def rank(candidates: list[Candidate], *, now: datetime) -> list[Candidate]:
    """Score and order candidates by the RR-3 formula (deterministic).

    ``now`` is injected, never read from the wall clock, so two runs
    over the same corpus produce identical ordering (asserted in
    tests). Ties break on higher support, then lexical (a, b).
    """
    if not candidates:
        return []
    max_support = max(c.support for c in candidates)
    for c in candidates:
        age_days = max((now - c.last_pair_at).total_seconds(), 0.0) / 86_400.0
        recency = math.exp(-math.log(2.0) * age_days / HALF_LIFE_DAYS)
        c.score = (
            _WEIGHT_FREQ * (c.support / max_support)
            + _WEIGHT_RATIO * c.ratio
            + _WEIGHT_RECENCY * recency
            + _WEIGHT_MANUAL * c.manual_fraction
        )
    return sorted(candidates, key=lambda c: (-c.score, -c.support, c.a, c.b))
