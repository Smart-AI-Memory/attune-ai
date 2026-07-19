"""Rotation pointer + baseline eligibility tests (V2-P4: RR-2, RR-4).

The pointer function is pure over the ledger — these tests replay
ledgers (including the A-absent/B-substitutes/A-owed-next case that
round 2 of thread ``table-p4-001`` left undefined) and assert the
assignment sequence with no I/O.
"""

from __future__ import annotations

import pytest

from attune.roundtable.rotation import (
    CANONICAL_SEATS,
    assignments_for,
    next_owed,
    rotation_status,
)


def _record(owed: str, actual: str, served: bool) -> dict:
    return {
        "run_id": f"producing-x-{owed}-{actual}-{served}",
        "spec_subject": "x",
        "owed_seat": owed,
        "actual_drafter": actual,
        "served": served,
    }


class TestNextOwed:
    def test_empty_ledger_owes_the_first_canonical_seat(self) -> None:
        assert next_owed([]) == CANONICAL_SEATS[0]

    def test_served_by_owed_advances_the_pointer(self) -> None:
        assert next_owed([_record("claude", "claude", True)]) == "antigravity"

    def test_wraps_around_the_canonical_order(self) -> None:
        assert next_owed([_record("codex", "codex", True)]) == "claude"

    def test_substitute_service_never_advances(self) -> None:
        # A owed, absent; B substituted and served — A is owed again.
        assert next_owed([_record("claude", "antigravity", True)]) == "claude"

    def test_failed_run_never_advances(self) -> None:
        assert next_owed([_record("antigravity", "", False)]) == "antigravity"

    def test_absence_then_return_sequence(self) -> None:
        # Spec N: A absent, B covers. Spec N+1: A back, serves.
        # Spec N+2: pointer moved to B (who may draft twice in three).
        ledger = [
            _record("claude", "antigravity", True),
            _record("claude", "claude", True),
        ]
        assert next_owed(ledger) == "antigravity"

    def test_unknown_owed_seat_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown owed_seat"):
            next_owed([_record("gpt", "gpt", True)])


class TestAssignments:
    def test_critics_are_the_two_non_drafter_seats(self) -> None:
        roles = assignments_for("antigravity")
        assert roles == {"claude": "critic", "antigravity": "drafter", "codex": "critic"}

    def test_unknown_seat_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown seat"):
            assignments_for("gpt")


BASELINE_ONE = "P4-BASELINE: thread=mem-signal-001 promoted=MI-1..MI-7 downstream=PR#1459\n"
BASELINE_TWO_PENDING = "P4-BASELINE: thread=table-p4-001 promoted=RR-1..RR-7 downstream=pending\n"
BASELINE_TWO_DONE = "P4-BASELINE: thread=table-p4-001 promoted=RR-1..RR-7 downstream=PR#9999\n"
ARMED = "P4-ROTATION: armed 2026-08-01\n"


class TestRotationStatus:
    def test_no_baselines_is_not_eligible(self) -> None:
        assert rotation_status("nothing here").state == "not_eligible"

    def test_one_baseline_is_not_eligible(self) -> None:
        status = rotation_status(BASELINE_ONE)
        assert status.state == "not_eligible"
        assert len(status.baselines) == 1

    def test_two_baselines_one_downstream_is_eligible_unarmed(self) -> None:
        status = rotation_status(BASELINE_ONE + BASELINE_TWO_PENDING)
        assert status.state == "eligible_unarmed"

    def test_two_pending_baselines_are_not_eligible(self) -> None:
        pending = BASELINE_TWO_PENDING.replace("table-p4-001", "other-001")
        status = rotation_status(pending + BASELINE_TWO_PENDING)
        assert status.state == "not_eligible"

    def test_armed_requires_the_explicit_chair_line(self) -> None:
        status = rotation_status(BASELINE_ONE + BASELINE_TWO_DONE + ARMED)
        assert status.state == "armed"
        assert status.armed_line is not None and "armed" in status.armed_line

    def test_eligibility_never_self_arms(self) -> None:
        status = rotation_status(BASELINE_ONE + BASELINE_TWO_DONE)
        assert status.state == "eligible_unarmed"

    def test_malformed_p4_lines_are_reported_not_guessed(self) -> None:
        status = rotation_status("P4-BASELINE: thread only, no fields\n" + BASELINE_ONE)
        assert status.state == "not_eligible"
        assert any("thread only" in p for p in status.problems)
        assert len(status.baselines) == 1

    def test_evidence_is_carried_never_a_bare_boolean(self) -> None:
        status = rotation_status(BASELINE_ONE + BASELINE_TWO_DONE)
        assert status.baselines[0]["thread"] == "mem-signal-001"
        assert status.baselines[1]["downstream"] == "PR#9999"
