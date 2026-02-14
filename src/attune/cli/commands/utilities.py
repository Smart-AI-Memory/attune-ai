"""Utility commands for Attune AI CLI.

General-purpose utility commands (sync, cheatsheet, dashboard, etc.).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import subprocess
import sys

import typer
from rich.panel import Panel

from attune.cli.core import console

# Create the utilities Typer app
utilities_app = typer.Typer(
    help="Utility tools - project init, cheatsheet, dashboard, costs",
    no_args_is_help=True,
)


@utilities_app.command("sync-claude")
def sync_claude(
    source: str = typer.Option("patterns", "--source", "-s", help="Source to sync"),
) -> None:
    """Sync patterns to Claude Code memory."""
    subprocess.run(["attune-sync-claude", "--source", source], check=False)


@utilities_app.command("cheatsheet")
def cheatsheet() -> None:
    """Show quick reference for all commands."""
    console.print(
        Panel.fit(
            """[bold]Getting Started[/bold]
  attune morning           Start-of-day briefing
  attune health            Quick health check
  attune ship              Pre-commit validation
  attune run               Interactive REPL

[bold]Memory System[/bold]
  attune memory status     Check Redis & patterns
  attune memory start      Start Redis server
  attune memory patterns   List stored patterns

[bold]Cross-Session Service[/bold]
  attune service start     Start coordination service
  attune service status    Show service & sessions
  attune service sessions  List active agents

[bold]Provider Config[/bold]
  attune provider          Show current config
  attune provider --set hybrid    Use best-of-breed
  attune provider registry        List all models

[bold]Code Inspection[/bold]
  attune scan .            Scan for issues
  attune inspect .         Deep analysis (SARIF)
  attune fix-all           Auto-fix everything

[bold]Profiling[/bold]
  attune profile memory-scan   Scan for memory leaks
  attune profile hot-files     Show riskiest files
  attune profile memory-test   Profile memory module

[bold]Pattern Learning[/bold]
  attune learn --analyze 20    Learn from commits
  attune utilities sync-claude Sync to Claude Code

[bold]Workflows[/bold]
  attune workflow list     Show available workflows
  attune workflow run <name>   Execute a workflow
  attune workflow create <name> -p <patterns>  Create workflow (12x faster)
  attune workflow list-patterns                List available patterns

[bold]Usage Telemetry[/bold]
  attune telemetry show    View recent LLM calls & costs
  attune telemetry savings Calculate cost savings (tier routing)
  attune telemetry export  Export usage data (JSON/CSV)""",
            title="[bold blue]Attune AI Cheatsheet[/bold blue]",
        )
    )


@utilities_app.command("dashboard")
def dashboard() -> None:
    """Launch visual dashboard."""
    subprocess.run([sys.executable, "-m", "attune.cli", "dashboard"], check=False)


@utilities_app.command("costs")
def costs() -> None:
    """View API cost tracking."""
    subprocess.run([sys.executable, "-m", "attune.cli", "costs"], check=False)


@utilities_app.command("init")
def init() -> None:
    """Create a new configuration file."""
    subprocess.run([sys.executable, "-m", "attune.cli", "init"], check=False)


@utilities_app.command("status")
def status() -> None:
    """What needs attention now."""
    subprocess.run([sys.executable, "-m", "attune.cli", "status"], check=False)
