"""Core telemetry CLI commands.

Commands for viewing, analyzing, and exporting local usage telemetry data.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
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

from attune.security.path_validation import _validate_file_path

from .usage_tracker import UsageTracker


def cmd_telemetry_show(args: Any) -> int:
    """Show recent telemetry entries.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    tracker = UsageTracker.get_instance()
    limit = getattr(args, "limit", 20)
    days = getattr(args, "days", None)

    entries = tracker.get_recent_entries(limit=limit, days=days)

    if not entries:
        print("No telemetry data found.")
        print(f"Data location: {tracker.telemetry_dir}")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()
        table = Table(title="Recent LLM Calls", show_header=True, header_style="bold magenta")
        table.add_column("Time", style="cyan", width=19)
        table.add_column("Workflow", style="green")
        table.add_column("Stage", style="blue")
        table.add_column("Tier", style="yellow")
        table.add_column("Cost", style="red", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cache", style="green")
        table.add_column("Duration", justify="right")

        total_cost = 0.0
        total_duration = 0

        for entry in entries:
            ts = entry.get("ts", "")
            # Format timestamp
            try:
                dt = datetime.fromisoformat(ts.rstrip("Z"))
                ts_display = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                ts_display = ts[:19] if len(ts) >= 19 else ts

            workflow = entry.get("workflow", "unknown")
            stage = entry.get("stage", "-")
            tier = entry.get("tier", "unknown")
            cost = entry.get("cost", 0.0)
            tokens = entry.get("tokens", {})
            cache = entry.get("cache", {})
            duration_ms = entry.get("duration_ms", 0)

            tokens_str = f"{tokens.get('input', 0)}/{tokens.get('output', 0)}"
            cache_str = "HIT" if cache.get("hit") else "MISS"
            if cache.get("hit"):
                cache_type = cache.get("type", "")
                if cache_type:
                    cache_str += f" ({cache_type})"

            table.add_row(
                ts_display,
                workflow[:20],
                stage[:15] if stage else "-",
                tier,
                f"${cost:.4f}",
                tokens_str,
                cache_str,
                f"{duration_ms}ms",
            )

            total_cost += cost
            total_duration += duration_ms

        console.print(table)
        console.print()
        console.print(f"[bold]Total Cost:[/bold] ${total_cost:.4f}")
        console.print(f"[bold]Avg Duration:[/bold] {total_duration // len(entries)}ms")
        console.print(f"\n[dim]Data location: {tracker.telemetry_dir}[/dim]")
    else:
        # Fallback to plain text
        print(
            f"\n{'Time':<19} {'Workflow':<20} {'Stage':<15} {'Tier':<10} {'Cost':>10} {'Cache':<10} {'Duration':>10}",
        )
        print("-" * 120)
        total_cost = 0.0
        for entry in entries:
            ts = entry.get("ts", "")[:19]
            workflow = entry.get("workflow", "unknown")[:20]
            stage = entry.get("stage", "-")[:15]
            tier = entry.get("tier", "unknown")
            cost = entry.get("cost", 0.0)
            cache = entry.get("cache", {})
            duration_ms = entry.get("duration_ms", 0)

            cache_str = "HIT" if cache.get("hit") else "MISS"
            print(
                f"{ts:<19} {workflow:<20} {stage:<15} {tier:<10} ${cost:>9.4f} {cache_str:<10} {duration_ms:>9}ms",
            )
            total_cost += cost

        print("-" * 120)
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"\nData location: {tracker.telemetry_dir}")

    return 0


def cmd_telemetry_savings(args: Any) -> int:
    """Calculate and display cost savings.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    tracker = UsageTracker.get_instance()
    days = getattr(args, "days", 30)

    savings = tracker.calculate_savings(days=days)

    if savings["total_calls"] == 0:
        print("No telemetry data found for the specified period.")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()

        # Create savings report
        title = Text("Cost Savings Analysis", style="bold magenta")
        content_lines = []

        content_lines.append(f"Period: Last {days} days")
        content_lines.append("")
        content_lines.append("Usage Pattern:")
        for tier, pct in sorted(savings["tier_distribution"].items()):
            content_lines.append(f"  {tier:8}: {pct:5.1f}%")
        content_lines.append("")
        content_lines.append("Cost Comparison:")
        content_lines.append(f"  Baseline (all PREMIUM): ${savings['baseline_cost']:.2f}")
        content_lines.append(f"  Actual (tier routing):  ${savings['actual_cost']:.2f}")
        content_lines.append("")
        savings_color = "green" if savings["savings"] > 0 else "red"
        content_lines.append(
            f"[bold {savings_color}]YOUR SAVINGS: ${savings['savings']:.2f} ({savings['savings_percent']:.1f}%)[/bold {savings_color}]",
        )
        content_lines.append("")
        content_lines.append(f"Cache savings: ${savings['cache_savings']:.2f}")
        content_lines.append(f"Total calls: {savings['total_calls']}")

        panel = Panel(
            "\n".join(content_lines),
            title=title,
            border_style="cyan",
        )
        console.print(panel)
    else:
        # Fallback to plain text
        print("\n" + "=" * 60)
        print("COST SAVINGS ANALYSIS")
        print("=" * 60)
        print(f"Period: Last {days} days\n")
        print("Usage Pattern:")
        for tier, pct in sorted(savings["tier_distribution"].items()):
            print(f"  {tier:8}: {pct:5.1f}%")
        print("\nCost Comparison:")
        print(f"  Baseline (all PREMIUM): ${savings['baseline_cost']:.2f}")
        print(f"  Actual (tier routing):  ${savings['actual_cost']:.2f}")
        print(f"\nYOUR SAVINGS: ${savings['savings']:.2f} ({savings['savings_percent']:.1f}%)")
        print(f"\nCache savings: ${savings['cache_savings']:.2f}")
        print(f"Total calls: {savings['total_calls']}")
        print("=" * 60)

    return 0


def cmd_telemetry_cache_stats(args: Any) -> int:
    """Show prompt caching performance statistics.

    Displays cache hit rates, cost savings, and workflow-level stats.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    tracker = UsageTracker.get_instance()
    days = getattr(args, "days", 7)

    stats = tracker.get_cache_stats(days=days)

    if stats["total_requests"] == 0:
        print("No telemetry data found for cache analysis.")
        print(f"Data location: {tracker.telemetry_dir}")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()

        # Main stats table
        table = Table(
            title=f"Prompt Caching Stats (Last {days} Days)",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        # Cache hit rate
        hit_rate_color = "green" if stats["hit_rate"] > 0.5 else "yellow"
        table.add_row(
            "Cache Hit Rate",
            f"[{hit_rate_color}]{stats['hit_rate']:.1%}[/{hit_rate_color}]",
        )

        # Tokens
        table.add_row("Cache Reads", f"{stats['total_reads']:,} tokens")
        table.add_row("Cache Writes", f"{stats['total_writes']:,} tokens")

        # Cost savings
        savings_color = "green" if stats["savings"] > 0 else "dim"
        table.add_row(
            "Estimated Savings",
            f"[bold {savings_color}]${stats['savings']:.2f}[/bold {savings_color}]",
        )

        # Requests
        table.add_row("Requests with Cache Hits", f"{stats['hit_count']:,}")
        table.add_row("Total Requests", f"{stats['total_requests']:,}")

        console.print(table)

        # Per-workflow breakdown
        if stats["by_workflow"]:
            console.print("\n")
            wf_table = Table(
                title="Cache Performance by Workflow",
                show_header=True,
                header_style="bold magenta",
            )
            wf_table.add_column("Workflow", style="cyan")
            wf_table.add_column("Hit Rate", justify="right")
            wf_table.add_column("Reads", justify="right")
            wf_table.add_column("Writes", justify="right")

            # Sort by hit rate descending
            sorted_workflows = sorted(
                stats["by_workflow"].items(),
                key=lambda x: x[1].get("hit_rate", 0),
                reverse=True,
            )

            for workflow, wf_stats in sorted_workflows[:10]:  # Top 10
                hit_rate = wf_stats.get("hit_rate", 0.0)
                hit_rate_color = "green" if hit_rate > 0.5 else "yellow"
                wf_table.add_row(
                    workflow,
                    f"[{hit_rate_color}]{hit_rate:.1%}[/{hit_rate_color}]",
                    f"{wf_stats['reads']:,}",
                    f"{wf_stats['writes']:,}",
                )

            console.print(wf_table)

        # Recommendations
        if stats["hit_rate"] < 0.3:
            console.print("\n")
            console.print(
                Panel(
                    "[yellow]⚠ Cache hit rate is low (<30%)[/yellow]\n\n"
                    "Recommendations:\n"
                    "  • Increase reuse of system prompts across requests\n"
                    "  • Group similar requests together (5-min cache TTL)\n"
                    "  • Consider using workflow batching\n"
                    "  • Structure prompts with static content first",
                    title="Optimization Tips",
                    border_style="yellow",
                ),
            )
    else:
        # Fallback to plain text
        print("\n" + "=" * 60)
        print(f"PROMPT CACHING STATS (LAST {days} DAYS)")
        print("=" * 60)
        print(f"Cache Hit Rate: {stats['hit_rate']:.1%}")
        print(f"Cache Reads: {stats['total_reads']:,} tokens")
        print(f"Cache Writes: {stats['total_writes']:,} tokens")
        print(f"Estimated Savings: ${stats['savings']:.2f}")
        print(f"Requests with Cache Hits: {stats['hit_count']:,}")
        print(f"Total Requests: {stats['total_requests']:,}")
        print("=" * 60)

        if stats["hit_rate"] < 0.3:
            print("\n⚠ Cache hit rate is low (<30%)")
            print("Recommendations:")
            print("  • Increase reuse of system prompts across requests")
            print("  • Group similar requests together (5-min cache TTL)")
            print("  • Consider using workflow batching")

    return 0


def cmd_telemetry_compare(args: Any) -> int:
    """Compare telemetry across two time periods.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    tracker = UsageTracker.get_instance()
    period1_days = getattr(args, "period1", 7)
    period2_days = getattr(args, "period2", 30)

    # Get stats for both periods
    stats1 = tracker.get_stats(days=period1_days)
    stats2 = tracker.get_stats(days=period2_days)

    if stats1["total_calls"] == 0 or stats2["total_calls"] == 0:
        print("Insufficient telemetry data for comparison.")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()
        table = Table(title="Telemetry Comparison", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column(f"Last {period1_days} days", justify="right", style="green")
        table.add_column(f"Last {period2_days} days", justify="right", style="yellow")
        table.add_column("Change", justify="right", style="blue")

        # Total calls
        calls_change = (
            ((stats1["total_calls"] - stats2["total_calls"]) / stats2["total_calls"] * 100)
            if stats2["total_calls"] > 0
            else 0
        )
        table.add_row(
            "Total Calls",
            str(stats1["total_calls"]),
            str(stats2["total_calls"]),
            f"{calls_change:+.1f}%",
        )

        # Total cost
        cost_change = (
            ((stats1["total_cost"] - stats2["total_cost"]) / stats2["total_cost"] * 100)
            if stats2["total_cost"] > 0
            else 0
        )
        table.add_row(
            "Total Cost",
            f"${stats1['total_cost']:.2f}",
            f"${stats2['total_cost']:.2f}",
            f"{cost_change:+.1f}%",
        )

        # Avg cost per call
        avg1 = stats1["total_cost"] / stats1["total_calls"] if stats1["total_calls"] > 0 else 0
        avg2 = stats2["total_cost"] / stats2["total_calls"] if stats2["total_calls"] > 0 else 0
        avg_change = ((avg1 - avg2) / avg2 * 100) if avg2 > 0 else 0
        table.add_row(
            "Avg Cost/Call",
            f"${avg1:.4f}",
            f"${avg2:.4f}",
            f"{avg_change:+.1f}%",
        )

        # Cache hit rate
        cache_change = stats1["cache_hit_rate"] - stats2["cache_hit_rate"]
        table.add_row(
            "Cache Hit Rate",
            f"{stats1['cache_hit_rate']:.1f}%",
            f"{stats2['cache_hit_rate']:.1f}%",
            f"{cache_change:+.1f}pp",
        )

        console.print(table)
    else:
        # Fallback to plain text
        print("\n" + "=" * 80)
        print("TELEMETRY COMPARISON")
        print("=" * 80)
        print(
            f"{'Metric':<20} {'Last ' + str(period1_days) + ' days':>20} {'Last ' + str(period2_days) + ' days':>20} {'Change':>15}",
        )
        print("-" * 80)

        calls_change = (
            ((stats1["total_calls"] - stats2["total_calls"]) / stats2["total_calls"] * 100)
            if stats2["total_calls"] > 0
            else 0
        )
        print(
            f"{'Total Calls':<20} {stats1['total_calls']:>20} {stats2['total_calls']:>20} {calls_change:>14.1f}%",
        )

        cost_change = (
            ((stats1["total_cost"] - stats2["total_cost"]) / stats2["total_cost"] * 100)
            if stats2["total_cost"] > 0
            else 0
        )
        print(
            f"{'Total Cost':<20} ${stats1['total_cost']:>19.2f} ${stats2['total_cost']:>19.2f} {cost_change:>14.1f}%",
        )

        avg1 = stats1["total_cost"] / stats1["total_calls"] if stats1["total_calls"] > 0 else 0
        avg2 = stats2["total_cost"] / stats2["total_calls"] if stats2["total_calls"] > 0 else 0
        avg_change = ((avg1 - avg2) / avg2 * 100) if avg2 > 0 else 0
        print(f"{'Avg Cost/Call':<20} ${avg1:>19.4f} ${avg2:>19.4f} {avg_change:>14.1f}%")

        cache_change = stats1["cache_hit_rate"] - stats2["cache_hit_rate"]
        print(
            f"{'Cache Hit Rate':<20} {stats1['cache_hit_rate']:>19.1f}% {stats2['cache_hit_rate']:>19.1f}% {cache_change:>14.1f}pp",
        )

        print("=" * 80)

    return 0


def cmd_telemetry_reset(args: Any) -> int:
    """Reset/clear all telemetry data.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    tracker = UsageTracker.get_instance()
    confirm = getattr(args, "confirm", False)

    if not confirm:
        print("WARNING: This will permanently delete all telemetry data.")
        print(f"Location: {tracker.telemetry_dir}")
        print("\nUse --confirm to proceed.")
        return 1

    count = tracker.reset()
    print(f"Deleted {count} telemetry entries.")
    print("New tracking starts now.")
    return 0


def cmd_telemetry_export(args: Any) -> int:
    """Export telemetry data to JSON or CSV.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    tracker = UsageTracker.get_instance()
    format_type = getattr(args, "format", "json")
    output_file = getattr(args, "output", None)
    days = getattr(args, "days", None)

    entries = tracker.export_to_dict(days=days)

    if not entries:
        print("No telemetry data to export.")
        return 0

    if format_type == "json":
        # Export as JSON
        if output_file:
            validated_path = _validate_file_path(output_file)
            with open(validated_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
            print(f"Exported {len(entries)} entries to {validated_path}")
        else:
            print(json.dumps(entries, indent=2))
    elif format_type == "csv":
        # Export as CSV
        if not entries:
            print("No data to export.")
            return 0

        # Get all possible fields
        fieldnames = [
            "ts",
            "workflow",
            "stage",
            "tier",
            "model",
            "provider",
            "cost",
            "tokens_input",
            "tokens_output",
            "cache_hit",
            "cache_type",
            "duration_ms",
        ]

        if output_file:
            validated_path = _validate_file_path(output_file)
            with open(validated_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for entry in entries:
                    row = {
                        "ts": entry.get("ts", ""),
                        "workflow": entry.get("workflow", ""),
                        "stage": entry.get("stage", ""),
                        "tier": entry.get("tier", ""),
                        "model": entry.get("model", ""),
                        "provider": entry.get("provider", ""),
                        "cost": entry.get("cost", 0.0),
                        "tokens_input": entry.get("tokens", {}).get("input", 0),
                        "tokens_output": entry.get("tokens", {}).get("output", 0),
                        "cache_hit": entry.get("cache", {}).get("hit", False),
                        "cache_type": entry.get("cache", {}).get("type", ""),
                        "duration_ms": entry.get("duration_ms", 0),
                    }
                    writer.writerow(row)
            print(f"Exported {len(entries)} entries to {validated_path}")
        else:
            # Print to stdout
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            for entry in entries:
                row = {
                    "ts": entry.get("ts", ""),
                    "workflow": entry.get("workflow", ""),
                    "stage": entry.get("stage", ""),
                    "tier": entry.get("tier", ""),
                    "model": entry.get("model", ""),
                    "provider": entry.get("provider", ""),
                    "cost": entry.get("cost", 0.0),
                    "tokens_input": entry.get("tokens", {}).get("input", 0),
                    "tokens_output": entry.get("tokens", {}).get("output", 0),
                    "cache_hit": entry.get("cache", {}).get("hit", False),
                    "cache_type": entry.get("cache", {}).get("type", ""),
                    "duration_ms": entry.get("duration_ms", 0),
                }
                writer.writerow(row)
    else:
        print(f"Unknown format: {format_type}")
        print("Supported formats: json, csv")
        return 1

    return 0
