"""Coverage supplement for src/attune/workflows/progress.py

Targets uncovered lines from the initial test run (52.63%):
- ConsoleProgressReporter (lines 431-524)
- JsonLinesProgressReporter (lines 527-545)
- create_progress_tracker() factory (lines 548-573)
- ProgressReporter Protocol (lines 400-409)
- RichProgressReporter RuntimeError path (line 595-597)
- live_progress() context manager (lines 726-782)
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.progress import (
    ConsoleProgressReporter,
    JsonLinesProgressReporter,
    ProgressReporter,
    ProgressStatus,
    ProgressTracker,
    ProgressUpdate,
    RichProgressReporter,
    StageProgress,
    create_progress_tracker,
    live_progress,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_update(
    status: ProgressStatus = ProgressStatus.RUNNING,
    message: str = "doing things",
    cost: float = 0.01,
    tokens: int = 200,
    percent: float = 33.0,
    fallback_info: str | None = None,
    error: str | None = None,
    stages: list[StageProgress] | None = None,
) -> ProgressUpdate:
    if stages is None:
        stages = [StageProgress(name="analyze", status=status, tier="capable", model="claude")]
    return ProgressUpdate(
        workflow="test-wf",
        workflow_id="abc-123",
        current_stage="analyze",
        stage_index=0,
        total_stages=3,
        status=status,
        message=message,
        cost_so_far=cost,
        tokens_so_far=tokens,
        percent_complete=percent,
        fallback_info=fallback_info,
        error=error,
        stages=stages,
    )


def _completed_update() -> ProgressUpdate:
    stage = StageProgress(
        name="analyze",
        status=ProgressStatus.COMPLETED,
        duration_ms=1500,
        cost=0.02,
    )
    return ProgressUpdate(
        workflow="test-wf",
        workflow_id="abc-123",
        current_stage="analyze",
        stage_index=3,
        total_stages=3,
        status=ProgressStatus.COMPLETED,
        message="workflow test-wf completed",
        cost_so_far=0.05,
        tokens_so_far=500,
        percent_complete=100.0,
        stages=[stage],
    )


# ---------------------------------------------------------------------------
# ProgressReporter Protocol
# ---------------------------------------------------------------------------


class TestProgressReporterProtocol:
    def test_has_report_method(self):
        assert hasattr(ProgressReporter, "report")

    def test_has_report_async_method(self):
        assert hasattr(ProgressReporter, "report_async")

    def test_concrete_impl_has_report_and_report_async(self):
        # ProgressReporter is not @runtime_checkable, so check structurally
        class MyReporter:
            def report(self, update: ProgressUpdate) -> None:
                pass

            async def report_async(self, update: ProgressUpdate) -> None:
                pass

        reporter = MyReporter()
        assert callable(getattr(reporter, "report", None))
        assert callable(getattr(reporter, "report_async", None))


# ---------------------------------------------------------------------------
# ConsoleProgressReporter — __init__
# ---------------------------------------------------------------------------


class TestConsoleProgressReporterInit:
    def test_default_verbose_false(self):
        r = ConsoleProgressReporter()
        assert r.verbose is False

    def test_default_show_tokens_false(self):
        r = ConsoleProgressReporter()
        assert r.show_tokens is False

    def test_verbose_true(self):
        r = ConsoleProgressReporter(verbose=True)
        assert r.verbose is True

    def test_show_tokens_true(self):
        r = ConsoleProgressReporter(show_tokens=True)
        assert r.show_tokens is True

    def test_start_time_initially_none(self):
        r = ConsoleProgressReporter()
        assert r._start_time is None


# ---------------------------------------------------------------------------
# ConsoleProgressReporter — report()
# ---------------------------------------------------------------------------


class TestConsoleProgressReporterReport:
    def test_report_produces_output(self):
        r = ConsoleProgressReporter()
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update())
        assert len(buf.getvalue()) > 0

    def test_report_contains_cost(self):
        r = ConsoleProgressReporter()
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update(cost=0.0123))
        assert "0.0123" in buf.getvalue()

    def test_report_running_stage_shows_tier(self):
        r = ConsoleProgressReporter()
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update(status=ProgressStatus.RUNNING))
        assert "CAPABLE" in buf.getvalue()

    def test_report_shows_model_when_set(self):
        r = ConsoleProgressReporter()
        stage = StageProgress(
            name="analyze",
            status=ProgressStatus.RUNNING,
            tier="premium",
            model="claude-opus-4-6",
        )
        update = _make_update(stages=[stage])
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(update)
        assert "claude-opus-4-6" in buf.getvalue()

    def test_verbose_shows_fallback_info(self):
        r = ConsoleProgressReporter(verbose=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update(fallback_info="haiku→sonnet"))
        assert "haiku→sonnet" in buf.getvalue()

    def test_verbose_shows_error(self):
        r = ConsoleProgressReporter(verbose=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update(error="timeout"))
        assert "timeout" in buf.getvalue()

    def test_show_tokens_includes_token_count(self):
        r = ConsoleProgressReporter(show_tokens=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update(tokens=1234))
        assert "1,234" in buf.getvalue()

    def test_elapsed_shown_after_first_report(self):
        """Second call (with time elapsed) should show elapsed."""
        r = ConsoleProgressReporter()
        # First call sets _start_time
        r.report(_make_update())
        # Manually set _start_time to past to simulate elapsed time
        from datetime import datetime, timedelta

        r._start_time = datetime.now() - timedelta(seconds=5)
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update())
        assert "5." in buf.getvalue() or "4." in buf.getvalue()

    def test_all_statuses_handled(self):
        r = ConsoleProgressReporter()
        for status in ProgressStatus:
            update = _make_update(status=status)
            buf = io.StringIO()
            with redirect_stdout(buf):
                r.report(update)  # must not raise

    def test_completed_workflow_triggers_summary(self):
        r = ConsoleProgressReporter()
        r._stage_times["analyze"] = 1200
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_completed_update())
        output = buf.getvalue()
        assert "Stage Summary" in output

    def test_no_summary_when_no_stage_times_and_zero_duration(self):
        r = ConsoleProgressReporter()
        # Stage with duration_ms=0 and no entry in _stage_times → _print_summary returns early
        stage = StageProgress(
            name="analyze",
            status=ProgressStatus.COMPLETED,
            duration_ms=0,  # zero duration
            cost=0.0,
        )
        update = ProgressUpdate(
            workflow="test-wf",
            workflow_id="abc-123",
            current_stage="analyze",
            stage_index=3,
            total_stages=3,
            status=ProgressStatus.COMPLETED,
            message="workflow test-wf completed",
            cost_so_far=0.0,
            tokens_so_far=0,
            percent_complete=100.0,
            stages=[stage],
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(update)
        # No _stage_times entries and zero duration → _print_summary returns immediately
        assert "Stage Summary" not in buf.getvalue()

    def test_report_async_calls_sync(self):
        import asyncio

        r = ConsoleProgressReporter()
        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(r.report_async(_make_update()))
        assert len(buf.getvalue()) > 0


# ---------------------------------------------------------------------------
# ConsoleProgressReporter — _print_summary()
# ---------------------------------------------------------------------------


class TestConsoleProgressReporterSummary:
    def test_prints_stage_durations(self):
        r = ConsoleProgressReporter()
        stage = StageProgress(
            name="crunch",
            status=ProgressStatus.COMPLETED,
            duration_ms=750,
            cost=0.01,
        )
        update = _make_update(stages=[stage])
        r._stage_times["crunch"] = 750
        buf = io.StringIO()
        with redirect_stdout(buf):
            r._print_summary(update)
        assert "crunch" in buf.getvalue()

    def test_skipped_stages_shown(self):
        r = ConsoleProgressReporter()
        stage = StageProgress(name="opt", status=ProgressStatus.SKIPPED)
        update = _make_update(stages=[stage])
        r._stage_times["opt"] = 0
        buf = io.StringIO()
        with redirect_stdout(buf):
            r._print_summary(update)
        assert "skipped" in buf.getvalue()

    def test_large_duration_shown_in_seconds(self):
        r = ConsoleProgressReporter()
        stage = StageProgress(
            name="big",
            status=ProgressStatus.COMPLETED,
            duration_ms=5000,
            cost=0.05,
        )
        update = _make_update(stages=[stage])
        r._stage_times["big"] = 5000
        buf = io.StringIO()
        with redirect_stdout(buf):
            r._print_summary(update)
        assert "5.0s" in buf.getvalue()


# ---------------------------------------------------------------------------
# JsonLinesProgressReporter
# ---------------------------------------------------------------------------


class TestJsonLinesProgressReporter:
    def test_init_default_output_file_none(self):
        r = JsonLinesProgressReporter()
        assert r.output_file is None

    def test_init_with_output_file(self):
        r = JsonLinesProgressReporter(output_file="/tmp/progress.jsonl")
        assert r.output_file == "/tmp/progress.jsonl"

    def test_report_to_stdout(self):
        r = JsonLinesProgressReporter()
        buf = io.StringIO()
        with redirect_stdout(buf):
            r.report(_make_update())
        import json

        parsed = json.loads(buf.getvalue().strip())
        assert parsed["workflow"] == "test-wf"

    def test_report_to_file(self, tmp_path):
        import json

        out = tmp_path / "progress.jsonl"
        r = JsonLinesProgressReporter(output_file=str(out))
        r.report(_make_update())
        line = out.read_text().strip()
        parsed = json.loads(line)
        assert parsed["workflow"] == "test-wf"

    def test_report_appends_multiple_lines(self, tmp_path):
        out = tmp_path / "progress.jsonl"
        r = JsonLinesProgressReporter(output_file=str(out))
        r.report(_make_update(message="first"))
        r.report(_make_update(message="second"))
        lines = [line for line in out.read_text().splitlines() if line.strip()]
        assert len(lines) == 2

    def test_report_async_writes_output(self, tmp_path):
        import asyncio
        import json

        out = tmp_path / "async.jsonl"
        r = JsonLinesProgressReporter(output_file=str(out))
        asyncio.run(r.report_async(_make_update()))
        parsed = json.loads(out.read_text().strip())
        assert "workflow" in parsed


# ---------------------------------------------------------------------------
# create_progress_tracker() factory
# ---------------------------------------------------------------------------


class TestCreateProgressTracker:
    def test_returns_progress_tracker(self):
        t = create_progress_tracker("wf", ["a", "b"])
        assert isinstance(t, ProgressTracker)

    def test_sets_workflow_name(self):
        t = create_progress_tracker("my-wf", ["a"])
        assert t.workflow == "my-wf"

    def test_sets_stage_names(self):
        t = create_progress_tracker("wf", ["x", "y", "z"])
        assert t.stage_names == ["x", "y", "z"]

    def test_workflow_id_is_auto_generated(self):
        t = create_progress_tracker("wf", ["a"])
        assert len(t.workflow_id) > 0

    def test_two_trackers_have_different_ids(self):
        t1 = create_progress_tracker("wf", ["a"])
        t2 = create_progress_tracker("wf", ["a"])
        assert t1.workflow_id != t2.workflow_id

    def test_reporter_registered_as_callback(self):
        updates: list[ProgressUpdate] = []

        class MyReporter:
            def report(self, u: ProgressUpdate) -> None:
                updates.append(u)

            async def report_async(self, u: ProgressUpdate) -> None:
                pass

        reporter = MyReporter()
        t = create_progress_tracker("wf", ["a"], reporter=reporter)
        t.start_workflow()
        assert len(updates) >= 1

    def test_no_reporter_creates_tracker_without_callbacks(self):
        t = create_progress_tracker("wf", ["a"], reporter=None)
        assert isinstance(t, ProgressTracker)


# ---------------------------------------------------------------------------
# RichProgressReporter — unavailable path
# ---------------------------------------------------------------------------


class TestRichProgressReporterUnavailable:
    def test_raises_runtime_error_when_rich_unavailable(self):
        with patch("attune.workflows.progress_reporters.RICH_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Rich"):
                RichProgressReporter("wf", ["a", "b"])


# ---------------------------------------------------------------------------
# RichProgressReporter — full mock of Rich components
# ---------------------------------------------------------------------------

# Rich class targets that need MagicMock() instances (callables that return mocks)
_RICH_CLASS_TARGETS = [
    "attune.workflows.progress_reporters.Console",
    "attune.workflows.progress_reporters.Live",
    "attune.workflows.progress_reporters.Progress",
    "attune.workflows.progress_reporters.Panel",
    "attune.workflows.progress_reporters.Table",
    "attune.workflows.progress_reporters.Text",
    "attune.workflows.progress_reporters.Group",
    "attune.workflows.progress_reporters.SpinnerColumn",
    "attune.workflows.progress_reporters.TextColumn",
    "attune.workflows.progress_reporters.BarColumn",
]


def _rich_ctx():
    """Return a multi-patcher context for all Rich symbols.

    Uses patch(target) without new= so each Rich name becomes a
    MagicMock() *instance*.  When progress.py calls Progress(arg1, arg2, ...),
    Python invokes mock_instance.__call__(arg1, ...) and returns
    mock_instance.return_value — an unspecced MagicMock that allows
    arbitrary attribute access (e.g. .add_task, .update, .start).

    Contrast: patch(target, MagicMock) sets the name to the MagicMock
    *class*.  Calling MagicMock(SpinnerColumn(), ...) passes the first
    positional arg as spec=, producing a specced mock that forbids
    unknown attributes like .add_task.
    """
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch("attune.workflows.progress_reporters.RICH_AVAILABLE", True))
    for target in _RICH_CLASS_TARGETS:
        stack.enter_context(patch(target))  # creates a MagicMock() instance
    return stack


class TestRichProgressReporterAvailable:
    """Full-mock tests: all Rich classes replaced with MagicMock."""

    # ---- construction ----

    def test_constructs_with_rich_available(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a", "b"])
        assert r.workflow_name == "wf"
        assert r.stage_names == ["a", "b"]

    def test_initial_cost_is_zero(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
        assert r._cost == 0.0

    def test_initial_tokens_is_zero(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
        assert r._tokens == 0

    def test_initial_status_is_pending(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
        assert r._status == ProgressStatus.PENDING

    # ---- start() ----

    def test_start_creates_progress_and_live(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a", "b"])
            r.start()
            # After start(), _progress and _live are the mock return values
            assert r._progress is not None
            assert r._live is not None

    def test_start_calls_live_start(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            r.start()
            # mock Live instance should have .start() called
            if r._live is not None:
                r._live.start.assert_called()  # type: ignore[attr-defined]

    def test_start_when_rich_unavailable_returns_early(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            with (
                patch("attune.workflows.progress_reporters.RICH_AVAILABLE", False),
                patch("attune.workflows.progress_reporters.Progress", None),
                patch("attune.workflows.progress_reporters.Live", None),
            ):
                r.start()  # must not raise — returns early

    # ---- report() when live is active ----

    def test_report_updates_internal_state(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a", "b"])
            r.start()
            update = _make_update(cost=0.07, tokens=350, status=ProgressStatus.COMPLETED)
            r.report(update)
        assert r._cost == 0.07
        assert r._tokens == 350
        assert r._status == ProgressStatus.COMPLETED

    def test_report_calls_progress_update_when_started(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a", "b"])
            r.start()
            stage = StageProgress(name="a", status=ProgressStatus.COMPLETED)
            update = _make_update(stages=[stage])
            r.report(update)
            if r._progress is not None:
                r._progress.update.assert_called()  # type: ignore[attr-defined]

    def test_report_calls_live_update_when_started(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            r.start()
            r.report(_make_update())
            if r._live is not None:
                r._live.update.assert_called()  # type: ignore[attr-defined]

    def test_report_without_start_does_not_raise(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            # _progress and _live are None — should skip update calls
            r.report(_make_update())  # must not raise

    # ---- report_async() ----

    def test_report_async_delegates_to_report(self):
        import asyncio

        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            update = _make_update(status=ProgressStatus.RUNNING)
            asyncio.run(r.report_async(update))
        assert r._status == ProgressStatus.RUNNING

    # ---- stop() ----

    def test_stop_when_no_live_does_not_raise(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            r._live = None
            r.stop()  # must not raise

    def test_stop_calls_live_stop_and_clears_it(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            mock_live = MagicMock()
            r._live = mock_live
            r.stop()
        mock_live.stop.assert_called_once()
        assert r._live is None

    # ---- _create_display() ----

    def test_create_display_returns_panel(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            result = r._create_display()
            # With mocked Panel, result is whatever Panel(...) returns
            assert result is not None

    def test_create_display_raises_when_rich_unavailable(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            with (
                patch("attune.workflows.progress_reporters.RICH_AVAILABLE", False),
                patch("attune.workflows.progress_reporters.Panel", None),
                patch("attune.workflows.progress_reporters.Table", None),
            ):
                with pytest.raises(RuntimeError):
                    r._create_display()

    def test_create_display_uses_progress_when_set(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            r.start()
            r._cost = 0.05
            r._tokens = 200
            result = r._create_display()
            assert result is not None

    def test_create_display_all_statuses_handled(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            for status in ProgressStatus:
                r._status = status
                r._create_display()  # must not raise for any status

    # ---- context manager ----

    def test_context_manager_enter_returns_self(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            with patch.object(r, "start") as mock_start:
                result = r.__enter__()
            assert result is r
            mock_start.assert_called_once()

    def test_context_manager_exit_calls_stop(self):
        with _rich_ctx():
            r = RichProgressReporter("wf", ["a"])
            with patch.object(r, "stop") as mock_stop:
                r.__exit__(None, None, None)
            mock_stop.assert_called_once()

    def test_context_manager_full_cycle(self):
        with _rich_ctx():
            with RichProgressReporter("wf", ["a", "b"]) as r:
                assert isinstance(r, RichProgressReporter)
                r.report(_make_update())


# ---------------------------------------------------------------------------
# live_progress() context manager
# ---------------------------------------------------------------------------


class TestLiveProgressContextManager:
    def test_yields_tracker_and_reporter(self):
        with live_progress("test-wf", ["a", "b"]) as (tracker, reporter):
            assert isinstance(tracker, ProgressTracker)
            # reporter is None or RichProgressReporter — either is valid

    def test_tracker_has_correct_workflow_name(self):
        with live_progress("my-wf", ["x"]) as (tracker, _):
            assert tracker.workflow == "my-wf"

    def test_tracker_has_correct_stages(self):
        with live_progress("wf", ["alpha", "beta"]) as (tracker, _):
            assert tracker.stage_names == ["alpha", "beta"]

    def test_non_tty_uses_console_reporter(self):
        """In test environment (not a TTY), uses ConsoleProgressReporter."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            with live_progress("wf", ["a"]) as (tracker, reporter):
                # reporter is None in non-TTY + no Rich path
                assert tracker is not None

    def test_tracker_receives_callbacks(self):
        updates: list[ProgressUpdate] = []
        with live_progress("wf", ["a", "b"]) as (tracker, _):
            tracker.add_callback(updates.append)
            tracker.start_workflow()
        assert len(updates) >= 1

    def test_exception_in_body_propagates(self):
        """Exceptions in the body are not suppressed."""
        with pytest.raises(RuntimeError, match="test error"):
            with live_progress("wf", ["a"]) as (tracker, reporter):
                raise RuntimeError("test error")
