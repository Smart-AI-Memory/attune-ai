#!/usr/bin/env python3
"""Generate Comparison templates — side-by-side feature matrices.

Sources:
  1. Plugin comparison (Lite vs Full)
  2. Workflow vs Wizard
  3. CLI vs Claude Code usage
  4. Authentication strategies

Usage:
    python scripts/generate_comparison_templates.py           # Generate
    python scripts/generate_comparison_templates.py --check   # Verify
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output


@dataclass
class ComparisonOption:
    """One option in a comparison."""

    name: str


@dataclass
class ComparisonRow:
    """One feature row in a comparison."""

    feature: str
    values: list[str]


@dataclass
class ComparisonTemplate:
    """Populated Comparison template."""

    name: str
    title: str
    context: str
    options: list[ComparisonOption]
    rows: list[ComparisonRow]
    recommendation: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


_COMPARISONS: list[dict] = [
    {
        "name": "lite-vs-full",
        "title": "Attune Lite vs Attune AI",
        "context": "Choosing between the lightweight plugin (no dependencies) and the full framework.",
        "options": [
            ComparisonOption("Attune Lite"),
            ComparisonOption("Attune AI"),
        ],
        "rows": [
            ComparisonRow("Install", ["No pip needed", "pip install attune-ai"]),
            ComparisonRow("API key required", ["No", "Yes (ANTHROPIC_API_KEY)"]),
            ComparisonRow("Skills", ["5", "13"]),
            ComparisonRow("Workflows", ["5 (via skills)", "17 (CLI + skills)"]),
            ComparisonRow("Wizards", ["0", "5"]),
            ComparisonRow("Agent templates", ["0", "14"]),
            ComparisonRow("MCP tools", ["0", "31"]),
            ComparisonRow("CLI", ["No", "Yes (attune command)"]),
            ComparisonRow("Tier routing", ["No", "Yes (up to 90% savings)"]),
            ComparisonRow("Telemetry", ["No", "Yes (cost tracking)"]),
        ],
        "recommendation": "Start with **Attune Lite** if you just want Claude Code skills with zero setup. Upgrade to **Attune AI** when you need CLI workflows, cost optimization, or the full MCP toolset.",
        "tags": ["plugin", "setup"],
        "source": "smartaimemory.com/attune-plugin/",
    },
    {
        "name": "workflow-vs-wizard",
        "title": "Workflow vs Wizard",
        "context": "Understanding the difference between non-interactive workflows and guided wizards.",
        "options": [
            ComparisonOption("Workflow"),
            ComparisonOption("Wizard"),
        ],
        "rows": [
            ComparisonRow("Interaction", ["Non-interactive", "Guided step-by-step"]),
            ComparisonRow("Input", ["CLI flags or JSON", "Interactive questions"]),
            ComparisonRow("Output", ["Structured JSON/report", "Conversation with follow-ups"]),
            ComparisonRow("Invocation", ["`attune workflow run <name>`", "`/wizard run <name>`"]),
            ComparisonRow("Count", ["17 built-in", "5 built-in"]),
            ComparisonRow("Customization", ["Python subclass", "YAML or Python"]),
            ComparisonRow("CI/CD friendly", ["Yes", "No (needs interaction)"]),
            ComparisonRow("Best for", ["Automated analysis", "Complex decision-making"]),
        ],
        "recommendation": "Use **workflows** for CI/CD pipelines and automated analysis. Use **wizards** when the task needs human judgment at each step (debugging, release prep).",
        "tags": ["workflow", "architecture"],
        "source": ".claude/CLAUDE.md",
    },
    {
        "name": "cli-vs-claude-code",
        "title": "CLI vs Claude Code usage",
        "context": "Two ways to use attune-ai: the standalone CLI or inside Claude Code conversations.",
        "options": [
            ComparisonOption("CLI (attune)"),
            ComparisonOption("Claude Code (skills)"),
        ],
        "rows": [
            ComparisonRow("Invocation", ["`attune workflow run`", "`/security-audit`"]),
            ComparisonRow("Scoping", ["CLI flags", "Socratic questions"]),
            ComparisonRow("Output", ["Terminal (Rich)", "Conversation (Markdown)"]),
            ComparisonRow("Context-aware", ["No", "Yes (sees your codebase)"]),
            ComparisonRow("CI/CD", ["Yes", "No"]),
            ComparisonRow("Follow-up", ["Manual", 'Interactive ("fix this?")']),
            ComparisonRow("Cost tracking", ["Yes (attune costs)", "Via MCP tools"]),
            ComparisonRow("Setup", ["pip install + API key", "Plugin install"]),
        ],
        "recommendation": "Use the **CLI** for scripting, CI/CD, and batch operations. Use **Claude Code skills** for interactive development where context and follow-up matter.",
        "tags": ["cli", "claude-code"],
        "source": "smartaimemory.com/attune-plugin/",
    },
    {
        "name": "auth-strategies",
        "title": "Authentication strategies",
        "context": "Choosing how attune-ai authenticates with the Anthropic API.",
        "options": [
            ComparisonOption("Subscription"),
            ComparisonOption("API Key"),
        ],
        "rows": [
            ComparisonRow("Setup", ["Automatic (Claude Code)", "Set ANTHROPIC_API_KEY"]),
            ComparisonRow("Cost", ["Included in subscription", "Pay per token"]),
            ComparisonRow("Tier routing", ["Limited", "Full (CHEAP/CAPABLE/PREMIUM)"]),
            ComparisonRow("Large files", ["May hit limits", "Full control"]),
            ComparisonRow("CI/CD", ["Not available", "Yes"]),
            ComparisonRow(
                "Best for", ["Quick start, small projects", "Production, cost optimization"]
            ),
        ],
        "recommendation": "**Subscription** works out of the box for most users. Switch to **API Key** when you need CI/CD, tier routing for cost savings, or processing large codebases.",
        "tags": ["auth", "setup"],
        "source": "src/attune/models/auth_cli.py",
    },
]


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Comparison template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "comparisons"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    templates = [ComparisonTemplate(**c) for c in _COMPARISONS]
    print(f"  Comparisons: {len(templates)} found")

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Comparison templates from {len(templates)} entries\n")

    items = [
        {
            "name": t.name,
            "title": t.title,
            "context": t.context,
            "options": [{"name": o.name} for o in t.options],
            "rows": [{"feature": r.feature, "cells": r.values} for r in t.rows],
            "recommendation": t.recommendation,
            "tags": t.tags,
            "source": t.source,
            "related_topics": t.related_topics,
        }
        for t in templates
    ]

    successes, failures = render_and_output(
        env,
        "comparison.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_comparison_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
