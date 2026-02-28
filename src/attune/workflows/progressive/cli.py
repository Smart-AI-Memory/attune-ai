"""CLI commands for progressive workflow management.

Provides commands for:
- Listing saved results
- Viewing detailed reports
- Generating analytics
- Cleaning up old results
"""

import argparse
import sys

from attune.workflows.progressive.reports import (
    cleanup_old_results,
    format_cost_analytics_report,
    generate_cost_analytics,
    list_saved_results,
    load_result_from_disk,
)


def cmd_list_results(args: argparse.Namespace) -> int:
    """List all saved progressive workflow results.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success)

    """
    storage_path = args.storage_path or ".attune/progressive_runs"
    results = list_saved_results(storage_path)

    if not results:
        print(f"No results found in {storage_path}")
        return 0

    print(f"\n📋 Found {len(results)} progressive workflow results:\n")
    print(f"{'Task ID':<40} {'Workflow':<15} {'Cost':<10} {'Savings':<12} {'Success'}")
    print("─" * 90)

    for result in results:
        task_id = result.get("task_id", "unknown")
        workflow = result.get("workflow", "unknown")[:14]
        cost = result.get("total_cost", 0.0)
        savings = result.get("cost_savings_percent", 0.0)
        success = "✅" if result.get("success", False) else "❌"

        print(f"{task_id:<40} {workflow:<15} ${cost:<9.2f} {savings:>6.1f}%      {success}")

    print()
    return 0


def cmd_show_report(args: argparse.Namespace) -> int:
    """Show detailed report for a specific task.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)

    """
    task_id = args.task_id
    storage_path = args.storage_path or ".attune/progressive_runs"

    try:
        result_data = load_result_from_disk(task_id, storage_path)

        if args.json:
            import json

            print(json.dumps(result_data, indent=2))
        else:
            # Show human-readable report
            report = result_data.get("report", "")
            if report:
                print(report)
            else:
                print("No report found for this task")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_analytics(args: argparse.Namespace) -> int:
    """Show cost optimization analytics.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success)

    """
    storage_path = args.storage_path or ".attune/progressive_runs"
    analytics = generate_cost_analytics(storage_path)

    if analytics["total_runs"] == 0:
        print(f"No results found in {storage_path}")
        return 0

    if args.json:
        import json

        print(json.dumps(analytics, indent=2))
    else:
        report = format_cost_analytics_report(analytics)
        print(report)

    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Clean up old progressive workflow results.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success)

    """
    storage_path = args.storage_path or ".attune/progressive_runs"
    retention_days = args.retention_days
    dry_run = args.dry_run

    deleted, retained = cleanup_old_results(
        storage_path=storage_path,
        retention_days=retention_days,
        dry_run=dry_run,
    )

    if dry_run:
        print("\n🔍 Dry run mode - no files deleted\n")
        print(f"Would delete: {deleted} results older than {retention_days} days")
        print(f"Would retain: {retained} recent results")
    else:
        print("\n🗑️  Cleanup complete\n")
        print(f"Deleted: {deleted} results older than {retention_days} days")
        print(f"Retained: {retained} recent results")

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for progressive CLI.

    Returns:
        Configured argument parser

    """
    parser = argparse.ArgumentParser(
        prog="empathy progressive",
        description="Manage progressive tier escalation workflows",
    )

    parser.add_argument(
        "--storage-path",
        type=str,
        default=None,
        help="Custom storage path (default: .attune/progressive_runs)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all saved progressive workflow results")
    list_parser.set_defaults(func=cmd_list_results)

    # Show command
    show_parser = subparsers.add_parser("show", help="Show detailed report for a specific task")
    show_parser.add_argument("task_id", type=str, help="Task ID to display")
    show_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    show_parser.set_defaults(func=cmd_show_report)

    # Analytics command
    analytics_parser = subparsers.add_parser("analytics", help="Show cost optimization analytics")
    analytics_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    analytics_parser.set_defaults(func=cmd_analytics)

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Clean up old progressive workflow results",
    )
    cleanup_parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Number of days to retain results (default: 30)",
    )
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    cleanup_parser.set_defaults(func=cmd_cleanup)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for progressive CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code

    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
