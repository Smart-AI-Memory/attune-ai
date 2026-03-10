"""CLI Config Commands.

Config Commands for meta-workflow system.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import typer
from rich.console import Console
from rich.table import Table

from attune.meta_workflows import (
    TemplateRegistry,
)

from . import meta_workflow_app

console = Console()


@meta_workflow_app.command("suggest-defaults")
def suggest_defaults_cmd(
    template_id: str = typer.Argument(..., help="Template ID to get defaults for"),
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        "-s",
        help="Session ID (optional)",
    ),
    user_id: str = typer.Option(
        "cli_user",
        "--user-id",
        "-u",
        help="User ID for session",
    ),
):
    """Get suggested default values based on session history.

    Analyzes recent choices for the specified template and suggests
    intelligent defaults for the next run.

    Examples:
        empathy meta-workflow suggest-defaults test_creation_management_workflow
        empathy meta-workflow suggest-defaults python_package_publish --session-id sess_123

    """
    try:
        from attune.memory.unified import UnifiedMemory
        from attune.meta_workflows.session_context import SessionContext

        # Initialize
        memory = UnifiedMemory(user_id=user_id)
        session = SessionContext(memory=memory, session_id=session_id)

        # Load template
        registry = TemplateRegistry()
        template = registry.load_template(template_id)
        if not template:
            console.print(f"[red]Error:[/red] Template not found: {template_id}")
            raise typer.Exit(code=1)

        console.print(f"\n[bold]Suggested Defaults for:[/bold] {template.name}")
        console.print(f"[dim]Template ID: {template_id}[/dim]\n")

        # Get suggestions
        defaults = session.suggest_defaults(
            template_id=template_id,
            form_schema=template.form_schema,
        )

        if not defaults:
            console.print("[yellow]No suggestions available (no recent history).[/yellow]\n")
            return

        # Display
        console.print(f"[green]Found {len(defaults)} suggested default(s):[/green]\n")

        table = Table(show_header=True)
        table.add_column("Question ID", style="cyan")
        table.add_column("Suggested Value")

        for question_id, value in defaults.items():
            # Find the question to get the display text
            question = next(
                (q for q in template.form_schema.questions if q.id == question_id),
                None,
            )
            question_text = question.text if question else question_id

            value_str = str(value)
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)

            table.add_row(question_text, value_str)

        console.print(table)
        console.print(
            f"\n[dim]Use these defaults by running:[/dim]\n"
            f"  empathy meta-workflow run {template_id} --use-defaults\n",
        )

    except ImportError:
        console.print(
            "[red]Error:[/red] Session context not available. "
            "Ensure memory and session modules are installed.",
        )
        raise typer.Exit(code=1) from None
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


# =============================================================================
# Migration Commands
# =============================================================================


@meta_workflow_app.command("migrate")
def show_migration_guide(
    crew_name: str | None = typer.Argument(
        None,
        help="Specific Crew workflow name (optional)",
    ),
):
    """Show migration guide from deprecated Crew workflows.

    Displays information about migrating from the deprecated Crew-based
    workflows to the new meta-workflow system.

    Examples:
        empathy meta-workflow migrate
        empathy meta-workflow migrate ReleasePreparationCrew

    """
    # Migration mapping
    CREW_MIGRATION_MAP = {
        "ReleasePreparationCrew": {
            "template_id": "release-prep",
            "old_import": "from attune.workflows.release_prep_crew import ReleasePreparationCrew",
            "old_usage": "crew = ReleasePreparationCrew(project_root='.')\nresult = await crew.execute()",
            "new_usage": "empathy meta-workflow run release-prep",
        },
        "TestCoverageBoostCrew": {
            "template_id": "test-coverage-boost",
            "old_import": "from attune.workflows.test_coverage_boost_crew import TestCoverageBoostCrew",
            "old_usage": "crew = TestCoverageBoostCrew(target_coverage=85.0)\nresult = await crew.execute()",
            "new_usage": "empathy meta-workflow run test-coverage-boost",
        },
        "TestMaintenanceCrew": {
            "template_id": "test-maintenance",
            "old_import": "from attune.workflows.test_maintenance_crew import TestMaintenanceCrew",
            "old_usage": "crew = TestMaintenanceCrew('.')\nresult = await crew.run(mode='full')",
            "new_usage": "empathy meta-workflow run test-maintenance",
        },
        "ManageDocumentationCrew": {
            "template_id": "manage-docs",
            "old_import": "from attune.workflows.manage_documentation import ManageDocumentationCrew",
            "old_usage": "crew = ManageDocumentationCrew()\nresult = await crew.execute(path='./src')",
            "new_usage": "empathy meta-workflow run manage-docs",
        },
    }

    console.print("\n[bold cyan]🔄 Crew → Meta-Workflow Migration Guide[/bold cyan]\n")

    if crew_name:
        # Show specific migration
        if crew_name not in CREW_MIGRATION_MAP:
            console.print(f"[red]Unknown Crew workflow:[/red] {crew_name}")
            console.print("\n[bold]Available Crew workflows:[/bold]")
            for name in CREW_MIGRATION_MAP:
                console.print(f"  • {name}")
            raise typer.Exit(code=1)

        info = CREW_MIGRATION_MAP[crew_name]
        console.print(f"[bold]Migrating:[/bold] {crew_name}\n")

        console.print("[bold red]DEPRECATED (Before):[/bold red]")
        console.print(f"[dim]{info['old_import']}[/dim]")
        console.print(f"\n[yellow]{info['old_usage']}[/yellow]\n")

        console.print("[bold green]RECOMMENDED (After):[/bold green]")
        console.print(f"[green]{info['new_usage']}[/green]\n")

        console.print("[bold]Benefits:[/bold]")
        console.print("  ✓ No CrewAI/LangChain dependency required")
        console.print("  ✓ Interactive configuration via Socratic questions")
        console.print("  ✓ Automatic cost optimization with tier escalation")
        console.print("  ✓ Session context for learning preferences")
        console.print("  ✓ Built-in analytics and pattern learning\n")

        console.print(f"[dim]Try it now: empathy meta-workflow run {info['template_id']}[/dim]\n")

    else:
        # Show overview
        console.print("[bold]Why Migrate?[/bold]")
        console.print("  The Crew-based workflows are deprecated since v4.3.0.")
        console.print("  The meta-workflow system provides the same functionality")
        console.print("  with better cost optimization and no extra dependencies.\n")

        # Show migration table
        table = Table(title="Migration Map", show_header=True)
        table.add_column("Deprecated Crew", style="yellow")
        table.add_column("Meta-Workflow Command", style="green")
        table.add_column("Template ID", style="cyan")

        for crew_name, info in CREW_MIGRATION_MAP.items():
            table.add_row(
                crew_name,
                info["new_usage"],
                info["template_id"],
            )

        console.print(table)

        console.print("\n[bold]Quick Start:[/bold]")
        console.print(
            "  1. List available templates: [cyan]empathy meta-workflow list-templates[/cyan]",
        )
        console.print("  2. Run a workflow: [cyan]empathy meta-workflow run release-prep[/cyan]")
        console.print("  3. View results: [cyan]empathy meta-workflow list-runs[/cyan]\n")

        console.print("[bold]More Details:[/bold]")
        console.print("  • Migration guide: [dim]empathy meta-workflow migrate <CrewName>[/dim]")
        console.print("  • Full documentation: [dim]docs/CREWAI_MIGRATION.md[/dim]\n")


# =============================================================================
# Dynamic Agent/Team Creation Commands (v4.4)
# =============================================================================
