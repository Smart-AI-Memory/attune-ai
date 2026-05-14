"""Unit tests for the discovery-sweep persistence watcher.

Spec: docs/specs/discovery-sweep-ops-integration/design.md
      (Phase 2B — daemon-side wiring)

Covers the watcher's subscription + persistence semantics:

- No-op for workflows other than ``discovery-sweep``.
- No-op when ``exit_code != 0`` (failed sweep).
- No-op when no scope path is available (today's main has no
  ``Run.path`` attribute; persistence activates once PR #324 lands).
- On success with a known scope path, calls
  ``sweep_results.persist_from_lines`` with the right args.
- All exceptions are caught + logged, never propagated.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.ops.config import Config
from attune.ops.runner import Run
from attune.ops.sweep_results_watcher import watch_and_persist
from attune.workflows.discovery_sweep import ds_stdout


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    return Config(
        project_root=tmp_path / "project",
        attune_home=tmp_path / "attune-home",
    )


def _make_completed_run(
    *,
    workflow: str = "discovery-sweep",
    exit_code: int = 0,
    lines: list[str] | None = None,
    path: str | None = "src/",
) -> Run:
    """Build a Run that's already in terminal state.

    ``subscribe()`` replays buffered state, so a terminal run yields
    its ``done`` event immediately — the test doesn't have to drive
    a real subprocess.
    """
    run = Run(id="test-run", workflow=workflow)
    if lines:
        run.lines = list(lines)
    run.mark_done(exit_code)
    if path is not None:
        # Simulate PR #324's Run.path attribute via plain assignment.
        # Production code uses getattr(run, "path", None) which works
        # whether the attribute is there or not.
        run.path = path  # type: ignore[attr-defined]
    return run


def _attune_ds_lines(payload: dict) -> list[str]:
    return [
        f"ATTUNE_DS_VERSION {ds_stdout.VERSION}",
        "ATTUNE_DS source_started fake ts=2026-05-13T12:00:00+00:00",
        "ATTUNE_DS source_finished fake ts=2026-05-13T12:00:05+00:00 findings=0",
        f"ATTUNE_DS final {json.dumps(payload)}",
    ]


# ---------------------------------------------------------------------------
# Workflow-name filtering
# ---------------------------------------------------------------------------


class TestWorkflowFiltering:
    def test_non_discovery_sweep_run_is_no_op(self, cfg: Config) -> None:
        # Watcher must not subscribe or write anything for a non-target run.
        run = _make_completed_run(workflow="code-review", path="src/")
        with patch("attune.ops.sweep_results_watcher.sweep_results.persist_from_lines") as persist:
            asyncio.run(watch_and_persist(run, cfg))
        persist.assert_not_called()


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestSuccessPersists:
    def test_successful_sweep_with_known_path_persists(self, cfg: Config) -> None:
        payload = {
            "queue": [{"source": "x"}],
            "questions": [],
            "rejected": [],
            "metadata": {},
        }
        run = _make_completed_run(
            exit_code=0,
            lines=_attune_ds_lines(payload),
            path="src/",
        )
        asyncio.run(watch_and_persist(run, cfg))
        # Persistence wrote a sidecar at the scope-hashed path.
        from attune.ops import sweep_results as sr

        digest = sr.scope_hash("src/")
        assert sr.read_result(digest, cfg) == payload


# ---------------------------------------------------------------------------
# No-op cases
# ---------------------------------------------------------------------------


class TestNoOpCases:
    def test_failed_run_does_not_persist(self, cfg: Config) -> None:
        # exit_code != 0 → don't persist a half-emitted stream.
        run = _make_completed_run(
            exit_code=1,
            lines=_attune_ds_lines({"queue": [], "questions": [], "rejected": [], "metadata": {}}),
            path="src/",
        )
        with patch("attune.ops.sweep_results_watcher.sweep_results.persist_from_lines") as persist:
            asyncio.run(watch_and_persist(run, cfg))
        persist.assert_not_called()

    def test_run_without_path_attribute_does_not_persist(self, cfg: Config) -> None:
        # Today's main has no Run.path. Watcher must skip cleanly,
        # not raise an AttributeError or persist with a junk hash.
        run = _make_completed_run(
            exit_code=0,
            lines=_attune_ds_lines({"queue": [], "questions": [], "rejected": [], "metadata": {}}),
            path=None,
        )
        with patch("attune.ops.sweep_results_watcher.sweep_results.persist_from_lines") as persist:
            asyncio.run(watch_and_persist(run, cfg))
        persist.assert_not_called()

    def test_run_with_empty_path_does_not_persist(self, cfg: Config) -> None:
        # Even if Run.path exists but is "" — same skip path. The
        # discovery-sweep workflow itself errors on empty path, so
        # the run would have failed too, but defense in depth.
        run = _make_completed_run(
            exit_code=0,
            lines=_attune_ds_lines({"queue": [], "questions": [], "rejected": [], "metadata": {}}),
            path="",
        )
        with patch("attune.ops.sweep_results_watcher.sweep_results.persist_from_lines") as persist:
            asyncio.run(watch_and_persist(run, cfg))
        persist.assert_not_called()


# ---------------------------------------------------------------------------
# Fault tolerance
# ---------------------------------------------------------------------------


class TestFaultTolerance:
    def test_persist_exception_is_caught(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        # persist_from_lines() raising must not propagate — observability
        # never breaks the dashboard.
        run = _make_completed_run(
            exit_code=0,
            lines=_attune_ds_lines({"queue": [], "questions": [], "rejected": [], "metadata": {}}),
            path="src/",
        )
        with patch(
            "attune.ops.sweep_results_watcher.sweep_results.persist_from_lines",
            side_effect=OSError("disk full"),
        ):
            with caplog.at_level("ERROR"):
                asyncio.run(watch_and_persist(run, cfg))
        # Logged the failure for the operator.
        assert any("persistence failed" in r.getMessage() for r in caplog.records)

    def test_subscription_exception_is_caught(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Run.subscribe() doesn't realistically raise (it's a generator
        # backed by an asyncio.Queue), but the watcher's defensive
        # try/except needs coverage. Replace subscribe with a function
        # that raises and assert: no exception propagates, persistence
        # is skipped, the failure is logged at exception level.
        class _BrokenRun:
            workflow = "discovery-sweep"
            id = "broken-1"
            exit_code = 0
            lines: list[str] = []

            def subscribe(self):
                raise RuntimeError("queue collapsed")

        with patch("attune.ops.sweep_results_watcher.sweep_results.persist_from_lines") as persist:
            with caplog.at_level("ERROR"):
                asyncio.run(watch_and_persist(_BrokenRun(), cfg))  # type: ignore[arg-type]
        persist.assert_not_called()
        assert any("subscription failed" in r.getMessage() for r in caplog.records)

    def test_no_final_line_logs_info_but_no_crash(
        self, cfg: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Run completed successfully but emission was disabled — no
        # ATTUNE_DS final line in run.lines. Watcher logs "no final
        # line" at info level, does not persist, does not raise.
        run = _make_completed_run(
            exit_code=0,
            lines=["## Queue (0 findings)", "## Questions (0 findings)"],
            path="src/",
        )
        with caplog.at_level("INFO"):
            asyncio.run(watch_and_persist(run, cfg))
        # No sidecar written.
        from attune.ops import sweep_results as sr

        digest = sr.scope_hash("src/")
        assert sr.read_result(digest, cfg) is None
        assert any("no ATTUNE_DS final line" in r.getMessage() for r in caplog.records)
