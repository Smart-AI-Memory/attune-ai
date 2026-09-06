"""Routine runner tests (agent-round-table Phase 3).

Seats and checks are injected fakes — no member CLI is invoked and
no real check battery runs. Board writes go against a REAL Redis
(same pattern as test_board.py) so the routine's thread shape is a
non-mocked receipt; tests skip when Redis is unreachable.
"""

from __future__ import annotations

import subprocess
import uuid
from unittest.mock import Mock

import pytest

from attune.roundtable import Board
from attune.roundtable.routine import (
    CLEAN_RUN,
    ROUTINES,
    RoutineSpec,
    default_invoke_seat,
    run_command,
    run_routine,
)


def _real_board_or_skip() -> Board:
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip("no reachable Redis on localhost:6379")
    board = Board(client=client)
    board.ensure_functions()
    return board


def _spec(**overrides) -> RoutineSpec:
    fields = {
        "name": "test-" + uuid.uuid4().hex[:8],
        "question": "Is the tree healthy?",
        "checks": (("noop", ("true",)),),
        "max_invocations": 4,
    }
    fields.update(overrides)
    return RoutineSpec(**fields)


def _ok_check(argv, timeout=0):
    return 0, "all green"


def _seat_by_kind(messages):
    return {(m.author, m.kind) for m in messages}


class TestRunRoutine:
    def test_full_run_posts_question_positions_synthesis(self) -> None:
        board = _real_board_or_skip()

        def invoke(recipe, brief):
            return 0, f"position from {recipe[0]}"

        thread = run_routine(_spec(), board=board, invoke_seat=invoke, run_check=_ok_check)
        msgs = board.read_thread(thread)
        kinds = _seat_by_kind(msgs)
        assert ("moderator", "question") in kinds
        for seat in ("claude", "antigravity", "codex"):
            assert (seat, "position") in kinds
        assert ("moderator", "synthesis") in kinds

    def test_thread_is_left_unpromoted_for_the_chair(self) -> None:
        """R8: a routine NEVER self-promotes."""
        board = _real_board_or_skip()
        thread = run_routine(
            _spec(), board=board, invoke_seat=lambda r, b: (0, "pos"), run_check=_ok_check
        )
        meta = board.client.hgetall(Board.thread_key(thread) + ":meta")
        assert "status" not in meta and "destination" not in meta

    def test_check_evidence_lands_in_the_question(self) -> None:
        board = _real_board_or_skip()

        def failing_check(argv, timeout=0):
            return 1, "3 failed, 1 passed"

        thread = run_routine(
            _spec(checks=(("suite", ("false",)),)),
            board=board,
            invoke_seat=lambda r, b: (0, "pos"),
            run_check=failing_check,
        )
        question = board.read_thread(thread)[0]
        assert "### suite: FAIL (exit 1)" in question.body
        assert "3 failed, 1 passed" in question.body

    def test_absent_seat_never_blocks_the_run(self) -> None:
        """R6: one dead CLI -> absent position, run completes."""
        board = _real_board_or_skip()

        def invoke(recipe, brief):
            if recipe[0] == "agy":
                return 127, "agy: not found"
            return 0, f"position from {recipe[0]}"

        thread = run_routine(_spec(), board=board, invoke_seat=invoke, run_check=_ok_check)
        msgs = board.read_thread(thread)
        absent = [m for m in msgs if m.extra.get("absent")]
        assert len(absent) == 1 and absent[0].author == "antigravity"
        assert absent[0].body.startswith("ABSENT — exit 127")
        assert ("moderator", "synthesis") in _seat_by_kind(msgs)

    def test_invocation_cap_halts_before_the_next_seat(self) -> None:
        """R5 / AC-5: invocation N+1 is not made; a halt is posted."""
        board = _real_board_or_skip()
        invoked: list[str] = []

        def invoke(recipe, brief):
            invoked.append(recipe[0])
            return 0, "pos"

        thread = run_routine(
            _spec(max_invocations=2), board=board, invoke_seat=invoke, run_check=_ok_check
        )
        assert invoked == ["claude", "agy"]  # codex (3rd) never invoked
        msgs = board.read_thread(thread)
        halts = [m for m in msgs if m.kind == "halt"]
        assert len(halts) == 1 and "cap (2) reached" in halts[0].body

    def test_unreachable_board_fails_fast_before_checks(self, capsys) -> None:
        """Live-run regression: a stale REDIS_URL must fail in seconds
        with a pointer — not after minutes of checks with a traceback."""
        redis = pytest.importorskip("redis")

        class DeadBoard:
            client = None

            def ensure_functions(self):
                raise redis.exceptions.ConnectionError("nodename nor servname")

        checks_run: list = []

        def recording_check(argv, timeout=0):
            checks_run.append(argv)
            return 0, "ok"

        with pytest.raises(SystemExit) as excinfo:
            run_routine(
                _spec(),
                board=DeadBoard(),
                invoke_seat=lambda r, b: (0, "pos"),
                run_check=recording_check,
            )
        assert excinfo.value.code == 2
        assert checks_run == []  # failed BEFORE the check battery
        out = capsys.readouterr().out
        assert "cannot reach the round-table board" in out
        assert "REDIS_URL" in out

    def test_dry_run_touches_nothing(self, capsys) -> None:
        def boom(*a, **k):
            raise AssertionError("no invocation in dry-run")

        run_routine(_spec(), board=None, invoke_seat=boom, run_check=_ok_check, dry_run=True)
        out = capsys.readouterr().out
        assert "[dry-run]" in out and "Is the tree healthy?" in out


class TestPlumbing:
    def test_clean_run_is_registered(self) -> None:
        assert ROUTINES["clean-run"] is CLEAN_RUN
        assert CLEAN_RUN.max_invocations == 4

    def test_run_command_missing_binary_is_absent_not_raise(self) -> None:
        code, out = run_command(("definitely-not-a-real-binary-xyz",))
        assert code == 127 and "not found" in out

    def test_run_command_is_keyless(self) -> None:
        code, out = run_command(("sh", "-c", 'echo "key=[$ANTHROPIC_API_KEY]"'))
        assert code == 0 and "key=[]" in out

    def test_default_invoke_substitutes_brief_or_uses_stdin(self) -> None:
        code, out = default_invoke_seat(("echo", "{brief}"), "hello table")
        assert code == 0 and out == "hello table"
        code, out = default_invoke_seat(("cat", "-"), "stdin brief")
        assert code == 0 and out == "stdin brief"

    def test_seats_run_provider_clean_but_keep_real_api_key(self, monkeypatch) -> None:
        """Live-run regression: seats must not inherit the parent
        session's BASE_URL/CLAUDE* vars (401 against its proxy), but a
        NON-EMPTY API key passes through (chair-authorized API path)."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-real")  # pragma: allowlist secret
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://parent-proxy")
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
        launch = Mock(return_value=subprocess.CompletedProcess([], 0, "position", ""))
        monkeypatch.setattr(subprocess, "run", launch)
        code, out = default_invoke_seat(("claude", "-p", "{brief}"), "fixture")
        assert code == 0 and out == "position"
        env = launch.call_args.kwargs["env"]
        assert env["ANTHROPIC_API_KEY"] == "sk-real"
        assert not {"ANTHROPIC_BASE_URL", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"} & env.keys()
        launch.assert_called_once()

    def test_seat_reply_keeps_head_and_drops_stderr_on_success(self) -> None:
        """Live-run regression: tail-truncation cut a position off
        mid-sentence, and CLI stderr warnings polluted board bodies."""
        code, out = default_invoke_seat(
            ("sh", "-c", 'echo "POSITION first"; echo "warning noise" >&2'), "unused"
        )
        assert code == 0 and out == "POSITION first"
        code, out = default_invoke_seat(
            ("sh", "-c", 'echo partial; echo "the diagnosis" >&2; exit 3'), "unused"
        )
        assert code == 3 and "the diagnosis" in out

    def test_seats_drop_empty_api_key(self, monkeypatch) -> None:
        """An EMPTY key must be removed, not passed through — empty
        401s the claude CLI instead of letting stored auth kick in."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        launch = Mock(return_value=subprocess.CompletedProcess([], 0, "position", ""))
        monkeypatch.setattr(subprocess, "run", launch)
        code, out = default_invoke_seat(("claude", "-p", "{brief}"), "fixture")
        assert code == 0 and out == "position"
        assert "ANTHROPIC_API_KEY" not in launch.call_args.kwargs["env"]
        launch.assert_called_once()

    def test_synthesis_failure_is_visible_on_the_thread(self) -> None:
        """Live-run regression: a failed synthesis must not read as a
        successful digest-less run."""
        board = _real_board_or_skip()

        def invoke(recipe, brief):
            if "moderator of a round-table routine" in brief:
                return 1, "Failed to authenticate"
            return 0, f"position from {recipe[0]}"

        thread = run_routine(_spec(), board=board, invoke_seat=invoke, run_check=_ok_check)
        msgs = board.read_thread(thread)
        assert not any(m.kind == "synthesis" for m in msgs)
        halts = [m for m in msgs if m.kind == "halt"]
        assert len(halts) == 1 and "synthesis invocation failed (exit 1)" in halts[0].body
