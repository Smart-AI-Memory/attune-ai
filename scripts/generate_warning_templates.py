#!/usr/bin/env python3
"""Generate Warning templates from Lessons Learned in CLAUDE.md.

Parses Lessons Learned entries that contain preventive guidance
(Always/Never/Avoid patterns) and reframes them as Warning
templates with Condition/Risk/Mitigation structure.

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/generate_warning_templates.py           # Generate
    python scripts/generate_warning_templates.py --check   # Verify
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from template_utils import (
    classify_tags,
    parse_lessons_learned,
    render_and_output,
    slugify,
    split_sentences,
)

# Keywords that indicate preventive guidance
_TITLE_KEYWORDS = (
    "always",
    "never",
    "avoid",
    "must",
    "before",
    "don't",
    "do not",
    "prefer",
    "keep",
    "ensure",
)

_IMPERATIVE_STARTS = (
    "Always",
    "Never",
    "Use",
    "Avoid",
    "Before",
    "Do not",
    "Don't",
    "Ensure",
    "Prefer",
    "Add",
    "Remove",
    "Check",
    "Run",
    "Set",
    "Move",
)


@dataclass
class WarningTemplate:
    """Populated Warning template ready for rendering."""

    name: str
    title: str
    condition: str
    risk: str
    mitigation_steps: list[str]
    confidence: str = "Verified"
    confidence_reason: str = "Confirmed by prior incident (Lessons Learned)"
    tags: list[str] = field(default_factory=list)
    source: str = ".claude/CLAUDE.md"
    related_topics: list[dict[str, str]] = field(default_factory=list)


def is_warning_worthy(title: str, body: str) -> bool:
    """Determine if a Lessons Learned entry qualifies as a Warning.

    An entry qualifies if:
    - Title contains prescriptive keywords, OR
    - Body contains prescriptive keywords, OR
    - Body has 1+ imperative sentences

    Args:
        title: Lesson title.
        body: Lesson body text.

    Returns:
        True if entry should generate a Warning template.
    """
    combined_lower = f"{title} {body}".lower()
    if any(kw in combined_lower for kw in _TITLE_KEYWORDS):
        return True

    sentences = split_sentences(body)
    return any(s.startswith(_IMPERATIVE_STARTS) and len(s) > 10 for s in sentences)


def extract_condition(body: str) -> str:
    """Extract the condition (when this warning applies).

    Uses the first sentence of the body as the setup.

    Args:
        body: Lesson body text.

    Returns:
        Condition string.
    """
    sentences = split_sentences(body)
    if sentences:
        return sentences[0]
    return body[:200]


def extract_risk(title: str, body: str) -> str:
    """Extract the risk description (what can go wrong).

    Looks for failure descriptions in the body. Falls back
    to deriving risk from the title.

    Args:
        title: Lesson title.
        body: Lesson body text.

    Returns:
        Risk description string.
    """
    sentences = split_sentences(body)

    # Look for sentences describing failures
    failure_words = (
        "fail",
        "crash",
        "break",
        "error",
        "bug",
        "conflict",
        "block",
        "reject",
        "timeout",
        "corrupt",
        "lost",
        "missing",
        "silent",
    )
    for sentence in sentences:
        lower = sentence.lower()
        if any(w in lower for w in failure_words):
            return sentence

    # Fallback: derive from title
    return f"Ignoring this guidance may cause: {title}"


def extract_mitigation_steps(body: str) -> list[str]:
    """Extract mitigation steps (how to avoid the risk).

    Extracts imperative sentences and Fix: markers.

    Args:
        body: Lesson body text.

    Returns:
        List of mitigation step strings.
    """
    steps: list[str] = []
    sentences = split_sentences(body)

    for sentence in sentences:
        fix_match = re.match(r"Fix:\s*(.+)", sentence)
        if fix_match:
            step = fix_match.group(1).strip()
            if step and step not in steps:
                steps.append(step)

    for sentence in sentences:
        if sentence.startswith(_IMPERATIVE_STARTS) and len(sentence) > 10:
            if sentence not in steps:
                steps.append(sentence)

    if not steps:
        if sentences:
            steps.append(sentences[0])
        else:
            steps.append(body[:200])

    return steps


def generate_related_topics(
    title: str,
    name: str,
) -> list[dict[str, str]]:
    """Generate Related Topics cross-links for a Warning.

    Always cross-links to the corresponding Error template.

    Args:
        title: Lesson title.
        name: Slugified name (matches Error template name).

    Returns:
        List of dicts with 'type' and 'description' keys.
    """
    return [
        {
            "type": "Error",
            "description": f"Diagnostic help: {title}",
        },
    ]


def lesson_to_warning(entry) -> WarningTemplate:
    """Convert a LessonEntry to a populated WarningTemplate.

    Args:
        entry: Parsed lesson entry.

    Returns:
        Populated WarningTemplate.
    """
    name = slugify(entry.title)
    tags = classify_tags(entry.title, entry.body)
    condition = extract_condition(entry.body)
    risk = extract_risk(entry.title, entry.body)
    mitigation_steps = extract_mitigation_steps(entry.body)
    related_topics = generate_related_topics(entry.title, name)

    return WarningTemplate(
        name=name,
        title=entry.title,
        condition=condition,
        risk=risk,
        mitigation_steps=mitigation_steps,
        tags=tags,
        related_topics=related_topics,
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Warning template generator.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    claude_md = repo_root / ".claude" / "CLAUDE.md"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "warnings"

    if not claude_md.exists():
        print(f"ERROR: {claude_md} not found")
        return 1

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    # Step 1: Discover
    entries = parse_lessons_learned(claude_md)
    if not entries:
        print("No Lessons Learned entries found")
        return 1

    # Step 2: Filter — only warning-worthy entries
    warning_entries = [e for e in entries if is_warning_worthy(e.title, e.body)]

    # Step 3: Transform
    templates = [lesson_to_warning(e) for e in warning_entries]

    # Step 4: Render
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(
        f"{mode} Warning templates from {len(warning_entries)}"
        f" of {len(entries)} Lessons Learned entries\n"
    )

    items = [
        {
            "name": t.name,
            "title": t.title,
            "condition": t.condition,
            "risk": t.risk,
            "mitigation_steps": t.mitigation_steps,
            "confidence": t.confidence,
            "confidence_reason": t.confidence_reason,
            "tags": t.tags,
            "source": t.source,
            "related_topics": t.related_topics,
        }
        for t in templates
    ]

    successes, failures = render_and_output(
        env,
        "warning.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_warning_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
