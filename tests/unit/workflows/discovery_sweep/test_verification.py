"""Verification-rule unit tests for discovery-sweep.

Each rule in isolation, plus the routing-order interaction.
See ``design.md`` § Verification rules.
"""

from __future__ import annotations

from attune.workflows.discovery_sweep import Finding
from attune.workflows.discovery_sweep.verification import (
    CONFIDENCE_THRESHOLD,
    SEVERITY_RANK,
    route_finding,
)


def _make(
    severity: str = "high",
    file: str | None = "a.py",
    line: int | None = 10,
    confidence: float = 0.9,
    source: str = "src",
    tags: tuple[str, ...] = (),
) -> Finding:
    return Finding(
        source=source,
        severity=severity,  # type: ignore[arg-type]
        title="t",
        description="d",
        file=file,
        line=line,
        confidence=confidence,
        tags=tags,
    )


def test_severity_rank_orders_high_above_low() -> None:
    assert SEVERITY_RANK["critical"] > SEVERITY_RANK["high"]
    assert SEVERITY_RANK["high"] > SEVERITY_RANK["medium"]
    assert SEVERITY_RANK["medium"] > SEVERITY_RANK["low"]
    assert SEVERITY_RANK["low"] > SEVERITY_RANK["info"]


def test_rule1_missing_location_routes_to_questions() -> None:
    f = _make(file=None, line=None)
    decision = route_finding(f, [f])
    assert decision.bucket == "questions"
    assert decision.reason == "LOCATION_MISSING"


def test_rule1_file_level_tag_bypasses_location_requirement() -> None:
    f = _make(file=None, line=None, tags=("file-level",))
    decision = route_finding(f, [f])
    # No file, but tag overrides — survives to queue (severity high, confidence 0.9)
    assert decision.bucket == "queue"


def test_rule2_low_severity_is_rejected() -> None:
    f = _make(severity="low")
    decision = route_finding(f, [f])
    assert decision.bucket == "rejected"
    assert decision.rule == "SEVERITY_BELOW_THRESHOLD"


def test_rule2_info_severity_is_rejected() -> None:
    f = _make(severity="info")
    decision = route_finding(f, [f])
    assert decision.bucket == "rejected"


def test_rule2_medium_severity_passes_threshold() -> None:
    f = _make(severity="medium")
    decision = route_finding(f, [f])
    assert decision.bucket == "queue"


def test_rule3_low_confidence_routes_to_questions() -> None:
    f = _make(confidence=CONFIDENCE_THRESHOLD - 0.1)
    decision = route_finding(f, [f])
    assert decision.bucket == "questions"
    assert decision.reason == "LOW_CONFIDENCE"


def test_rule4_dedup_at_same_location_routes_duplicate_to_rejected() -> None:
    """Two same-severity findings at the same file:line → one queue, one rejected."""
    a = _make(severity="high", source="src-a")
    b = _make(severity="high", source="src-b")
    all_findings = [a, b]

    decision_a = route_finding(a, all_findings)
    decision_b = route_finding(b, all_findings)
    buckets = {decision_a.bucket, decision_b.bucket}
    # Exactly one survives to queue; the other is dedup-rejected.
    assert buckets == {"queue", "rejected"}
    loser = decision_a if decision_a.bucket == "rejected" else decision_b
    assert loser.rule is not None and loser.rule.startswith("DUPLICATE_OF:")


def test_rule5_severity_conflict_routes_to_questions() -> None:
    high = _make(severity="high", source="src-a")
    medium = _make(severity="medium", source="src-b")
    all_findings = [high, medium]

    # Both same location; severities differ → conflict.
    decision = route_finding(high, all_findings)
    assert decision.bucket == "questions"
    assert decision.reason == "SEVERITY_CONFLICT"


def test_rule_order_severity_before_confidence_before_dedup() -> None:
    """Low severity wins over a conflicting peer — Rule 2 fires before Rule 4/5."""
    low = _make(severity="low", source="src-a")
    high_peer = _make(severity="high", source="src-b")
    decision = route_finding(low, [low, high_peer])
    assert decision.bucket == "rejected"
    assert decision.rule == "SEVERITY_BELOW_THRESHOLD"


def test_clean_high_severity_finding_lands_in_queue() -> None:
    f = _make()
    assert route_finding(f, [f]).bucket == "queue"
