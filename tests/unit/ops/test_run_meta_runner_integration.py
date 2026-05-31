"""Integration tests for ATTUNE_RUN_META side-channel in the runner.

Covers ``RunnerService.handle_stdout_line``'s parsing + stashing
behavior and the end-to-end ``_execute`` env-var wiring. The pure
``run_meta_stdout`` formatter / parser surface is tested in
``test_run_meta_stdout.py``.

Spec: docs/specs/sdk-error-message-fidelity/ Phase 3b
"""

from __future__ import annotations

import asyncio
import base64
import sys

import pytest

pytest.importorskip("fastapi")

from attune.ops.runner import Run, RunnerService  # noqa: E402

# ---------------------------------------------------------------------------
# handle_stdout_line — parses marker lines + stashes on Run, filters log
# ---------------------------------------------------------------------------


def _make_runner() -> RunnerService:
    """Lightweight runner (no executor, no persistence) for line-routing tests."""
    return RunnerService(command_builder=lambda _name: ("true",))


def _new_run() -> Run:
    return Run(id="testrunid01", workflow="code-review")


class TestHandleStdoutLineStashing:
    def test_sdk_error_kind_marker_stashes_on_run(self):
        runner = _make_runner()
        run = _new_run()
        runner.handle_stdout_line(run, "ATTUNE_RUN_META sdk_error_kind=api_quota")
        assert run.sdk_error_kind == "api_quota"
        # Marker line MUST NOT appear in the visible log
        assert "ATTUNE_RUN_META" not in "\n".join(run.lines)

    def test_sdk_stderr_b64_marker_decodes_and_stashes(self):
        runner = _make_runner()
        run = _new_run()
        original = "anthropic.AuthError: 401 - bad key\nrequest_id: req_xyz\n"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        runner.handle_stdout_line(run, f"ATTUNE_RUN_META sdk_stderr_b64={encoded}")
        assert run.sdk_stderr == original
        assert "ATTUNE_RUN_META" not in "\n".join(run.lines)

    def test_version_line_is_silently_consumed(self):
        runner = _make_runner()
        run = _new_run()
        runner.handle_stdout_line(run, "ATTUNE_RUN_META_VERSION 1")
        # No log entry, no state change on Run
        assert run.lines == []
        assert run.sdk_error_kind is None
        assert run.sdk_stderr is None

    def test_unknown_marker_key_is_silently_dropped(self):
        runner = _make_runner()
        run = _new_run()
        # Looks like a valid marker line shape but the key isn't in
        # _ALLOWED_KEYS — parser returns None, runner drops silently.
        runner.handle_stdout_line(run, "ATTUNE_RUN_META not_a_real_key=foo")
        assert run.lines == []
        assert run.sdk_error_kind is None
        assert run.sdk_stderr is None

    def test_malformed_marker_is_silently_dropped(self):
        runner = _make_runner()
        run = _new_run()
        # Marker prefix but garbage after — parser returns None.
        runner.handle_stdout_line(run, "ATTUNE_RUN_META no equals here")
        assert run.lines == []

    def test_marker_lines_never_pollute_log_buffer(self):
        """End-to-end: a sequence of mixed real-log + marker lines
        produces a log buffer with ONLY the real-log lines."""
        runner = _make_runner()
        run = _new_run()
        runner.handle_stdout_line(run, "starting code-review")
        runner.handle_stdout_line(run, "ATTUNE_RUN_META_VERSION 1")
        runner.handle_stdout_line(run, "scanning files...")
        runner.handle_stdout_line(run, "ATTUNE_RUN_META sdk_error_kind=auth")
        runner.handle_stdout_line(
            run,
            f"ATTUNE_RUN_META sdk_stderr_b64={base64.b64encode(b'oops').decode('ascii')}",
        )
        runner.handle_stdout_line(run, "done")
        # All marker lines filtered out
        assert run.lines == ["starting code-review", "scanning files...", "done"]
        # But the side-channel metadata reached the Run
        assert run.sdk_error_kind == "auth"
        assert run.sdk_stderr == "oops"

    def test_empty_value_does_not_clobber_existing_stash(self):
        """A marker with an empty value (e.g. ``sdk_error_kind=``)
        shouldn't blank out a previously-set field. The parser returns
        an empty-value dict; the runner gates on truthiness before
        assigning."""
        runner = _make_runner()
        run = _new_run()
        runner.handle_stdout_line(run, "ATTUNE_RUN_META sdk_error_kind=api_quota")
        runner.handle_stdout_line(run, "ATTUNE_RUN_META sdk_error_kind=")
        # First value preserved, second (empty) didn't blank it
        assert run.sdk_error_kind == "api_quota"

    def test_invalid_b64_decode_does_not_clobber_existing_stash(self):
        runner = _make_runner()
        run = _new_run()
        original = "real stderr text"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        runner.handle_stdout_line(run, f"ATTUNE_RUN_META sdk_stderr_b64={encoded}")
        # Now send a malformed b64 marker — must not blank the stash
        runner.handle_stdout_line(run, "ATTUNE_RUN_META sdk_stderr_b64=!!notb64!!")
        assert run.sdk_stderr == original


# ---------------------------------------------------------------------------
# _execute — verify ATTUNE_RUN_META_EMIT=1 is set in subprocess env
# ---------------------------------------------------------------------------


def _echo_env_cmd(workflow: str) -> tuple[str, ...]:
    """Subprocess that prints whether ATTUNE_RUN_META_EMIT is set in its env."""
    script = (
        "import os; "
        "v = os.environ.get('ATTUNE_RUN_META_EMIT', 'MISSING'); "
        f"print(f'WORKFLOW={workflow}'); "
        "print(f'ENV_RUN_META_EMIT={v}')"
    )
    return (sys.executable, "-c", script)


@pytest.mark.asyncio
async def test_execute_sets_run_meta_emit_env_var(tmp_path):
    """The subprocess spawned by _execute receives ATTUNE_RUN_META_EMIT=1
    in its environment so _print_workflow_result actually emits the
    side-channel lines."""
    svc = RunnerService(command_builder=_echo_env_cmd, persistence_dir=None)
    run = await svc.start("code-review")
    # Poll until terminal (no asyncio.wait — small fast subprocess)
    deadline = asyncio.get_running_loop().time() + 5.0
    while True:
        live = svc.get(run.id)
        assert live is not None
        if live.is_terminal:
            break
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail(f"run {run.id} did not finish within 5s")
        await asyncio.sleep(0.02)
    # The subprocess's printed line confirms the env var was set
    joined = "\n".join(live.lines)
    assert "ENV_RUN_META_EMIT=1" in joined


# ---------------------------------------------------------------------------
# End-to-end: subprocess emits ATTUNE_RUN_META lines, runner consumes them
# ---------------------------------------------------------------------------


def _emit_meta_cmd(workflow: str) -> tuple[str, ...]:
    """Subprocess that emits a real ATTUNE_RUN_META sequence —
    simulates a failed SDK workflow's _print_workflow_result output."""
    script = (
        "import base64; "
        "msg = 'You have reached your API usage limits.'; "
        "encoded = base64.b64encode(msg.encode()).decode(); "
        f"print('running {workflow}'); "
        "print('ATTUNE_RUN_META_VERSION 1'); "
        "print('ATTUNE_RUN_META sdk_error_kind=api_quota'); "
        "print(f'ATTUNE_RUN_META sdk_stderr_b64={encoded}'); "
        "print('done')"
    )
    return (sys.executable, "-c", script)


@pytest.mark.asyncio
async def test_execute_end_to_end_stashes_marker_metadata(tmp_path):
    """Subprocess emits ATTUNE_RUN_META lines; runner parses + stashes
    on Run, filters from the visible log."""
    svc = RunnerService(command_builder=_emit_meta_cmd, persistence_dir=None)
    run = await svc.start("code-review")
    deadline = asyncio.get_running_loop().time() + 5.0
    while True:
        live = svc.get(run.id)
        assert live is not None
        if live.is_terminal:
            break
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail(f"run {run.id} did not finish within 5s")
        await asyncio.sleep(0.02)
    # Metadata reached the Run via the side-channel
    assert live.sdk_error_kind == "api_quota"
    assert live.sdk_stderr == "You have reached your API usage limits."
    # User-facing log contains the real output but NOT real marker lines.
    # NOTE: the run's first log entry is the ``$ <full command>`` echo,
    # which here includes the inline Python script's literal
    # ``ATTUNE_RUN_META`` string-content — that's expected and benign.
    # The check that matters: no STANDALONE log line should START with
    # ``ATTUNE_RUN_META`` (a real marker that leaked through unfiltered).
    real_log_lines = [line for line in live.lines if not line.startswith("$ ")]
    assert "running code-review" in real_log_lines
    assert "done" in real_log_lines
    for line in real_log_lines:
        assert not line.startswith("ATTUNE_RUN_META"), f"marker line leaked into log: {line!r}"
