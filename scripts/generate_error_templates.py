#!/usr/bin/env python3
"""Generate Error templates from Lessons Learned in CLAUDE.md.

Parses the ## Lessons Learned section, extracts each entry's
title and body, classifies it into an Error template, and
renders via Jinja2 to plugin/help/generated/errors/.

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/generate_error_templates.py           # Generate
    python scripts/generate_error_templates.py --check   # Verify
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


@dataclass
class ErrorTemplate:
    """Populated Error template ready for rendering."""

    name: str
    title: str
    signature: str
    root_cause: str
    resolution_steps: list[str]
    confidence: str = "Verified"
    confidence_reason: str = "Confirmed by prior incident (Lessons Learned)"
    tags: list[str] = field(default_factory=list)
    source: str = "CLAUDE.md Lessons Learned"
    related_topics: list[dict[str, str]] = field(default_factory=list)


def extract_resolution_steps(body: str) -> list[str]:
    """Extract actionable resolution steps from lesson body.

    Looks for imperative sentences (Fix:, Always, Use, etc.)
    and "Fix:" markers. Respects backtick-quoted code when
    splitting on periods.

    Args:
        body: Lesson body text.

    Returns:
        List of resolution step strings.
    """
    steps: list[str] = []
    sentences = split_sentences(body)

    # Look for explicit "Fix:" marker
    for sentence in sentences:
        fix_match = re.match(r"Fix:\s*(.+)", sentence)
        if fix_match:
            step = fix_match.group(1).strip()
            if step and step not in steps:
                steps.append(step)

    # Extract imperative sentences
    imperative_starts = (
        "Always",
        "Never",
        "Use",
        "Add",
        "Remove",
        "Check",
        "Run",
        "Set",
        "Move",
        "Strip",
        "Grep",
        "Pass",
    )
    for sentence in sentences:
        if sentence.startswith(imperative_starts) and len(sentence) > 10:
            if sentence not in steps:
                steps.append(sentence)

    if not steps:
        if sentences:
            steps.append(sentences[0])
        else:
            steps.append(body[:200])

    return steps


def extract_signature(title: str, body: str) -> str:
    """Extract the error signature from a lesson.

    Looks for backtick-quoted error messages, or falls
    back to the title itself.

    Args:
        title: Lesson title.
        body: Lesson body text.

    Returns:
        Error signature string.
    """
    error_patterns = [
        r"`([A-Z][a-zA-Z]*Error[^`]*)`",
        r"`([A-Z][a-zA-Z]*Exception[^`]*)`",
        r"`([A-Z][a-zA-Z]*Warning[^`]*)`",
        r'"([^"]*(?:Error|error|fail|failed|denied)[^"]*)"',
    ]
    for pattern in error_patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(1)

    return title


def generate_related_topics(
    title: str,
    body: str,
    tags: list[str],
) -> list[dict[str, str]]:
    """Generate Related Topics cross-links.

    Args:
        title: Lesson title.
        body: Lesson body text.
        tags: Classified tags.

    Returns:
        List of dicts with 'type' and 'description' keys.
    """
    topics: list[dict[str, str]] = []

    if any(w in body.lower() for w in ["avoid", "never", "don't", "do not"]):
        topics.append(
            {
                "type": "Warning",
                "description": f"Avoid: {title}",
            }
        )

    if any(w in body.lower() for w in ["always", "prefer", "use", "recommended"]):
        topics.append(
            {
                "type": "Tip",
                "description": f"Best practice: {title}",
            }
        )

    if "testing" in tags:
        topics.append(
            {
                "type": "Task",
                "description": "Update test mocks and assertions",
            }
        )

    return topics


def lesson_to_template(entry):
    """Convert a LessonEntry to a populated ErrorTemplate.

    Args:
        entry: Parsed lesson entry.

    Returns:
        Populated ErrorTemplate ready for rendering.
    """
    name = slugify(entry.title)
    tags = classify_tags(entry.title, entry.body)
    signature = extract_signature(entry.title, entry.body)
    resolution_steps = extract_resolution_steps(entry.body)
    related_topics = generate_related_topics(entry.title, entry.body, tags)

    return ErrorTemplate(
        name=name,
        title=entry.title,
        signature=signature,
        root_cause=entry.body.split("Fix:")[0].strip() if "Fix:" in entry.body else entry.body,
        resolution_steps=resolution_steps,
        tags=tags,
        related_topics=related_topics,
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Error template generator.

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
    output_dir = repo_root / "plugin" / "help" / "generated" / "errors"

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

    # Step 2: Transform
    templates = [lesson_to_template(entry) for entry in entries]

    # Step 3: Render via shared utility
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"{mode} Error templates from {len(entries)} Lessons Learned entries\n")

    items = [
        {
            "name": t.name,
            "title": t.title,
            "signature": t.signature,
            "root_cause": t.root_cause,
            "resolution_steps": t.resolution_steps,
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
        "error.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_error_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
