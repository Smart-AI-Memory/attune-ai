"""Tier 1 automation monitoring CLI commands.

Commands for monitoring task routing, test execution, coverage, and agent performance.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

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


def cmd_tier1_status(args: Any) -> int:
    """Show comprehensive Tier 1 automation status.

    Args:
        args: Parsed command-line arguments (hours)

    Returns:
        Exit code (0 for success)

    """
    from datetime import timedelta

    from attune.models.telemetry import TelemetryAnalytics, get_telemetry_store

    try:
        store = get_telemetry_store()
        analytics = TelemetryAnalytics(store)

        hours = getattr(args, "hours", 24)
        since = datetime.utcnow() - timedelta(hours=hours)

        summary = analytics.tier1_summary(since=since)
    except Exception as e:
        print(f"Error retrieving Tier 1 status: {e}")
        return 1

    if RICH_AVAILABLE and Console is not None:
        console = Console()

        # Task Routing Panel
        routing = summary["task_routing"]
        routing_text = Text()
        routing_text.append(f"Total Tasks: {routing['total_tasks']}\n")
        routing_text.append(f"Success Rate: {routing['accuracy_rate']:.1%}\n", style="green bold")
        routing_text.append(f"Avg Confidence: {routing['avg_confidence']:.2f}\n")

        # Test Execution Panel
        tests = summary["test_execution"]
        tests_text = Text()
        tests_text.append(f"Total Runs: {tests['total_executions']}\n")
        tests_text.append(f"Success Rate: {tests['success_rate']:.1%}\n", style="green bold")
        tests_text.append(f"Avg Duration: {tests['avg_duration_seconds']:.1f}s\n")
        tests_text.append(f"Total Failures: {tests['total_failures']}\n")

        # Coverage Panel
        coverage = summary["coverage"]
        coverage_text = Text()
        coverage_text.append(f"Current: {coverage['current_coverage']:.1f}%\n", style="cyan bold")
        coverage_text.append(f"Change: {coverage['change']:+.1f}%\n")
        coverage_text.append(f"Trend: {coverage['trend']}\n")
        coverage_text.append(f"Critical Gaps: {coverage['critical_gaps_count']}\n")

        # Agent Performance Panel
        agent = summary["agent_performance"]
        agent_text = Text()
        agent_text.append(f"Active Agents: {len(agent['by_agent'])}\n")
        agent_text.append(f"Automation Rate: {agent['automation_rate']:.1%}\n", style="green bold")
        agent_text.append(f"Human Review Rate: {agent['human_review_rate']:.1%}\n")

        # Display all panels
        console.print(f"\n[bold]Tier 1 Automation Status[/bold] (last {hours} hours)\n")
        console.print(Panel(routing_text, title="Task Routing", border_style="blue"))
        console.print(Panel(tests_text, title="Test Execution", border_style="green"))
        console.print(Panel(coverage_text, title="Coverage", border_style="cyan"))
        console.print(Panel(agent_text, title="Agent Performance", border_style="magenta"))
    else:
        # Plain text fallback
        routing = summary["task_routing"]
        tests = summary["test_execution"]
        coverage = summary["coverage"]
        agent = summary["agent_performance"]

        print(f"\nTier 1 Automation Status (last {hours} hours)")
        print("=" * 50)
        print("\nTask Routing:")
        print(f"  Total Tasks: {routing['total_tasks']}")
        print(f"  Success Rate: {routing['accuracy_rate']:.1%}")
        print(f"  Avg Confidence: {routing['avg_confidence']:.2f}")

        print("\nTest Execution:")
        print(f"  Total Runs: {tests['total_executions']}")
        print(f"  Success Rate: {tests['success_rate']:.1%}")
        print(f"  Avg Duration: {tests['avg_duration_seconds']:.1f}s")

        print("\nCoverage:")
        print(f"  Current: {coverage['current_coverage']:.1f}%")
        print(f"  Trend: {coverage['trend']}")

        print("\nAgent Performance:")
        print(f"  Active Agents: {len(agent['by_agent'])}")
        print(f"  Automation Rate: {agent['automation_rate']:.1%}")

    return 0


def cmd_task_routing_report(args: Any) -> int:
    """Show detailed task routing report.

    Args:
        args: Parsed command-line arguments (hours)

    Returns:
        Exit code (0 for success)

    """
    from datetime import timedelta

    from attune.models.telemetry import TelemetryAnalytics, get_telemetry_store

    try:
        store = get_telemetry_store()
        analytics = TelemetryAnalytics(store)

        hours = getattr(args, "hours", 24)
        since = datetime.utcnow() - timedelta(hours=hours)

        stats = analytics.task_routing_accuracy(since=since)
    except Exception as e:
        print(f"Error retrieving task routing report: {e}")
        return 1

    if not stats["total_tasks"]:
        print(f"No task routing data found in the last {hours} hours.")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()

        # Summary table
        table = Table(title=f"Task Routing Report (last {hours} hours)")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total Tasks", str(stats["total_tasks"]))
        table.add_row("Successful", str(stats["successful_routing"]))
        table.add_row("Accuracy Rate", f"{stats['accuracy_rate']:.1%}")
        table.add_row("Avg Confidence", f"{stats['avg_confidence']:.2f}")

        console.print(table)

        # By task type table
        if stats["by_task_type"]:
            type_table = Table(title="Breakdown by Task Type")
            type_table.add_column("Task Type", style="cyan")
            type_table.add_column("Total", justify="right")
            type_table.add_column("Success", justify="right")
            type_table.add_column("Rate", justify="right", style="green")

            for task_type, data in stats["by_task_type"].items():
                type_table.add_row(
                    task_type,
                    str(data["total"]),
                    str(data["success"]),
                    f"{data['rate']:.1%}",
                )

            console.print(type_table)
    else:
        # Plain text fallback
        print(f"\nTask Routing Report (last {hours} hours)")
        print("=" * 50)
        print(f"Total Tasks: {stats['total_tasks']}")
        print(f"Successful: {stats['successful_routing']}")
        print(f"Accuracy Rate: {stats['accuracy_rate']:.1%}")
        print(f"Avg Confidence: {stats['avg_confidence']:.2f}")

        if stats["by_task_type"]:
            print("\nBy Task Type:")
            for task_type, data in stats["by_task_type"].items():
                print(f"  {task_type}: {data['success']}/{data['total']} ({data['rate']:.1%})")

    return 0


def cmd_test_status(args: Any) -> int:
    """Show test execution status.

    Args:
        args: Parsed command-line arguments (hours)

    Returns:
        Exit code (0 for success)

    """
    from datetime import timedelta

    from attune.models.telemetry import TelemetryAnalytics, get_telemetry_store

    try:
        store = get_telemetry_store()
        analytics = TelemetryAnalytics(store)

        hours = getattr(args, "hours", 24)
        since = datetime.utcnow() - timedelta(hours=hours)

        stats = analytics.test_execution_trends(since=since)
        coverage = analytics.coverage_progress(since=since)
    except Exception as e:
        print(f"Error retrieving test status: {e}")
        return 1

    if not stats["total_executions"]:
        print(f"No test execution data found in the last {hours} hours.")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()

        # Test execution table
        table = Table(title=f"Test Execution Status (last {hours} hours)")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total Runs", str(stats["total_executions"]))
        table.add_row("Success Rate", f"{stats['success_rate']:.1%}")
        table.add_row("Avg Duration", f"{stats['avg_duration_seconds']:.1f}s")
        table.add_row("Total Tests Run", str(stats["total_tests_run"]))
        table.add_row("Total Failures", str(stats["total_failures"]))
        table.add_row("Current Coverage", f"{coverage['current_coverage']:.1f}%")
        table.add_row("Coverage Trend", coverage["trend"])

        console.print(table)

        # Most failing tests
        if stats["most_failing_tests"]:
            fail_table = Table(title="Most Frequently Failing Tests")
            fail_table.add_column("Test Name", style="cyan")
            fail_table.add_column("Failures", justify="right", style="red")

            for test in stats["most_failing_tests"][:10]:
                fail_table.add_row(test["name"], str(test["failures"]))

            console.print(fail_table)
    else:
        # Plain text fallback
        print(f"\nTest Execution Status (last {hours} hours)")
        print("=" * 50)
        print(f"Total Runs: {stats['total_executions']}")
        print(f"Success Rate: {stats['success_rate']:.1%}")
        print(f"Avg Duration: {stats['avg_duration_seconds']:.1f}s")
        print(f"Total Tests Run: {stats['total_tests_run']}")
        print(f"Total Failures: {stats['total_failures']}")
        print(f"Current Coverage: {coverage['current_coverage']:.1f}%")

        if stats["most_failing_tests"]:
            print("\nMost Frequently Failing Tests:")
            for test in stats["most_failing_tests"][:10]:
                print(f"  {test['name']}: {test['failures']} failures")

    return 0


def cmd_agent_performance(args: Any) -> int:
    """Show agent performance metrics.

    Args:
        args: Parsed command-line arguments (hours)

    Returns:
        Exit code (0 for success)

    """
    from datetime import timedelta

    from attune.models.telemetry import TelemetryAnalytics, get_telemetry_store

    try:
        store = get_telemetry_store()
        analytics = TelemetryAnalytics(store)

        hours = getattr(args, "hours", 168)  # Default 7 days for agent performance
        since = datetime.utcnow() - timedelta(hours=hours)

        stats = analytics.agent_performance(since=since)
    except Exception as e:
        print(f"Error retrieving agent performance: {e}")
        return 1

    if not stats["by_agent"]:
        print(f"No agent assignment data found in the last {hours} hours.")
        return 0

    if RICH_AVAILABLE and Console is not None:
        console = Console()

        # Agent performance table
        table = Table(title=f"Agent Performance (last {hours} hours)")
        table.add_column("Agent", style="cyan")
        table.add_column("Assignments", justify="right")
        table.add_column("Completed", justify="right")
        table.add_column("Success Rate", justify="right", style="green")
        table.add_column("Avg Duration", justify="right")

        for agent, data in stats["by_agent"].items():
            table.add_row(
                agent,
                str(data["assignments"]),
                str(data["completed"]),
                f"{data['success_rate']:.1%}",
                f"{data['avg_duration_hours']:.2f}h",
            )

        console.print(table)

        # Summary panel
        summary_text = Text()
        summary_text.append(
            f"Automation Rate: {stats['automation_rate']:.1%}\n",
            style="green bold",
        )
        summary_text.append(f"Human Review Rate: {stats['human_review_rate']:.1%}\n")

        console.print(Panel(summary_text, title="Summary", border_style="blue"))
    else:
        # Plain text fallback
        print(f"\nAgent Performance (last {hours} hours)")
        print("=" * 50)

        for agent, data in stats["by_agent"].items():
            print(f"\n{agent}:")
            print(f"  Assignments: {data['assignments']}")
            print(f"  Completed: {data['completed']}")
            print(f"  Success Rate: {data['success_rate']:.1%}")
            print(f"  Avg Duration: {data['avg_duration_hours']:.2f}h")

        print(f"\nAutomation Rate: {stats['automation_rate']:.1%}")
        print(f"Human Review Rate: {stats['human_review_rate']:.1%}")

    return 0
