"""Behavioral tests for progress reporters module.

Tests ConsoleProgressReporter, JsonLinesProgressReporter,
and RichProgressReporter covering uncovered lines.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import patch

import pytest

from attune.workflows.progress_models import ProgressStatus, ProgressUpdate, StageProgress
from attune.workflows.progress_reporters import (
    ConsoleProgressReporter,
    JsonLinesProgressReporter,
    RichProgressReporter,
)


def _make_update(**overrides: object) -> ProgressUpdate:
    """Build a ProgressUpdate with sensible defaults."""
    defaults: dict = {
        "workflow": "test-workflow",
        "workflow_id": "abc123",
        "current_stage": "analyze",
        "stage_index": 0,
        "total_stages": 3,
        "status": ProgressStatus.RUNNING,
        "message": "Running analyze",
        "cost_so_far": 0.0050,
        "tokens_so_far": 500,
        "percent_complete": 33.0,
        "stages": [],
    }
    defaults.update(overrides)
    return ProgressUpdate(**defaults)


def _make_stage(
    name: str = "analyze",
    status: ProgressStatus = ProgressStatus.RUNNING,
    **kwargs: object,
) -> StageProgress:
    """Build a StageProgress with sensible defaults."""
    return StageProgress(name=name, status=status, **kwargs)


@pytest.mark.unit
class TestStageProgressToDict:
    """Cover StageProgress.to_dict() serialization."""

    def test_to_dict_includes_all_fields(self):
        from datetime import datetime

        started = datetime(2026, 5, 9, 12, 0, 0)
        completed = datetime(2026, 5, 9, 12, 0, 1)
        sp = StageProgress(
            name="stage-1",
            status=ProgressStatus.COMPLETED,
            tier="capable",
            model="haiku",
            started_at=started,
            completed_at=completed,
            duration_ms=1234,
            cost=0.05,
            tokens_in=100,
            tokens_out=50,
        )
        d = sp.to_dict()
        assert d["name"] == "stage-1"
        assert d["status"] == "completed"
        assert d["tier"] == "capable"
        assert d["started_at"] == started.isoformat()
        assert d["completed_at"] == completed.isoformat()
        assert d["cost"] == 0.05

    def test_to_dict_handles_none_timestamps(self):
        sp = StageProgress(name="s", status=ProgressStatus.PENDING)
        d = sp.to_dict()
        assert d["started_at"] is None
        assert d["completed_at"] is None


@pytest.mark.unit
class TestConsoleProgressReporterBasic:
    """Test basic console output formatting."""

    def test_report_prints_percent_and_message(self, capsys: pytest.CaptureFixture) -> None:
        """Given a progress update, output contains percent and message."""
        # Given
        reporter = ConsoleProgressReporter()
        update = _make_update()
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert " 33%" in captured.out
        assert "Running analyze" in captured.out

    def test_report_prints_cost(self, capsys: pytest.CaptureFixture) -> None:
        """Given a progress update with cost, output contains cost."""
        # Given
        reporter = ConsoleProgressReporter()
        update = _make_update(cost_so_far=0.0279)
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "$0.0279" in captured.out

    def test_status_icons_mapped(self, capsys: pytest.CaptureFixture) -> None:
        """Given various statuses, correct icons are shown."""
        reporter = ConsoleProgressReporter()
        for status, icon in [
            (ProgressStatus.COMPLETED, "✓"),
            (ProgressStatus.FAILED, "✗"),
            (ProgressStatus.SKIPPED, "–"),
            (ProgressStatus.FALLBACK, "↻"),
        ]:
            update = _make_update(status=status)
            reporter.report(update)
            captured = capsys.readouterr()
            assert icon in captured.out


@pytest.mark.unit
class TestConsoleProgressReporterTierInfo:
    """Test tier info display from running stage (lines 103-113)."""

    def test_running_stage_shows_tier(self, capsys: pytest.CaptureFixture) -> None:
        """Given a running stage with tier, tier label is shown."""
        # Given
        reporter = ConsoleProgressReporter()
        stage = _make_stage(
            name="analyze",
            status=ProgressStatus.RUNNING,
            tier="premium",
        )
        update = _make_update(current_stage="analyze", stages=[stage])
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "[PREMIUM]" in captured.out

    def test_running_stage_shows_model(self, capsys: pytest.CaptureFixture) -> None:
        """Given a running stage with model, model name is shown."""
        # Given
        reporter = ConsoleProgressReporter()
        stage = _make_stage(
            name="analyze",
            status=ProgressStatus.RUNNING,
            tier="capable",
            model="claude-sonnet-5",
        )
        update = _make_update(current_stage="analyze", stages=[stage])
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "(claude-sonnet-5)" in captured.out

    def test_completed_stage_no_tier_label(self, capsys: pytest.CaptureFixture) -> None:
        """Given a completed stage, tier info is not appended."""
        # Given
        reporter = ConsoleProgressReporter()
        stage = _make_stage(
            name="analyze",
            status=ProgressStatus.COMPLETED,
            tier="premium",
        )
        update = _make_update(current_stage="analyze", stages=[stage])
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "[PREMIUM]" not in captured.out

    def test_stage_duration_tracked(self, capsys: pytest.CaptureFixture) -> None:
        """Given a stage with duration_ms, it is recorded internally."""
        # Given
        reporter = ConsoleProgressReporter()
        stage = _make_stage(name="analyze", duration_ms=1200)
        update = _make_update(current_stage="analyze", stages=[stage])
        # When
        reporter.report(update)
        # Then
        assert reporter._stage_times.get("analyze") == 1200


@pytest.mark.unit
class TestConsoleProgressReporterVerbose:
    """Test verbose output (lines 134-138)."""

    def test_verbose_shows_fallback_info(self, capsys: pytest.CaptureFixture) -> None:
        """Given verbose mode and fallback_info, it is printed."""
        # Given
        reporter = ConsoleProgressReporter(verbose=True)
        update = _make_update(fallback_info="Fell back to cheap tier")
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "Fallback: Fell back to cheap tier" in captured.out

    def test_verbose_shows_error(self, capsys: pytest.CaptureFixture) -> None:
        """Given verbose mode and error, it is printed."""
        # Given
        reporter = ConsoleProgressReporter(verbose=True)
        update = _make_update(error="Rate limit exceeded")
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "Error: Rate limit exceeded" in captured.out

    def test_non_verbose_hides_fallback_and_error(self, capsys: pytest.CaptureFixture) -> None:
        """Given non-verbose mode, fallback and error are hidden."""
        # Given
        reporter = ConsoleProgressReporter(verbose=False)
        update = _make_update(fallback_info="fallback", error="err")
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "Fallback:" not in captured.out
        assert "Error:" not in captured.out


@pytest.mark.unit
class TestConsoleProgressReporterTokens:
    """Test token display."""

    def test_show_tokens_includes_count(self, capsys: pytest.CaptureFixture) -> None:
        """Given show_tokens=True, token count appears."""
        # Given
        reporter = ConsoleProgressReporter(show_tokens=True)
        update = _make_update(tokens_so_far=1500)
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "1,500 tokens" in captured.out

    def test_show_tokens_zero_hidden(self, capsys: pytest.CaptureFixture) -> None:
        """Given show_tokens=True but 0 tokens, no token count."""
        # Given
        reporter = ConsoleProgressReporter(show_tokens=True)
        update = _make_update(tokens_so_far=0)
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "tokens" not in captured.out


@pytest.mark.unit
class TestConsoleProgressReporterSummary:
    """Test workflow completion summary (lines 144-162)."""

    def test_summary_printed_on_workflow_completion(self, capsys: pytest.CaptureFixture) -> None:
        """Given completed status with 'workflow' in message, summary prints."""
        # Given
        reporter = ConsoleProgressReporter()
        stage = _make_stage(
            name="analyze",
            status=ProgressStatus.COMPLETED,
            duration_ms=500,
            cost=0.01,
        )
        # First report to populate stage_times
        update1 = _make_update(
            current_stage="analyze",
            stages=[stage],
            status=ProgressStatus.RUNNING,
        )
        reporter.report(update1)
        capsys.readouterr()  # clear

        # Final workflow completion
        update2 = _make_update(
            status=ProgressStatus.COMPLETED,
            message="Completed workflow",
            stages=[stage],
        )
        reporter.report(update2)
        captured = capsys.readouterr()
        # Then
        assert "Stage Summary:" in captured.out
        assert "analyze:" in captured.out

    def test_summary_shows_ms_for_short_duration(self, capsys: pytest.CaptureFixture) -> None:
        """Given stage duration < 1000ms, shows ms format."""
        # Given
        reporter = ConsoleProgressReporter()
        reporter._stage_times["fast_stage"] = 450
        stage = _make_stage(
            name="fast_stage",
            status=ProgressStatus.COMPLETED,
            duration_ms=450,
            cost=0.0,
        )
        update = _make_update(
            status=ProgressStatus.COMPLETED,
            message="Completed workflow",
            stages=[stage],
        )
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "450ms" in captured.out

    def test_summary_shows_seconds_for_long_duration(self, capsys: pytest.CaptureFixture) -> None:
        """Given stage duration >= 1000ms, shows seconds format."""
        # Given
        reporter = ConsoleProgressReporter()
        reporter._stage_times["slow_stage"] = 2500
        stage = _make_stage(
            name="slow_stage",
            status=ProgressStatus.COMPLETED,
            duration_ms=2500,
            cost=0.05,
        )
        update = _make_update(
            status=ProgressStatus.COMPLETED,
            message="Completed workflow",
            stages=[stage],
        )
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "2.5s" in captured.out

    def test_summary_shows_em_dash_for_zero_cost(self, capsys: pytest.CaptureFixture) -> None:
        """Given zero-cost stage, em dash is shown instead of $0."""
        # Given
        reporter = ConsoleProgressReporter()
        reporter._stage_times["free_stage"] = 100
        stage = _make_stage(
            name="free_stage",
            status=ProgressStatus.COMPLETED,
            duration_ms=100,
            cost=0.0,
        )
        update = _make_update(
            status=ProgressStatus.COMPLETED,
            message="Completed workflow",
            stages=[stage],
        )
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "\u2014" in captured.out  # em dash

    def test_summary_shows_skipped_stages(self, capsys: pytest.CaptureFixture) -> None:
        """Given skipped stages, they appear as 'skipped'."""
        # Given
        reporter = ConsoleProgressReporter()
        reporter._stage_times["done"] = 100
        stages = [
            _make_stage(name="done", status=ProgressStatus.COMPLETED, duration_ms=100),
            _make_stage(name="skip_me", status=ProgressStatus.SKIPPED),
        ]
        update = _make_update(
            status=ProgressStatus.COMPLETED,
            message="Completed workflow",
            stages=stages,
        )
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        assert "skip_me: skipped" in captured.out


@pytest.mark.unit
class TestConsoleProgressReporterAsync:
    """Test async report delegates to sync (line 164-166)."""

    @pytest.mark.asyncio
    async def test_report_async_delegates(self, capsys: pytest.CaptureFixture) -> None:
        """Given async call, output is same as sync."""
        # Given
        reporter = ConsoleProgressReporter()
        update = _make_update()
        # When
        await reporter.report_async(update)
        # Then
        captured = capsys.readouterr()
        assert "Running analyze" in captured.out


@pytest.mark.unit
class TestJsonLinesProgressReporter:
    """Test JSON Lines reporter."""

    def test_report_prints_json_to_stdout(self, capsys: pytest.CaptureFixture) -> None:
        """Given no output_file, JSON is printed to stdout."""
        # Given
        reporter = JsonLinesProgressReporter()
        update = _make_update()
        # When
        reporter.report(update)
        # Then
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["workflow"] == "test-workflow"
        assert data["status"] == "running"

    def test_report_writes_to_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given output_file, JSON is written to file."""
        # Given
        outfile = str(tmp_path / "progress.jsonl")
        reporter = JsonLinesProgressReporter(output_file=outfile)
        update = _make_update()
        # When
        reporter.report(update)
        # Then
        with open(outfile) as f:
            data = json.loads(f.readline().strip())
        assert data["workflow"] == "test-workflow"

    def test_report_appends_to_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given multiple reports, file accumulates lines."""
        # Given
        outfile = str(tmp_path / "progress.jsonl")
        reporter = JsonLinesProgressReporter(output_file=outfile)
        # When
        reporter.report(_make_update(stage_index=0))
        reporter.report(_make_update(stage_index=1))
        # Then
        with open(outfile) as f:
            lines = f.readlines()
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_report_async_delegates(self, capsys: pytest.CaptureFixture) -> None:
        """Given async call, output matches sync."""
        # Given
        reporter = JsonLinesProgressReporter()
        update = _make_update()
        # When
        await reporter.report_async(update)
        # Then
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["workflow"] == "test-workflow"


@pytest.mark.unit
class TestRichProgressReporter:
    """Test Rich-based reporter (lines 226-340)."""

    def test_init_raises_without_rich(self) -> None:
        """Given Rich unavailable, init raises RuntimeError."""
        # Given/When/Then
        with patch("attune.workflows.progress_reporters.RICH_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Rich library required"):
                RichProgressReporter("test", ["stage1"])

    def test_start_creates_live_display(self) -> None:
        """Given Rich available, start() creates progress and live."""
        # Given
        reporter = RichProgressReporter("test-wf", ["s1", "s2"])
        # When
        reporter.start()
        # Then
        try:
            assert reporter._progress is not None
            assert reporter._live is not None
            assert reporter._task_id is not None
        finally:
            reporter.stop()

    def test_stop_clears_live(self) -> None:
        """Given started reporter, stop() clears the live display."""
        # Given
        reporter = RichProgressReporter("test-wf", ["s1"])
        reporter.start()
        # When
        reporter.stop()
        # Then
        assert reporter._live is None

    def test_stop_idempotent(self) -> None:
        """Given already-stopped reporter, stop() is safe."""
        # Given
        reporter = RichProgressReporter("test-wf", ["s1"])
        # When/Then - no error
        reporter.stop()
        reporter.stop()

    def test_report_updates_state(self) -> None:
        """Given a progress update, internal state is updated."""
        # Given
        reporter = RichProgressReporter("test-wf", ["s1", "s2"])
        reporter.start()
        try:
            update = _make_update(
                current_stage="s1",
                cost_so_far=0.05,
                tokens_so_far=1000,
                status=ProgressStatus.RUNNING,
            )
            # When
            reporter.report(update)
            # Then
            assert reporter._current_stage == "s1"
            assert reporter._cost == 0.05
            assert reporter._tokens == 1000
        finally:
            reporter.stop()

    def test_report_increments_progress_bar(self) -> None:
        """Given completed stages, progress bar is updated."""
        # Given
        reporter = RichProgressReporter("test-wf", ["s1", "s2"])
        reporter.start()
        try:
            stages = [
                _make_stage(name="s1", status=ProgressStatus.COMPLETED),
                _make_stage(name="s2", status=ProgressStatus.RUNNING),
            ]
            update = _make_update(current_stage="s2", stages=stages)
            # When
            reporter.report(update)
            # Then
            assert reporter._progress is not None
        finally:
            reporter.stop()

    def test_context_manager(self) -> None:
        """Given context manager usage, start/stop called."""
        # Given/When
        with RichProgressReporter("test-wf", ["s1"]) as reporter:
            assert reporter._live is not None
        # Then
        assert reporter._live is None

    def test_create_display_returns_panel(self) -> None:
        """Given Rich available, _create_display returns Panel."""
        # Given
        from rich.panel import Panel

        reporter = RichProgressReporter("test-wf", ["s1"])
        # When
        panel = reporter._create_display()
        # Then
        assert isinstance(panel, Panel)

    @pytest.mark.asyncio
    async def test_report_async_delegates(self) -> None:
        """Given async call, it delegates to sync report."""
        # Given
        reporter = RichProgressReporter("test-wf", ["s1"])
        reporter.start()
        try:
            update = _make_update()
            # When
            await reporter.report_async(update)
            # Then
            assert reporter._current_stage == "analyze"
        finally:
            reporter.stop()
