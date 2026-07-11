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
    attune telemetry status           Show opt-in usage-ping status + payload
    attune telemetry enable           Opt in to anonymous usage pinging
    attune telemetry disable          Opt out of anonymous usage pinging

    attune provider show              Show current provider config
    attune provider set <name>        Set provider (anthropic)

    attune auth status                Show subscription/auth strategy status
    attune auth status --json         Output subscription status as JSON
    attune auth setup                 Configure auth strategy interactively
    attune auth reset --confirm       Clear auth strategy configuration
    attune auth recommend <file>      Get auth recommendation for a file

    attune validate                   Validate configuration
    attune version                    Show version

For interactive development, use Claude Code skills:
    /dev        Developer tools (commit, review, debug, refactor)
    /testing    Run tests, coverage, generate tests
    /workflows  AI-powered workflows (security, bug prediction)
    /docs       Documentation generation
    /release    Release preparation
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
from attune.cli_commands.curator import cmd_curator
from attune.cli_commands.help_commands import cmd_help
from attune.cli_commands.memory_agent import cmd_memory_agent
from attune.cli_commands.memory_commands import (
    cmd_forget,
    cmd_lessons,
    cmd_memory_capture,
    cmd_memory_forget_topic,
    cmd_memory_recall,
    cmd_memory_topics,
    cmd_remember,
)
from attune.cli_commands.pattern_review import (
    cmd_patterns_promote,
    cmd_patterns_reject,
    cmd_patterns_review,
)
from attune.cli_commands.provider_commands import (
    cmd_provider_set,
    cmd_provider_show,
)
from attune.cli_commands.telemetry_commands import (
    cmd_telemetry_agents,
    cmd_telemetry_disable,
    cmd_telemetry_enable,
    cmd_telemetry_export,
    cmd_telemetry_models,
    cmd_telemetry_routing_check,
    cmd_telemetry_routing_stats,
    cmd_telemetry_savings,
    cmd_telemetry_show,
    cmd_telemetry_signals,
    cmd_telemetry_status,
)
from attune.cli_commands.utility_commands import (
    cmd_doctor,
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
from attune.models.auth_cli import (
    cmd_auth_recommend,
    cmd_auth_reset,
    cmd_auth_setup,
    cmd_auth_status,
)
from attune.ops.cli import add_subparser as _add_ops_subparser
from attune.ops.cli import cmd_ops

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Get package version."""
    try:
        from importlib.metadata import version

        return version("attune-ai")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Fallback for dev installs without metadata
        return "dev"


# =============================================================================
# Main Entry Point
# =============================================================================


def _add_workflow_subparsers(subparsers: argparse._SubParsersAction) -> None:
    """Add workflow subcommand parsers.

    Args:
        subparsers: Parent subparsers action to attach to

    """
    workflow_parser = subparsers.add_parser("workflow", help="Workflow management")
    workflow_sub = workflow_parser.add_subparsers(dest="workflow_command")

    workflow_sub.add_parser("list", help="List available workflows")

    info_parser = workflow_sub.add_parser("info", help="Show workflow details")
    info_parser.add_argument("name", help="Workflow name")

    run_parser = workflow_sub.add_parser("run", help="Run a workflow")
    run_parser.add_argument("name", help="Workflow name")
    run_parser.add_argument("--input", "-i", help="JSON input data")
    run_parser.add_argument(
        "--path",
        "-p",
        default=".",
        help="Target path (defaults to current directory)",
    )
    run_parser.add_argument("--target", "-t", help="Target value (e.g., coverage target)")
    run_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help=(
            "Full report disclosure (detail sections inline); "
            "discovery-sweep: include rejected bucket in markdown output"
        ),
    )
    run_parser.add_argument(
        "--no-llm",
        dest="no_llm",
        action="store_true",
        help="Discovery-sweep: filter to non-LLM sources only (pattern scan)",
    )
    run_parser.add_argument(
        "--source",
        help="Discovery-sweep: run only the named source (e.g. bug-predict)",
    )
    run_parser.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        help="Analysis depth (workflow-specific); defaults to 'standard'",
    )
    run_parser.add_argument(
        "--cheap",
        action="store_true",
        help=(
            "Cost-saving mode: sets ATTUNE_AGENT_MODEL_DEFAULT=haiku for "
            "this run, forcing every subagent without an explicit model "
            "(see _SUBAGENT_MODEL_MAP) onto Haiku. Subagents pinned to "
            "opus/sonnet by keyword (security, vuln, architect, quality, "
            "plan, research) are unaffected."
        ),
    )


def _add_telemetry_subparsers(subparsers: argparse._SubParsersAction) -> None:
    """Add telemetry subcommand parsers.

    Args:
        subparsers: Parent subparsers action to attach to

    """
    telemetry_parser = subparsers.add_parser("telemetry", help="Usage telemetry")
    telemetry_sub = telemetry_parser.add_subparsers(dest="telemetry_command")

    show_parser = telemetry_sub.add_parser("show", help="Display usage summary")
    show_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days (default: 30)",
    )

    telemetry_sub.add_parser(
        "status",
        help="Show opt-in usage-ping status and exact payload",
    )
    telemetry_sub.add_parser("enable", help="Opt in to anonymous usage pinging")
    telemetry_sub.add_parser("disable", help="Opt out of anonymous usage pinging")

    savings_parser = telemetry_sub.add_parser("savings", help="Show cost savings")
    savings_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days (default: 30)",
    )

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

    telemetry_sub.add_parser("agents", help="Show active agents and their status")

    signals_parser = telemetry_sub.add_parser("signals", help="Show coordination signals")
    signals_parser.add_argument("--agent", "-a", required=True, help="Agent ID to view signals for")


def _add_costs_subparsers(subparsers: argparse._SubParsersAction) -> None:
    """Add cost tracking subcommand parsers.

    Args:
        subparsers: Parent subparsers action to attach to

    """
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

    costs_sub.add_parser("today", help="Show today's costs")

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

    costs_reset = costs_sub.add_parser("reset", help="Clear all cost data")
    costs_reset.add_argument("--confirm", action="store_true", help="Confirm deletion (required)")


def _add_misc_subparsers(subparsers: argparse._SubParsersAction) -> None:
    """Add provider, memory, setup, and utility subcommand parsers.

    Args:
        subparsers: Parent subparsers action to attach to

    """
    # Provider commands
    provider_parser = subparsers.add_parser("provider", help="LLM provider configuration")
    provider_sub = provider_parser.add_subparsers(dest="provider_command")
    provider_sub.add_parser("show", help="Show current provider")
    set_parser = provider_sub.add_parser("set", help="Set provider")
    set_parser.add_argument("name", choices=["anthropic"], help="Provider name")

    # Memory commands (quick lessons)
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

    # Setup command
    subparsers.add_parser("setup", help="Install slash commands to ~/.claude/commands/")

    # --- Auth / subscription commands ---
    auth_parser = subparsers.add_parser("auth", help="Subscription and authentication management")
    auth_sub = auth_parser.add_subparsers(dest="auth_command")

    # auth status
    auth_status_parser = auth_sub.add_parser(
        "status", help="Show subscription/auth strategy status"
    )
    auth_status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted table",
    )

    # auth setup
    auth_sub.add_parser("setup", help="Configure auth strategy interactively")

    # auth reset
    auth_reset_parser = auth_sub.add_parser("reset", help="Clear auth strategy configuration")
    auth_reset_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm deletion of configuration",
    )

    # auth recommend
    auth_rec_parser = auth_sub.add_parser(
        "recommend",
        help="Get auth recommendation for a file",
    )
    auth_rec_parser.add_argument("file_path", help="Path to the file to analyze")

    # --- Utility commands ---
    help_parser = subparsers.add_parser("help-docs", help="Browse documentation templates")
    help_parser.add_argument("topic", nargs="?", help="Category or template name")
    help_parser.add_argument("--tag", help="Filter by tag")
    help_parser.add_argument("--tags", action="store_true", help="List all tags")
    help_parser.add_argument("--detail", action="store_true", help="Show normal detail level")
    help_parser.add_argument(
        "--deep", action="store_true", help="Show full detail with related topics"
    )
    help_parser.add_argument("--feedback", choices=["good", "bad"], help="Rate a template")

    subparsers.add_parser("doctor", help="Run comprehensive environment health check")
    subparsers.add_parser("features", help="Show available features and dependencies")
    subparsers.add_parser("validate", help="Validate configuration")

    curator_parser = subparsers.add_parser(
        "curator", help="Show the project briefing (ranked attention items)"
    )
    curator_parser.add_argument(
        "--refresh", action="store_true", help="Bypass cache and re-synthesize"
    )
    curator_parser.add_argument("--json", action="store_true", help="Output as JSON")
    curator_parser.add_argument(
        "--max-items",
        type=int,
        default=5,
        dest="max_items",
        help="Max attention items to surface (default: 5)",
    )

    memory_agent_parser = subparsers.add_parser(
        "memory-agent",
        help="Run a single-shot agent with a Redis-backed Anthropic Memory tool",
    )
    memory_agent_parser.add_argument("prompt", help="Prompt to send to the agent")
    memory_agent_parser.add_argument(
        "--path", help="Memory namespace root the agent addresses (default /memories)"
    )
    memory_agent_parser.add_argument(
        "--model", help="Model id (default: claude-sonnet-5, the CAPABLE tier)"
    )
    memory_agent_parser.add_argument("--user-id", dest="user_id", help="Namespace memory per user")
    memory_agent_parser.add_argument(
        "--max-tokens",
        dest="max_tokens",
        type=int,
        default=4096,
        help="Max output tokens per turn (default: 4096)",
    )

    patterns_parser = subparsers.add_parser(
        "patterns",
        help="Review staged patterns before they enter the library",
    )
    patterns_sub = patterns_parser.add_subparsers(dest="patterns_command")
    review_p = patterns_sub.add_parser("review", help="List staged patterns")
    review_p.add_argument("--type", help="Filter by pattern type")
    review_p.add_argument("--agent", help="Filter by source agent id")
    review_p.add_argument(
        "--min-confidence",
        dest="min_confidence",
        type=float,
        help="Only show patterns at or above this confidence",
    )
    review_p.add_argument("--json", action="store_true", help="Output as JSON")
    promote_p = patterns_sub.add_parser("promote", help="Promote a staged pattern")
    promote_p.add_argument("pattern_id", help="Id of the staged pattern to promote")
    reject_p = patterns_sub.add_parser("reject", help="Reject a staged pattern")
    reject_p.add_argument("pattern_id", help="Id of the staged pattern to reject")
    reject_p.add_argument("--reason", help="Rejection reason (recorded for audit)")

    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed info")

    # Personal cross-session memory
    memory_parser = subparsers.add_parser(
        "memory",
        help="Personal cross-session memory (decisions, patterns, troubleshooting)",
    )
    memory_sub = memory_parser.add_subparsers(dest="memory_command")

    capture_p = memory_sub.add_parser("capture", help="Save a topic to personal memory")
    capture_p.add_argument("topic", help="Topic slug (letters, digits, hyphens, max 50 chars)")
    capture_p.add_argument("content", help="Raw content to capture and polish")
    capture_p.add_argument(
        "--kind",
        choices=["decision", "pattern", "troubleshooting", "reference"],
        default="decision",
        help="Memory kind (default: decision)",
    )
    capture_p.add_argument(
        "--project",
        action="store_true",
        dest="project_local",
        help="Save to project-local .attune/memory/ instead of global",
    )

    recall_p = memory_sub.add_parser("recall", help="Search personal memory")
    recall_p.add_argument("query", help="Natural language search query")
    recall_p.add_argument("--k", type=int, default=3, help="Number of results (default: 3)")
    recall_p.add_argument("--kind", dest="kind_filter", help="Filter results by kind")
    recall_p.add_argument("--json", action="store_true", help="Output as JSON")

    memory_sub.add_parser("topics", help="List all personal memory topics")

    forget_topic_p = memory_sub.add_parser("forget-topic", help="Delete a topic from memory")
    forget_topic_p.add_argument("topic", help="Topic slug to delete")
    forget_topic_p.add_argument("--kind", help="Delete only a specific kind")


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
    /docs       Documentation generation
    /release    Release preparation

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

    _add_workflow_subparsers(subparsers)
    _add_telemetry_subparsers(subparsers)
    _add_costs_subparsers(subparsers)
    _add_misc_subparsers(subparsers)
    _add_ops_subparser(subparsers)

    return parser


_SUBCOMMAND_DISPATCH: dict[str, dict[str, object]] = {
    "patterns": {
        "_attr": "patterns_command",
        "review": cmd_patterns_review,
        "promote": cmd_patterns_promote,
        "reject": cmd_patterns_reject,
    },
    "workflow": {
        "_attr": "workflow_command",
        "list": cmd_workflow_list,
        "info": cmd_workflow_info,
        "run": cmd_workflow_run,
    },
    "telemetry": {
        "_attr": "telemetry_command",
        "show": cmd_telemetry_show,
        "savings": cmd_telemetry_savings,
        "export": cmd_telemetry_export,
        "routing-stats": cmd_telemetry_routing_stats,
        "routing-check": cmd_telemetry_routing_check,
        "models": cmd_telemetry_models,
        "agents": cmd_telemetry_agents,
        "signals": cmd_telemetry_signals,
        "status": cmd_telemetry_status,
        "enable": cmd_telemetry_enable,
        "disable": cmd_telemetry_disable,
    },
    "provider": {
        "_attr": "provider_command",
        "show": cmd_provider_show,
        "set": cmd_provider_set,
    },
    "auth": {
        "_attr": "auth_command",
        "status": cmd_auth_status,
        "setup": cmd_auth_setup,
        "reset": cmd_auth_reset,
        "recommend": cmd_auth_recommend,
    },
    "costs": {
        "_attr": "costs_command",
        "today": cmd_costs_today,
        "export": cmd_costs_export,
        "reset": cmd_costs_reset,
    },
    "memory": {
        "_attr": "memory_command",
        "capture": cmd_memory_capture,
        "recall": cmd_memory_recall,
        "topics": cmd_memory_topics,
        "forget-topic": cmd_memory_forget_topic,
    },
}

_SIMPLE_DISPATCH: dict[str, object] = {
    "remember": cmd_remember,
    "forget": cmd_forget,
    "lessons": cmd_lessons,
    "setup": cmd_setup,
    "help-docs": cmd_help,
    "doctor": cmd_doctor,
    "features": cmd_features,
    "validate": cmd_validate,
    "version": cmd_version,
    "ops": cmd_ops,
    "curator": cmd_curator,
    "memory-agent": cmd_memory_agent,
}

# Commands that should NOT trigger the first-run usage-ping consent prompt:
# telemetry (the user is already managing it), plus meta/info/onboarding
# commands where an unsolicited prompt would be intrusive.
_CONSENT_SKIP_COMMANDS: frozenset[str] = frozenset(
    {"telemetry", "setup", "version", "doctor", "auth"}
)


def _dispatch_subcommand(args, command: str) -> int:
    """Dispatch a command that has subcommands."""
    table = _SUBCOMMAND_DISPATCH[command]
    attr = table["_attr"]
    sub = getattr(args, attr, None)
    handler = table.get(sub)
    if handler:
        return handler(args)
    # costs has a default handler (no subcommand = show report)
    if command == "costs":
        return cmd_costs(args)
    sub_names = [k for k in table if k != "_attr"]
    print(f"Usage: attune {command} {{{'|'.join(sub_names)}}}")
    return 1


def _show_welcome() -> int:
    """Show welcome message when no command is given."""
    try:
        from attune import __version__

        ver = __version__
    except Exception:  # noqa: BLE001
        # INTENTIONAL: version is non-critical for welcome message
        ver = "?"
    print(
        f"""Attune AI v{ver} — AI-powered developer workflows

Get started:
  attune workflow list        See all available workflows
  attune workflow run <name>  Run a workflow (requires ANTHROPIC_API_KEY)
  attune auth status          Check your subscription/auth status
  attune validate             Check your configuration

For interactive development in Claude Code:
  /attune       Socratic discovery — finds the right workflow for you
  /dev          Developer tools (commit, review, debug, refactor)
  /testing      Run tests, coverage, generate tests
  /wizard run   Guided multi-step wizards

More: attune --help | Docs: https://smartaimemory.com/framework-docs/"""
    )
    return 0


class _OneLineLogFormatter(logging.Formatter):
    """Formatter that suppresses tracebacks on non-verbose CLI runs.

    A full traceback on a user's first failed workflow reads as a crash
    even when the workflow returns a structured, actionable error right
    below it (setup-friction F1). Errors stay one line; ``--verbose``
    restores complete tracebacks via the default formatter.
    """

    def format(self, record: logging.LogRecord) -> str:
        exc_info, exc_text = record.exc_info, record.exc_text
        record.exc_info, record.exc_text = None, None
        try:
            message = super().format(record)
        finally:
            record.exc_info, record.exc_text = exc_info, exc_text
        if exc_info:
            message += " (re-run with --verbose for the full traceback)"
        return message


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Configure logging (one-line records unless --verbose; see
    # _OneLineLogFormatter).
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        _handler = logging.StreamHandler()
        _handler.setFormatter(_OneLineLogFormatter(fmt="%(levelname)s:%(name)s:%(message)s"))
        logging.basicConfig(level=logging.WARNING, handlers=[_handler])

    command = args.command

    # First-run, interactive-only consent prompt for the anonymous usage
    # ping — the opt-in lever for usage-signals. Asks at most once; silently
    # no-ops in CI/pipes and for meta commands (telemetry/setup/version/etc.).
    # Best-effort: it must NEVER block or break the CLI.
    if command not in _CONSENT_SKIP_COMMANDS:
        try:
            from attune.telemetry.usage_ping import maybe_prompt_consent

            maybe_prompt_consent()
        except Exception:  # noqa: BLE001
            # INTENTIONAL: a telemetry prompt failure can't be allowed to
            # take down a normal command.
            logging.getLogger(__name__).debug("usage-ping consent prompt failed", exc_info=True)

    # Subcommand dispatch (workflow, telemetry, provider, auth, costs)
    if command in _SUBCOMMAND_DISPATCH:
        return _dispatch_subcommand(args, command)

    # Simple command dispatch
    handler = _SIMPLE_DISPATCH.get(command)
    if handler:
        return handler(args)

    # No command given
    return _show_welcome()


if __name__ == "__main__":
    sys.exit(main())
