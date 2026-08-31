#!/usr/bin/env python3
"""Generate Task templates from CLI commands and skill workflows.

Sources:
  1. CLI argparse commands from src/attune/cli_minimal.py
  2. Skill execution patterns from plugin/skills/*/SKILL.md

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/generate_task_templates.py           # Generate
    python scripts/generate_task_templates.py --check   # Verify
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output, slugify


@dataclass
class Step:
    """A single task step."""

    action: str
    detail: str = ""
    code: str = ""
    code_language: str = ""


@dataclass(frozen=True)
class ExecutionPart:
    """One execution code fence or trailing prose segment."""

    detail: str
    code: str
    language: str = ""


@dataclass
class TaskTemplate:
    """Populated Task template ready for rendering."""

    name: str
    title: str
    introduction: str
    steps: list[Step]
    prerequisites: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


# CLI command definitions — structured data for task generation.
# Each entry describes a user-facing command with its steps.
_CLI_TASKS: list[dict] = [
    {
        "name": "run-workflow",
        "title": "Run a workflow",
        "introduction": (
            "Execute an AI-powered analysis workflow on your codebase. "
            "Workflows include security audits, code reviews, test "
            "generation, and more."
        ),
        "prerequisites": ["ANTHROPIC_API_KEY set in environment"],
        "steps": [
            Step("List available workflows", code="attune workflow list"),
            Step(
                "Run a workflow by name",
                detail="Specify the workflow name and optional target path.",
                code='attune workflow run security-audit --path "src/"',
            ),
            Step(
                "View results",
                detail="Results are displayed in the terminal with severity grouping.",
            ),
        ],
        "tags": ["cli", "workflow"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "check-auth-status",
        "title": "Check authentication status",
        "introduction": (
            "Verify your subscription and authentication strategy. "
            "Shows which provider is active and whether your API key "
            "is configured correctly."
        ),
        "steps": [
            Step("Check status", code="attune auth status"),
            Step("View as JSON", detail="For programmatic use.", code="attune auth status --json"),
            Step("Reconfigure if needed", code="attune auth setup"),
        ],
        "tags": ["cli", "auth"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "export-telemetry",
        "title": "Export telemetry data",
        "introduction": (
            "Export your workflow usage data to CSV or JSON for "
            "analysis. Useful for tracking costs and identifying "
            "most-used workflows."
        ),
        "prerequisites": ["At least one workflow run to have data"],
        "steps": [
            Step("View usage summary", code="attune telemetry show --days 30"),
            Step(
                "Export to JSON", code="attune telemetry export --output usage.json --format json"
            ),
            Step("Export to CSV", code="attune telemetry export --output usage.csv --format csv"),
        ],
        "tags": ["cli", "telemetry"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "manage-lessons",
        "title": "Manage lessons learned",
        "introduction": (
            "Save, list, and remove lessons that persist across "
            "sessions. Lessons are stored locally and help avoid "
            "repeating mistakes."
        ),
        "steps": [
            Step("Save a lesson", code='attune remember "Always use encoding=utf-8"'),
            Step("List current lessons", code="attune lessons"),
            Step(
                "Remove a lesson",
                detail="By line number or keyword.",
                code="attune forget encoding",
            ),
        ],
        "tags": ["cli", "memory"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "run-doctor",
        "title": "Run environment health check",
        "introduction": (
            "Diagnose configuration issues, missing dependencies, "
            "and environment problems. Run this when something "
            "isn't working as expected."
        ),
        "steps": [
            Step("Run the health check", code="attune doctor"),
            Step(
                "Review findings",
                detail="Doctor reports issues with severity levels and suggested fixes.",
            ),
            Step(
                "Fix reported issues",
                detail="Follow the suggested fixes for any WARN or ERROR items.",
            ),
        ],
        "tags": ["cli", "setup"],
        "source": "src/attune/cli_minimal.py",
    },
    {
        "name": "install-plugin",
        "title": "Install the attune-ai plugin for Claude Code",
        "introduction": (
            "Install attune-ai as a Claude Code plugin to get "
            "slash commands, skills, and MCP tools directly in "
            "your Claude Code sessions."
        ),
        "prerequisites": ["Claude Code CLI installed", "pip install attune-ai"],
        "steps": [
            Step(
                "Add the marketplace",
                code="claude plugin marketplace add Smart-AI-Memory/attune-ai",
            ),
            Step("Install the plugin", code="claude plugin install attune-ai@attune-ai"),
            Step("Verify installation", detail="Type /attune in a Claude Code session to test."),
        ],
        "tags": ["setup", "claude-code", "plugin"],
        "source": "README.md",
    },
    {
        "name": "browse-help-docs",
        "title": "Browse documentation templates",
        "introduction": (
            "Use the built-in help system to browse error resolutions, "
            "tips, tool references, and warnings. Supports tag filtering "
            "and feedback."
        ),
        "steps": [
            Step("List categories", code="attune help-docs"),
            Step("Browse a category", code="attune help-docs errors"),
            Step(
                "Show a specific template",
                code="attune help-docs err-shadow-directories-at-repo-root-break-imports --deep",
            ),
            Step("Filter by tag", code="attune help-docs --tag security"),
        ],
        "tags": ["cli", "help"],
        "source": "src/attune/cli_commands/help_commands.py",
    },
]


_FENCE_LINE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$")


def _fence_line(line: str) -> tuple[str, int, str] | None:
    match = _FENCE_LINE_RE.match(line)
    if not match:
        return None
    marker = match.group(1)
    return marker[0], len(marker), match.group(2).strip()


def _extract_section(body: str, heading: str) -> str:
    """Extract a ## section's body from markdown.

    Args:
        body: Full markdown body.
        heading: Section heading (without ##).

    Returns:
        Section body text, or empty string.
    """
    lines = body.splitlines()
    start: int | None = None
    active_fence: tuple[str, int] | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        fence = _fence_line(line)
        if active_fence is None and fence:
            active_fence = fence[:2]
            continue
        if active_fence is not None:
            if fence:
                closes = (
                    fence[0] == active_fence[0] and fence[1] >= active_fence[1] and not fence[2]
                )
                if closes:
                    active_fence = None
            continue
        if start is None and stripped == f"## {heading}":
            start = index + 1
            continue
        if start is not None and stripped.startswith("## "):
            return "\n".join(lines[start:index]).strip()
    return "\n".join(lines[start:]).strip() if start is not None else ""


def _parse_numbered_items(text: str) -> list[tuple[str, str]]:
    """Parse numbered items like '1. **Label**: description'.

    Args:
        text: Section body text.

    Returns:
        List of (label, description) tuples.
    """
    items: list[tuple[str, str]] = []
    for match in re.finditer(
        r"\d+\.\s+\*\*([^*]+)\*\*:?\s*(.*?)(?=\n\d+\.|\Z)",
        text,
        re.DOTALL,
    ):
        label = match.group(1).strip()
        desc = re.sub(r"\n\s+", " ", match.group(2).strip())
        items.append((label, desc))
    return items


def _parse_bullet_items(text: str) -> list[str]:
    """Parse bullet-point items from markdown.

    Args:
        text: Section body text.

    Returns:
        List of item strings.
    """
    items: list[str] = []
    for match in re.finditer(
        r"^- (.+?)(?=\n- |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    ):
        items.append(re.sub(r"\n\s+", " ", match.group(1).strip()))
    return items


def _execution_parts(execution: str) -> list[ExecutionPart]:
    """Pair each fenced command with its immediately preceding Markdown."""
    parts: list[ExecutionPart] = []
    cursor = 0
    active: tuple[str, int, int, int, str] | None = None
    offset = 0
    for line in execution.splitlines(keepends=True):
        fence = _fence_line(line.rstrip("\r\n"))
        if active is None and fence:
            active = (fence[0], fence[1], offset, offset + len(line), fence[2])
        elif active is not None and fence:
            closes = fence[0] == active[0] and fence[1] >= active[1] and not fence[2]
            if closes:
                detail = re.sub(r"\n{3,}", "\n\n", execution[cursor : active[2]].strip())
                info = active[4]
                language = info.split(maxsplit=1)[0].lower() if info else ""
                parts.append(ExecutionPart(detail, execution[active[3] : offset].strip(), language))
                cursor = offset + len(line)
                active = None
        offset += len(line)
    trailing = re.sub(r"\n{3,}", "\n\n", execution[cursor:].strip())
    if trailing or not parts:
        parts.append(ExecutionPart(trailing, ""))
    return parts


def parse_skill_tasks(skills_dir: Path) -> list[TaskTemplate]:
    """Parse SKILL.md files to generate task templates.

    Extracts specific steps from Scoping (numbered items),
    Execution (all code blocks), and Follow-Up (bullet items).

    Args:
        skills_dir: Path to plugin/skills/ directory.

    Returns:
        List of TaskTemplate objects.
    """
    templates: list[TaskTemplate] = []

    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        post = frontmatter.load(str(skill_file))
        name = post.get("name", skill_dir.name)
        description = post.get("description", "")
        argument_hint = post.get("argument-hint", "")

        body = post.content
        if "## Execution" not in body and "## Scoping" not in body:
            continue

        steps: list[Step] = []

        # Scoping: extract numbered questions
        scoping = _extract_section(body, "Scoping")
        if scoping:
            numbered = _parse_numbered_items(scoping)
            if numbered:
                for label, desc in numbered:
                    steps.append(
                        Step(
                            action=f"Define {label.lower()}",
                            detail=desc or f"Answer the {label.lower()} question.",
                        )
                    )
            else:
                steps.append(
                    Step(
                        action=f"Scope the {name} request",
                        detail="Answer the scoping questions before running.",
                    )
                )

        # Execution: extract all code blocks
        execution = _extract_section(body, "Execution")
        if execution:
            code_index = 0
            output_languages = {"markdown", "md", "json", "yaml", "yml", "toml", "text"}
            for part in _execution_parts(execution):
                if part.code and part.language not in output_languages:
                    code_index += 1
                    action = (
                        "Run the tool" if code_index == 1 else f"Run tool (option {code_index})"
                    )
                elif part.code:
                    action = "Review output example"
                else:
                    action = f"Review {name} execution guidance"
                detail = part.detail
                if not detail and part.code and part.language in output_languages:
                    detail = "Compare the result with this expected output shape."
                elif not detail and part.code:
                    detail = "Run this command with the scoped parameters."
                elif not detail:
                    detail = "Review the execution guidance."
                steps.append(
                    Step(
                        action=action,
                        detail=detail,
                        code=part.code,
                        code_language=part.language,
                    )
                )

        # Follow-Up: extract bullet items
        followup = _extract_section(body, "Follow-Up")
        if followup:
            bullets = _parse_bullet_items(followup)
            if bullets:
                options = "; ".join(b.strip('"') for b in bullets[:3])
                steps.append(Step(action="Choose follow-up action", detail=options))
            else:
                steps.append(Step(action="Review results and choose next steps"))

        if not steps:
            continue

        usage = f"`/{name} {argument_hint}`" if argument_hint else f"`/{name}`"

        templates.append(
            TaskTemplate(
                name=slugify(f"use-{name}"),
                title=f"Use the {name} skill",
                introduction=f"{description}\n\nInvoke with: {usage}",
                steps=steps,
                tags=["skill", "task"],
                source=f"plugin/skills/{skill_dir.name}/SKILL.md",
                related_topics=[
                    {
                        "type": "Reference",
                        "description": f"Skill: {name} — full reference",
                    }
                ],
            )
        )

    return templates


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Task template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "plugin" / "skills"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "tasks"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    tasks: list[TaskTemplate] = []

    # Source 1: CLI command tasks
    for task_def in _CLI_TASKS:
        tasks.append(
            TaskTemplate(
                name=task_def["name"],
                title=task_def["title"],
                introduction=task_def["introduction"],
                steps=task_def["steps"],
                prerequisites=task_def.get("prerequisites", []),
                tags=task_def.get("tags", []),
                source=task_def.get("source", ""),
            )
        )
    print(f"  CLI tasks: {len(_CLI_TASKS)} found")

    # Source 2: Skill usage tasks
    if skills_dir.exists():
        skill_tasks = parse_skill_tasks(skills_dir)
        tasks.extend(skill_tasks)
        print(f"  Skill tasks: {len(skill_tasks)} found")

    if not tasks:
        print("No tasks found")
        return 1

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Task templates from {len(tasks)} entries\n")

    items = [
        {
            "name": t.name,
            "title": t.title,
            "introduction": t.introduction,
            "steps": [
                {
                    "action": s.action,
                    "detail": s.detail,
                    "code": s.code,
                    "code_language": s.code_language,
                }
                for s in t.steps
            ],
            "prerequisites": t.prerequisites,
            "tags": t.tags,
            "source": t.source,
            "related_topics": t.related_topics,
        }
        for t in tasks
    ]

    successes, failures = render_and_output(
        env,
        "task.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_task_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
