#!/usr/bin/env python3
"""Attune AI CLI.

IMPORTANT: This CLI is for automation only (git hooks, scripts, CI/CD).
For interactive use, use Claude Code skills in VSCode or Claude Desktop.

Automation commands:
    attune workflow list              List available workflows
    attune workflow run <name>        Execute a workflow
    attune workflow info <name>       Show workflow details

Cost tracking:
    attune costs                      Show cost report (last 7 days)
    attune costs --days 30            Show cost report for 30 days
    attune costs --json               Output cost data as JSON
    attune costs --workflow NAME      Filter by workflow
    attune costs today                Show today's costs
    attune costs export -o FILE       Export costs to file
    attune costs reset --confirm      Clear all cost data

Utility commands:
    attune features                   Show available features and dependencies
    attune telemetry show             Display usage summary
    attune telemetry savings          Show cost savings
    attune telemetry export           Export to CSV/JSON
    attune telemetry routing-stats    Show adaptive routing statistics
    attune telemetry routing-check    Check for tier upgrade recommendations
    attune telemetry models           Show model performance by provider
    attune telemetry agents           Show active agents and their status
    attune telemetry signals          Show coordination signals for an agent

    attune provider show              Show current provider config
    attune provider set <name>        Set provider (anthropic)

    attune validate                   Validate configuration
    attune version                    Show version

For interactive development, use Claude Code skills:
    /dev        Developer tools (commit, review, debug, refactor)
    /testing    Run tests, coverage, generate tests
    /workflows  AI-powered workflows (security, bug prediction)
    /docs       Documentation generation
    /release    Release preparation
    /learning   Session evaluation and improvement
"""

from __future__ import annotations

import argparse
import logging
import sys

from attune.cli_commands.cost_commands import (
    cmd_costs,
    cmd_costs_export,
    cmd_costs_reset,
    cmd_costs_today,
)
from attune.cli_commands.memory_commands import (
    cmd_forget,
    cmd_lessons,
    cmd_remember,
)
from attune.cli_commands.provider_commands import (
    cmd_provider_set,
    cmd_provider_show,
)
from attune.cli_commands.telemetry_commands import (
    cmd_telemetry_agents,
    cmd_telemetry_export,
    cmd_telemetry_models,
    cmd_telemetry_routing_check,
    cmd_telemetry_routing_stats,
    cmd_telemetry_savings,
    cmd_telemetry_show,
    cmd_telemetry_signals,
)
from attune.cli_commands.utility_commands import (
    cmd_features,
    cmd_setup,
    cmd_validate,
    cmd_version,
)
from attune.cli_commands.workflow_commands import (
    cmd_workflow_info,
    cmd_workflow_list,
    cmd_workflow_run,
)

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Get package version."""
    try:
        from importlib.metadata import version

        return version("attune-ai")
    except Exception:
        # INTENTIONAL: Fallback for dev installs without metadata
        return "dev"


# =============================================================================
# Main Entry Point
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="attune",
        description="Attune AI CLI (automation interface - for git hooks, scripts, CI/CD)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
NOTE: This CLI is for automation only. For interactive development,
use Claude Code skills in VSCode or Claude Desktop:

    /dev        Developer tools (commit, review, debug, refactor)
    /testing    Run tests, coverage, generate tests
    /workflows  AI-powered workflows (security, bug prediction)
    /learning   Session evaluation

Documentation: https://smartaimemory.com/framework-docs/
        """,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Workflow commands ---
    workflow_parser = subparsers.add_parser("workflow", help="Workflow management")
    workflow_sub = workflow_parser.add_subparsers(dest="workflow_command")

    # workflow list
    workflow_sub.add_parser("list", help="List available workflows")

    # workflow info
    info_parser = workflow_sub.add_parser("info", help="Show workflow details")
    info_parser.add_argument("name", help="Workflow name")

    # workflow run
    run_parser = workflow_sub.add_parser("run", help="Run a workflow")
    run_parser.add_argument("name", help="Workflow name")
    run_parser.add_argument("--input", "-i", help="JSON input data")
    run_parser.add_argument("--path", "-p", help="Target path")
    run_parser.add_argument("--target", "-t", help="Target value (e.g., coverage target)")
    run_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    # --- Telemetry commands ---
    telemetry_parser = subparsers.add_parser("telemetry", help="Usage telemetry")
    telemetry_sub = telemetry_parser.add_subparsers(dest="telemetry_command")

    # telemetry show
    show_parser = telemetry_sub.add_parser("show", help="Display usage summary")
    show_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days (default: 30)",
    )

    # telemetry savings
    savings_parser = telemetry_sub.add_parser("savings", help="Show cost savings")
    savings_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days (default: 30)",
    )

    # telemetry export
    export_parser = telemetry_sub.add_parser("export", help="Export telemetry data")
    export_parser.add_argument("--output", "-o", required=True, help="Output file path")
    export_parser.add_argument(
        "--format",
        "-f",
        choices=["csv", "json"],
        default="json",
        help="Output format",
    )
    export_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days (default: 30)",
    )

    # telemetry routing-stats
    routing_stats_parser = telemetry_sub.add_parser(
        "routing-stats",
        help="Show adaptive routing statistics",
    )
    routing_stats_parser.add_argument("--workflow", "-w", help="Workflow name")
    routing_stats_parser.add_argument("--stage", "-s", help="Stage name")
    routing_stats_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=7,
        help="Number of days (default: 7)",
    )

    # telemetry routing-check
    routing_check_parser = telemetry_sub.add_parser(
        "routing-check",
        help="Check for tier upgrade recommendations",
    )
    routing_check_parser.add_argument("--workflow", "-w", help="Workflow name")
    routing_check_parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Check all workflows",
    )

    # telemetry models
    models_parser = telemetry_sub.add_parser("models", help="Show model performance by provider")
    models_parser.add_argument(
        "--provider",
        "-p",
        choices=["anthropic"],
        help="Filter by provider",
    )
    models_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=7,
        help="Number of days (default: 7)",
    )

    # telemetry agents
    telemetry_sub.add_parser("agents", help="Show active agents and their status")

    # telemetry signals
    signals_parser = telemetry_sub.add_parser("signals", help="Show coordination signals")
    signals_parser.add_argument("--agent", "-a", required=True, help="Agent ID to view signals for")

    # --- Provider commands ---
    provider_parser = subparsers.add_parser("provider", help="LLM provider configuration")
    provider_sub = provider_parser.add_subparsers(dest="provider_command")

    # provider show
    provider_sub.add_parser("show", help="Show current provider")

    # provider set
    set_parser = provider_sub.add_parser("set", help="Set provider")
    set_parser.add_argument("name", choices=["anthropic"], help="Provider name")

    # --- Memory commands (quick lessons) ---
    remember_parser = subparsers.add_parser(
        "remember",
        help='Save a lesson: attune remember "lesson text"',
    )
    remember_parser.add_argument("lesson_text", help="Lesson to remember")
    remember_parser.add_argument(
        "--global",
        action="store_true",
        dest="global",
        help="Save to global ~/.attune/lessons.md instead of project",
    )

    forget_parser = subparsers.add_parser("forget", help="Remove a lesson by number or keyword")
    forget_parser.add_argument("identifier", help="Line number or keyword to match")

    lessons_parser = subparsers.add_parser("lessons", help="List current lessons")
    lessons_parser.add_argument(
        "--global",
        action="store_true",
        dest="global",
        help="Show only global lessons",
    )

    # --- Cost tracking commands ---
    costs_parser = subparsers.add_parser("costs", help="View API cost tracking and savings")
    costs_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=7,
        help="Number of days (default: 7)",
    )
    costs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    costs_parser.add_argument("--workflow", "-w", help="Filter by workflow name")

    costs_sub = costs_parser.add_subparsers(dest="costs_command")

    # costs today
    costs_sub.add_parser("today", help="Show today's costs")

    # costs export
    costs_export = costs_sub.add_parser("export", help="Export cost data")
    costs_export.add_argument("--output", "-o", required=True, help="Output file path")
    costs_export.add_argument(
        "--format",
        "-f",
        choices=["csv", "json"],
        default="json",
        help="Output format",
    )
    costs_export.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days (default: 30)",
    )

    # costs reset
    costs_reset = costs_sub.add_parser("reset", help="Clear all cost data")
    costs_reset.add_argument("--confirm", action="store_true", help="Confirm deletion (required)")

    # --- Setup command ---
    subparsers.add_parser("setup", help="Install slash commands to ~/.claude/commands/")

    # --- Utility commands ---
    subparsers.add_parser("features", help="Show available features and dependencies")
    subparsers.add_parser("validate", help="Validate configuration")

    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed info")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    # Route to command handlers
    if args.command == "workflow":
        if args.workflow_command == "list":
            return cmd_workflow_list(args)
        if args.workflow_command == "info":
            return cmd_workflow_info(args)
        if args.workflow_command == "run":
            return cmd_workflow_run(args)
        print("Usage: attune workflow {list|info|run}")
        return 1

    if args.command == "telemetry":
        if args.telemetry_command == "show":
            return cmd_telemetry_show(args)
        if args.telemetry_command == "savings":
            return cmd_telemetry_savings(args)
        if args.telemetry_command == "export":
            return cmd_telemetry_export(args)
        if args.telemetry_command == "routing-stats":
            return cmd_telemetry_routing_stats(args)
        if args.telemetry_command == "routing-check":
            return cmd_telemetry_routing_check(args)
        if args.telemetry_command == "models":
            return cmd_telemetry_models(args)
        if args.telemetry_command == "agents":
            return cmd_telemetry_agents(args)
        if args.telemetry_command == "signals":
            return cmd_telemetry_signals(args)
        print(
            "Usage: attune telemetry {show|savings|export|routing-stats|routing-check|models|agents|signals}",
        )
        return 1

    if args.command == "provider":
        if args.provider_command == "show":
            return cmd_provider_show(args)
        if args.provider_command == "set":
            return cmd_provider_set(args)
        print("Usage: attune provider {show|set}")
        return 1

    if args.command == "remember":
        return cmd_remember(args)

    if args.command == "forget":
        return cmd_forget(args)

    if args.command == "lessons":
        return cmd_lessons(args)

    if args.command == "costs":
        if getattr(args, "costs_command", None) == "today":
            return cmd_costs_today(args)
        if getattr(args, "costs_command", None) == "export":
            return cmd_costs_export(args)
        if getattr(args, "costs_command", None) == "reset":
            return cmd_costs_reset(args)
        # Default: show cost report
        return cmd_costs(args)

    if args.command == "setup":
        return cmd_setup(args)

    if args.command == "features":
        return cmd_features(args)

    if args.command == "validate":
        return cmd_validate(args)

    if args.command == "version":
        return cmd_version(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
