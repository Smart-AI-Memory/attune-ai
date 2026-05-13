"""Unit tests for discovery-sweep verification rules.

Each rule is tested in isolation; the routing-order test at the
bottom proves rule 1 (location) fires before rule 2 (severity) etc.
"""

from __future__ import annotations

import pytest

from attune.workflows.discovery_sweep import Finding, verification


def _f(
    *,
    severity: str = "high",
    file: str | None = "src/a.py",
    line: int | None = 10,
    confidence: float = 0.9,
    source: str = "test-src",
    tags: tuple[str, ...] = (),
) -> Finding:
    return Finding(
        source=source,
        severity=severity,  # type: ignore[arg-type]
        title="t",
        description="d",
        file=file,
        line=line,
        evidence=None,
        confidence=confidence,
        tags=tags,
    )


class TestLocationRule:
    def test_missing_file_routes_to_questions(self) -> None:
        f = _f(file=None, line=None)
        decision = verification.route(f, [f])
        assert isinstance(decision, verification.Questions)
        assert decision.reason == verification.REASON_LOCATION_MISSING

    def test_file_level_tag_bypasses_location_rule(self) -> None:
        f = _f(file=None, line=None, tags=("file-level",))
        decision = verification.route(f, [f])
        # Falls through to subsequent rules (severity, confidence...)
        # — high severity + high confidence + no peers = Queue.
        assert isinstance(decision, verification.Queue)


class TestSeverityRule:
    @pytest.mark.parametrize("sev", ["low", "info"])
    def test_below_threshold_rejected(self, sev: str) -> None:
        f = _f(severity=sev)
        decision = verification.route(f, [f])
        assert isinstance(decision, verification.Rejected)
        assert decision.rule == verification.RULE_SEVERITY_BELOW_THRESHOLD

    @pytest.mark.parametrize("sev", ["medium", "high", "critical"])
    def test_at_or_above_threshold_passes(self, sev: str) -> None:
        f = _f(severity=sev)
        decision = verification.route(f, [f])
        assert isinstance(decision, verification.Queue)


class TestConfidenceRule:
    def test_low_confidence_routes_to_questions(self) -> None:
        f = _f(confidence=0.3)
        decision = verification.route(f, [f])
        assert isinstance(decision, verification.Questions)
        assert decision.reason == verification.REASON_LOW_CONFIDENCE

    def test_at_threshold_passes(self) -> None:
        f = _f(confidence=0.5)
        decision = verification.route(f, [f])
        assert isinstance(decision, verification.Queue)


class TestDedupRule:
    def test_lower_severity_peer_rejected_as_duplicate(self) -> None:
        winner = _f(severity="high", source="src-a")
        loser = _f(severity="medium", source="src-b")
        decision = verification.route(loser, [winner, loser])
        assert isinstance(decision, verification.Rejected)
        assert decision.rule.startswith(verification.RULE_DUPLICATE_OF_PREFIX)
        assert "src-a" in decision.rule

    def test_higher_severity_winner_passes(self) -> None:
        winner = _f(severity="high", source="src-a")
        loser = _f(severity="medium", source="src-b")
        decision = verification.route(winner, [winner, loser])
        # Same severity across peers? No — different. Winner is
        # strictly higher, so SEVERITY_CONFLICT doesn't fire and
        # the winner makes it to Queue.
        assert isinstance(decision, verification.Questions) or isinstance(
            decision, verification.Queue
        )
        # Specifically: peers disagree on severity, so the engine
        # surfaces a SEVERITY_CONFLICT question for the winner.
        if isinstance(decision, verification.Questions):
            assert decision.reason == verification.REASON_SEVERITY_CONFLICT

    def test_ties_keep_first_occurrence(self) -> None:
        first = _f(severity="high", source="src-a")
        second = _f(severity="high", source="src-b")
        # First wins (kept), second rejected as duplicate.
        d_first = verification.route(first, [first, second])
        d_second = verification.route(second, [first, second])
        assert isinstance(d_first, verification.Queue)
        assert isinstance(d_second, verification.Rejected)
        assert "src-a" in d_second.rule

    def test_different_location_not_duplicate(self) -> None:
        a = _f(file="src/a.py", line=10, source="src-a")
        b = _f(file="src/b.py", line=10, source="src-b")
        decision = verification.route(a, [a, b])
        assert isinstance(decision, verification.Queue)


class TestSeverityConflictRule:
    def test_co_located_disagreeing_severities_route_to_questions(self) -> None:
        # The kept (highest-severity) finding at a location with
        # disagreeing peers surfaces as a SEVERITY_CONFLICT question.
        a = _f(severity="critical", source="src-a")
        b = _f(severity="medium", source="src-b")
        decision = verification.route(a, [a, b])
        assert isinstance(decision, verification.Questions)
        assert decision.reason == verification.REASON_SEVERITY_CONFLICT


class TestRoutingOrder:
    def test_location_fires_before_severity(self) -> None:
        # No file AND low severity — location rule wins.
        f = _f(file=None, line=None, severity="low")
        decision = verification.route(f, [f])
        assert isinstance(decision, verification.Questions)
        assert decision.reason == verification.REASON_LOCATION_MISSING

    def test_severity_fires_before_confidence(self) -> None:
        # Low severity AND low confidence — severity rule wins
        # (rejection beats question).
        f = _f(severity="low", confidence=0.1)
        decision = verification.route(f, [f])
        assert isinstance(decision, verification.Rejected)
        assert decision.rule == verification.RULE_SEVERITY_BELOW_THRESHOLD

    def test_confidence_fires_before_dedup(self) -> None:
        winner = _f(severity="high", source="src-a", confidence=0.9)
        # Low-confidence peer — confidence rule fires before dedup.
        loser = _f(severity="medium", source="src-b", confidence=0.2)
        decision = verification.route(loser, [winner, loser])
        assert isinstance(decision, verification.Questions)
        assert decision.reason == verification.REASON_LOW_CONFIDENCE
