"""Tests for progress_reporters.py.

Covers the untested branches in RichProgressReporter and live_progress()
to push coverage from 52.9% to 80%+.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import attune.workflows.progress_reporters as reporters_module
from attune.workflows.progress_reporters import (
    RichProgressReporter,
    live_progress,
)

# ---------------------------------------------------------------------------
# RichProgressReporter — Rich unavailable paths
# ---------------------------------------------------------------------------


class TestRichProgressReporterNoRich:
    """Test RichProgressReporter when Rich is not available."""

    def test_init_raises_when_rich_unavailable(self) -> None:
        """RuntimeError raised when RICH_AVAILABLE is False."""
        with patch.object(reporters_module, "RICH_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Rich library required"):
                RichProgressReporter("test-wf", ["stage1"])

    def test_start_returns_silently_when_rich_unavailable(self) -> None:
        """start() is a no-op when RICH_AVAILABLE is False."""
        # Create reporter while Rich is available
        reporter = RichProgressReporter("test-wf", ["stage1"])
        # Then patch Rich away for the start() call
        with patch.object(reporters_module, "RICH_AVAILABLE", False):
            reporter.start()  # Should not raise
        # Nothing was initialised
        assert reporter._live is None
        assert reporter._progress is None

    def test_create_display_raises_when_rich_unavailable(self) -> None:
        """_create_display() raises RuntimeError when Rich is patched away."""
        reporter = RichProgressReporter("test-wf", ["stage1"])
        with (
            patch.object(reporters_module, "RICH_AVAILABLE", False),
            pytest.raises(RuntimeError, match="Rich library not available"),
        ):
            reporter._create_display()


# ---------------------------------------------------------------------------
# live_progress context manager
# ---------------------------------------------------------------------------


class TestLiveProgress:
    """Tests for the live_progress() context manager."""

    def test_no_tty_uses_console_reporter(self) -> None:
        """When stdout is not a TTY, ConsoleProgressReporter is used."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            with live_progress("wf", ["a", "b"]) as (tracker, reporter):
                assert reporter is None  # No rich reporter
                # Tracker has callbacks (the console reporter)
                assert len(tracker._callbacks) >= 1

    def test_rich_unavailable_uses_console_reporter(self) -> None:
        """When RICH_AVAILABLE is False, ConsoleProgressReporter is used."""
        with (
            patch.object(reporters_module, "RICH_AVAILABLE", False),
            patch("sys.stdout") as mock_stdout,
        ):
            mock_stdout.isatty.return_value = True  # TTY but no Rich
            with live_progress("wf", ["a"]) as (tracker, reporter):
                assert reporter is None

    def test_rich_init_exception_falls_back_to_console(self) -> None:
        """If RichProgressReporter() raises, falls back to ConsoleProgressReporter."""
        with (
            patch.object(reporters_module, "RICH_AVAILABLE", True),
            patch("sys.stdout") as mock_stdout,
            patch.object(
                reporters_module,
                "RichProgressReporter",
                side_effect=RuntimeError("rich broken"),
            ),
        ):
            mock_stdout.isatty.return_value = True
            with live_progress("wf", ["a"]) as (tracker, reporter):
                assert reporter is None
                assert len(tracker._callbacks) >= 1

    def test_tty_with_rich_uses_rich_reporter(self) -> None:
        """When TTY + Rich available, RichProgressReporter is created and yielded."""
        mock_reporter = MagicMock(spec=RichProgressReporter)
        with (
            patch.object(reporters_module, "RICH_AVAILABLE", True),
            patch("sys.stdout") as mock_stdout,
            patch.object(
                reporters_module,
                "RichProgressReporter",
                return_value=mock_reporter,
            ),
        ):
            mock_stdout.isatty.return_value = True
            with live_progress("wf", ["a", "b"]) as (tracker, reporter):
                assert reporter is mock_reporter
                mock_reporter.start.assert_called_once()

    def test_finally_calls_stop_on_rich_reporter(self) -> None:
        """reporter.stop() is called in the finally block when reporter is set."""
        mock_reporter = MagicMock(spec=RichProgressReporter)
        with (
            patch.object(reporters_module, "RICH_AVAILABLE", True),
            patch("sys.stdout") as mock_stdout,
            patch.object(
                reporters_module,
                "RichProgressReporter",
                return_value=mock_reporter,
            ),
        ):
            mock_stdout.isatty.return_value = True
            with live_progress("wf", ["a"]) as (tracker, reporter):
                pass  # Normal exit

        mock_reporter.stop.assert_called_once()

    def test_finally_calls_stop_even_on_exception(self) -> None:
        """reporter.stop() is called even when an exception occurs inside the block."""
        mock_reporter = MagicMock(spec=RichProgressReporter)
        with (
            patch.object(reporters_module, "RICH_AVAILABLE", True),
            patch("sys.stdout") as mock_stdout,
            patch.object(
                reporters_module,
                "RichProgressReporter",
                return_value=mock_reporter,
            ),
        ):
            mock_stdout.isatty.return_value = True
            with pytest.raises(ValueError):
                with live_progress("wf", ["a"]) as (tracker, reporter):
                    raise ValueError("workflow error")

        mock_reporter.stop.assert_called_once()

    def test_no_stop_when_reporter_is_none(self) -> None:
        """stop() is not called when reporter is None (no-Rich path)."""
        with (
            patch.object(reporters_module, "RICH_AVAILABLE", False),
            patch("sys.stdout") as mock_stdout,
        ):
            mock_stdout.isatty.return_value = False
            # Should not raise even without a reporter
            with live_progress("wf", ["a"]) as (tracker, reporter):
                assert reporter is None
