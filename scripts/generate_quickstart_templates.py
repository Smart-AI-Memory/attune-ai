#!/usr/bin/env python3
"""Generate Quickstart templates — one goal, one command, one result.

Sources:
  1. Workflow one-liners from CLI argparse
  2. Skill invocations from plugin/skills/*/SKILL.md
  3. Key setup commands (install, plugin, auth)

Usage:
    python scripts/generate_quickstart_templates.py           # Generate
    python scripts/generate_quickstart_templates.py --check   # Verify
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output, slugify


@dataclass
class QuickstartTemplate:
    """Populated Quickstart template."""

    name: str
    title: str
    goal: str
    command: str
    result: str = ""
    next_step: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


# Hand-crafted quickstarts for key entry points
_QUICKSTARTS: list[dict] = [
    {
        "name": "install",
        "title": "Install attune-ai",
        "goal": "Install the attune-ai package from PyPI.",
        "command": "pip install attune-ai",
        "result": "The `attune` CLI is now available in your terminal.",
        "next_step": "Run `attune doctor` to verify your environment.",
        "tags": ["setup"],
        "source": "README.md",
    },
    {
        "name": "install-plugin",
        "title": "Install the Claude Code plugin",
        "goal": "Add attune-ai skills to Claude Code.",
        "command": "claude plugin marketplace add Smart-AI-Memory/attune-ai && claude plugin install attune-ai@attune-ai",
        "result": "13 skills available via slash commands in Claude Code.",
        "next_step": "Type `/attune` in a Claude Code session.",
        "tags": ["setup", "claude-code"],
        "source": "README.md",
    },
    {
        "name": "run-security-audit",
        "title": "Run a security audit",
        "goal": "Scan your codebase for security vulnerabilities.",
        "command": 'attune workflow run security-audit --path "src/"',
        "result": "Severity-grouped findings with CWE identifiers.",
        "next_step": "Fix critical issues, then run `attune workflow run test-gen`.",
        "tags": ["workflow", "security"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "run-code-review",
        "title": "Run a code review",
        "goal": "Get AI-powered code quality analysis.",
        "command": 'attune workflow run code-review --path "src/"',
        "result": "Quality findings grouped by severity.",
        "next_step": "Follow up with `/smart-test` to generate tests for flagged areas.",
        "tags": ["workflow", "code-quality"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "generate-tests",
        "title": "Generate tests for a module",
        "goal": "Auto-generate pytest tests for uncovered code.",
        "command": "attune workflow run test-gen --path src/attune/help/engine.py",
        "result": "Generated test file with edge cases and assertions.",
        "next_step": "Run `pytest` to verify the generated tests pass.",
        "tags": ["workflow", "testing"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "check-costs",
        "title": "Check API costs",
        "goal": "See how much your workflow runs have cost.",
        "command": "attune costs",
        "result": "Cost breakdown by workflow with savings from tier routing.",
        "next_step": "Export with `attune telemetry export -o costs.json`.",
        "tags": ["cli", "telemetry"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "check-health",
        "title": "Run environment health check",
        "goal": "Diagnose configuration and dependency issues.",
        "command": "attune doctor",
        "result": "Health report with PASS/WARN/ERROR for each check.",
        "next_step": "Fix any WARN or ERROR items shown.",
        "tags": ["cli", "setup"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "browse-help",
        "title": "Browse documentation",
        "goal": "Find help templates for errors, tips, and tools.",
        "command": "attune help-docs --tags",
        "result": "List of 34 tags with template counts for filtering.",
        "next_step": "Filter by tag: `attune help-docs --tag security`.",
        "tags": ["cli", "help"],
        "source": "src/attune/cli_commands/help_commands.py",
    },
]


def parse_skill_quickstarts(skills_dir: Path) -> list[QuickstartTemplate]:
    """Generate quickstarts from skill invocations.

    Each skill with an argument-hint gets a one-liner
    quickstart showing the slash command.

    Args:
        skills_dir: Path to plugin/skills/ directory.

    Returns:
        List of QuickstartTemplate objects.
    """
    templates: list[QuickstartTemplate] = []

    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        post = frontmatter.load(str(skill_file))
        name = post.get("name", skill_dir.name)
        description = post.get("description", "")
        argument_hint = post.get("argument-hint", "")

        if not argument_hint:
            continue

        # Truncate description to first sentence
        desc = description.split(".")[0] + "." if "." in description else description

        templates.append(
            QuickstartTemplate(
                name=slugify(f"skill-{name}"),
                title=f"Use /{name}",
                goal=desc,
                command=f"/{name} {argument_hint}",
                result="Structured results in your Claude Code conversation.",
                next_step=f"See full reference: `attune help-docs ref-skill-{slugify(name)}`",
                tags=["skill", "claude-code"],
                source=f"plugin/skills/{skill_dir.name}/SKILL.md",
            )
        )

    return templates


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Quickstart template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "plugin" / "skills"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "quickstarts"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    quickstarts: list[QuickstartTemplate] = []

    # Source 1: Hand-crafted quickstarts
    for qs in _QUICKSTARTS:
        quickstarts.append(QuickstartTemplate(**qs))
    print(f"  CLI quickstarts: {len(_QUICKSTARTS)} found")

    # Source 2: Skill quickstarts
    if skills_dir.exists():
        skill_qs = parse_skill_quickstarts(skills_dir)
        quickstarts.extend(skill_qs)
        print(f"  Skill quickstarts: {len(skill_qs)} found")

    if not quickstarts:
        print("No quickstarts found")
        return 1

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Quickstart templates from {len(quickstarts)} entries\n")

    items = [
        {
            "name": q.name,
            "title": q.title,
            "goal": q.goal,
            "command": q.command,
            "result": q.result,
            "next_step": q.next_step,
            "tags": q.tags,
            "source": q.source,
            "related_topics": q.related_topics,
        }
        for q in quickstarts
    ]

    successes, failures = render_and_output(
        env,
        "quickstart.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_quickstart_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
