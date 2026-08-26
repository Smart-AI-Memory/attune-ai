"""Session-spend-ledger enforcement at the roundtable seam.

Spec: docs/specs/session-spend-ledger/ (R2, R4, R5, D6). The seam is
``default_invoke_seat`` — every lane (routine seats, synthesis,
review, producing, countersign, gate-triage, skeptic) composes it by
default, so a refusal here is a refusal everywhere. The hermetic
ledger environment comes from this directory's ``conftest.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.gates.session_ledger import SessionSpendCapError
from attune.roundtable import review, routine
from attune.roundtable.routine import CLEAN_RUN, default_invoke_seat


def _ledger_path() -> Path:
    import os

    return Path(os.environ["ATTUNE_SESSION_LEDGER_PATH"])


class TestSeatSeam:
    def test_claude_seat_at_cap_refuses_before_the_subprocess_spawns(self, monkeypatch) -> None:
        """R2/R3: the refusal fires BEFORE any billable process starts."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
        monkeypatch.setattr(
            routine,
            "run_command",
            lambda *a, **k: pytest.fail("subprocess spawned despite the spend refusal"),
        )
        with pytest.raises(SessionSpendCapError):
            default_invoke_seat(("claude", "-p", "{brief}"), "hello")

    def test_codex_seat_is_not_anthropic_spend(self, monkeypatch) -> None:
        """R4: non-Anthropic seats are neither checked nor recorded."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
        monkeypatch.setattr(routine, "run_command", lambda *a, **k: (0, "position"))
        code, out = default_invoke_seat(("codex", "exec", "--skip-git-repo-check", "-"), "hi")
        assert (code, out) == (0, "position")
        assert not _ledger_path().exists()

    def test_claude_seat_records_the_flat_estimate(self, monkeypatch) -> None:
        monkeypatch.setattr(routine, "run_command", lambda *a, **k: (0, "position"))
        code, _ = default_invoke_seat(("claude", "-p", "{brief}"), "hi")
        assert code == 0
        entries = [json.loads(line) for line in _ledger_path().read_text().splitlines()]
        assert len(entries) == 1
        assert entries[0]["label"] == "seat:claude"
        assert entries[0]["cost_usd"] == pytest.approx(0.25)

    def test_missing_binary_is_not_recorded_as_spend(self, monkeypatch) -> None:
        monkeypatch.setattr(routine, "run_command", lambda *a, **k: (127, "claude: not found"))
        code, _ = default_invoke_seat(("claude", "-p", "{brief}"), "hi")
        assert code == 127
        assert not _ledger_path().exists()

    def test_failed_but_spawned_seat_still_records(self, monkeypatch) -> None:
        """An AMBIGUOUS failure may still have billed — overcount, never
        undercount (D5).

        Narrowed 2026-08-25 (#2311): this docstring used to read "a
        timeout or auth failure", but D5's text rules the ESTIMATE'S
        MAGNITUDE, not whether a call that never reached the provider
        records. A refusal-before-authentication is provably free and is
        now excluded; a timeout, which may have billed, still records.
        """
        monkeypatch.setattr(routine, "run_command", lambda *a, **k: (124, "timed out"))
        default_invoke_seat(("claude", "-p", "{brief}"), "hi")
        entries = [json.loads(line) for line in _ledger_path().read_text().splitlines()]
        assert len(entries) == 1

    def test_an_ambiguous_nonzero_exit_still_records(self, monkeypatch) -> None:
        """The conservative default survives the #2311 narrowing: only
        recognised never-authenticated output is excluded, not every
        failure."""
        monkeypatch.setattr(routine, "run_command", lambda *a, **k: (1, "segmentation fault"))
        default_invoke_seat(("claude", "-p", "{brief}"), "hi")
        entries = [json.loads(line) for line in _ledger_path().read_text().splitlines()]
        assert len(entries) == 1

    def test_a_never_authenticated_seat_records_nothing(self, monkeypatch) -> None:
        """#2311: three release-audit sittings each charged $0.25 against
        a claude seat whose OAuth session had expired. No token was ever
        consumed — auth precedes the request — so the cap was being eaten
        by calls that never reached the provider.

        The failure string is the one the CLI actually emitted, captured
        live on 2026-08-25.
        """
        monkeypatch.setattr(
            routine,
            "run_command",
            lambda *a, **k: (
                1,
                "Failed to authenticate: OAuth session expired and could not be refreshed",
            ),
        )
        code, _ = default_invoke_seat(("claude", "-p", "{brief}"), "hi")

        assert code == 1
        assert not _ledger_path().exists(), "an unauthenticated call is not spend"

    def test_the_cap_check_still_fires_before_an_auth_failure(self, monkeypatch) -> None:
        """Excluding auth failures from RECORDING must not weaken the
        pre-spawn refusal — the cap is checked before we know how the
        call will fail."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
        monkeypatch.setattr(
            routine,
            "run_command",
            lambda *a, **k: pytest.fail("subprocess spawned despite the spend refusal"),
        )
        with pytest.raises(SessionSpendCapError):
            default_invoke_seat(("claude", "-p", "{brief}"), "hi")


class TestRoutineUpfrontRefusal:
    def test_run_routine_at_cap_exits_3_before_touching_the_board(self, monkeypatch, capsys):
        """D6: no partial thread for a run that cannot afford its seats."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")

        class NeverBoard:
            def __init__(self) -> None:
                pytest.fail("board constructed despite the spend refusal")

        monkeypatch.setattr(routine, "Board", NeverBoard)
        with pytest.raises(SystemExit) as excinfo:
            routine.run_routine(
                CLEAN_RUN,
                run_check=lambda *a, **k: pytest.fail("check battery ran"),
            )
        assert excinfo.value.code == 3
        assert "REFUSED" in capsys.readouterr().out

    def test_dry_run_never_consults_the_ledger(self, monkeypatch, capsys) -> None:
        """A dry run makes no billable call, so a zero cap must not
        block it."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
        thread = routine.run_routine(CLEAN_RUN, run_check=lambda *a, **k: (0, "ok"), dry_run=True)
        assert thread.startswith("routine-clean-run-")


class TestReviewRefusal:
    def test_claude_seat_review_at_cap_raises(self, monkeypatch, tmp_path) -> None:
        """The seam's raise propagates through run_review — a hard
        refusal of the launch, not an 'absent' downgrade."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
        # Safety net: were the refusal to regress, fail loudly rather
        # than spawn a real (billable) claude subprocess in a unit test.
        monkeypatch.setattr(
            routine,
            "run_command",
            lambda *a, **k: pytest.fail("subprocess spawned despite the spend refusal"),
        )
        monkeypatch.setattr(
            review,
            "resolve_target",
            lambda *a, **k: {
                "mode": "branch",
                "description": "test target",
                "branch": "test-branch",
                "per_file": {"src/x.py": "diff"},
            },
        )
        with pytest.raises(SessionSpendCapError):
            review.run_review(tmp_path, seat="claude")
