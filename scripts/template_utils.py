"""Shared utilities for documentation template generators.

Provides common functions used across all template type
generators: slugification, tag classification, sentence
splitting, Lessons Learned parsing, and render/output.

All generators follow the sync paradigm:
Discover -> Parse -> Transform -> Validate -> Output -> Verify
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment


@dataclass
class LessonEntry:
    """A single Lessons Learned entry parsed from CLAUDE.md."""

    title: str
    body: str
    raw: str


def parse_lessons_learned(claude_md_path: Path) -> list[LessonEntry]:
    """Parse Lessons Learned entries from CLAUDE.md.

    Each entry follows the format:
        - **Title**: Body text spanning
          multiple indented lines.

    Args:
        claude_md_path: Path to CLAUDE.md file.

    Returns:
        List of parsed LessonEntry objects.
    """
    text = claude_md_path.read_text(encoding="utf-8")

    # Find the Lessons Learned section
    section_match = re.search(r"^## Lessons Learned\s*\n", text, re.MULTILINE)
    if not section_match:
        return []

    section_start = section_match.end()

    # Find the next ## heading or end of file
    next_section = re.search(r"^## ", text[section_start:], re.MULTILINE)
    if next_section:
        section_text = text[section_start : section_start + next_section.start()]
    else:
        section_text = text[section_start:]

    # Parse individual entries.  Each starts with "- **Title**:"
    # and continues on indented lines until the next entry or
    # end of section.
    entry_pattern = re.compile(
        r"^- \*\*(.+?)\*\*:\s*(.+?)(?=\n- \*\*|\n\n\Z|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    entries: list[LessonEntry] = []
    for match in entry_pattern.finditer(section_text):
        title = match.group(1).strip()
        body_raw = match.group(2).strip()
        body = textwrap.dedent(body_raw).strip()
        body = re.sub(r"\n  ", " ", body)
        entries.append(LessonEntry(title=title, body=body, raw=match.group(0)))

    return entries


def slugify(title: str) -> str:
    """Convert a title to a filesystem-safe slug.

    Args:
        title: The title text.

    Returns:
        Lowercase slug with hyphens, max 64 chars.
    """
    slug = title.lower()
    slug = re.sub(r"[`'\"\(\)]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if len(slug) > 64:
        slug = slug[:64].rsplit("-", 1)[0]
    return slug


def classify_tags(title: str, body: str) -> list[str]:
    """Classify content into tags based on keywords.

    Args:
        title: Content title.
        body: Content body text.

    Returns:
        List of tag strings.
    """
    combined = f"{title} {body}".lower()
    tags: list[str] = []

    tag_patterns = {
        "ci": ["ci ", "ci/", "github actions", "workflow yaml"],
        "testing": ["test", "pytest", "mock", "patch", "fixture"],
        "security": [
            "ssrf",
            "security",
            "eval()",
            "exec()",
            "path traversal",
            "validate",
        ],
        "imports": ["import", "module", "shadow dir"],
        "git": [
            "git ",
            "commit",
            "push",
            "merge",
            "tag",
            "branch",
            "pre-commit",
        ],
        "windows": ["windows", "cp1252", "drive letter"],
        "macos": ["macos", "/var", "/private"],
        "claude-code": [
            "claude code",
            "plugin",
            "skill",
            "hook",
            "stop hook",
            "mcp",
        ],
        "packaging": ["pypi", "dist/", "twine", "pip"],
        "python": [
            "dataclass",
            "datetime",
            "path.",
            "ruff",
            "mypy",
            "bandit",
        ],
    }

    for tag, patterns in tag_patterns.items():
        if any(p in combined for p in patterns):
            tags.append(tag)

    return tags


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, respecting backtick-quoted code.

    Periods inside backticks (e.g. `Path.read_text()`) are
    preserved. Only sentence-ending periods followed by a
    space or end-of-string are treated as boundaries.

    Args:
        text: Input text.

    Returns:
        List of sentence strings.
    """
    placeholder = "\x00DOT\x00"
    protected = re.sub(
        r"`[^`]+`",
        lambda m: m.group(0).replace(".", placeholder),
        text,
    )
    parts = re.split(r"\.(?:\s|$)", protected)
    return [p.replace(placeholder, ".").strip() for p in parts if p.strip()]


def render_and_output(
    env: Environment,
    template_name: str,
    items: list[dict],
    output_dir: Path,
    check: bool,
) -> tuple[int, int]:
    """Render templates and write or check output files.

    Each item dict must have a 'name' key for the filename
    and all other keys required by the Jinja2 template.

    Args:
        env: Jinja2 Environment with template loader.
        template_name: Name of the .jinja2 template file.
        items: List of dicts, each rendered to one file.
        output_dir: Directory to write generated files.
        check: If True, compare instead of writing.

    Returns:
        Tuple of (successes, failures) counts.
    """
    template = env.get_template(template_name)
    successes = 0
    failures = 0

    for item in items:
        rendered = template.render(**item)
        output_file = output_dir / f"{item['name']}.md"

        if check:
            if not output_file.exists():
                print(f"  [FAIL] {item['name']}: missing")
                failures += 1
            elif output_file.read_text(encoding="utf-8") == rendered:
                print(f"  [  OK] {item['name']}: in sync")
                successes += 1
            else:
                print(f"  [FAIL] {item['name']}: out of sync")
                failures += 1
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered, encoding="utf-8")
            print(f"  [  OK] {item['name']}: generated")
            successes += 1

    return successes, failures
