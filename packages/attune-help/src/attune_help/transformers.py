"""Audience transformers for the help system.

Three render functions that convert a PopulatedTemplate into
output format for each channel:
  - Claude Code: concise Markdown for inline conversation
  - Marketplace: YAML frontmatter + full Markdown for static site
  - CLI: Rich panels and color for terminal display
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune_help.templates import PopulatedTemplate


def render_claude_code(template: PopulatedTemplate) -> str:
    """Render template for inline Claude Code conversation.

    Produces concise Markdown optimized for conversation:
    - Strips verbose sections (Confidence, Related Topics)
    - Adds tool call hints for actionable templates
    - Keeps body under ~500 chars when possible

    Args:
        template: Populated template to render.

    Returns:
        Markdown string for conversation.
    """
    lines: list[str] = []
    lines.append(f"**{template.title}**")
    lines.append("")

    if template.type == "error":
        if "Signature" in template.sections:
            lines.append(f"**Signature:** `{template.sections['Signature']}`")
        if "Root Cause" in template.sections:
            root = template.sections["Root Cause"]
            if len(root) > 200:
                root = root[:197] + "..."
            lines.append(f"\n{root}")
        if "Resolution" in template.sections:
            lines.append(f"\n**Resolution:**\n{template.sections['Resolution']}")

    elif template.type == "warning":
        if "Condition" in template.sections:
            lines.append(f"**When:** {template.sections['Condition']}")
        if "Risk" in template.sections:
            lines.append(f"\n**Risk:** {template.sections['Risk']}")
        if "Mitigation" in template.sections:
            lines.append(f"\n**Mitigation:**\n{template.sections['Mitigation']}")

    elif template.type == "tip":
        if "Recommendation" in template.sections:
            lines.append(template.sections["Recommendation"])
        if "Why" in template.sections:
            lines.append(f"\n*{template.sections['Why']}*")

    elif template.type == "reference":
        return template.body

    if template.related:
        tool_refs = [r for r in template.related if r["type"] == "Tool Reference"]
        if tool_refs:
            tool_id = tool_refs[0]["id"].replace("ref-tool-", "")
            lines.append(f"\n*Run `{tool_id}()` to investigate further.*")

    return "\n".join(lines)


def render_marketplace(template: PopulatedTemplate) -> str:
    """Render template for static site documentation.

    Produces Markdown with YAML frontmatter suitable for
    static site generation. Includes full content, navigation
    hints, and linked related topics.

    Args:
        template: Populated template to render.

    Returns:
        Markdown string with YAML frontmatter.
    """
    lines: list[str] = []

    lines.append("---")
    safe_title = template.title.replace('"', '\\"')
    lines.append(f'title: "{safe_title}"')
    lines.append(f"type: {template.type}")
    if template.subtype:
        lines.append(f"subtype: {template.subtype}")
    if template.tags:
        lines.append(f"tags: [{', '.join(template.tags)}]")
    if template.confidence:
        lines.append(f"confidence: {template.confidence}")
    lines.append(f"source: {template.source}")
    lines.append("---")
    lines.append("")

    lines.append(template.body)

    if template.related:
        lines.append("")
        lines.append("## See Also")
        lines.append("")
        for rel in template.related:
            lines.append(f"- **{rel['type']}:** `{rel['id']}`")

    return "\n".join(lines)


def render_cli(template: PopulatedTemplate) -> str:
    """Render template for terminal display.

    Produces text formatted for Rich console output with
    panels, color markup, and width constraints. Falls back
    to plain text if Rich is not available.

    Args:
        template: Populated template to render.

    Returns:
        Formatted string for terminal display.
    """
    try:
        return _render_cli_rich(template)
    except ImportError:
        return _render_cli_plain(template)


def _render_cli_rich(template: PopulatedTemplate) -> str:
    """Render with Rich formatting.

    Args:
        template: Populated template to render.

    Returns:
        Rich-formatted string.
    """
    from io import StringIO

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    buf = StringIO()
    console = Console(file=buf, width=80, force_terminal=True)

    title_style = {
        "error": "red",
        "warning": "yellow",
        "tip": "green",
        "reference": "blue",
    }.get(template.type, "white")

    console.print(
        Panel(
            Text(template.title, style=f"bold {title_style}"),
            subtitle=f"[dim]{template.type}[/dim]",
        )
    )

    for heading, body in template.sections.items():
        if heading in ("Related Topics", "Confidence"):
            continue
        if not body.strip():
            continue
        console.print(f"\n[bold]{heading}[/bold]")
        console.print(body)

    if template.tags:
        tag_str = " ".join(f"[dim]#{t}[/dim]" for t in template.tags)
        console.print(f"\n{tag_str}")

    if template.related:
        console.print("\n[bold]Related[/bold]")
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Type", style="cyan")
        table.add_column("ID")
        for rel in template.related:
            table.add_row(rel["type"], rel["id"])
        console.print(table)

    return buf.getvalue()


def _render_cli_plain(template: PopulatedTemplate) -> str:
    """Render as plain text fallback.

    Args:
        template: Populated template to render.

    Returns:
        Plain text string.
    """
    lines: list[str] = []
    lines.append(f"{'=' * 60}")
    lines.append(f"  {template.title}")
    lines.append(f"  [{template.type}]")
    lines.append(f"{'=' * 60}")

    for heading, body in template.sections.items():
        if heading in ("Related Topics", "Confidence"):
            continue
        if not body.strip():
            continue
        lines.append(f"\n--- {heading} ---\n")
        lines.append(body)

    if template.tags:
        lines.append(f"\nTags: {', '.join(template.tags)}")

    if template.related:
        lines.append("\nRelated:")
        for i, rel in enumerate(template.related, 1):
            lines.append(f"  {i}. [{rel['type']}] {rel['id']}")

    return "\n".join(lines)
