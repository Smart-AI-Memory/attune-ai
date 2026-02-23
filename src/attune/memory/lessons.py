"""Quick-memory lessons manager.

Provides a simple, file-based "lessons learned" system inspired
by Boris Cherny's CLAUDE.md pattern. Lessons are stored as
human-readable markdown and automatically injected into all
workflow prompts.

No Redis required. No encryption. Pure file-based.

Paths:
    Project-local: .attune/lessons.md (primary)
    Global:        ~/.attune/lessons.md (fallback)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# Token budget defaults
DEFAULT_MAX_TOKENS = 3000
WARN_TOKEN_THRESHOLD = 2500

# Lesson line pattern: - **YYYY-MM-DD** lesson text
_LESSON_PATTERN = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2})\*\* (.+)$")


def _estimate_tokens(text: str) -> int:
    """Rough token estimate for text.

    Uses word count * 1.3 as a simple heuristic.

    Args:
        text: Input text.

    Returns:
        Estimated token count.

    """
    words = len(text.split())
    return int(words * 1.3)


def _get_project_lessons_path() -> Path:
    """Get the project-local lessons file path.

    Returns:
        Path to .attune/lessons.md in the current directory.

    """
    return Path(".attune/lessons.md")


def _get_global_lessons_path() -> Path:
    """Get the global lessons file path.

    Returns:
        Path to ~/.attune/lessons.md.

    """
    return Path.home() / ".attune" / "lessons.md"


class LessonsManager:
    """Manages lessons learned from previous sessions.

    Lessons are stored as markdown lines in a simple format:
    ``- **YYYY-MM-DD** lesson text``

    Supports project-local and global lessons files with
    automatic merging (project takes precedence).

    Args:
        project_path: Override for project lessons file path.
        global_path: Override for global lessons file path.

    """

    def __init__(
        self,
        project_path: Path | None = None,
        global_path: Path | None = None,
    ) -> None:
        self._project_path = project_path or _get_project_lessons_path()
        self._global_path = global_path or _get_global_lessons_path()

    def add_lesson(self, text: str, global_: bool = False) -> str:
        """Add a lesson to the lessons file.

        Args:
            text: The lesson text to remember.
            global_: If True, save to global file instead of project.

        Returns:
            Confirmation message.

        Raises:
            ValueError: If text is empty or path is invalid.

        """
        if not text or not text.strip():
            raise ValueError("Lesson text cannot be empty")

        target = self._global_path if global_ else self._project_path
        validated_path = _validate_file_path(str(target))

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lesson_line = f"- **{date_str}** {text.strip()}\n"

        # Create directory and file if needed
        validated_path.parent.mkdir(parents=True, exist_ok=True)

        if not validated_path.exists():
            validated_path.write_text(f"# Attune Lessons\n\n{lesson_line}")
        else:
            content = validated_path.read_text()
            # Ensure trailing newline before appending
            if content and not content.endswith("\n"):
                content += "\n"
            content += lesson_line
            validated_path.write_text(content)

        scope = "global" if global_ else "project"
        token_count = self._check_token_budget(target)
        warning = ""
        if token_count > WARN_TOKEN_THRESHOLD:
            warning = (
                f" Warning: lessons file is {token_count} tokens "
                f"(max {DEFAULT_MAX_TOKENS}). Consider pruning "
                f"with `attune lessons` and `attune forget`."
            )

        return f"Lesson saved ({scope}).{warning}"

    def remove_lesson(self, identifier: str) -> str:
        """Remove a lesson by line number or keyword.

        Searches project file first, then global.

        Args:
            identifier: Line number (1-based) or keyword to match.

        Returns:
            Confirmation message with removed lesson text.

        Raises:
            ValueError: If no matching lesson is found.

        """
        # Try as line number first
        try:
            line_num = int(identifier)
        except ValueError:
            # Not a number — treat as keyword
            return self._remove_by_keyword(identifier)

        return self._remove_by_line_number(line_num)

    def get_lessons(
        self,
        global_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Get all lessons with metadata.

        Args:
            global_only: If True, only return global lessons.

        Returns:
            List of dicts with keys: number, date, text, source.

        """
        lessons: list[dict[str, Any]] = []
        number = 1

        if not global_only:
            for date, text in self._parse_file(self._project_path):
                lessons.append(
                    {
                        "number": number,
                        "date": date,
                        "text": text,
                        "source": "project",
                    }
                )
                number += 1

        for date, text in self._parse_file(self._global_path):
            # Deduplicate: skip global lessons that match project
            if any(lesson["text"] == text for lesson in lessons):
                continue
            lessons.append(
                {
                    "number": number,
                    "date": date,
                    "text": text,
                    "source": "global",
                }
            )
            number += 1

        return lessons

    def format_for_prompt(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str | None:
        """Format lessons for injection into workflow prompts.

        Merges project and global lessons (project first).
        Caps output at max_tokens, including most recent first
        when over budget.

        Args:
            max_tokens: Maximum token budget for lessons text.

        Returns:
            Formatted lessons string, or None if no lessons.

        """
        lessons = self.get_lessons()
        if not lessons:
            return None

        # Build lines (most recent first for truncation)
        lines = [f"- {lesson['text']}" for lesson in lessons]

        # Check if we need to truncate
        full_text = "\n".join(lines)
        if _estimate_tokens(full_text) <= max_tokens:
            return full_text

        # Over budget: include from most recent, trim oldest
        logger.warning(
            "Lessons exceed %d token budget, truncating oldest",
            max_tokens,
        )
        included: list[str] = []
        for line in reversed(lines):
            candidate = "\n".join([line, *reversed(included)])
            if _estimate_tokens(candidate) > max_tokens:
                break
            included.append(line)

        included.reverse()
        return "\n".join(included) if included else None

    def _parse_file(self, path: Path) -> list[tuple[str, str]]:
        """Parse lessons from a markdown file.

        Args:
            path: Path to the lessons file.

        Returns:
            List of (date, text) tuples.

        """
        if not path.exists():
            return []

        try:
            content = path.read_text()
        except OSError as e:
            logger.warning("Cannot read lessons file %s: %s", path, e)
            return []

        results: list[tuple[str, str]] = []
        for line in content.splitlines():
            match = _LESSON_PATTERN.match(line.strip())
            if match:
                results.append((match.group(1), match.group(2)))

        return results

    def _remove_by_line_number(self, line_num: int) -> str:
        """Remove a lesson by its displayed line number.

        Args:
            line_num: 1-based line number from `attune lessons`.

        Returns:
            Confirmation message.

        Raises:
            ValueError: If line number is out of range.

        """
        lessons = self.get_lessons()
        target = None
        for lesson in lessons:
            if lesson["number"] == line_num:
                target = lesson
                break

        if target is None:
            raise ValueError(
                f"No lesson at line {line_num}. " f"Run `attune lessons` to see current lessons."
            )

        return self._remove_from_file(target)

    def _remove_by_keyword(self, keyword: str) -> str:
        """Remove the first lesson matching a keyword.

        Args:
            keyword: Text to search for in lessons.

        Returns:
            Confirmation message.

        Raises:
            ValueError: If no matching lesson is found.

        """
        lessons = self.get_lessons()
        keyword_lower = keyword.lower()

        for lesson in lessons:
            if keyword_lower in lesson["text"].lower():
                return self._remove_from_file(lesson)

        raise ValueError(
            f"No lesson matching {keyword!r}. " f"Run `attune lessons` to see current lessons."
        )

    def _remove_from_file(self, lesson: dict[str, Any]) -> str:
        """Remove a specific lesson from its source file.

        Args:
            lesson: Lesson dict with text, date, source keys.

        Returns:
            Confirmation message.

        """
        path = self._global_path if lesson["source"] == "global" else self._project_path
        validated_path = _validate_file_path(str(path))

        if not validated_path.exists():
            raise ValueError("Lessons file not found")

        content = validated_path.read_text()
        date_str = lesson["date"]
        text = lesson["text"]
        target_line = f"- **{date_str}** {text}"

        new_lines = [line for line in content.splitlines() if line.strip() != target_line]

        validated_path.write_text("\n".join(new_lines) + "\n")

        return f"Removed: {text}"

    def _check_token_budget(self, path: Path) -> int:
        """Check token count of a lessons file.

        Args:
            path: Path to the lessons file.

        Returns:
            Estimated token count.

        """
        if not path.exists():
            return 0
        try:
            content = path.read_text()
            return _estimate_tokens(content)
        except OSError:
            return 0


__all__ = ["LessonsManager"]
