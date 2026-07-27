"""Progress Reporters

Reporter implementations for the progress tracking system.
Includes console, JSON Lines, and Rich-based live reporters.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Protocol

from .progress_models import ProgressStatus, ProgressUpdate

# Rich imports with fallback
try:
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    Live = None  # type: ignore
    Panel = None  # type: ignore
    Progress = None  # type: ignore


class ProgressReporter(Protocol):
    """Protocol for progress reporting implementations."""

    def report(self, update: ProgressUpdate) -> None:
        """Report a progress update."""
        ...

    async def report_async(self, update: ProgressUpdate) -> None:
        """Report a progress update asynchronously."""
        ...


class ConsoleProgressReporter:
    """Console-based progress reporter optimized for IDE environments.

    Provides clear, readable progress output that works reliably in:
    - VSCode integrated terminal
    - VSCode output panel
    - IDE debug consoles
    - Standard terminals

    Uses Unicode symbols that render correctly in most environments.
    """

    def __init__(self, verbose: bool = False, show_tokens: bool = False):
        """Initialize console progress reporter.

        Args:
            verbose: Show additional details (fallback info, errors)
            show_tokens: Include token counts in output

        """
        self.verbose = verbose
        self.show_tokens = show_tokens
        self._start_time: datetime | None = None
        self._stage_times: dict[str, int] = {}

    def report(self, update: ProgressUpdate) -> None:
        """Print progress to console.

        Args:
            update: Progress update from the tracker

        """
        # Track start time for elapsed calculation
        if self._start_time is None:
            self._start_time = datetime.now()

        percent = f"{update.percent_complete:3.0f}%"
        cost = f"${update.cost_so_far:.4f}"

        # Status icons that work in most environments
        status_icon = {
            ProgressStatus.PENDING: "○",
            ProgressStatus.RUNNING: "►",
            ProgressStatus.COMPLETED: "✓",
            ProgressStatus.FAILED: "✗",
            ProgressStatus.SKIPPED: "–",
            ProgressStatus.FALLBACK: "↻",
            ProgressStatus.RETRYING: "↻",
        }.get(update.status, "?")

        # Get current tier from running stage
        tier_info = ""
        if update.current_stage and update.stages:
            for stage in update.stages:
                if stage.name == update.current_stage:
                    if stage.status == ProgressStatus.RUNNING:
                        tier_info = f" [{stage.tier.upper()}]"
                        if stage.model:
                            tier_info += f" ({stage.model})"
                    # Track stage duration
                    if stage.duration_ms > 0:
                        self._stage_times[stage.name] = stage.duration_ms
                    break

        # Build output line
        elapsed = ""
        if self._start_time:
            elapsed_sec = (datetime.now() - self._start_time).total_seconds()
            if elapsed_sec >= 1:
                elapsed = f" [{elapsed_sec:.1f}s]"

        tokens_str = ""
        if self.show_tokens and update.tokens_so_far > 0:
            tokens_str = f" | {update.tokens_so_far:,} tokens"

        # Format: [100%] check Completed optimize [PREMIUM] ($0.0279) [12.3s]
        output = (
            f"[{percent}] {status_icon} {update.message}"
            f"{tier_info} ({cost}{tokens_str}){elapsed}"
        )
        print(output)

        # Verbose output
        if self.verbose:
            if update.fallback_info:
                print(f"         ↳ Fallback: {update.fallback_info}")
            if update.error:
                print(f"         ↳ Error: {update.error}")

        # Print summary only on final workflow completion (not stage completion)
        if update.status == ProgressStatus.COMPLETED and "workflow" in update.message.lower():
            self._print_summary(update)

    def _print_summary(self, update: ProgressUpdate) -> None:
        """Print workflow completion summary."""
        if not self._stage_times:
            return

        print()
        print("\u2500" * 50)
        print("Stage Summary:")
        for stage in update.stages:
            if stage.status == ProgressStatus.COMPLETED:
                duration_ms = stage.duration_ms or self._stage_times.get(stage.name, 0)
                duration_str = (
                    f"{duration_ms}ms" if duration_ms < 1000 else f"{duration_ms/1000:.1f}s"
                )
                cost_str = f"${stage.cost:.4f}" if stage.cost > 0 else "\u2014"
                print(f"  {stage.name}: {duration_str} | {cost_str}")
            elif stage.status == ProgressStatus.SKIPPED:
                print(f"  {stage.name}: skipped")
        print("\u2500" * 50)

    async def report_async(self, update: ProgressUpdate) -> None:
        """Async version just calls sync."""
        self.report(update)


class JsonLinesProgressReporter:
    """JSON Lines progress reporter for machine parsing."""

    def __init__(self, output_file: str | None = None):
        """Initialize JsonLinesProgressReporter.

        Args:
            output_file: Optional file path for JSON lines output.
                Defaults to stdout if None.

        """
        self.output_file = output_file

    def report(self, update: ProgressUpdate) -> None:
        """Output progress as JSON line."""
        json_line = update.to_json()

        if self.output_file:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")
        else:
            print(json_line)

    async def report_async(self, update: ProgressUpdate) -> None:
        """Async version just calls sync."""
        self.report(update)


class RichProgressReporter:
    """Rich-based live progress display with spinner, progress bar, and metrics.

    Provides real-time visual feedback during workflow execution:
    - Progress bar showing stage completion (1/3, 2/3, etc.)
    - Spinner during active LLM API calls
    - Real-time cost and token display
    - In-place updates (no terminal scrolling)

    Requires Rich library. Falls back gracefully if unavailable.
    """

    def __init__(self, workflow_name: str, stage_names: list[str]) -> None:
        """Initialize the Rich progress reporter.

        Args:
            workflow_name: Name of the workflow for display
            stage_names: List of stage names for progress tracking

        """
        if not RICH_AVAILABLE:
            raise RuntimeError(
                "Rich library required for RichProgressReporter. Install with: pip install rich",
            )

        self.workflow_name = workflow_name
        self.stage_names = stage_names
        self.console = Console()
        self._live: Live | None = None
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None
        self._current_stage = ""
        self._cost = 0.0
        self._tokens = 0
        self._status = ProgressStatus.PENDING

    def start(self) -> None:
        """Start the live progress display."""
        if not RICH_AVAILABLE or Progress is None or Live is None:
            return

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            console=self.console,
            transient=False,
        )

        self._task_id = self._progress.add_task(
            self.workflow_name,
            total=len(self.stage_names),
        )

        self._live = Live(
            self._create_display(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.start()

    def stop(self) -> None:
        """Stop the live progress display."""
        if self._live:
            self._live.stop()
            self._live = None

    def report(self, update: ProgressUpdate) -> None:
        """Handle a progress update.

        Args:
            update: Progress update from the tracker

        """
        self._current_stage = update.current_stage
        self._cost = update.cost_so_far
        self._tokens = update.tokens_so_far
        self._status = update.status

        # Update progress bar
        if self._progress is not None and self._task_id is not None:
            completed = sum(1 for s in update.stages if s.status == ProgressStatus.COMPLETED)
            self._progress.update(
                self._task_id,
                completed=completed,
                description=(f"{self.workflow_name}: {update.current_stage}"),
            )

        # Refresh display
        if self._live:
            self._live.update(self._create_display())

    async def report_async(self, update: ProgressUpdate) -> None:
        """Async version of report."""
        self.report(update)

    def _create_display(self) -> Panel:
        """Create the Rich display panel.

        Returns:
            Rich Panel containing progress information

        """
        if not RICH_AVAILABLE or Panel is None or Table is None:
            raise RuntimeError("Rich library not available. Install with: pip install rich")

        # Build metrics table
        metrics = Table(show_header=False, box=None, padding=(0, 2))
        metrics.add_column("Label", style="dim")
        metrics.add_column("Value", style="bold")

        metrics.add_row("Cost:", f"${self._cost:.4f}")
        metrics.add_row("Tokens:", f"{self._tokens:,}")
        metrics.add_row("Stage:", self._current_stage or "Starting...")

        # Status indicator
        status_style = {
            ProgressStatus.PENDING: "dim",
            ProgressStatus.RUNNING: "blue",
            ProgressStatus.COMPLETED: "green",
            ProgressStatus.FAILED: "red",
            ProgressStatus.FALLBACK: "yellow",
            ProgressStatus.RETRYING: "yellow",
        }.get(self._status, "white")

        status_text = Text(self._status.value.upper(), style=status_style)

        # Combine into panel
        if self._progress is not None:
            content = Group(self._progress, metrics)
        else:
            content = metrics

        return Panel(
            content,
            title=f"[bold]{self.workflow_name}[/bold]",
            subtitle=status_text,
            border_style=status_style,
        )

    def __enter__(self) -> RichProgressReporter:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


@contextmanager
def live_progress(
    workflow_name: str,
    stage_names: list[str],
    console: Console | None = None,
) -> Generator[tuple, None, None]:
    """Context manager for live progress display during workflow execution.

    Provides a ProgressTracker with optional Rich-based live display.
    Falls back gracefully when Rich is unavailable or output is not a TTY.

    Args:
        workflow_name: Name of the workflow
        stage_names: List of stage names in order
        console: Optional Rich Console (creates new one if not provided)

    Yields:
        Tuple of (ProgressTracker, RichProgressReporter or None)

    Example:
        with live_progress("Code Review", ["analyze", "review"]) as (tracker, _):
            tracker.start_workflow()
            for stage in stages:
                tracker.start_stage(stage)
                # ... do work ...
                tracker.complete_stage(stage, cost=0.01)
            tracker.complete_workflow()

    """
    # Import here to avoid circular imports

    from .progress import ProgressTracker

    tracker = ProgressTracker(
        workflow_name=workflow_name,
        workflow_id=uuid.uuid4().hex[:12],
        stage_names=stage_names,
    )

    reporter: RichProgressReporter | None = None

    # Use Rich if available and output is a TTY
    if RICH_AVAILABLE and sys.stdout.isatty():
        try:
            reporter = RichProgressReporter(workflow_name, stage_names)
            tracker.add_callback(reporter.report)
            reporter.start()
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Rich display is optional - fall back to console output
            reporter = None
            simple_reporter = ConsoleProgressReporter(verbose=False)
            tracker.add_callback(simple_reporter.report)
    else:
        # No Rich or not a TTY - use simple console reporter
        simple_reporter = ConsoleProgressReporter(verbose=False)
        tracker.add_callback(simple_reporter.report)

    try:
        yield tracker, reporter
    finally:
        if reporter:
            reporter.stop()
