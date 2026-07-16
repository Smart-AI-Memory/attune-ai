"""CLI Agent Commands.

Agent Commands for meta-workflow system.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import typer
from rich.console import Console
from rich.panel import Panel

from attune.security.path_validation import _validate_file_path

from . import meta_workflow_app

console = Console()


@meta_workflow_app.command("create-agent")
def create_agent(
    interactive: bool = typer.Option(
        True,
        "--interactive/--quick",
        "-i/-q",
        help="Use interactive Socratic-guided creation",
    ),
    name: str = typer.Option(
        None,
        "--name",
        "-n",
        help="Agent name (for quick mode)",
    ),
    role: str = typer.Option(
        None,
        "--role",
        "-r",
        help="Agent role description (for quick mode)",
    ),
    tier: str = typer.Option(
        "capable",
        "--tier",
        "-t",
        help="Model tier: cheap, capable, or premium",
    ),
    output_file: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save agent spec to file",
    ),
):
    """Create a custom AI agent with Socratic-guided questions.

    Interactive mode asks clarifying questions to help you define:
    - Agent capabilities and responsibilities
    - Model tier selection (cost vs quality tradeoff)
    - Tools and success criteria

    Quick mode creates an agent directly from provided options.

    Examples:
        empathy meta-workflow create-agent --interactive
        empathy meta-workflow create-agent -q --name "SecurityBot" --role "Scan for vulnerabilities"

    """
    import json

    if interactive:
        console.print("\n[bold cyan]🤖 Create Custom Agent - Socratic Guide[/bold cyan]\n")
        console.print("[dim]I'll ask you a few questions to help define your agent.[/dim]\n")

        # Question 1: Purpose
        console.print("[bold]1. What should this agent do?[/bold]")
        purpose = typer.prompt("   Describe the agent's main purpose")

        # Question 2: Specific tasks
        console.print("\n[bold]2. What specific tasks will it perform?[/bold]")
        console.print(
            "   [dim]Examples: analyze code, generate tests, review PRs, write docs[/dim]",
        )
        tasks = typer.prompt("   List main tasks (comma-separated)")

        # Question 3: Tier selection
        console.print("\n[bold]3. What quality/cost balance do you need?[/bold]")
        console.print("   [dim]cheap[/dim]    - Fast & low-cost, good for simple analysis")
        console.print("   [dim]capable[/dim]  - Balanced, good for most development tasks")
        console.print("   [dim]premium[/dim]  - Highest quality, for complex reasoning")
        tier = typer.prompt("   Select tier", default="capable")

        # Question 4: Tools
        console.print("\n[bold]4. What tools should it have access to?[/bold]")
        console.print("   [dim]Examples: file_read, file_write, web_search, code_exec[/dim]")
        tools_input = typer.prompt("   List tools (comma-separated, or 'none')", default="none")
        tools = [t.strip() for t in tools_input.split(",")] if tools_input != "none" else []

        # Question 5: Success criteria
        console.print("\n[bold]5. How will you measure success?[/bold]")
        success = typer.prompt("   Describe success criteria")

        # Generate name from purpose
        name = purpose.split()[0].title() + "Agent" if not name else name

        # Build agent spec
        agent_spec = {
            "name": name,
            "role": purpose,
            "tasks": [t.strip() for t in tasks.split(",")],
            "tier": tier,
            "tools": tools,
            "success_criteria": success,
            "base_template": "generic",
        }

    else:
        # Quick mode
        if not name or not role:
            console.print("[red]Error:[/red] --name and --role required in quick mode")
            console.print("[dim]Use --interactive for guided creation[/dim]")
            raise typer.Exit(code=1)

        agent_spec = {
            "name": name,
            "role": role,
            "tier": tier,
            "tools": [],
            "success_criteria": "Task completed successfully",
            "base_template": "generic",
        }

    # Display result
    console.print("\n[bold green]✓ Agent Specification Created[/bold green]\n")

    spec_json = json.dumps(agent_spec, indent=2)
    console.print(Panel(spec_json, title=f"Agent: {agent_spec['name']}", border_style="green"))

    # Save if requested
    if output_file:
        validated_output = _validate_file_path(output_file)
        validated_output.write_text(spec_json)
        console.print(f"\n[green]Saved to:[/green] {validated_output}")

    # Show usage
    console.print("\n[bold]Next Steps:[/bold]")
    console.print(
        "  1. Use this agent in a custom team: [cyan]empathy meta-workflow create-team[/cyan]",
    )
    console.print("  2. Or add to an existing template manually")
    costs = {"cheap": "$0.001-0.01", "capable": "$0.01-0.05", "premium": "$0.05-0.20"}
    console.print(
        f"\n[dim]Agent tier '{tier}' will cost approximately:\n"
        f"   {costs.get(tier, costs['capable'])} per execution[/dim]\n"
    )


@meta_workflow_app.command("create-team")
def create_team(
    interactive: bool = typer.Option(
        True,
        "--interactive/--quick",
        "-i/-q",
        help="Use interactive Socratic-guided creation",
    ),
    name: str = typer.Option(
        None,
        "--name",
        "-n",
        help="Team name (for quick mode)",
    ),
    goal: str = typer.Option(
        None,
        "--goal",
        "-g",
        help="Team goal description (for quick mode)",
    ),
    output_file: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save team template to file",
    ),
):
    """Create a custom AI agent team with Socratic-guided workflow.

    Interactive mode asks clarifying questions to help you define:
    - Team composition and agent roles
    - Collaboration pattern (sequential, parallel, mixed)
    - Success criteria and cost estimates

    Examples:
        empathy meta-workflow create-team --interactive
        empathy meta-workflow create-team -q --name "ReviewTeam" --goal "Code review pipeline"

    """
    import json

    if interactive:
        console.print("\n[bold cyan]👥 Create Custom Agent Team - Socratic Guide[/bold cyan]\n")
        console.print("[dim]I'll help you design a team of agents that work together.[/dim]\n")

        # Question 1: Goal
        console.print("[bold]1. What is the team's overall goal?[/bold]")
        console.print("   [dim]Example: prepare code for production release[/dim]")
        goal = typer.prompt("   Describe the team's mission")

        # Question 2: Agent count
        console.print("\n[bold]2. How many agents should be on this team?[/bold]")
        console.print("   [dim]Typical teams have 2-5 agents with specialized roles[/dim]")
        agent_count = typer.prompt("   Number of agents", default="3")
        agent_count = int(agent_count)

        # Question 3: Agent roles
        console.print(f"\n[bold]3. Define {agent_count} agent roles:[/bold]")
        console.print(
            "   [dim]Common roles: analyst, reviewer, generator, validator, reporter[/dim]",
        )

        agents = []
        for i in range(agent_count):
            console.print(f"\n   [bold]Agent {i + 1}:[/bold]")
            role = typer.prompt("     Role name")
            purpose = typer.prompt("     What does this agent do?")
            tier = typer.prompt("     Tier (cheap/capable/premium)", default="capable")

            agents.append(
                {
                    "role": role,
                    "purpose": purpose,
                    "tier": tier,
                    "base_template": "generic",
                },
            )

        # Question 4: Collaboration pattern
        console.print("\n[bold]4. How should agents collaborate?[/bold]")
        console.print("   [dim]sequential[/dim] - Each agent waits for the previous one")
        console.print("   [dim]parallel[/dim]   - All agents run simultaneously")
        console.print("   [dim]mixed[/dim]      - Some parallel, then sequential synthesis")
        pattern = typer.prompt("   Collaboration pattern", default="sequential")

        # Question 5: Team name
        console.print("\n[bold]5. What should we call this team?[/bold]")
        name = typer.prompt("   Team name", default=goal.split()[0].title() + "Team")

        # Build team template
        team_template = {
            "id": name.lower().replace(" ", "-"),
            "name": name,
            "description": goal,
            "collaboration_pattern": pattern,
            "agents": agents,
            "estimated_cost_range": {
                "min": len(agents) * 0.01,
                "max": len(agents) * 0.15,
            },
        }

    else:
        # Quick mode
        if not name or not goal:
            console.print("[red]Error:[/red] --name and --goal required in quick mode")
            console.print("[dim]Use --interactive for guided creation[/dim]")
            raise typer.Exit(code=1)

        # Create a default 3-agent team
        team_template = {
            "id": name.lower().replace(" ", "-"),
            "name": name,
            "description": goal,
            "collaboration_pattern": "sequential",
            "agents": [
                {
                    "role": "Analyst",
                    "purpose": "Analyze requirements",
                    "tier": "cheap",
                    "base_template": "generic",
                },
                {
                    "role": "Executor",
                    "purpose": "Perform main task",
                    "tier": "capable",
                    "base_template": "generic",
                },
                {
                    "role": "Validator",
                    "purpose": "Verify results",
                    "tier": "capable",
                    "base_template": "generic",
                },
            ],
            "estimated_cost_range": {"min": 0.03, "max": 0.45},
        }

    # Display result
    console.print("\n[bold green]✓ Agent Team Template Created[/bold green]\n")

    spec_json = json.dumps(team_template, indent=2)
    console.print(Panel(spec_json, title=f"Team: {team_template['name']}", border_style="green"))

    # Save if requested
    if output_file:
        validated_output = _validate_file_path(output_file)
        validated_output.write_text(spec_json)
        console.print(f"\n[green]Saved to:[/green] {validated_output}")

    # Show usage
    console.print("\n[bold]Next Steps:[/bold]")
    console.print(
        f"  1. Save as template: [cyan]--output .attune/meta_workflows/templates/{team_template['id']}.json[/cyan]",
    )
    console.print(
        f"  2. Run the team: [cyan]empathy meta-workflow run {team_template['id']}[/cyan]",
    )

    cost_min = team_template["estimated_cost_range"]["min"]
    cost_max = team_template["estimated_cost_range"]["max"]
    console.print(f"\n[dim]Estimated cost: ${cost_min:.2f} - ${cost_max:.2f} per execution[/dim]\n")


if __name__ == "__main__":
    meta_workflow_app()
