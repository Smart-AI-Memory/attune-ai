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
    source: str = ".claude/CLAUDE.md"
    related_topics: list[dict[str, str]] = field(default_factory=list)


def _clean_title(title: str) -> str:
    """Clean a title for use in a question.

    Strips backticks, normalizes whitespace, lowercases
    the first word if it's not an acronym.

    Args:
        title: Raw lesson title.

    Returns:
        Cleaned title string.
    """
    cleaned = re.sub(r"`([^`]+)`", r"\1", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Lowercase first word if it's not an acronym (all caps)
    words = cleaned.split(" ", 1)
    if words and not words[0].isupper() and len(words[0]) > 2:
        words[0] = words[0][0].lower() + words[0][1:]
        cleaned = " ".join(words)
    return cleaned


def _extract_error_signature(title: str, body: str) -> str:
    """Extract an error name from title or body.

    Args:
        title: Lesson title.
        body: Lesson body.

    Returns:
        Error signature string, or empty.
    """
    # Look for ErrorType in backticks
    for text in [body, title]:
        match = re.search(r"`([A-Z][a-zA-Z]*(?:Error|Exception))`", text)
        if match:
            return match.group(1)
    return ""


def _generate_question(title: str, body: str) -> str:
    """Generate a natural FAQ question from a lesson.

    Classifies the lesson type and produces a natural
    question phrasing.

    Args:
        title: Lesson title.
        body: Lesson body text.

    Returns:
        Natural question string.
    """
    clean = _clean_title(title)
    lower = clean.lower()
    error_sig = _extract_error_signature(title, body)

    # Error/crash patterns -> "Why do I get...?"
    if error_sig:
        return f"Why do I get `{error_sig}` ({clean})?"

    # Failure patterns
    if re.search(r"(fail|break|crash|block|reject|timeout)", lower):
        return f"Why does {clean}?"

    # "must", "need", "required" patterns
    if re.search(r"(must|need|require)", lower):
        return f"What do I need to know about {clean}?"

    # "can't", "cannot", "doesn't", "won't" patterns
    if re.search(r"(can.?t|cannot|doesn.?t|won.?t|missing)", lower):
        return f"Why {clean}?"

    # Best practice / imperative patterns
    if re.search(r"^(always|never|avoid|use |prefer|ensure)", lower):
        return f"What is the best practice for {clean}?"

    # Configuration / setup patterns
    if re.search(r"(config|setup|install|enable|disable)", lower):
        return f"How do I handle {clean}?"

    # Default: "What should I know about...?"
    return f"What should I know about {clean}?"


def _extract_code_example(body: str) -> str:
    """Extract the first code-like example from a body.

    Looks for backtick-quoted commands that look like
    actionable code. Strips trailing whitespace.

    Args:
        body: Lesson body text.

    Returns:
        Code example string, or empty.
    """
    match = re.search(r"`([^`]{10,80})`", body)
    if match:
        return match.group(1).rstrip()
    return ""


def _build_answer(body: str) -> str:
    """Build a concise FAQ answer from the lesson body.

    Separates explanation (first 2 sentences) from
    actionable fix steps (Fix:, Always, Never, etc.).

    Args:
        body: Lesson body text.

    Returns:
        Structured answer string.
    """
    sentences = split_sentences(body)
    if not sentences:
        return body[:300]

    explanation: list[str] = []
    fix_steps: list[str] = []

    for sentence in sentences:
        if sentence.startswith("Fix:"):
            fix_steps.append(sentence[4:].strip())
        elif sentence.startswith(
            ("Always", "Never", "Use", "Avoid", "Check", "Run", "Set"),
        ):
            fix_steps.append(sentence)
        elif len(explanation) < 2:
            explanation.append(sentence)

    parts: list[str] = []
    if explanation:
        parts.append(". ".join(explanation) + ".")
    if fix_steps:
        parts.append("\n\n**How to fix:**")
        for step in fix_steps:
            parts.append(f"\n- {step}")

    return "".join(parts) if parts else body[:300]


def lesson_to_faq(entry) -> FAQTemplate:
    """Convert a LessonEntry to a FAQ template.

    Args:
        entry: Parsed LessonEntry.

    Returns:
        FAQTemplate.
    """
    name = slugify(entry.title)
    question = _generate_question(entry.title, entry.body)
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
