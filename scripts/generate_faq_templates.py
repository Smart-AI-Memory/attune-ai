#!/usr/bin/env python3
"""Generate FAQ templates from Lessons Learned entries.

Reformulates Lessons Learned as question-answer pairs.
Each lesson becomes a "Why does X happen?" or "How do
I fix X?" FAQ entry with the lesson body as the answer.

Follows the sync paradigm: Discover -> Parse -> Transform ->
Validate -> Output -> Verify (--check mode).

Usage:
    python scripts/generate_faq_templates.py           # Generate
    python scripts/generate_faq_templates.py --check   # Verify
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
class FAQTemplate:
    """Populated FAQ template ready for rendering."""

    name: str
    question: str
    answer: str
    code_example: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = "CLAUDE.md Lessons Learned"
    related_topics: list[dict[str, str]] = field(default_factory=list)


# Patterns for generating questions from lesson titles
_QUESTION_PATTERNS: list[tuple[str, str]] = [
    # Titles starting with action verbs -> "How do I..." questions
    (r"^(Always|Never|Use|Avoid|Check|Run|Set|Move|Add|Remove)\b", "How should I handle: {title}?"),
    # Titles with "fails" or "breaks" -> "Why does..." questions
    (r"(fail|break|crash|block|reject|timeout|missing)", "Why does {title}?"),
    # Titles with "must" or "need" -> "What do I need to know about..." questions
    (r"(must|need|require)", "What do I need to know about: {title}?"),
    # Default -> "What is the issue with..." question
    (r".", "What is the issue with: {title}?"),
]


def _generate_question(title: str) -> str:
    """Generate a natural FAQ question from a lesson title.

    Args:
        title: Lesson title text.

    Returns:
        Question string.
    """
    title_lower = title.lower()
    for pattern, template in _QUESTION_PATTERNS:
        if re.search(pattern, title_lower):
            return template.format(title=title)
    return f"What is the issue with: {title}?"


def _extract_code_example(body: str) -> str:
    """Extract the first code-like example from a body.

    Looks for backtick-quoted commands or identifiers
    that serve as examples.

    Args:
        body: Lesson body text.

    Returns:
        Code example string, or empty.
    """
    # Look for backtick-quoted commands
    match = re.search(r"`([^`]{10,80})`", body)
    if match:
        return match.group(1)
    return ""


def _build_answer(body: str) -> str:
    """Build a concise FAQ answer from the lesson body.

    Takes the first 2-3 sentences as the explanation,
    then appends any Fix: instructions.

    Args:
        body: Lesson body text.

    Returns:
        Answer string.
    """
    sentences = split_sentences(body)
    if not sentences:
        return body[:300]

    # Take explanation sentences (non-imperative)
    explanation: list[str] = []
    fix_steps: list[str] = []

    for sentence in sentences:
        if sentence.startswith("Fix:"):
            fix_steps.append(sentence[4:].strip())
        elif sentence.startswith(("Always", "Never", "Use", "Avoid", "Check", "Run", "Set")):
            fix_steps.append(sentence)
        elif len(explanation) < 2:
            explanation.append(sentence)

    parts: list[str] = []
    if explanation:
        parts.append(". ".join(explanation) + ".")
    if fix_steps:
        parts.append("\n\n**Fix:**\n")
        for step in fix_steps:
            parts.append(f"- {step}")

    return "\n".join(parts) if parts else body[:300]


def lesson_to_faq(entry) -> FAQTemplate:
    """Convert a LessonEntry to a FAQ template.

    Args:
        entry: Parsed LessonEntry.

    Returns:
        FAQTemplate.
    """
    name = slugify(entry.title)
    question = _generate_question(entry.title)
    answer = _build_answer(entry.body)
    code_example = _extract_code_example(entry.body)
    tags = classify_tags(entry.title, entry.body)

    # Cross-link to error template
    related: list[dict[str, str]] = [
        {
            "type": "Error",
            "description": f"Detailed error: {entry.title}",
        }
    ]

    return FAQTemplate(
        name=name,
        question=question,
        answer=answer,
        code_example=code_example,
        tags=tags,
        related_topics=related,
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point for the FAQ template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    claude_md = repo_root / ".claude" / "CLAUDE.md"
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "faqs"

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
    templates = [lesson_to_faq(e) for e in entries]

    # Step 3: Render
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"{mode} FAQ templates from {len(entries)} Lessons Learned entries\n")

    items = [
        {
            "name": t.name,
            "question": t.question,
            "answer": t.answer,
            "code_example": t.code_example,
            "tags": t.tags,
            "source": t.source,
            "related_topics": t.related_topics,
        }
        for t in templates
    ]

    successes, failures = render_and_output(
        env,
        "faq.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_faq_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
