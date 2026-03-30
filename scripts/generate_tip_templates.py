#!/usr/bin/env python3
"""Generate Tip templates from discovery tips and workflow transitions.

Sources:
  1. DISCOVERY_TIPS dict in src/attune/discovery.py (8 tips)
  2. Workflow transition registry in src/attune/workflows/suggestions.py
     (static extraction of workflow-name mappings)

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/generate_tip_templates.py           # Generate
    python scripts/generate_tip_templates.py --check   # Verify
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output, slugify


@dataclass
class TipTemplate:
    """Populated Tip template ready for rendering."""

    name: str
    title: str
    context: str
    recommendation: str
    why: str
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


def parse_discovery_tips(discovery_path: Path) -> list[TipTemplate]:
    """Parse DISCOVERY_TIPS from discovery.py source.

    Extracts tip entries using regex on the source file to
    avoid importing the module (which has runtime deps).

    Args:
        discovery_path: Path to discovery.py.

    Returns:
        List of TipTemplate objects.
    """
    text = discovery_path.read_text(encoding="utf-8")

    # Extract entries between DISCOVERY_TIPS = { ... }
    tips_match = re.search(
        r"DISCOVERY_TIPS\s*=\s*\{(.+?)^\}",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not tips_match:
        return []

    tips_block = tips_match.group(1)

    # Parse each entry: "tip_id": { "tip": "...", ... }
    entry_pattern = re.compile(
        r'"(\w+)":\s*\{([^}]+)\}',
        re.DOTALL,
    )

    templates: list[TipTemplate] = []
    for match in entry_pattern.finditer(tips_block):
        tip_id = match.group(1)
        block = match.group(2)

        # Extract fields
        tip_text = _extract_field(block, "tip")
        trigger = _extract_field(block, "trigger")
        priority = _extract_int_field(block, "priority")
        min_uses = _extract_int_field(block, "min_uses")

        if not tip_text:
            continue

        # Build context from trigger/condition info
        if trigger and min_uses:
            context = f"After using '{trigger}' {min_uses}+ times"
        elif trigger:
            context = f"After using '{trigger}' for the first time"
        else:
            context = "Based on project state analysis"

        # Build why from priority
        why_map = {
            1: "High-priority workflow recommendation",
            2: "Productivity improvement suggestion",
            3: "Nice-to-know efficiency tip",
        }
        why = why_map.get(priority, "Workflow efficiency")

        name = slugify(tip_id.replace("_", "-"))
        templates.append(
            TipTemplate(
                name=name,
                title=tip_text,
                context=context,
                recommendation=tip_text,
                why=why,
                tags=["discovery"],
                source="src/attune/discovery.py",
            )
        )

    return templates


def parse_workflow_transitions(suggestions_path: Path) -> list[TipTemplate]:
    """Parse workflow transition mappings from suggestions.py.

    Extracts which workflows suggest which follow-up workflows
    by regex-matching NextAction constructor calls.

    Args:
        suggestions_path: Path to suggestions.py.

    Returns:
        List of TipTemplate objects.
    """
    text = suggestions_path.read_text(encoding="utf-8")

    # Find each _transitions_for_X function and its NextAction calls
    func_pattern = re.compile(
        r"def (_transitions_for_(\w+))\(.*?\).*?(?=\ndef |\Z)",
        re.DOTALL,
    )

    templates: list[TipTemplate] = []
    for func_match in func_pattern.finditer(text):
        source_workflow = func_match.group(2).replace("_", "-")
        func_body = func_match.group(0)

        # Find all NextAction workflow_name values
        targets = re.findall(
            r'workflow_name="([^"]+)"',
            func_body,
        )
        if not targets:
            continue

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_targets: list[str] = []
        for t in targets:
            if t not in seen:
                seen.add(t)
                unique_targets.append(t)

        targets_str = ", ".join(unique_targets)
        name = slugify(f"after-{source_workflow}")

        templates.append(
            TipTemplate(
                name=name,
                title=f"After {source_workflow}: consider {targets_str}",
                context=f"After running the {source_workflow} workflow",
                recommendation=(
                    f"Follow up with: {targets_str}. "
                    f"These workflows complement {source_workflow} findings."
                ),
                why=(
                    f"Workflow transitions are based on common patterns "
                    f"where {source_workflow} results inform next steps."
                ),
                tags=["workflow-transition"],
                source="src/attune/workflows/suggestions.py",
            )
        )

    return templates


def _extract_field(block: str, field_name: str) -> str:
    """Extract a quoted string field from a dict block.

    Args:
        block: Raw text of dict contents.
        field_name: Field name to extract.

    Returns:
        Extracted string value, or empty string.
    """
    match = re.search(rf'"{field_name}":\s*"([^"]+)"', block)
    return match.group(1) if match else ""


def _extract_int_field(block: str, field_name: str) -> int:
    """Extract an integer field from a dict block.

    Args:
        block: Raw text of dict contents.
        field_name: Field name to extract.

    Returns:
        Extracted int value, or 0.
    """
    match = re.search(rf'"{field_name}":\s*(\d+)', block)
    return int(match.group(1)) if match else 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Tip template generator.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    discovery_path = repo_root / "src" / "attune" / "discovery.py"
    suggestions_path = repo_root / "src" / "attune" / "workflows" / "suggestions.py"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "tips"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    # Step 1: Discover from both sources
    tips: list[TipTemplate] = []

    if discovery_path.exists():
        tips.extend(parse_discovery_tips(discovery_path))
        print(f"  Discovery tips: {len(tips)} found")

    transition_tips: list[TipTemplate] = []
    if suggestions_path.exists():
        transition_tips = parse_workflow_transitions(suggestions_path)
        tips.extend(transition_tips)
        print(f"  Workflow transitions: {len(transition_tips)} found")

    if not tips:
        print("No tips found from any source")
        return 1

    # Step 2: Render
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Tip templates from {len(tips)} entries\n")

    items = [
        {
            "name": t.name,
            "title": t.title,
            "context": t.context,
            "recommendation": t.recommendation,
            "why": t.why,
            "tags": t.tags,
            "source": t.source,
            "related_topics": t.related_topics,
        }
        for t in tips
    ]

    successes, failures = render_and_output(
        env,
        "tip.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_tip_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
