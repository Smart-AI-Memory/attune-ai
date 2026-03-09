"""CLI Workflow Commands.

Workflow Commands for meta-workflow system.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from attune.meta_workflows import (
    MetaWorkflow,
    PatternLearner,
    TemplateRegistry,
)
from attune.meta_workflows.intent_detector import IntentDetector

from . import meta_workflow_app

console = Console()


@meta_workflow_app.command("run")
def run_workflow(
    template_id: str = typer.Argument(..., help="Template ID to execute"),
    mock: bool = typer.Option(
        True,
        "--mock/--real",
        help="Use mock execution (for testing)",
    ),
    use_memory: bool = typer.Option(
        False,
        "--use-memory",
        "-m",
        help="Enable memory integration for enhanced analytics",
    ),
    use_defaults: bool = typer.Option(
        False,
        "--use-defaults",
        "-d",
        help="Use default values instead of asking questions (non-interactive mode)",
    ),
    user_id: str = typer.Option(
        "cli_user",
        "--user-id",
        "-u",
        help="User ID for memory integration",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output result as JSON (for programmatic use)",
    ),
):
    """Execute a meta-workflow from template.

    This will:
    1. Load the template
    2. Ask form questions interactively (or use defaults with --use-defaults)
    3. Generate dynamic agent team
    4. Execute agents (mock or real)
    5. Save results (files + optional memory)
    6. Display summary

    Examples:
        empathy meta-workflow run release-prep
        empathy meta-workflow run test-coverage-boost --real
        empathy meta-workflow run manage-docs --use-defaults
        empathy meta-workflow run release-prep --json --use-defaults

    """
    import json

    try:
        # Load template
        if not json_output:
            console.print(f"\n[bold]Loading template:[/bold] {template_id}")
        registry = TemplateRegistry()
        template = registry.load_template(template_id)

        if not template:
            if json_output:
                print(json.dumps({"success": False, "error": f"Template not found: {template_id}"}))
            else:
                console.print(f"[red]Template not found:[/red] {template_id}")
            raise typer.Exit(code=1)

        if not json_output:
            console.print(f"[green]✓[/green] {template.name}")

        # Setup memory if requested
        pattern_learner = None
        if use_memory:
            if not json_output:
                console.print("\n[bold]Initializing memory integration...[/bold]")
            from attune.memory.unified import UnifiedMemory

            try:
                memory = UnifiedMemory(user_id=user_id)
                pattern_learner = PatternLearner(memory=memory)
                if not json_output:
                    console.print("[green]✓[/green] Memory enabled")
            except Exception as e:  # noqa: BLE001
                if not json_output:
                    console.print(f"[yellow]Warning:[/yellow] Memory initialization failed: {e}")
                    console.print("[yellow]Continuing without memory integration[/yellow]")

        # Create workflow
        workflow = MetaWorkflow(
            template=template,
            pattern_learner=pattern_learner,
        )

        # Execute (will ask questions via AskUserQuestion unless --use-defaults)
        if not json_output:
            console.print("\n[bold]Executing workflow...[/bold]")
            console.print(f"Mode: {'Mock' if mock else 'Real'}")
            if use_defaults:
                console.print("[cyan]Using default values (non-interactive)[/cyan]")

        result = workflow.execute(mock_execution=mock, use_defaults=use_defaults)

        # JSON output mode - print result as JSON and exit
        if json_output:
            output = {
                "run_id": result.run_id,
                "template_id": template_id,
                "timestamp": result.timestamp,
                "success": result.success,
                "error": result.error,
                "total_cost": result.total_cost,
                "total_duration": result.total_duration,
                "agents_created": len(result.agents_created),
                "form_responses": {
                    "template_id": result.form_responses.template_id,
                    "responses": result.form_responses.responses,
                    "timestamp": result.form_responses.timestamp,
                    "response_id": result.form_responses.response_id,
                },
                "agent_results": [
                    {
                        "agent_id": ar.agent_id,
                        "role": ar.role,
                        "success": ar.success,
                        "cost": ar.cost,
                        "duration": ar.duration,
                        "tier_used": ar.tier_used,
                        "output": ar.output,
                        "error": ar.error,
                    }
                    for ar in result.agent_results
                ],
            }
            print(json.dumps(output))
            return

        # Display summary (normal mode)
        console.print("\n[bold green]Execution Complete![/bold green]\n")

        summary_lines = [
            f"[bold]Run ID:[/bold] {result.run_id}",
            f"[bold]Status:[/bold] {'✅ Success' if result.success else '❌ Failed'}",
            "",
            f"[bold]Agents Created:[/bold] {len(result.agents_created)}",
            f"[bold]Agents Executed:[/bold] {len(result.agent_results)}",
            f"[bold]Total Cost:[/bold] ${result.total_cost:.2f}",
            f"[bold]Duration:[/bold] {result.total_duration:.1f}s",
        ]

        if result.error:
            summary_lines.append(f"\n[bold red]Error:[/bold red] {result.error}")

        console.print(
            Panel("\n".join(summary_lines), title="Execution Summary", border_style="green"),
        )

        # Show agents
        console.print("\n[bold]Agents Executed:[/bold]\n")

        for agent_result in result.agent_results:
            status = "✅" if agent_result.success else "❌"
            console.print(
                f"  {status} [cyan]{agent_result.role}[/cyan] "
                f"(tier: {agent_result.tier_used}, cost: ${agent_result.cost:.2f})",
            )

        # Show where results saved
        console.print("\n[bold]Results saved to:[/bold]")
        console.print(f"  📁 Files: .attune/meta_workflows/executions/{result.run_id}/")
        if use_memory and pattern_learner and pattern_learner.memory:
            console.print("  🧠 Memory: Long-term storage")

        console.print(f"\n[dim]View details: empathy meta-workflow show {result.run_id}[/dim]")
        console.print()

    except Exception as e:  # noqa: BLE001
        if json_output:
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            console.print(f"\n[red]Error:[/red] {e}")
            import traceback

            traceback.print_exc()
        raise typer.Exit(code=1)


@meta_workflow_app.command("ask")
def natural_language_run(
    request: str = typer.Argument(..., help="Natural language description of what you need"),
    auto_run: bool = typer.Option(
        False,
        "--auto",
        "-a",
        help="Automatically run if high confidence match (>60%)",
    ),
    mock: bool = typer.Option(
        True,
        "--mock/--real",
        help="Use mock execution (for testing)",
    ),
    use_defaults: bool = typer.Option(
        True,
        "--use-defaults/--interactive",
        "-d/-i",
        help="Use default values (non-interactive)",
    ),
):
    """Create agent teams using natural language.

    Analyzes your request and suggests appropriate agent teams.
    Use --auto to automatically run the best match.

    Examples:
        empathy meta-workflow ask "I need to prepare for a release"
        empathy meta-workflow ask "improve my test coverage" --auto --real
        empathy meta-workflow ask "check if documentation is up to date"

    """
    try:
        detector = IntentDetector()
        matches = detector.detect(request)

        if not matches:
            console.print(
                "\n[yellow]I couldn't identify a matching agent team for your request.[/yellow]",
            )
            console.print("\n[bold]Available agent teams:[/bold]")
            console.print(
                "  • [cyan]release-prep[/cyan] - Security, testing, code quality, documentation checks",
            )
            console.print(
                "  • [cyan]test-coverage-boost[/cyan] - Analyze and improve test coverage",
            )
            console.print("  • [cyan]test-maintenance[/cyan] - Test lifecycle management")
            console.print("  • [cyan]manage-docs[/cyan] - Documentation sync and gap detection")
            console.print("\n[dim]Try: empathy meta-workflow run <template-id>[/dim]\n")
            return

        # Show detected matches
        console.print(f'\n[bold]Analyzing:[/bold] "{request}"\n')

        best_match = matches[0]
        confidence_pct = int(best_match.confidence * 100)

        # If auto-run and high confidence, run immediately
        if auto_run and best_match.confidence >= 0.6:
            console.print(
                f"[bold green]Auto-detected:[/bold green] {best_match.template_name} ({confidence_pct}% confidence)",
            )
            console.print(f"[dim]{best_match.description}[/dim]\n")
            console.print(f"[bold]Running {best_match.template_id}...[/bold]\n")

            # Run the workflow
            run_workflow(
                template_id=best_match.template_id,
                mock=mock,
                use_memory=False,
                use_defaults=use_defaults,
                user_id="cli_user",
            )
            return

        # Show suggestions
        console.print("[bold]Suggested Agent Teams:[/bold]\n")

        for i, match in enumerate(matches[:3], 1):
            confidence = int(match.confidence * 100)
            style = (
                "green"
                if match.confidence >= 0.6
                else "yellow" if match.confidence >= 0.4 else "dim"
            )

            console.print(f"  {i}. [{style}]{match.template_name}[/{style}] ({confidence}% match)")
            console.print(f"     [dim]{match.description}[/dim]")
            if match.matched_keywords:
                keywords = ", ".join(match.matched_keywords[:5])
                console.print(f"     [dim]Matched: {keywords}[/dim]")
            console.print(f"     Run: [cyan]empathy meta-workflow run {match.template_id}[/cyan]")
            console.print()

        # Prompt to run best match
        if best_match.confidence >= 0.5:
            console.print(
                "[bold]Quick Run:[/bold] Use [cyan]--auto[/cyan] to automatically run the best match",
            )
            console.print(
                f'[dim]Example: empathy meta-workflow ask "{request}" --auto --real[/dim]\n',
            )

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@meta_workflow_app.command("detect")
def detect_intent(
    request: str = typer.Argument(..., help="Natural language request to analyze"),
    threshold: float = typer.Option(
        0.3,
        "--threshold",
        "-t",
        help="Minimum confidence threshold (0.0-1.0)",
    ),
):
    """Detect intent from natural language without running.

    Useful for testing what agent teams would be suggested for a given request.

    Examples:
        empathy meta-workflow detect "check security vulnerabilities"
        empathy meta-workflow detect "generate more tests" --threshold 0.5

    """
    try:
        detector = IntentDetector()
        matches = detector.detect(request, threshold=threshold)

        console.print(f'\n[bold]Intent Analysis:[/bold] "{request}"\n')
        console.print(f"[dim]Threshold: {threshold:.0%}[/dim]\n")

        if not matches:
            console.print("[yellow]No matches above threshold.[/yellow]\n")
            return

        # Create table
        table = Table(show_header=True)
        table.add_column("Template", style="cyan")
        table.add_column("Confidence", justify="right")
        table.add_column("Matched Keywords")
        table.add_column("Would Auto-Run?")

        for match in matches:
            confidence = f"{match.confidence:.0%}"
            keywords = ", ".join(match.matched_keywords[:4])
            auto_run = "✅ Yes" if match.confidence >= 0.6 else "❌ No"

            table.add_row(
                match.template_id,
                confidence,
                keywords or "-",
                auto_run,
            )

        console.print(table)
        console.print()

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Analytics Commands
# =============================================================================
