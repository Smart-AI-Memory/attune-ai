"""CLI Template Commands.

Template Commands for meta-workflow system.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from attune.meta_workflows import (
    TemplateRegistry,
)
from attune.security.path_validation import _validate_file_path

from . import meta_workflow_app

console = Console()


@meta_workflow_app.command("list-templates")
def list_templates(
    storage_dir: str = typer.Option(
        ".attune/meta_workflows/templates",
        "--storage-dir",
        "-d",
        help="Templates storage directory",
    ),
):
    """List all available workflow templates.

    Shows template metadata including:
    - Template ID and name
    - Description
    - Estimated cost range
    - Number of questions and agent rules
    """
    try:
        registry = TemplateRegistry(storage_dir=storage_dir)
        template_ids = registry.list_templates()

        if not template_ids:
            console.print("[yellow]No templates found.[/yellow]")
            console.print(f"\nLooking in: {storage_dir}")
            console.print("\nCreate templates by running workflow workflow or")
            console.print("placing template JSON files in the templates directory.")
            return

        # Count built-in vs user templates
        builtin_count = sum(1 for t in template_ids if registry.is_builtin(t))
        user_count = len(template_ids) - builtin_count

        console.print(f"\n[bold]Available Templates[/bold] ({len(template_ids)} total)")
        console.print(
            f"  [cyan]📦 Built-in:[/cyan] {builtin_count}  [green]👤 User:[/green] {user_count}\n",
        )

        # Show migration hint for users coming from Crew workflows
        if builtin_count > 0:
            console.print(
                "[dim]💡 Tip: Built-in templates replace deprecated Crew workflows.[/dim]",
            )
            console.print("[dim]   See: empathy meta-workflow migrate --help[/dim]\n")

        for template_id in template_ids:
            template = registry.load_template(template_id)

            if template:
                # Add badge for built-in templates
                is_builtin = registry.is_builtin(template_id)
                badge = "[cyan]📦 BUILT-IN[/cyan]" if is_builtin else "[green]👤 USER[/green]"

                # Create info panel
                info_lines = [
                    f"[bold]{template.name}[/bold] {badge}",
                    f"[dim]{template.description}[/dim]",
                    "",
                    f"ID: {template.template_id}",
                    f"Version: {template.version}",
                    f"Author: {template.author}",
                    f"Tags: {', '.join(template.tags)}",
                    "",
                    f"Questions: {len(template.form_schema.questions)}",
                    f"Agent Rules: {len(template.agent_composition_rules)}",
                    "",
                    f"Est. Cost: ${template.estimated_cost_range[0]:.2f}-${template.estimated_cost_range[1]:.2f}",
                    f"Est. Duration: ~{template.estimated_duration_minutes} min",
                ]

                # Add quick start command
                info_lines.append("")
                info_lines.append(
                    f"[bold]Quick Start:[/bold] empathy meta-workflow run {template_id}",
                )

                console.print(
                    Panel("\n".join(info_lines), border_style="blue" if is_builtin else "green"),
                )
                console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@meta_workflow_app.command("inspect")
def inspect_template(
    template_id: str = typer.Argument(..., help="Template ID to inspect"),
    storage_dir: str = typer.Option(
        ".attune/meta_workflows/templates",
        "--storage-dir",
        "-d",
        help="Templates storage directory",
    ),
    show_rules: bool = typer.Option(
        False,
        "--show-rules",
        "-r",
        help="Show agent composition rules",
    ),
):
    """Inspect a specific template in detail.

    Shows comprehensive template information including:
    - Form questions and types
    - Agent composition rules (optional)
    - Configuration mappings
    """
    try:
        registry = TemplateRegistry(storage_dir=storage_dir)
        template = registry.load_template(template_id)

        if not template:
            console.print(f"[red]Template not found:[/red] {template_id}")
            raise typer.Exit(code=1)

        # Header
        console.print(f"\n[bold cyan]Template: {template.name}[/bold cyan]")
        console.print(f"[dim]{template.description}[/dim]\n")

        # Form Schema
        console.print("[bold]Form Questions:[/bold]")
        form_tree = Tree("📋 Questions")

        for i, question in enumerate(template.form_schema.questions, 1):
            question_text = f"[cyan]{question.text}[/cyan]"
            q_node = form_tree.add(f"{i}. {question_text}")
            q_node.add(f"ID: {question.id}")
            q_node.add(f"Type: {question.type.value}")
            if question.options:
                options_str = ", ".join(question.options[:3])
                if len(question.options) > 3:
                    options_str += f", ... ({len(question.options) - 3} more)"
                q_node.add(f"Options: {options_str}")
            if question.required:
                q_node.add("[yellow]Required[/yellow]")
            if question.default:
                q_node.add(f"Default: {question.default}")

        console.print(form_tree)

        # Agent Composition Rules (optional)
        if show_rules:
            console.print(
                f"\n[bold]Agent Composition Rules:[/bold] ({len(template.agent_composition_rules)})\n",
            )

            for i, rule in enumerate(template.agent_composition_rules, 1):
                rule_lines = [
                    f"[bold cyan]{i}. {rule.role}[/bold cyan]",
                    f"   Base Template: {rule.base_template}",
                    f"   Tier Strategy: {rule.tier_strategy.value}",
                    f"   Tools: {', '.join(rule.tools) if rule.tools else 'None'}",
                ]

                if rule.required_responses:
                    rule_lines.append(f"   Required When: {rule.required_responses}")

                if rule.config_mapping:
                    rule_lines.append(f"   Config Mapping: {len(rule.config_mapping)} fields")

                console.print("\n".join(rule_lines))
                console.print()

        # Summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Questions: {len(template.form_schema.questions)}")
        console.print(f"  Agent Rules: {len(template.agent_composition_rules)}")
        console.print(
            f"  Estimated Cost: ${template.estimated_cost_range[0]:.2f}-${template.estimated_cost_range[1]:.2f}",
        )
        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Plan Generation Commands (Claude Code Integration)
# =============================================================================


@meta_workflow_app.command("plan")
def generate_plan_cmd(
    template_id: str = typer.Argument(..., help="Template ID to generate plan for"),
    output_format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format: markdown, skill, or json",
    ),
    output_file: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    ),
    use_defaults: bool = typer.Option(
        True,
        "--use-defaults/--interactive",
        help="Use default values or ask interactively",
    ),
    install_skill: bool = typer.Option(
        False,
        "--install",
        "-i",
        help="Install as Claude Code skill in .claude/commands/",
    ),
):
    """Generate execution plan for Claude Code (no API costs).

    This generates a plan that can be executed by Claude Code using your
    Max subscription instead of making API calls.

    Output formats:
    - markdown: Human-readable plan to paste into Claude Code
    - skill: Claude Code skill format for .claude/commands/
    - json: Structured format for programmatic use

    Examples:
        empathy meta-workflow plan release-prep
        empathy meta-workflow plan release-prep --format skill --install
        empathy meta-workflow plan test-coverage-boost -o plan.md
        empathy meta-workflow plan manage-docs --format json

    """
    try:
        from attune.meta_workflows.plan_generator import generate_plan

        # Load template
        console.print(f"\n[bold]Generating plan for:[/bold] {template_id}")
        registry = TemplateRegistry()
        template = registry.load_template(template_id)

        if not template:
            console.print(f"[red]Template not found:[/red] {template_id}")
            raise typer.Exit(code=1)

        # Collect responses if interactive
        form_responses = None
        if not use_defaults and template.form_schema.questions:
            console.print("\n[bold]Configuration:[/bold]")
            form_responses = {}
            for question in template.form_schema.questions:
                if question.options:
                    # Multiple choice
                    console.print(f"\n{question.text}")
                    for i, opt in enumerate(question.options, 1):
                        default_mark = " (default)" if opt == question.default else ""
                        console.print(f"  {i}. {opt}{default_mark}")
                    choice = typer.prompt("Choice", default="1")
                    try:
                        idx = int(choice) - 1
                        form_responses[question.id] = question.options[idx]
                    except (ValueError, IndexError):
                        form_responses[question.id] = question.default or question.options[0]
                else:
                    # Yes/No or text
                    default = question.default or "Yes"
                    response = typer.prompt(question.text, default=default)
                    form_responses[question.id] = response

        # Generate plan
        plan_content = generate_plan(
            template_id=template_id,
            form_responses=form_responses,
            use_defaults=use_defaults,
            output_format=output_format,
        )

        # Handle output
        if install_skill:
            # Install as Claude Code skill
            skill_dir = Path(".claude/commands")
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skill_dir / f"{template_id}.md"

            # Convert to skill format if not already
            if output_format != "skill":
                plan_content = generate_plan(
                    template_id=template_id,
                    form_responses=form_responses,
                    use_defaults=use_defaults,
                    output_format="skill",
                )

            validated_skill_path = _validate_file_path(str(skill_path))
            validated_skill_path.write_text(plan_content)
            console.print(
                f"\n[green]✓ Installed as Claude Code skill:[/green] {validated_skill_path}",
            )
            console.print(f"\nRun with: [bold]/project:{template_id}[/bold]")

        elif output_file:
            # Write to file
            validated_output = _validate_file_path(output_file)
            validated_output.write_text(plan_content)
            console.print(f"\n[green]✓ Plan saved to:[/green] {validated_output}")

        else:
            # Print to stdout
            console.print("\n" + "=" * 60)
            console.print(plan_content)
            console.print("=" * 60)

        # Show usage hints
        console.print("\n[bold]Usage Options:[/bold]")
        console.print("1. Copy prompts into Claude Code conversation")
        console.print("2. Install as skill with: --install")
        console.print("3. Use with Claude Code Task tool")
        console.print("\n[dim]Cost: $0 (uses your Max subscription)[/dim]")

    except ImportError:
        console.print("[red]Plan generator not available.[/red]")
        console.print("This feature requires the plan_generator module.")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error generating plan:[/red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Execution Commands
# =============================================================================
