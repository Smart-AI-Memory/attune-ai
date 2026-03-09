"""CLI Memory Commands.

Memory Commands for meta-workflow system.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import meta_workflow_app

console = Console()


@meta_workflow_app.command("search-memory")
def search_memory(
    query: str = typer.Argument(..., help="Search query for patterns"),
    pattern_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by pattern type (e.g., 'meta_workflow_execution')",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum number of results to return",
    ),
    user_id: str = typer.Option(
        "cli_user",
        "--user-id",
        "-u",
        help="User ID for memory access",
    ),
):
    """Search memory for patterns using keyword matching.

    Searches long-term memory for patterns matching the query.
    Uses relevance scoring: exact phrase (10 pts), keyword in content (2 pts),
    keyword in metadata (1 pt).

    Examples:
        empathy meta-workflow search-memory "successful workflow"
        empathy meta-workflow search-memory "test coverage" --type meta_workflow_execution
        empathy meta-workflow search-memory "error" --limit 20

    """
    try:
        from attune.memory.unified import UnifiedMemory

        console.print(f"\n[bold]Searching memory for:[/bold] '{query}'")
        if pattern_type:
            console.print(f"[dim]Pattern type: {pattern_type}[/dim]")
        console.print()

        # Initialize memory
        memory = UnifiedMemory(user_id=user_id)

        # Search
        results = memory.search_patterns(
            query=query,
            pattern_type=pattern_type,
            limit=limit,
        )

        if not results:
            console.print("[yellow]No matching patterns found.[/yellow]\n")
            return

        # Display results
        console.print(f"[green]Found {len(results)} matching pattern(s):[/green]\n")

        for i, pattern in enumerate(results, 1):
            panel = Panel(
                f"[bold]Pattern ID:[/bold] {pattern.get('pattern_id', 'N/A')}\n"
                f"[bold]Type:[/bold] {pattern.get('pattern_type', 'N/A')}\n"
                f"[bold]Classification:[/bold] {pattern.get('classification', 'N/A')}\n\n"
                f"[bold]Content:[/bold]\n{str(pattern.get('content', 'N/A'))[:200]}...\n\n"
                f"[bold]Metadata:[/bold] {pattern.get('metadata', {})}",
                title=f"Result {i}/{len(results)}",
                border_style="blue",
            )
            console.print(panel)
            console.print()

    except ImportError:
        console.print(
            "[red]Error:[/red] UnifiedMemory not available. Ensure memory module is installed.",
        )
        raise typer.Exit(code=1)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Session Context Commands
# =============================================================================


@meta_workflow_app.command("session-stats")
def show_session_stats(
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        "-s",
        help="Session ID (optional, creates new if not specified)",
    ),
    user_id: str = typer.Option(
        "cli_user",
        "--user-id",
        "-u",
        help="User ID for session",
    ),
):
    """Show session context statistics.

    Displays information about user's session including:
    - Recent form choices
    - Templates used
    - Choice counts

    Examples:
        empathy meta-workflow session-stats
        empathy meta-workflow session-stats --session-id sess_123

    """
    try:
        from attune.memory.unified import UnifiedMemory
        from attune.meta_workflows.session_context import SessionContext

        # Initialize memory and session
        memory = UnifiedMemory(user_id=user_id)
        session = SessionContext(
            memory=memory,
            session_id=session_id,
        )

        console.print("\n[bold]Session Statistics[/bold]")
        console.print(f"[dim]Session ID: {session.session_id}[/dim]")
        console.print(f"[dim]User ID: {session.user_id}[/dim]\n")

        # Get stats
        stats = session.get_session_stats()

        # Display
        table = Table(show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        table.add_row("Total Choices", str(stats.get("choice_count", 0)))
        table.add_row("Templates Used", str(len(stats.get("templates_used", []))))
        table.add_row("Most Recent Choice", stats.get("most_recent_choice_timestamp", "N/A"))

        console.print(table)
        console.print()

        # Show templates used
        templates = stats.get("templates_used", [])
        if templates:
            console.print("[bold]Templates Used:[/bold]")
            for template_id in templates:
                console.print(f"  • {template_id}")
            console.print()

    except ImportError:
        console.print(
            "[red]Error:[/red] Session context not available. "
            "Ensure memory and session modules are installed.",
        )
        raise typer.Exit(code=1)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
