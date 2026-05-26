"""Bulletin wiring tests for RunnerService.

Verifies the integration with the multi-actor-bulletin module:

- ``bulletin=None`` (default) preserves existing behavior exactly
- start() writes a ``running`` entry when bulletin is wired
- _finish_run() writes a terminal entry (``completed`` / ``failed``)
- A heartbeat asyncio task lives in the wrapper process while running
- The heartbeat task is cancelled when the run terminates
- Bulletin backend exceptions never propagate out of the runner
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from attune.bulletin import BulletinEntry
from attune.ops.runner import RunnerService, echo_command_builder


class _FakeBulletin:
    """Records every ``append`` call so tests can assert on the stream."""

    def __init__(self) -> None:
        self.entries: list[BulletinEntry] = []
        self.raise_on_next: Exception | None = None

    def append(self, entry: BulletinEntry) -> None:
        if self.raise_on_next is not None:
            exc = self.raise_on_next
            self.raise_on_next = None
            raise exc
        self.entries.append(entry)

    def read_active(self, *, stale_after_seconds: float = 90.0) -> list[BulletinEntry]:
        return list(self.entries)

    @property
    def statuses(self) -> list[str]:
        return [e.current_status for e in self.entries]

    @property
    def run_ids(self) -> list[str]:
        return [e.run_id for e in self.entries]


# ---------------------------------------------------------------------------
# bulletin=None preserves existing behavior
# ---------------------------------------------------------------------------


class TestBulletinDisabled:
    @pytest.mark.asyncio
    async def test_no_bulletin_runs_complete_normally(self) -> None:
        runner = RunnerService(command_builder=echo_command_builder)
        run = await runner.start("noop")
        # Wait for the executor task to finish.
        await _wait_for_terminal(runner, run.id)
        assert run.status == "completed"
        assert run.exit_code == 0

    @pytest.mark.asyncio
    async def test_no_bulletin_no_heartbeat_task(self) -> None:
        runner = RunnerService(command_builder=echo_command_builder)
        run = await runner.start("noop")
        # No heartbeat task should have been registered.
        assert run.id not in runner._heartbeat_tasks
        await _wait_for_terminal(runner, run.id)


# ---------------------------------------------------------------------------
# start() and _finish_run() bulletin writes
# ---------------------------------------------------------------------------


class TestStartAndFinishWrites:
    @pytest.mark.asyncio
    async def test_start_writes_running_entry(self) -> None:
        bulletin = _FakeBulletin()
        runner = RunnerService(
            command_builder=echo_command_builder,
            bulletin=bulletin,
            actor_id="test-actor",
        )
        run = await runner.start("noop")
        # The "running" record is the first entry.
        assert bulletin.statuses[0] == "running"
        assert bulletin.entries[0].run_id == run.id
        assert bulletin.entries[0].actor_id == "test-actor"
        assert bulletin.entries[0].workflow == "noop"
        await _wait_for_terminal(runner, run.id)

    @pytest.mark.asyncio
    async def test_finish_writes_completed_entry(self) -> None:
        bulletin = _FakeBulletin()
        runner = RunnerService(
            command_builder=echo_command_builder,
            bulletin=bulletin,
            actor_id="test-actor",
        )
        run = await runner.start("noop")
        await _wait_for_terminal(runner, run.id)
        # Last entry for this run_id should be terminal.
        terminal = [e for e in bulletin.entries if e.run_id == run.id][-1]
        assert terminal.current_status == "completed"

    @pytest.mark.asyncio
    async def test_failed_run_writes_failed_entry(self) -> None:
        bulletin = _FakeBulletin()

        def _failing_command(_workflow: str) -> tuple[str, ...]:
            import sys

            return (sys.executable, "-c", "import sys; sys.exit(1)")

        runner = RunnerService(
            command_builder=_failing_command,
            bulletin=bulletin,
            actor_id="test-actor",
        )
        run = await runner.start("noop")
        await _wait_for_terminal(runner, run.id)
        terminal = [e for e in bulletin.entries if e.run_id == run.id][-1]
        assert terminal.current_status == "failed"

    @pytest.mark.asyncio
    async def test_scope_propagated_to_bulletin(self) -> None:
        bulletin = _FakeBulletin()
        runner = RunnerService(
            command_builder=echo_command_builder,
            bulletin=bulletin,
            actor_id="test-actor",
        )
        run = await runner.start("noop", path="src/attune/ops/")
        await _wait_for_terminal(runner, run.id)
        # Every entry for the run should carry the scope.
        for entry in bulletin.entries:
            if entry.run_id == run.id:
                assert entry.scope == "src/attune/ops/"


# ---------------------------------------------------------------------------
# Heartbeat task lifecycle
# ---------------------------------------------------------------------------


class TestHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat_task_created_on_execute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The heartbeat task is registered before the subprocess starts."""
        bulletin = _FakeBulletin()
        # Build a runner with a fake executor that pauses long enough
        # for us to observe the heartbeat task being registered.
        observed: dict[str, Any] = {}

        async def _slow_executor(run: Any) -> None:
            run.status = "running"
            # Register a heartbeat manually inline so we mirror what
            # _execute does. But we want to test that _execute itself
            # registers — so just call the real _execute on a script
            # that's slow enough to observe.
            ...

        # Use the real _execute with a slow command instead.
        import sys

        def _slow_command(_workflow: str) -> tuple[str, ...]:
            return (sys.executable, "-c", "import time; time.sleep(0.5); print('done')")

        runner = RunnerService(
            command_builder=_slow_command,
            bulletin=bulletin,
            actor_id="test-actor",
        )
        run = await runner.start("noop")
        # Give the executor a moment to register the heartbeat task.
        await asyncio.sleep(0.05)
        observed["registered"] = run.id in runner._heartbeat_tasks
        await _wait_for_terminal(runner, run.id)
        assert observed["registered"] is True

    @pytest.mark.asyncio
    async def test_heartbeat_task_cancelled_on_finish(self) -> None:
        """After terminal status, the heartbeat task is gone."""
        bulletin = _FakeBulletin()
        runner = RunnerService(
            command_builder=echo_command_builder,
            bulletin=bulletin,
            actor_id="test-actor",
        )
        run = await runner.start("noop")
        await _wait_for_terminal(runner, run.id)
        assert run.id not in runner._heartbeat_tasks

    @pytest.mark.asyncio
    async def test_heartbeat_loop_writes_when_ticking(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Direct-drive the heartbeat loop with patched sleep."""
        bulletin = _FakeBulletin()
        runner = RunnerService(bulletin=bulletin, actor_id="test-actor")

        # Manually construct a Run we can drive (don't start a subprocess).
        from attune.ops.runner import Run

        run = Run(id="abc123", workflow="noop")
        run.status = "running"

        # Patch asyncio.sleep so the loop ticks instantly. After three
        # ticks, mark the run terminal so the loop returns cleanly.
        tick_count = {"n": 0}
        original_sleep = asyncio.sleep

        async def _fast_sleep(_seconds: float) -> None:
            tick_count["n"] += 1
            if tick_count["n"] >= 3:
                run.mark_done(0)
            # Yield once to let the loop iterate.
            await original_sleep(0)

        monkeypatch.setattr("attune.ops.runner.asyncio.sleep", _fast_sleep)

        await runner._heartbeat_loop(run)
        # The heartbeat should have written at least two "running" entries
        # (the third tick saw a terminal run and returned without writing).
        running_writes = [e for e in bulletin.entries if e.current_status == "running"]
        assert len(running_writes) >= 2


# ---------------------------------------------------------------------------
# Bulletin failure is non-fatal
# ---------------------------------------------------------------------------


class TestFailureToleration:
    @pytest.mark.asyncio
    async def test_bulletin_exception_doesnt_kill_run(self) -> None:
        """Backend bug must not propagate — bulletin is advisory."""
        bulletin = _FakeBulletin()
        bulletin.raise_on_next = RuntimeError("backend exploded")
        runner = RunnerService(
            command_builder=echo_command_builder,
            bulletin=bulletin,
            actor_id="test-actor",
        )
        # start() invokes _bulletin_write which would raise without
        # the try/except guard. Must not raise.
        run = await runner.start("noop")
        await _wait_for_terminal(runner, run.id)
        assert run.status == "completed"


# ---------------------------------------------------------------------------
# Actor identity
# ---------------------------------------------------------------------------


class TestActorIdentity:
    def test_explicit_actor_id_used(self) -> None:
        bulletin = _FakeBulletin()
        runner = RunnerService(bulletin=bulletin, actor_id="explicit-id", actor_kind="cli")
        assert runner._actor_id == "explicit-id"
        assert runner._actor_kind == "cli"

    def test_default_resolves_to_dashboard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # No CLAUDE_CODE_SESSION_ID env — the dashboard fallback fires.
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        bulletin = _FakeBulletin()
        runner = RunnerService(bulletin=bulletin)
        assert runner._actor_kind == "dashboard"
        assert runner._actor_id.startswith("dashboard-")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _wait_for_terminal(runner: RunnerService, run_id: str, timeout: float = 5.0) -> None:
    """Spin until the named run reaches a terminal status."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        run = runner.get(run_id)
        if run is not None and run.is_terminal:
            return
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"run {run_id} did not terminate within {timeout}s")
        await asyncio.sleep(0.02)
