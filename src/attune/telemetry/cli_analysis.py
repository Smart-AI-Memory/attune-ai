"""Telemetry analysis CLI commands.

Commands for model fallback analysis and per-file test status reporting.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore


def cmd_sonnet_opus_analysis(args: Any) -> int:
    """Show Sonnet 4.5 -> Opus 4.5 fallback analysis and cost savings.

    Args:
        args: Parsed command-line arguments (days)

    Returns:
        Exit code (0 for success)

    """
    from datetime import timedelta

    from attune.models.telemetry import TelemetryAnalytics, get_telemetry_store

    store = get_telemetry_store()
    analytics = TelemetryAnalytics(store)

    days = getattr(args, "days", 30)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stats = analytics.sonnet_opus_fallback_analysis(since=since)

    if stats["total_calls"] == 0:
        print(f"No Sonnet/Opus calls found in the last {days} days.")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()

        # Fallback Performance Panel
        perf_text = Text()
        perf_text.append(f"Total Anthropic Calls: {stats['total_calls']}\n")
        perf_text.append(f"Sonnet 4.5 Attempts: {stats['sonnet_attempts']}\n")
        perf_text.append(
            f"Sonnet Success Rate: {stats['success_rate_sonnet']:.1f}%\n",
            style="green bold",
        )
        perf_text.append(f"Opus Fallbacks: {stats['opus_fallbacks']}\n")
        perf_text.append(
            f"Fallback Rate: {stats['fallback_rate']:.1f}%\n",
            style="yellow bold" if stats["fallback_rate"] > 10 else "green",
        )

        console.print(
            Panel(
                perf_text,
                title=f"Sonnet 4.5 -> Opus 4.5 Fallback Performance (last {days} days)",
                border_style="cyan",
            ),
        )

        # Cost Savings Panel
        savings_text = Text()
        savings_text.append(f"Actual Cost: ${stats['actual_cost']:.2f}\n")
        savings_text.append(f"Always-Premium Cost: ${stats['always_opus_cost']:.2f}\n")
        savings_text.append(
            f"Savings: ${stats['savings']:.2f} ({stats['savings_percent']:.1f}%)\n",
            style="green bold",
        )
        savings_text.append("\n")
        savings_text.append(f"Avg Cost/Call (actual): ${stats['avg_cost_per_call']:.4f}\n")
        savings_text.append(f"Avg Cost/Call (all Opus): ${stats['avg_opus_cost_per_call']:.4f}\n")

        console.print(Panel(savings_text, title="Cost Savings Analysis", border_style="green"))

        # Recommendation
        if stats["fallback_rate"] < 5:
            rec_text = Text()
            rec_text.append("Excellent Performance!\n", style="green bold")
            rec_text.append(
                f"Sonnet 4.5 handles {100 - stats['fallback_rate']:.1f}% of tasks successfully.\n",
            )
            rec_text.append(
                f"You're saving ${stats['savings']:.2f} compared to always using Opus.\n",
            )
            console.print(Panel(rec_text, title="Recommendation", border_style="green"))
        elif stats["fallback_rate"] < 15:
            rec_text = Text()
            rec_text.append("Moderate Fallback Rate\n", style="yellow bold")
            rec_text.append(f"{stats['fallback_rate']:.1f}% of tasks need Opus fallback.\n")
            rec_text.append("Consider analyzing which tasks fail on Sonnet.\n")
            console.print(Panel(rec_text, title="Recommendation", border_style="yellow"))
        else:
            rec_text = Text()
            rec_text.append("High Fallback Rate\n", style="red bold")
            rec_text.append(f"{stats['fallback_rate']:.1f}% of tasks need Opus fallback.\n")
            rec_text.append(
                "Consider using Opus directly for complex tasks to avoid retry overhead.\n",
            )
            console.print(Panel(rec_text, title="Recommendation", border_style="red"))
    else:
        # Plain text fallback
        print(f"\nSonnet 4.5 -> Opus 4.5 Fallback Analysis (last {days} days)")
        print("=" * 60)
        print("\nFallback Performance:")
        print(f"  Total Anthropic Calls: {stats['total_calls']}")
        print(f"  Sonnet 4.5 Attempts: {stats['sonnet_attempts']}")
        print(f"  Sonnet Success Rate: {stats['success_rate_sonnet']:.1f}%")
        print(f"  Opus Fallbacks: {stats['opus_fallbacks']}")
        print(f"  Fallback Rate: {stats['fallback_rate']:.1f}%")
        print("\nCost Savings:")
        print(f"  Actual Cost: ${stats['actual_cost']:.2f}")
        print(f"  Always-Premium Cost: ${stats['always_opus_cost']:.2f}")
        print(f"  Savings: ${stats['savings']:.2f} ({stats['savings_percent']:.1f}%)")
        print(f"  Avg Cost/Call (actual): ${stats['avg_cost_per_call']:.4f}")
        print(f"  Avg Cost/Call (all Opus): ${stats['avg_opus_cost_per_call']:.4f}")

        if stats["fallback_rate"] < 5:
            print(f"\nExcellent! Sonnet handles {100 - stats['fallback_rate']:.1f}% of tasks.")
        elif stats["fallback_rate"] < 15:
            print(f"\nModerate fallback rate ({stats['fallback_rate']:.1f}%).")
        else:
            print(f"\nHigh fallback rate ({stats['fallback_rate']:.1f}%).")

    return 0


def _get_file_test_records(args: Any) -> list | None:
    """Retrieve and filter file test records.

    Returns:
        List of records, or None on error.
    """
    from attune.models.telemetry import get_telemetry_store

    store = get_telemetry_store()
    file_path = getattr(args, "file", None)
    failed_only = getattr(args, "failed", False)
    stale_only = getattr(args, "stale", False)
    limit = getattr(args, "limit", 50)

    if file_path:
        record = store.get_latest_file_test(file_path)
        if record is None:
            print(f"No test record found for: {file_path}")
            return []
        return [record]

    all_records = store.get_file_tests(limit=100000)
    if not all_records:
        print("No per-file test records found.")
        print("Run: empathy test-file <source_file> to track tests for a file.")
        return []

    # Get latest record per file
    latest_by_file: dict[str, Any] = {}
    for record in all_records:
        existing = latest_by_file.get(record.file_path)
        if existing is None or record.timestamp > existing.timestamp:
            latest_by_file[record.file_path] = record

    records = list(latest_by_file.values())

    if failed_only:
        records = [r for r in records if r.last_test_result in ("failed", "error")]
    if stale_only:
        records = [r for r in records if r.is_stale]

    records.sort(key=lambda r: r.file_path)
    return records[:limit]


def cmd_file_test_status(args: Any) -> int:
    """Show per-file test status.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    try:
        records = _get_file_test_records(args)
    except Exception as e:  # noqa: BLE001
        print(f"Error retrieving file test status: {e}")
        return 1

    if not records:
        failed_only = getattr(args, "failed", False)
        stale_only = getattr(args, "stale", False)
        filter_desc = []
        if failed_only:
            filter_desc.append("failed")
        if stale_only:
            filter_desc.append("stale")
        filter_str = " and ".join(filter_desc) if filter_desc else "matching"
        print(f"No {filter_str} file test records found.")
        return 0

    if RICH_AVAILABLE and Console is not None:
        _render_file_test_status_rich(records)
    else:
        _render_file_test_status_plain(records)

    return 0


_RESULT_STYLES = {
    "passed": "green",
    "failed": "red",
    "error": "red",
    "no_tests": "yellow",
}


def _render_file_test_status_rich(records: list) -> None:
    """Render file test status using Rich tables."""
    console = Console()

    total = len(records)
    passed = sum(1 for r in records if r.last_test_result == "passed")
    failed = sum(1 for r in records if r.last_test_result in ("failed", "error"))
    no_tests = sum(1 for r in records if r.last_test_result == "no_tests")
    stale = sum(1 for r in records if r.is_stale)

    summary = Text()
    summary.append(f"Files: {total}  ", style="bold")
    summary.append(f"Passed: {passed}  ", style="green")
    summary.append(f"Failed: {failed}  ", style="red")
    summary.append(f"No Tests: {no_tests}  ", style="yellow")
    summary.append(f"Stale: {stale}", style="magenta")
    console.print(Panel(summary, title="Per-File Test Status Summary", border_style="cyan"))

    table = Table(title="File Test Status")
    table.add_column("File", style="cyan", max_width=50)
    table.add_column("Result", style="bold")
    table.add_column("Tests", justify="right")
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Duration", justify="right")
    table.add_column("Last Run", style="dim")
    table.add_column("Stale", style="magenta")

    for record in records:
        result_style = _RESULT_STYLES.get(record.last_test_result, "dim")
        try:
            dt = datetime.fromisoformat(record.timestamp.rstrip("Z"))
            ts_display = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            ts_display = record.timestamp[:16] if record.timestamp else "-"

        table.add_row(
            record.file_path,
            Text(record.last_test_result, style=result_style),
            str(record.test_count),
            str(record.passed),
            str(record.failed + record.errors),
            f"{record.duration_seconds:.1f}s" if record.duration_seconds else "-",
            ts_display,
            "YES" if record.is_stale else "",
        )

    console.print(table)

    failed_records = [r for r in records if r.failed_tests]
    if failed_records:
        fail_table = Table(title="Failed Test Details")
        fail_table.add_column("File", style="cyan")
        fail_table.add_column("Test Name", style="red")
        fail_table.add_column("Error")

        for record in failed_records[:10]:
            for test in record.failed_tests[:3]:
                fail_table.add_row(
                    record.file_path,
                    test.get("name", "unknown"),
                    test.get("error", "")[:50],
                )

        console.print(fail_table)


def _render_file_test_status_plain(records: list) -> None:
    """Render file test status as plain text."""
    print("\nPer-File Test Status")
    print("=" * 80)

    for record in records:
        status = record.last_test_result.upper()
        stale_marker = " [STALE]" if record.is_stale else ""
        print(f"\n{record.file_path}")
        print(f"  Status: {status}{stale_marker}")
        print(
            f"  Tests: {record.test_count} (passed: {record.passed}, failed: {record.failed})",
        )
        if record.duration_seconds:
            print(f"  Duration: {record.duration_seconds:.1f}s")
        print(f"  Last Run: {record.timestamp[:19]}")

        if record.failed_tests:
            print("  Failed Tests:")
            for test in record.failed_tests[:3]:
                print(f"    - {test.get('name', 'unknown')}: {test.get('error', '')[:40]}")
