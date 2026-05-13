"""Deterministic verification rules for discovery-sweep.

Pure functions that route a single ``Finding`` into one of
three buckets — ``queue``, ``questions``, ``rejected`` — based
on severity, confidence, location presence, and cross-source
duplication. Rules are evaluated in order; the first rule
that returns a non-queue decision wins. See ``design.md`` §
Verification rules.

Resolution baked in 2026-05-13 (Phase 1):

- Severity rank: ``critical > high > medium > low > info``
- Queue eligibility threshold: ``medium`` (low / info reject)
- Confidence threshold: ``0.5`` (below routes to questions)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .workflow import Finding


Bucket = Literal["queue", "questions", "rejected"]


SEVERITY_RANK: dict[str, int] = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

QUEUE_SEVERITY_THRESHOLD = SEVERITY_RANK["medium"]
CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class RouteDecision:
    """Outcome of routing a single Finding through the rules."""

    bucket: Bucket
    rule: str | None = None
    reason: str | None = None
    next_step: str | None = None


def _severity_rank(sev: str) -> int:
    return SEVERITY_RANK.get(sev, 0)


def _same_location(a: Finding, b: Finding) -> bool:
    return a.file is not None and a.file == b.file and a.line == b.line


def _highest_at_location(target: Finding, peers: list[Finding]) -> Finding:
    """Return the highest-severity finding at ``target``'s location.

    Ties on severity are broken by ``source`` name (lexicographic
    ascending) so the routing decision is deterministic — exactly
    one finding per location survives the dedup rule.
    """
    candidates = [p for p in peers if _same_location(p, target)] + [target]
    return max(
        candidates,
        key=lambda f: (_severity_rank(f.severity), f.source),
    )


def route_finding(
    finding: Finding,
    all_findings: list[Finding],
) -> RouteDecision:
    """Route one Finding into queue / questions / rejected.

    Rule order matters. The first rule that produces a
    non-queue decision wins. A finding that survives every
    rule lands in ``queue``.
    """
    # Rule 1: location required for queue.
    if finding.file is None and "file-level" not in finding.tags:
        return RouteDecision(
            bucket="questions",
            reason="LOCATION_MISSING",
            next_step=(
                "Re-run source with --explain to surface a file/line, "
                "or treat as a file-level finding by adding the "
                "'file-level' tag."
            ),
        )

    # Rule 2: severity threshold.
    if _severity_rank(finding.severity) < QUEUE_SEVERITY_THRESHOLD:
        return RouteDecision(
            bucket="rejected",
            rule="SEVERITY_BELOW_THRESHOLD",
        )

    # Rule 3: confidence threshold.
    if finding.confidence < CONFIDENCE_THRESHOLD:
        return RouteDecision(
            bucket="questions",
            reason="LOW_CONFIDENCE",
            next_step="Manually verify; source rated < 50% confident.",
        )

    # Rules 4 & 5 only apply when multiple findings share a
    # file:line location.
    peers_at_loc = [f for f in all_findings if f is not finding and _same_location(finding, f)]
    if peers_at_loc:
        # Rule 5: conflicting severity → question, not queue.
        if _has_severity_conflict(finding, peers_at_loc):
            return RouteDecision(
                bucket="questions",
                reason="SEVERITY_CONFLICT",
                next_step=(
                    f"Sources disagree on severity at "
                    f"{finding.file}:{finding.line}. Read both findings "
                    f"and decide which lens is correct."
                ),
            )

        # Rule 4: dedup by location — keep highest severity, route others.
        winner = _highest_at_location(finding, peers_at_loc)
        if winner is not finding:
            return RouteDecision(
                bucket="rejected",
                rule=f"DUPLICATE_OF:{winner.source}",
            )

    return RouteDecision(bucket="queue")


def _has_severity_conflict(finding: Finding, peers_at_loc: list[Finding]) -> bool:
    """True if any peer at the same location has a different severity."""
    return any(p.severity != finding.severity for p in peers_at_loc)


__all__ = [
    "Bucket",
    "CONFIDENCE_THRESHOLD",
    "QUEUE_SEVERITY_THRESHOLD",
    "RouteDecision",
    "SEVERITY_RANK",
    "route_finding",
]
