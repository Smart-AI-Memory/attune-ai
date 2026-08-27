#!/usr/bin/env python3
"""Generate Tip templates from the static tip catalog and workflow transitions.

Sources:
  1. DISCOVERY_TIPS catalog below (8 tips — formerly parsed out of the
     retired src/attune/discovery.py)
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


# The tip catalog. These tips originated as the runtime DISCOVERY_TIPS
# dict in src/attune/discovery.py (progressive-discovery engine, removed
# 2026-08-26 with zero runtime callers); the generated help pages
# outlived the engine, so the catalog now lives here, in its only
# consumer.
DISCOVERY_TIPS: list[dict[str, str]] = [
    {
        "name": "after-first-inspect",
        "tip": "Try 'attune workflow run ship' before commits for pre-flight checks",
        "context": "After using 'inspect' 1+ times",
        "why": "Productivity improvement suggestion",
    },
    {
        "name": "after-first-health",
        "tip": "Use 'ruff check --fix . && ruff format .' to auto-fix lint and format issues",
        "context": "After using 'health' 1+ times",
        "why": "Productivity improvement suggestion",
    },
    {
        "name": "after-10-inspects",
        "tip": "Run 'attune workflow run code-review' for AI-powered code analysis",
        "context": "After using 'inspect' 10+ times",
        "why": "High-priority workflow recommendation",
    },
    {
        "name": "after-5-ships",
        "tip": "Run 'attune doctor' for a comprehensive environment health check",
        "context": "After using 'ship' 5+ times",
        "why": "High-priority workflow recommendation",
    },
    {
        "name": "high-tech-debt",
        "tip": "Tech debt is trending up. Run 'attune doctor' for priority focus areas",
        "context": "Based on project state analysis",
        "why": "High-priority workflow recommendation",
    },
    {
        "name": "no-patterns",
        "tip": "Run 'attune workflow run code-review' to analyze your codebase",
        "context": "Based on project state analysis",
        "why": "High-priority workflow recommendation",
    },
    {
        "name": "cost-savings",
        "tip": "Check your API savings with 'attune costs' - model routing can save 80%!",
        "context": "Based on project state analysis",
        "why": "Productivity improvement suggestion",
    },
    {
        "name": "weekly-review",
        "tip": "Weekly reminder: Run 'attune workflow run security-audit' to check for issues",
        "context": "Based on project state analysis",
        "why": "Productivity improvement suggestion",
    },
]


def discovery_tip_templates() -> list[TipTemplate]:
    """Build TipTemplate objects from the static tip catalog.

    Returns:
        List of TipTemplate objects.
    """
    return [
        TipTemplate(
            name=entry["name"],
            title=entry["tip"],
            context=entry["context"],
            recommendation=entry["tip"],
            why=entry["why"],
            tags=["discovery"],
            source="scripts/generate_tip_templates.py",
        )
        for entry in DISCOVERY_TIPS
    ]


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
    suggestions_path = repo_root / "src" / "attune" / "workflows" / "suggestions.py"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "tips"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    # Step 1: Discover from both sources
    tips: list[TipTemplate] = list(discovery_tip_templates())
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
