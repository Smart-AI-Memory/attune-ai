#!/usr/bin/env python3
"""Generate Note templates from terms, rules, and design decisions.

Sources:
  1. Terms table from CLAUDE.md (root)
  2. Key sections from .claude/CLAUDE.md (Socratic,
     Critical Rules, Code Simplification, Markdown)
  3. Architecture notes from .claude/CLAUDE.md
  4. Design decisions from documentation-stack-spec.md

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/generate_note_templates.py           # Generate
    python scripts/generate_note_templates.py --check   # Verify
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output, slugify


@dataclass
class NoteTemplate:
    """Populated Note template ready for rendering."""

    name: str
    title: str
    context: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


def parse_terms(root_claude_md: Path) -> list[NoteTemplate]:
    """Parse Terms table from root CLAUDE.md.

    Args:
        root_claude_md: Path to CLAUDE.md (repo root).

    Returns:
        List of NoteTemplate objects.
    """
    text = root_claude_md.read_text(encoding="utf-8")

    terms_match = re.search(
        r"## Terms\n+\|[^\n]+\n\|[-\s|]+\n((?:\|[^\n]+\n)+)",
        text,
    )
    if not terms_match:
        return []

    templates: list[NoteTemplate] = []
    rows = terms_match.group(1).strip().split("\n")

    for row in rows:
        cells = [c.strip() for c in row.split("|") if c.strip()]
        if len(cells) < 2:
            continue

        term = cells[0].strip("*")
        meaning = cells[1]

        templates.append(
            NoteTemplate(
                name=slugify(f"term-{term}"),
                title=f"Term: {term}",
                context="Project terminology used in the attune-ai codebase.",
                content=f"**{term}** — {meaning}",
                tags=["terminology"],
                source="CLAUDE.md",
            )
        )

    return templates


def _extract_section(text: str, heading: str) -> str:
    """Extract a ## section body from markdown.

    Args:
        text: Full markdown text.
        heading: Section heading (without ##).

    Returns:
        Section body, or empty string.
    """
    pattern = rf"## {re.escape(heading)}\n+(.+?)(?=\n## |\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_claude_md_sections(
    claude_md_path: Path,
) -> list[NoteTemplate]:
    """Parse key sections from .claude/CLAUDE.md as notes.

    Extracts Socratic rules, Critical Rules, Code
    Simplification, and Markdown Formatting as
    supplementary context notes.

    Args:
        claude_md_path: Path to .claude/CLAUDE.md.

    Returns:
        List of NoteTemplate objects.
    """
    text = claude_md_path.read_text(encoding="utf-8")
    templates: list[NoteTemplate] = []

    sections = {
        "Socratic Interaction Rule": {
            "context": "Core UX principle: always guide users with "
            "questions before executing actions.",
            "tags": ["philosophy", "ux"],
        },
        "Critical Rules": {
            "context": "Non-negotiable security and quality rules " "for the attune-ai codebase.",
            "tags": ["security", "rules"],
        },
        "Code Simplification": {
            "context": "Engineering philosophy: simpler is better. "
            "Three clear lines beat one clever abstraction.",
            "tags": ["philosophy", "code-quality"],
        },
        "Markdown Formatting": {
            "context": "Formatting standards for all .md files in " "the project.",
            "tags": ["formatting", "standards"],
        },
    }

    for heading, meta in sections.items():
        body = _extract_section(text, heading)
        if not body:
            continue

        templates.append(
            NoteTemplate(
                name=slugify(heading),
                title=heading,
                context=meta["context"],
                content=body,
                tags=meta["tags"],
                source=".claude/CLAUDE.md",
            )
        )

    return templates


def parse_architecture_notes(
    claude_md_path: Path,
) -> list[NoteTemplate]:
    """Parse architecture/project structure notes.

    Args:
        claude_md_path: Path to .claude/CLAUDE.md.

    Returns:
        List of NoteTemplate objects.
    """
    text = claude_md_path.read_text(encoding="utf-8")
    templates: list[NoteTemplate] = []

    struct_match = re.search(
        r"## Project Structure\n+```text\n(.+?)```",
        text,
        re.DOTALL,
    )
    if struct_match:
        templates.append(
            NoteTemplate(
                name="project-structure",
                title="Project structure overview",
                context="Directory layout of the attune-ai package.",
                content=f"```text\n{struct_match.group(1).strip()}\n```",
                tags=["architecture"],
                source=".claude/CLAUDE.md",
            )
        )

    hubs = _extract_section(text, "Command Hubs")
    if hubs:
        templates.append(
            NoteTemplate(
                name="command-hubs",
                title="Command hub overview",
                context="Available slash command hubs in Claude Code.",
                content=hubs,
                tags=["cli", "claude-code"],
                source=".claude/CLAUDE.md",
            )
        )

    return templates


def parse_design_decisions(spec_path: Path) -> list[NoteTemplate]:
    """Parse design decisions from the documentation stack spec.

    Args:
        spec_path: Path to documentation-stack-spec.md.

    Returns:
        List of NoteTemplate objects.
    """
    if not spec_path.exists():
        return []

    text = spec_path.read_text(encoding="utf-8")
    templates: list[NoteTemplate] = []

    decision_pattern = re.compile(
        r"^### (D\d+)\.\s+(.+?)\n\n(.+?)(?=\n### D\d+|\n---|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    for match in decision_pattern.finditer(text):
        d_id = match.group(1).lower()
        title = match.group(2).strip()
        body = match.group(3).strip()

        templates.append(
            NoteTemplate(
                name=slugify(f"decision-{d_id}-{title}"),
                title=f"Design decision: {title}",
                context="Documentation stack architecture decision.",
                content=body,
                tags=["architecture", "design-decision"],
                source=".claude/plans/documentation-stack-spec.md",
            )
        )

    return templates


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Note template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    root_claude_md = repo_root / "CLAUDE.md"
    dot_claude_md = repo_root / ".claude" / "CLAUDE.md"
    spec_path = repo_root / ".claude" / "plans" / "documentation-stack-spec.md"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "notes"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    notes: list[NoteTemplate] = []

    # Source 1: Terms from root CLAUDE.md
    if root_claude_md.exists():
        terms = parse_terms(root_claude_md)
        notes.extend(terms)
        print(f"  Terms: {len(terms)} found")

    # Source 2: Key sections from .claude/CLAUDE.md
    if dot_claude_md.exists():
        sections = parse_claude_md_sections(dot_claude_md)
        notes.extend(sections)
        print(f"  CLAUDE.md sections: {len(sections)} found")

    # Source 3: Architecture notes
    if dot_claude_md.exists():
        arch = parse_architecture_notes(dot_claude_md)
        notes.extend(arch)
        print(f"  Architecture notes: {len(arch)} found")

    # Source 4: Design decisions
    decisions = parse_design_decisions(spec_path)
    notes.extend(decisions)
    print(f"  Design decisions: {len(decisions)} found")

    if not notes:
        print("No notes found from any source")
        return 1

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Note templates from {len(notes)} entries\n")

    items = [
        {
            "name": n.name,
            "title": n.title,
            "context": n.context,
            "content": n.content,
            "tags": n.tags,
            "source": n.source,
            "related_topics": n.related_topics,
        }
        for n in notes
    ]

    successes, failures = render_and_output(
        env,
        "note.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_note_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
