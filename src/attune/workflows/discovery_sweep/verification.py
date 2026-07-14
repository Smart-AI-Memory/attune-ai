"""Deterministic routing rules for the discovery sweep engine.

Each rule is a pure function over ``Finding`` inputs. The engine
calls :func:`route` on every finding; rules execute in order and the
first one that returns a non-None decision wins. A finding that
survives every rule lands in ``Queue``.

No LLM calls live here — that's enforced by the spec's NFR-4 (engine
is LLM-free) and by ``test_verification.py`` keeping its imports
narrow.

Spec: ``docs/specs/discovery-sweep/design.md`` § Verification rules.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workflow import Finding, Severity


# ---------------------------------------------------------------------------
# Decision sentinels
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Queue:
    """Finding passed every rule; route to the act-on bucket."""


@dataclass(frozen=True)
class Questions:
    """Engine can't auto-classify; surface to the human."""

    reason: str
    next_step: str


@dataclass(frozen=True)
class Rejected:
    """Filtered out by a deterministic rule; visible only in --verbose."""

    rule: str


Decision = Queue | Questions | Rejected


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Severity rank order. Larger = more severe. Used by both the
# threshold check and the dedup "keep highest" rule.
SEVERITY_RANK: dict[Severity, int] = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
}

QUEUE_SEVERITY_THRESHOLD: int = SEVERITY_RANK["medium"]
CONFIDENCE_THRESHOLD: float = 0.5

# Reason / rule constants exposed in the user-visible output.
REASON_LOCATION_MISSING = "LOCATION_MISSING"
REASON_LOW_CONFIDENCE = "LOW_CONFIDENCE"
REASON_SEVERITY_CONFLICT = "SEVERITY_CONFLICT"
REASON_SOURCE_FAILED = "SOURCE_FAILED"

RULE_SEVERITY_BELOW_THRESHOLD = "SEVERITY_BELOW_THRESHOLD"
RULE_DUPLICATE_OF_PREFIX = "DUPLICATE_OF:"


# ---------------------------------------------------------------------------
# Per-rule helpers (pure, testable in isolation)
# ---------------------------------------------------------------------------


def _rank(severity: Severity) -> int:
    return SEVERITY_RANK.get(severity, 0)


def _same_location_others(finding: Finding, all_findings: list[Finding]) -> list[Finding]:
    """Other findings (excluding ``finding`` itself) at the same file:line.

    File-level findings (``line is None``) only co-locate with other
    file-level findings on the same file — line-level peers are
    treated as a different location.
    """
    return [
        f
        for f in all_findings
        if f is not finding and f.file == finding.file and f.line == finding.line
    ]


def _max_severity_rank(findings: list[Finding]) -> int:
    return max((_rank(f.severity) for f in findings), default=0)


def _is_highest_severity_at_location(finding: Finding, all_findings: list[Finding]) -> bool:
    """True if ``finding`` is the chosen winner at its (file, line).

    Strict winner: ``finding`` has strictly higher severity than
    every co-located peer. Tie-break: among co-located findings of
    the same max severity, the first one in ``all_findings`` order
    wins. The list order reflects source iteration, so this gives
    stable, reproducible dedup across runs.
    """
    finding_rank = _rank(finding.severity)
    same_loc = [f for f in all_findings if f.file == finding.file and f.line == finding.line]
    max_rank = _max_severity_rank(same_loc)
    if finding_rank < max_rank:
        return False
    # finding_rank == max_rank; first at that rank wins.
    for f in same_loc:
        if _rank(f.severity) == max_rank:
            return f is finding
    return False


def _severity_conflict(finding: Finding, peers: list[Finding]) -> bool:
    """True if any peer has a different severity from ``finding``."""
    return any(f.severity != finding.severity for f in peers)


def _highest_severity_peer(peers: list[Finding]) -> Finding:
    """Return the peer with the highest severity (first on tie)."""
    return max(peers, key=lambda f: _rank(f.severity))


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------


def route(finding: Finding, all_findings: list[Finding]) -> Decision:
    """Route a single finding to queue / questions / rejected.

    Rule order (first non-None wins):

    0. **Source failure marker.** Tagged ``source-failure`` →
       ``Questions(SOURCE_FAILED)``. These are health signals about
       the sweep itself, not code findings — they must stay visible
       regardless of severity or file. Without this rule an ``info``
       marker WITH a file fell through to rule 2 and was silently
       buried in ``rejected`` (the 2026-07-14 6-of-7-dead-sources
       sweep that still rendered as clean).
    1. **Location required.** No ``file`` and not tagged
       ``file-level`` → ``Questions(LOCATION_MISSING)``.
    2. **Severity threshold.** Below ``medium`` →
       ``Rejected(SEVERITY_BELOW_THRESHOLD)``.
    3. **Confidence threshold.** Below ``0.5`` →
       ``Questions(LOW_CONFIDENCE)``.
    4. **Dedup by (file, line).** Not the highest-severity at this
       location → ``Rejected(DUPLICATE_OF:<source>)``.
    5. **Severity conflict.** Same location, conflicting severities
       among peers → ``Questions(SEVERITY_CONFLICT)``.

    A finding that survives all five lands in ``Queue``.
    """
    # 0. source failure markers surface as questions, never rejected
    if "source-failure" in finding.tags:
        return Questions(
            reason=REASON_SOURCE_FAILED,
            next_step=(
                f"Run `attune workflow run discovery-sweep --path X "
                f"--source {finding.source}` to reproduce."
            ),
        )

    # 1. location required
    if finding.file is None and "file-level" not in finding.tags:
        return Questions(
            reason=REASON_LOCATION_MISSING,
            next_step=(
                "Re-run the source with --explain (or directly) so it "
                "surfaces a file:line for this finding."
            ),
        )

    # 2. severity threshold
    if _rank(finding.severity) < QUEUE_SEVERITY_THRESHOLD:
        return Rejected(rule=RULE_SEVERITY_BELOW_THRESHOLD)

    # 3. confidence threshold
    if finding.confidence < CONFIDENCE_THRESHOLD:
        return Questions(
            reason=REASON_LOW_CONFIDENCE,
            next_step=("Manually verify; source rated this finding below " "50% confidence."),
        )

    peers = _same_location_others(finding, all_findings)

    # 4. dedup by (file, line)
    if peers and not _is_highest_severity_at_location(finding, all_findings):
        winner = _highest_severity_peer(peers)
        return Rejected(rule=f"{RULE_DUPLICATE_OF_PREFIX}{winner.source}")

    # 5. severity conflict (only fires when there ARE peers AND we
    # didn't already reject in rule 4 — i.e. this finding is the
    # highest-severity at its location but peers disagree).
    if peers and _severity_conflict(finding, peers):
        loc = f"{finding.file}:{finding.line}" if finding.line else finding.file
        return Questions(
            reason=REASON_SEVERITY_CONFLICT,
            next_step=(
                f"Sources disagree on severity at {loc}. "
                "Read both findings and decide which lens is correct."
            ),
        )

    return Queue()
