"""CLI help commands for browsing documentation templates.

Provides `attune help` with subcommands for listing,
searching, and displaying generated documentation.

Usage:
    attune help                       # List categories
    attune help errors                # List error templates
    attune help warnings              # List warning templates
    attune help tips                  # List tip templates
    attune help references            # List reference templates
    attune help <template-name>       # Show specific template
    attune help --tag security        # Filter by tag
    attune help --tags                # List all tags
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Template type categories
_CATEGORIES = ("errors", "warnings", "tips", "references")


def _get_generated_dir() -> Path:
    """Locate the generated templates directory.

    Returns:
        Path to plugin/help/generated/.
    """
    # Walk up from this file to repo root
    here = Path(__file__).resolve()
    repo_root = here.parents[3]  # src/attune/cli_commands/help_commands.py -> repo root
    return repo_root / "plugin" / "help" / "generated"


def _list_categories() -> int:
    """List template categories with counts.

    Returns:
        Exit code.
    """
    generated_dir = _get_generated_dir()
    if not generated_dir.exists():
        print("No generated templates found.")
        print("Run: python scripts/generate_all.py")
        return 1

    print("Documentation template categories:\n")

    total = 0
    for category in _CATEGORIES:
        cat_dir = generated_dir / category
        if cat_dir.exists():
            count = len(list(cat_dir.glob("*.md")))
            total += count
            print(f"  {category:<15} {count:>4} templates")
        else:
            print(f"  {category:<15}    0 templates")

    # Cross-links
    cross_links = generated_dir / "cross_links.json"
    if cross_links.exists():
        import json

        data = json.loads(cross_links.read_text(encoding="utf-8"))
        stats = data.get("stats", {})
        print(
            f"\n  Total: {total} templates, "
            f"{stats.get('linked_templates', 0)} linked, "
            f"{stats.get('total_tags', 0)} tags"
        )

    print("\nUsage:")
    print("  attune help <category>      List templates in category")
    print("  attune help <name>          Show a specific template")
    print("  attune help --tag <tag>     Filter by tag")
    print("  attune help --tags          List all tags")
    return 0


def _list_category(category: str) -> int:
    """List templates in a category.

    Args:
        category: Category name (errors, warnings, etc.).

    Returns:
        Exit code.
    """
    generated_dir = _get_generated_dir()
    cat_dir = generated_dir / category
    if not cat_dir.exists():
        print(f"Category '{category}' not found.")
        return 1

    files = sorted(cat_dir.glob("*.md"))
    if not files:
        print(f"No templates in '{category}'.")
        return 1

    print(f"{category} ({len(files)} templates):\n")
    for f in files:
        print(f"  {f.stem}")

    return 0


def _show_template(name: str, verbosity: str = "normal") -> int:
    """Show a specific template by name.

    Tries all categories to find the template, then
    renders it for the CLI audience.

    Args:
        name: Template name (without .md extension).
        verbosity: One of compact, normal, detailed.

    Returns:
        Exit code.
    """
    from attune.help.engine import AudienceProfile, populate

    audience = AudienceProfile(channel="cli", verbosity=verbosity)

    # Try to find by prefix
    prefix_map = {
        "err": "err",
        "war": "war",
        "tip": "tip",
        "ref": "ref",
    }

    # If name already has a prefix, use it directly
    for prefix in prefix_map:
        if name.startswith(f"{prefix}-"):
            result = populate(name, audience=audience)
            if result:
                from attune.help.transformers import render_cli

                print(render_cli(result))
                return 0
            print(f"Template '{name}' not found.")
            return 1

    # Try each prefix
    for prefix in prefix_map.values():
        template_id = f"{prefix}-{name}"
        result = populate(template_id, audience=audience)
        if result:
            from attune.help.transformers import render_cli

            print(render_cli(result))
            return 0

    print(f"Template '{name}' not found.")
    print("Try: attune help <category> to browse available templates.")
    return 1


def _filter_by_tag(tag: str) -> int:
    """Show templates matching a tag.

    Args:
        tag: Tag to filter by.

    Returns:
        Exit code.
    """
    from attune.help.engine import search_by_tag

    results = search_by_tag(tag)
    if not results:
        print(f"No templates with tag '{tag}'.")
        return 1

    print(f"Templates tagged '{tag}' ({len(results)}):\n")
    for template_id in results:
        print(f"  {template_id}")

    print("\nShow details: attune help <template-id>")
    return 0


def _list_all_tags() -> int:
    """List all tags with counts.

    Returns:
        Exit code.
    """
    from attune.help.engine import list_tags

    tags = list_tags()
    if not tags:
        print("No tags found.")
        return 1

    print(f"Tags ({len(tags)}):\n")
    for tag, count in tags.items():
        print(f"  {tag:<20} {count:>4} templates")

    print("\nFilter: attune help --tag <tag>")
    return 0


def cmd_help(args: argparse.Namespace) -> int:
    """Handle the `attune help` command.

    Routes to the appropriate subfunction based on args.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    # --tags flag: list all tags
    if getattr(args, "tags", False):
        return _list_all_tags()

    # --tag <tag>: filter by tag
    tag = getattr(args, "tag", None)
    if tag:
        return _filter_by_tag(tag)

    # Positional topic argument
    topic = getattr(args, "topic", None)
    if not topic:
        return _list_categories()

    # Check if it's a category name
    if topic in _CATEGORIES:
        return _list_category(topic)

    # Determine verbosity from flags
    verbosity = "normal"
    if getattr(args, "deep", False):
        verbosity = "detailed"
    elif getattr(args, "detail", False):
        verbosity = "normal"
    else:
        verbosity = "compact"

    # Otherwise try to show a specific template
    return _show_template(topic, verbosity=verbosity)
