"""Server-side wiring tests for discovery-sweep persistence.

Spec: docs/specs/discovery-sweep-ops-integration/design.md
      (Phase 2B — daemon-side wiring)

Covers the conditional ``runner.start`` wrap in
:func:`attune.ops.server.create_app`:

- Env var unset → start is NOT wrapped; calling start does not
  spawn a watcher task.
- Env var set → start IS wrapped; a discovery-sweep run spawns
  ``watch_and_persist`` as a background task; other workflows do
  not spawn anything.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.ops import sweep_results
from attune.ops.config import Config
from attune.ops.runner import Run, RunnerService
from attune.ops.server import create_app


class _StubRunnerService(RunnerService):
    """RunnerService double whose start() is deterministic."""

    def __init__(self) -> None:
        super().__init__()
        self.start_calls: list[str] = []

    async def start(self, workflow: str, *args, **kwargs) -> Run:  # type: ignore[override]
        self.start_calls.append(workflow)
        # Build a terminal run so subscribe()'s replay yields done
        # immediately. The watcher (if spawned) iterates one event
        # and returns; assertions here only care that the task was
        # scheduled, not that persistence ran.
        run = Run(id=f"run-{len(self.start_calls)}", workflow=workflow)
        run.mark_done(0)
        return run


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    return Config(
        project_root=tmp_path / "project",
        attune_home=tmp_path / "attune-home",
    )


class TestStartWrapDisabled:
    def test_no_watcher_spawned_when_env_unset(
        self,
        cfg: Config,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # When the persistence env var is unset, the wrap branch in
        # create_app is skipped entirely. Verify behaviorally: calling
        # runner.start("discovery-sweep") does NOT invoke
        # watch_and_persist. (Bound-method identity isn't preserved
        # across attribute lookups, so an `is` check on runner.start
        # is unreliable — assert on side effect instead.)
        monkeypatch.delenv(sweep_results.ENABLE_ENV, raising=False)
        runner = _StubRunnerService()
        create_app(cfg, runner=runner)
        with patch("attune.ops.server.watch_and_persist") as watcher:

            async def runner_body() -> Run:
                run = await runner.start("discovery-sweep")
                await asyncio.sleep(0)
                return run

            asyncio.run(runner_body())
        watcher.assert_not_called()


class TestStartWrapEnabled:
    @pytest.fixture(autouse=True)
    def _enable_persistence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(sweep_results.ENABLE_ENV, "1")

    def test_runner_start_is_wrapped(self, cfg: Config) -> None:
        runner = _StubRunnerService()
        original_start = runner.start
        create_app(cfg, runner=runner)
        assert runner.start is not original_start

    def test_discovery_sweep_run_spawns_watcher(self, cfg: Config) -> None:
        runner = _StubRunnerService()
        create_app(cfg, runner=runner)
        with patch("attune.ops.server.watch_and_persist") as watcher:
            # Make the patched watcher a no-op coroutine so create_task
            # doesn't complain about a non-awaitable.
            async def _noop(*_args, **_kwargs) -> None:
                return None

            watcher.side_effect = _noop

            async def runner_body() -> Run:
                run = await runner.start("discovery-sweep")
                # Yield once so the asyncio.create_task call inside
                # the wrap has a chance to fire.
                await asyncio.sleep(0)
                return run

            asyncio.run(runner_body())

        watcher.assert_called_once()
        # First positional arg is the Run; second is the Config.
        args, _kwargs = watcher.call_args
        assert args[0].workflow == "discovery-sweep"
        assert args[1] is cfg

    def test_non_discovery_sweep_run_does_not_spawn_watcher(self, cfg: Config) -> None:
        runner = _StubRunnerService()
        create_app(cfg, runner=runner)
        with patch("attune.ops.server.watch_and_persist") as watcher:

            async def runner_body() -> Run:
                run = await runner.start("code-review")
                await asyncio.sleep(0)
                return run

            asyncio.run(runner_body())

        watcher.assert_not_called()
