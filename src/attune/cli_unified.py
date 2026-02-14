"""Unified CLI for Attune AI

DEPRECATED: This module is deprecated as of v5.0.0.
Use the minimal CLI instead: `empathy` (attune.cli_minimal)

The minimal CLI provides:
- `empathy workflow list|info|run` - Workflow management
- `empathy telemetry show|savings|export` - Usage tracking
- `empathy provider show|set` - Provider configuration
- `empathy validate` - Configuration validation

For interactive features, use Claude Code slash commands:
- /dev, /testing, /docs, /release, /help

Migration guide: https://smartaimemory.com/framework-docs/migration/cli/

---

A simplified, intelligent CLI using Socratic questioning.

Usage:
    empathy do "review code in src/"    # Intelligent - asks questions if needed
    empathy r .                         # Quick: review
    empathy s .                         # Quick: security
    empathy t .                         # Quick: test
    empathy scan .                      # Quick scan (no API)
    empathy ship                        # Pre-commit check

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

# ruff: noqa: E402
# Deprecation warning must be shown before other imports

import warnings

warnings.warn(
    "empathy-unified CLI is deprecated. Use 'empathy' (cli_minimal) instead. "
    "See: https://smartaimemory.com/framework-docs/reference/cli-reference/",
    DeprecationWarning,
    stacklevel=2,
)

import json
import subprocess
import sys
from importlib.metadata import version as get_version
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from attune.config import _validate_file_path

# =============================================================================
# CONSTANTS
# =============================================================================

CHEATSHEET_CONTENT = """\
[bold]Main Command[/bold]
  empathy do "..."        Intelligent task execution (asks questions if needed)

[bold]Quick Actions (short aliases)[/bold]
  empathy r [path]        Review code
  empathy s [path]        Security audit
  empathy t [path]        Generate tests
  empathy d [path]        Generate docs

[bold]Utilities[/bold]
  empathy scan [path]     Quick scan (no API needed)
  empathy ship            Pre-commit validation
  empathy health          Project health check

[bold]Reports[/bold]
  empathy report costs    API cost tracking
  empathy report health   Project health summary
  empathy report patterns Learned patterns

[bold]Memory[/bold]
  empathy memory          Memory system status
  empathy memory start    Start Redis"""

TIER_CONFIG_PATH = Path(".empathy") / "tier_config.json"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _load_tier_config() -> dict:
    """Load tier configuration from .attune/tier_config.json."""
    if TIER_CONFIG_PATH.exists():
        try:
            return json.loads(TIER_CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_tier_config(config: dict) -> None:
    """Save tier configuration to .attune/tier_config.json."""
    TIER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    validated_path = _validate_file_path(str(TIER_CONFIG_PATH))
    validated_path.write_text(json.dumps(config, indent=2))


def _auto_sync_patterns() -> None:
    """Automatically sync patterns to Claude Code after workflow completion."""
    try:
        result = subprocess.run(
            ["empathy-sync-claude", "--source", "patterns"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            console.print("\n[dim]✓ Patterns synced to Claude Code[/dim]")
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass  # Silent fail


def _run_workflow(name: str, path: Path, json_output: bool = False):
    """Helper to run a workflow via the legacy CLI."""
    workflow_input = f'{{"path": "{path}"}}'

    cmd = [
        sys.executable,
        "-m",
        "attune.cli",
        "workflow",
        "run",
        name,
        "--input",
        workflow_input,
    ]
    if json_output:
        cmd.append("--json")

    result = subprocess.run(cmd, check=False)

    if result.returncode == 0 and not json_output:
        _auto_sync_patterns()


# =============================================================================
# APP SETUP
# =============================================================================

app = typer.Typer(
    name="empathy",
    help="Attune AI - Intelligent AI-Developer Collaboration",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


def get_attune_version() -> str:
    """Get the installed version of attune-ai."""
    try:
        return get_version("attune-ai")
    except Exception:
        return "dev"


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]Attune AI[/bold blue] v{get_attune_version()}")
        raise typer.Exit()


@app.callback()
def callback(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """Attune AI - Intelligent AI-Developer Collaboration

    [bold]Quick Start:[/bold]
        empathy do "review the code"    Ask AI to do something
        empathy r .                     Quick code review
        empathy scan .                  Quick security scan

    [bold]Shortcuts:[/bold]
        r = review, s = security, t = test, d = docs
    """


# =============================================================================
# MAIN COMMAND: do
# =============================================================================


@app.command("do")
def do_command(
    goal: str = typer.Argument(..., help="What you want to accomplish"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Path to analyze"),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i", help="Ask clarifying questions"
    ),
):
    """Intelligent task execution using Socratic questioning.

    The AI will understand your goal and ask clarifying questions if needed.
    Uses domain templates for common tasks like code review, security, testing.

    Examples:
        empathy do "review the authentication code"
        empathy do "find security vulnerabilities" --path ./src
        empathy do "generate tests for the API" --no-interactive
    """
    console.print(f"\n[bold]Goal:[/bold] {goal}")
    console.print(f"[dim]Path: {path}[/dim]\n")

    # Use Socratic system for intelligent task execution
    try:
        from attune.socratic import SocraticWorkflowBuilder
        from attune.socratic.cli import console as socratic_console
        from attune.socratic.cli import render_form_interactive
        from attune.socratic.storage import get_default_storage

        builder = SocraticWorkflowBuilder()
        storage = get_default_storage()

        # Start session with the goal
        session = builder.start_session()
        session = builder.set_goal(session, f"{goal} (path: {path})")
        storage.save_session(session)

        # Show domain detection
        if session.goal_analysis:
            console.print(f"[cyan]Detected domain:[/cyan] {session.goal_analysis.domain}")
            console.print(f"[cyan]Confidence:[/cyan] {session.goal_analysis.confidence:.0%}")

            if session.goal_analysis.ambiguities and interactive:
                console.print("\n[yellow]Clarifications needed:[/yellow]")
                for amb in session.goal_analysis.ambiguities:
                    console.print(f"  • {amb}")

        # Interactive questioning if needed
        if interactive:
            while not builder.is_ready_to_generate(session):
                form = builder.get_next_questions(session)
                if not form:
                    break

                answers = render_form_interactive(form, socratic_console)
                session = builder.submit_answers(session, answers)
                storage.save_session(session)

        # Generate and execute workflow
        if builder.is_ready_to_generate(session):
            console.print("\n[bold]Generating workflow...[/bold]")
            workflow = builder.generate_workflow(session)
            storage.save_session(session)

            console.print(
                f"\n[green]✓ Generated workflow with {len(workflow.agents)} agents[/green]"
            )
            console.print(workflow.describe())

            # Execute the workflow
            if session.blueprint:
                storage.save_blueprint(session.blueprint)
                console.print(f"\n[dim]Blueprint saved: {session.blueprint.id[:8]}...[/dim]")

        _auto_sync_patterns()

    except ImportError as e:
        console.print(f"[yellow]Socratic system not fully available: {e}[/yellow]")
        console.print("[dim]Falling back to keyword matching...[/dim]\n")

        # Fallback: keyword-based workflow selection
        goal_lower = goal.lower()
        if any(w in goal_lower for w in ["review", "check", "analyze"]):
            _run_workflow("code-review", path)
        elif any(w in goal_lower for w in ["security", "vulnerab", "owasp"]):
            _run_workflow("security-audit", path)
        elif any(w in goal_lower for w in ["test", "coverage"]):
            _run_workflow("test-gen", path)
        elif any(w in goal_lower for w in ["doc", "document"]):
            _run_workflow("doc-gen", path)
        else:
            _run_workflow("code-review", path)


# =============================================================================
# SHORT ALIASES
# =============================================================================


@app.command("r")
def review_short(
    path: Path = typer.Argument(Path("."), help="Path to review"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """[bold]Review[/bold] - Quick code review.

    Alias for: empathy do "review code"
    """
    _run_workflow("code-review", path, json_output)


@app.command("s")
def security_short(
    path: Path = typer.Argument(Path("."), help="Path to scan"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """[bold]Security[/bold] - Quick security audit.

    Alias for: empathy do "security audit"
    """
    _run_workflow("security-audit", path, json_output)


@app.command("t")
def test_short(
    path: Path = typer.Argument(Path("."), help="Path to analyze"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """[bold]Test[/bold] - Generate tests.

    Alias for: empathy do "generate tests"
    """
    _run_workflow("test-gen", path, json_output)


@app.command("d")
def docs_short(
    path: Path = typer.Argument(Path("."), help="Path to document"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """[bold]Docs[/bold] - Generate documentation.

    Alias for: empathy do "generate docs"
    """
    _run_workflow("doc-gen", path, json_output)


# =============================================================================
# UTILITY COMMANDS
# =============================================================================


@app.command("scan")
def scan_command(
    scan_type: str = typer.Argument("all", help="Scan type: security, performance, or all"),
    path: Path = typer.Argument(Path("."), help="Path to scan"),
):
    """Quick security/performance scan (no API needed).

    Examples:
        empathy scan all .
        empathy scan security ./src
    """
    if scan_type not in ("security", "performance", "all"):
        console.print(f"[red]Invalid scan type: {scan_type}[/red]")
        console.print("Valid types: security, performance, all")
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Scanning {path} ({scan_type})...[/bold blue]\n")

    if scan_type in ("all", "security"):
        # Run ruff for linting
        console.print("[bold]Running ruff (linting)...[/bold]")
        subprocess.run(["ruff", "check", str(path)], check=False)

        # Run bandit for security
        console.print("\n[bold]Running bandit (security)...[/bold]")
        result = subprocess.run(["bandit", "-r", str(path), "-q"], check=False, capture_output=True)
        if result.returncode == 0:
            console.print("[green]No security issues found[/green]")
        elif result.stdout:
            console.print(result.stdout.decode())

    if scan_type in ("all", "performance"):
        console.print("\n[bold]Checking for performance patterns...[/bold]")
        # Basic performance check - look for common issues
        subprocess.run(["ruff", "check", str(path), "--select", "PERF"], check=False)

    console.print("\n[bold green]Scan complete![/bold green]")


@app.command("ship")
def ship_command(
    skip_sync: bool = typer.Option(False, "--skip-sync", help="Skip pattern sync"),
):
    """Pre-commit validation (lint, format, tests, security).

    Run this before committing to ensure code quality.
    """
    args = [sys.executable, "-m", "attune.cli", "ship"]
    if skip_sync:
        args.append("--skip-sync")
    subprocess.run(args, check=False)


@app.command("health")
def health_command(
    deep: bool = typer.Option(False, "--deep", help="Comprehensive check"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues"),
):
    """Quick project health check.

    Shows lint issues, test status, and overall health score.
    """
    args = [sys.executable, "-m", "attune.cli", "health"]
    if deep:
        args.append("--deep")
    if fix:
        args.append("--fix")
    subprocess.run(args, check=False)


# =============================================================================
# REPORT SUBCOMMAND GROUP
# =============================================================================

report_app = typer.Typer(help="View reports and dashboards")
app.add_typer(report_app, name="report")


@report_app.command("costs")
def report_costs():
    """View API cost tracking."""
    subprocess.run([sys.executable, "-m", "attune.cli", "costs"], check=False)


@report_app.command("health")
def report_health():
    """View project health summary."""
    subprocess.run([sys.executable, "-m", "attune.cli", "status"], check=False)


@report_app.command("patterns")
def report_patterns():
    """View learned patterns."""
    subprocess.run(
        [sys.executable, "-m", "attune.memory.control_panel", "patterns"],
        check=False,
    )


@report_app.command("telemetry")
def report_telemetry(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of entries"),
):
    """View LLM usage telemetry."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "telemetry", "show", "--limit", str(limit)],
        check=False,
    )


# =============================================================================
# MEMORY SUBCOMMAND GROUP
# =============================================================================

memory_app = typer.Typer(help="Memory system control panel")
app.add_typer(memory_app, name="memory")


@memory_app.callback(invoke_without_command=True)
def memory_default(ctx: typer.Context):
    """Memory system control panel."""
    if ctx.invoked_subcommand is None:
        subprocess.run(
            [sys.executable, "-m", "attune.memory.control_panel", "status"],
            check=False,
        )


@memory_app.command("status")
def memory_status():
    """Check memory system status."""
    subprocess.run(
        [sys.executable, "-m", "attune.memory.control_panel", "status"],
        check=False,
    )


@memory_app.command("start")
def memory_start():
    """Start Redis server for short-term memory."""
    subprocess.run(
        [sys.executable, "-m", "attune.memory.control_panel", "start"],
        check=False,
    )


@memory_app.command("stop")
def memory_stop():
    """Stop Redis server."""
    subprocess.run(
        [sys.executable, "-m", "attune.memory.control_panel", "stop"],
        check=False,
    )


@memory_app.command("patterns")
def memory_patterns():
    """List stored patterns."""
    subprocess.run(
        [sys.executable, "-m", "attune.memory.control_panel", "patterns"],
        check=False,
    )


# =============================================================================
# UTILITIES SUBCOMMAND GROUP
# =============================================================================

utilities_app = typer.Typer(help="Utility tools - init, cheatsheet, dashboard, sync")
app.add_typer(utilities_app, name="utilities")
app.add_typer(utilities_app, name="utility", hidden=True)  # Alias for common typo


@utilities_app.command("cheatsheet")
def utilities_cheatsheet():
    """Show quick reference for all commands."""
    console.print(
        Panel.fit(
            CHEATSHEET_CONTENT,
            title="[bold blue]Attune AI Cheatsheet[/bold blue]",
        ),
    )


@utilities_app.command("init")
def utilities_init():
    """Create a new configuration file."""
    subprocess.run([sys.executable, "-m", "attune.cli", "init"], check=False)


@utilities_app.command("dashboard")
def utilities_dashboard():
    """Launch visual dashboard."""
    subprocess.run([sys.executable, "-m", "attune.cli", "dashboard"], check=False)


@utilities_app.command("sync-claude")
def utilities_sync_claude(
    source: str = typer.Option("patterns", "--source", "-s", help="Source to sync"),
):
    """Sync patterns to Claude Code memory."""
    subprocess.run(["empathy-sync-claude", "--source", source], check=False)


@utilities_app.command("costs")
def utilities_costs():
    """View API cost tracking."""
    subprocess.run([sys.executable, "-m", "attune.cli", "costs"], check=False)


@utilities_app.command("status")
def utilities_status():
    """What needs attention now."""
    subprocess.run([sys.executable, "-m", "attune.cli", "status"], check=False)


@utilities_app.command("scan")
def utilities_scan(
    path: Path = typer.Argument(Path("."), help="Path to scan"),
    scan_type: str = typer.Option(
        "all", "--type", "-t", help="Scan type: security, performance, or all"
    ),
):
    """Scan codebase for issues.

    Examples:
        empathy utility scan .
        empathy utility scan ./src --type security
    """
    # Delegate to main scan command
    scan_command(scan_type, path)


# =============================================================================
# CHEATSHEET (top-level alias for convenience)
# =============================================================================


@app.command("cheatsheet")
def cheatsheet():
    """Show quick reference for all commands."""
    console.print(
        Panel.fit(
            CHEATSHEET_CONTENT,
            title="[bold blue]Attune AI Cheatsheet[/bold blue]",
        ),
    )


# =============================================================================
# ADDITIONAL COMMAND APPS (exported for cli/__init__.py)
# These provide structure for commands that will be migrated from legacy CLI
# =============================================================================

# Workflow commands - run multi-model AI workflows
workflow_app = typer.Typer(help="Run multi-model AI workflows")


@workflow_app.command("list")
def workflow_list():
    """List available workflows."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "workflow", "list"],
        check=False,
    )


@workflow_app.command("run")
def workflow_run(
    name: str = typer.Argument(..., help="Workflow name"),
    input_json: str = typer.Option("{}", "--input", "-i", help="Input JSON"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Run a workflow by name."""
    args = [sys.executable, "-m", "attune.cli", "workflow", "run", name, "--input", input_json]
    if json_output:
        args.append("--json")
    subprocess.run(args, check=False)


@workflow_app.command("describe")
def workflow_describe(name: str = typer.Argument(..., help="Workflow name")):
    """Describe a workflow."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "workflow", "describe", name],
        check=False,
    )


# Orchestrate commands - advanced orchestration features
orchestrate_app = typer.Typer(help="Advanced workflow orchestration")


@orchestrate_app.command("run")
def orchestrate_run(
    task: str = typer.Argument(..., help="Task description"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Path to analyze"),
):
    """Run orchestrated task."""
    task_json = json.dumps({"task": task, "path": str(path)})
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "orchestrate", "--input", task_json],
        check=False,
    )


# Telemetry commands - LLM usage tracking
telemetry_app = typer.Typer(help="LLM usage telemetry and cost tracking")


@telemetry_app.command("show")
def telemetry_show(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of entries"),
):
    """Show telemetry data."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "telemetry", "show", "--limit", str(limit)],
        check=False,
    )


@telemetry_app.command("export")
def telemetry_export(
    output: Path = typer.Argument(..., help="Output file path"),
    format_type: str = typer.Option("json", "--format", "-f", help="Output format: json, csv"),
):
    """Export telemetry data."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "attune.cli",
            "telemetry",
            "export",
            str(output),
            "--format",
            format_type,
        ],
        check=False,
    )


@telemetry_app.command("reset")
def telemetry_reset():
    """Reset telemetry data."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "telemetry", "reset"],
        check=False,
    )


# Service commands - background services
service_app = typer.Typer(help="Background services management")


@service_app.command("status")
def service_status():
    """Check service status."""
    # Check Redis status via memory control panel
    subprocess.run(
        [sys.executable, "-m", "attune.memory.control_panel", "status"],
        check=False,
    )


@service_app.command("start")
def service_start(service_name: str = typer.Argument("all", help="Service to start")):
    """Start background services."""
    if service_name in ("all", "redis"):
        subprocess.run(
            [sys.executable, "-m", "attune.memory.control_panel", "start"],
            check=False,
        )


@service_app.command("stop")
def service_stop(service_name: str = typer.Argument("all", help="Service to stop")):
    """Stop background services."""
    if service_name in ("all", "redis"):
        subprocess.run(
            [sys.executable, "-m", "attune.memory.control_panel", "stop"],
            check=False,
        )


# Progressive commands - progressive test generation
progressive_app = typer.Typer(help="Progressive test generation")


@progressive_app.command("list")
def progressive_list():
    """List progressive test results."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "progressive", "list"],
        check=False,
    )


@progressive_app.command("report")
def progressive_report(session_id: str = typer.Argument(..., help="Session ID")):
    """Show progressive test report."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "progressive", "report", session_id],
        check=False,
    )


@progressive_app.command("analytics")
def progressive_analytics():
    """Show progressive test analytics."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "progressive", "analytics"],
        check=False,
    )


# Tier commands - model tier management
tier_app = typer.Typer(help="Model tier configuration")


@tier_app.command("recommend")
def tier_recommend(
    task: str = typer.Argument("code-review", help="Task type"),
):
    """Get tier recommendation for a task."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "tier", "recommend", task],
        check=False,
    )


@tier_app.command("stats")
def tier_stats():
    """Show tier usage statistics."""
    subprocess.run(
        [sys.executable, "-m", "attune.cli", "tier", "stats"],
        check=False,
    )


@tier_app.command("set")
def tier_set(
    task: str = typer.Argument(..., help="Task type"),
    tier_name: str = typer.Argument(..., help="Tier name: cheap, balanced, premium"),
):
    """Set tier for a task type."""
    config = _load_tier_config()
    config[task] = tier_name
    _save_tier_config(config)
    console.print(f"[green]Set {task} to use {tier_name} tier[/green]")


# =============================================================================
# ENTRY POINT
# =============================================================================


def main():
    """Entry point for the unified CLI."""
    app()


if __name__ == "__main__":
    main()
