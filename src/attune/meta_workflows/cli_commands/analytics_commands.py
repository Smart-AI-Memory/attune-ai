"""CLI Analytics Commands.

Analytics Commands for meta-workflow system.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from attune.meta_workflows import (
    PatternLearner,
    list_execution_results,
    load_execution_result,
)

from . import meta_workflow_app

console = Console()


@meta_workflow_app.command("analytics")
def show_analytics(
    template_id: str | None = typer.Argument(
        None,
        help="Template ID to analyze (optional, all if not specified)",
    ),
    min_confidence: float = typer.Option(
        0.5,
        "--min-confidence",
        "-c",
        help="Minimum confidence threshold (0.0-1.0)",
    ),
    use_memory: bool = typer.Option(
        False,
        "--use-memory",
        "-m",
        help="Use memory-enhanced analytics",
    ),
):
    """Show pattern learning analytics and recommendations.

    Displays:
    - Execution statistics
    - Tier performance insights
    - Cost analysis
    - Recommendations
    """
    try:
        # Initialize pattern learner
        pattern_learner = PatternLearner()

        if use_memory:
            console.print("[bold]Initializing memory-enhanced analytics...[/bold]\n")
            from attune.memory.unified import UnifiedMemory

            memory = UnifiedMemory(user_id="cli_analytics")
            pattern_learner = PatternLearner(memory=memory)

        # Generate report
        report = pattern_learner.generate_analytics_report(template_id=template_id)

        # Display summary
        summary = report["summary"]

        console.print("\n[bold cyan]Meta-Workflow Analytics Report[/bold cyan]")
        if template_id:
            console.print(f"[dim]Template: {template_id}[/dim]")
        console.print()

        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value")

        summary_table.add_row("Total Runs", str(summary["total_runs"]))
        summary_table.add_row(
            "Successful",
            f"{summary['successful_runs']} ({summary['success_rate']:.0%})",
        )
        summary_table.add_row("Total Cost", f"${summary['total_cost']:.2f}")
        summary_table.add_row("Avg Cost/Run", f"${summary['avg_cost_per_run']:.2f}")
        summary_table.add_row("Total Agents", str(summary["total_agents_created"]))
        summary_table.add_row("Avg Agents/Run", f"{summary['avg_agents_per_run']:.1f}")

        console.print(Panel(summary_table, title="Summary", border_style="cyan"))

        # Recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            console.print("\n[bold]Recommendations:[/bold]\n")
            for rec in recommendations:
                console.print(f"  {rec}")

        # Insights
        insights = report.get("insights", {})

        if insights.get("tier_performance"):
            console.print("\n[bold]Tier Performance:[/bold]\n")
            for insight in insights["tier_performance"][:5]:  # Top 5
                console.print(f"  • {insight['description']}")
                console.print(
                    f"    [dim]Confidence: {insight['confidence']:.0%} (n={insight['sample_size']})[/dim]",
                )

        if insights.get("cost_analysis"):
            console.print("\n[bold]Cost Analysis:[/bold]\n")
            for insight in insights["cost_analysis"]:
                console.print(f"  • {insight['description']}")

                # Tier breakdown
                breakdown = insight["data"].get("tier_breakdown", {})
                if breakdown:
                    console.print("\n  [dim]By Tier:[/dim]")
                    for tier, stats in breakdown.items():
                        console.print(
                            f"    {tier}: ${stats['avg']:.2f} avg "
                            f"(${stats['total']:.2f} total, {stats['count']} runs)",
                        )

        if insights.get("failure_analysis"):
            console.print("\n[bold yellow]Failure Analysis:[/bold yellow]\n")
            for insight in insights["failure_analysis"]:
                console.print(f"  ⚠️  {insight['description']}")

        console.print()

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


# =============================================================================
# Execution History Commands
# =============================================================================


@meta_workflow_app.command("list-runs")
def list_runs(
    template_id: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Filter by template ID",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results",
    ),
):
    """List execution history.

    Shows recent workflow executions with:
    - Run ID and timestamp
    - Template name
    - Success status
    - Cost and duration
    """
    try:
        run_ids = list_execution_results()

        if not run_ids:
            console.print("[yellow]No execution results found.[/yellow]")
            return

        console.print(
            f"\n[bold]Recent Executions[/bold] (showing {min(limit, len(run_ids))} of {len(run_ids)}):\n",
        )

        # Create table
        table = Table(show_header=True)
        table.add_column("Run ID", style="cyan")
        table.add_column("Template")
        table.add_column("Status")
        table.add_column("Cost", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Timestamp")

        count = 0
        for run_id in run_ids[:limit]:
            try:
                result = load_execution_result(run_id)

                # Filter by template if specified
                if template_id and result.template_id != template_id:
                    continue

                status = "✅" if result.success else "❌"
                cost = f"${result.total_cost:.2f}"
                duration = f"{result.total_duration:.1f}s"

                # Parse timestamp
                try:
                    ts = datetime.fromisoformat(result.timestamp)
                    timestamp = ts.strftime("%Y-%m-%d %H:%M")
                except Exception:  # noqa: BLE001
                    timestamp = result.timestamp[:16]

                table.add_row(
                    run_id,
                    result.template_id,
                    status,
                    cost,
                    duration,
                    timestamp,
                )

                count += 1

            except Exception as e:  # noqa: BLE001
                console.print(f"[yellow]Warning:[/yellow] Failed to load {run_id}: {e}")
                continue

        if count == 0:
            if template_id:
                console.print(f"[yellow]No executions found for template: {template_id}[/yellow]")
            else:
                console.print("[yellow]No valid execution results found.[/yellow]")
            return

        console.print(table)
        console.print("\n[dim]View details: empathy meta-workflow show <run_id>[/dim]\n")

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


@meta_workflow_app.command("show")
def show_execution(
    run_id: str = typer.Argument(..., help="Run ID to display"),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format (text or json)",
    ),
):
    """Show detailed execution report.

    Displays comprehensive information about a specific workflow execution:
    - Form responses
    - Agents created and executed
    - Cost breakdown
    - Success/failure details
    """
    try:
        result = load_execution_result(run_id)

        if format == "json":
            # JSON output
            print(result.to_json())
            return

        # Text format (default)
        console.print(f"\n[bold cyan]Execution Report: {run_id}[/bold cyan]\n")

        # Status
        status = "✅ Success" if result.success else "❌ Failed"
        console.print(f"[bold]Status:[/bold] {status}")
        console.print(f"[bold]Template:[/bold] {result.template_id}")
        console.print(f"[bold]Timestamp:[/bold] {result.timestamp}")

        if result.error:
            console.print(f"\n[bold red]Error:[/bold red] {result.error}\n")

        # Summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Agents Created: {len(result.agents_created)}")
        console.print(f"  Agents Executed: {len(result.agent_results)}")
        console.print(f"  Total Cost: ${result.total_cost:.2f}")
        console.print(f"  Duration: {result.total_duration:.1f}s")

        # Form Responses
        console.print("\n[bold]Form Responses:[/bold]\n")
        for key, value in result.form_responses.responses.items():
            console.print(f"  [cyan]{key}:[/cyan] {value}")

        # Agents
        console.print("\n[bold]Agents Executed:[/bold]\n")
        for i, agent_result in enumerate(result.agent_results, 1):
            status_emoji = "✅" if agent_result.success else "❌"
            console.print(f"  {i}. {status_emoji} [cyan]{agent_result.role}[/cyan]")
            console.print(f"     Tier: {agent_result.tier_used}")
            console.print(f"     Cost: ${agent_result.cost:.2f}")
            console.print(f"     Duration: {agent_result.duration:.1f}s")
            if agent_result.error:
                console.print(f"     [red]Error: {agent_result.error}[/red]")
            console.print()

        # Cost breakdown
        console.print("[bold]Cost Breakdown by Tier:[/bold]\n")
        tier_costs = {}
        for agent_result in result.agent_results:
            tier = agent_result.tier_used
            tier_costs[tier] = tier_costs.get(tier, 0.0) + agent_result.cost

        for tier, cost in sorted(tier_costs.items()):
            console.print(f"  {tier}: ${cost:.2f}")

        console.print()

    except FileNotFoundError:
        console.print(f"[red]Execution not found:[/red] {run_id}")
        console.print("\n[dim]List available runs: empathy meta-workflow list-runs[/dim]")
        raise typer.Exit(code=1) from None
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


# =============================================================================
# Maintenance Commands
# =============================================================================


@meta_workflow_app.command("cleanup")
def cleanup_executions(
    older_than_days: int = typer.Option(
        30,
        "--older-than",
        "-d",
        help="Delete executions older than N days",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deleted without deleting",
    ),
    template_id: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Filter by template ID",
    ),
):
    """Clean up old execution results.

    Deletes execution directories older than the specified number of days.
    Use --dry-run to preview what would be deleted.
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        run_ids = list_execution_results()

        if not run_ids:
            console.print("[yellow]No execution results found.[/yellow]")
            return

        to_delete = []

        for run_id in run_ids:
            try:
                result = load_execution_result(run_id)

                # Filter by template if specified
                if template_id and result.template_id != template_id:
                    continue

                # Parse timestamp
                ts = datetime.fromisoformat(result.timestamp)

                if ts < cutoff_date:
                    to_delete.append((run_id, result, ts))

            except Exception as e:  # noqa: BLE001
                console.print(f"[yellow]Warning:[/yellow] Failed to load {run_id}: {e}")
                continue

        if not to_delete:
            console.print(f"[green]No executions older than {older_than_days} days found.[/green]")
            return

        # Show what will be deleted
        console.print(f"\n[bold]Executions to delete:[/bold] ({len(to_delete)})\n")

        table = Table(show_header=True)
        table.add_column("Run ID", style="cyan")
        table.add_column("Template")
        table.add_column("Age (days)", justify="right")
        table.add_column("Cost", justify="right")

        total_cost_saved = 0.0
        for run_id, result, ts in to_delete:
            age_days = (datetime.now() - ts).days
            table.add_row(
                run_id,
                result.template_id,
                str(age_days),
                f"${result.total_cost:.2f}",
            )
            total_cost_saved += result.total_cost

        console.print(table)
        console.print(f"\nTotal cost represented: ${total_cost_saved:.2f}")

        if dry_run:
            console.print("\n[yellow]DRY RUN - No files deleted[/yellow]")
            console.print(f"Run without --dry-run to delete {len(to_delete)} executions")
            return

        # Confirm deletion
        if not typer.confirm(f"\nDelete {len(to_delete)} execution(s)?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        # Delete
        import shutil

        deleted = 0
        for run_id, _, _ in to_delete:
            try:
                run_dir = Path.home() / ".attune" / "meta_workflows" / "executions" / run_id
                if run_dir.exists():
                    shutil.rmtree(run_dir)
                    deleted += 1
            except Exception as e:  # noqa: BLE001
                console.print(f"[red]Failed to delete {run_id}:[/red] {e}")

        console.print(f"\n[green]✓ Deleted {deleted} execution(s)[/green]\n")

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


# =============================================================================
# Memory Search Commands
# =============================================================================
