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

from attune.memory.atomic_io import append_line
from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# Token budget defaults
DEFAULT_MAX_TOKENS = 3000
WARN_TOKEN_THRESHOLD = 2500

# Lesson line pattern: - **YYYY-MM-DD** lesson text
_LESSON_PATTERN = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2})\*\* (.+)$")

# Marker comments for managed section in CLAUDE.md
_CLAUDE_MD_START = "<!-- attune-lessons-start -->"
_CLAUDE_MD_END = "<!-- attune-lessons-end -->"


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


def _get_claude_md_path() -> Path:
    """Get the default CLAUDE.md file path.

    Returns:
        Path to .claude/CLAUDE.md in the current directory.

    """
    return Path(".claude/CLAUDE.md")


class LessonsManager:
    """Manages lessons learned from previous sessions.

    Lessons are stored as markdown lines in a simple format:
    ``- **YYYY-MM-DD** lesson text``

    Supports project-local and global lessons files with
    automatic merging (project takes precedence). Optionally
    bridges with .claude/CLAUDE.md for Claude Code native
    integration.

    Args:
        project_path: Override for project lessons file path.
        global_path: Override for global lessons file path.
        sync_to_claude_md: If True, sync lessons to CLAUDE.md.
        claude_md_path: Override for CLAUDE.md file path.

    """

    def __init__(
        self,
        project_path: Path | None = None,
        global_path: Path | None = None,
        sync_to_claude_md: bool = True,
        claude_md_path: Path | None = None,
    ) -> None:
        """Initialize the lessons manager.

        Args:
            project_path: Override for project lessons file path.
            global_path: Override for global lessons file path.
            sync_to_claude_md: If True, sync lessons to CLAUDE.md.
            claude_md_path: Override for CLAUDE.md file path.
        """
        self._project_path = project_path or _get_project_lessons_path()
        self._global_path = global_path or _get_global_lessons_path()
        self._sync_to_claude_md = sync_to_claude_md
        self._claude_md_path = claude_md_path or _get_claude_md_path()

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
            # APPEND: reading the whole file, adding a line and writing it
            # back loses a concurrent session's lesson (library-review G1).
            content = validated_path.read_text()
            if content and not content.endswith("\n"):
                append_line(validated_path, "")
            append_line(validated_path, lesson_line)

        # Sync to CLAUDE.md if enabled (project lessons only)
        if not global_ and self._sync_to_claude_md:
            self._sync_lesson_to_claude_md(lesson_line)

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
                    },
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
                },
            )
            number += 1

        # Merge lessons from CLAUDE.md (if bridge is enabled)
        if self._sync_to_claude_md:
            for date, text in self._parse_claude_md_lessons():
                # Deduplicate against project and global
                if any(lesson["text"] == text for lesson in lessons):
                    continue
                lessons.append(
                    {
                        "number": number,
                        "date": date,
                        "text": text,
                        "source": "claude_md",
                    },
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

    def _sync_lesson_to_claude_md(self, lesson_line: str) -> None:
        """Sync a lesson line to the CLAUDE.md managed section.

        Appends the lesson inside ``<!-- attune-lessons-start -->`` /
        ``<!-- attune-lessons-end -->`` markers. If markers don't exist,
        appends the full section at the end of the file.

        Silently skips if CLAUDE.md doesn't exist. Never crashes.

        Args:
            lesson_line: The formatted lesson line (with newline).

        """
        try:
            claude_md = self._claude_md_path
            if not claude_md.exists():
                logger.debug("CLAUDE.md not found at %s, skipping sync", claude_md)
                return

            validated_path = _validate_file_path(str(claude_md))
            content = validated_path.read_text()

            if _CLAUDE_MD_START in content and _CLAUDE_MD_END in content:
                # Insert lesson before end marker
                content = content.replace(
                    _CLAUDE_MD_END,
                    lesson_line + _CLAUDE_MD_END,
                )
            else:
                # Append new section at end of file
                section = (
                    f"\n{_CLAUDE_MD_START}\n"
                    f"## Lessons Learned\n\n"
                    f"{lesson_line}"
                    f"{_CLAUDE_MD_END}\n"
                )
                if not content.endswith("\n"):
                    content += "\n"
                content += section

            validated_path.write_text(content)
            logger.debug("Lesson synced to CLAUDE.md")

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: CLAUDE.md sync is best-effort, never crash
            logger.debug("CLAUDE.md sync failed: %s", e)

    def _parse_claude_md_lessons(self) -> list[tuple[str, str]]:
        """Parse lessons from the managed section of CLAUDE.md.

        Only reads content between the attune marker comments.

        Returns:
            List of (date, text) tuples. Empty if file missing
            or no markers found.

        """
        try:
            claude_md = self._claude_md_path
            if not claude_md.exists():
                return []

            content = claude_md.read_text()

            # Find content between markers
            start_idx = content.find(_CLAUDE_MD_START)
            end_idx = content.find(_CLAUDE_MD_END)
            if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
                return []

            section = content[start_idx + len(_CLAUDE_MD_START) : end_idx]

            results: list[tuple[str, str]] = []
            for line in section.splitlines():
                match = _LESSON_PATTERN.match(line.strip())
                if match:
                    results.append((match.group(1), match.group(2)))

            return results

        except OSError as e:
            logger.debug("Cannot read CLAUDE.md: %s", e)
            return []

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
                f"No lesson at line {line_num}. Run `attune lessons` to see current lessons.",
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
            f"No lesson matching {keyword!r}. Run `attune lessons` to see current lessons.",
        )

    def _remove_from_file(self, lesson: dict[str, Any]) -> str:
        """Remove a specific lesson from its source file.

        For project/global lessons, removes from the corresponding
        markdown file. For claude_md lessons, removes from the
        managed section in CLAUDE.md. Also syncs removal to
        CLAUDE.md when removing project lessons.

        Args:
            lesson: Lesson dict with text, date, source keys.

        Returns:
            Confirmation message.

        """
        date_str = lesson["date"]
        text = lesson["text"]
        target_line = f"- **{date_str}** {text}"

        if lesson["source"] == "claude_md":
            self._remove_lesson_from_claude_md(target_line)
            return f"Removed: {text}"

        path = self._global_path if lesson["source"] == "global" else self._project_path
        validated_path = _validate_file_path(str(path))

        if not validated_path.exists():
            raise ValueError("Lessons file not found")

        content = validated_path.read_text()
        new_lines = [line for line in content.splitlines() if line.strip() != target_line]
        validated_path.write_text("\n".join(new_lines) + "\n")

        # Sync removal to CLAUDE.md for project lessons
        if lesson["source"] == "project" and self._sync_to_claude_md:
            self._remove_lesson_from_claude_md(target_line)

        return f"Removed: {text}"

    def _remove_lesson_from_claude_md(self, target_line: str) -> None:
        """Remove a lesson line from the CLAUDE.md managed section.

        Silently skips if CLAUDE.md doesn't exist or has no markers.
        Never crashes.

        Args:
            target_line: The full lesson line to remove
                (e.g. ``- **2026-02-23** lesson text``).

        """
        try:
            claude_md = self._claude_md_path
            if not claude_md.exists():
                return

            validated_path = _validate_file_path(str(claude_md))
            content = validated_path.read_text()

            start_idx = content.find(_CLAUDE_MD_START)
            end_idx = content.find(_CLAUDE_MD_END)
            if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
                return

            section = content[start_idx + len(_CLAUDE_MD_START) : end_idx]
            new_lines = [line for line in section.splitlines() if line.strip() != target_line]
            new_section = "\n".join(new_lines)
            if new_section and not new_section.endswith("\n"):
                new_section += "\n"

            new_content = (
                content[: start_idx + len(_CLAUDE_MD_START)] + new_section + content[end_idx:]
            )
            validated_path.write_text(new_content)
            logger.debug("Lesson removed from CLAUDE.md")

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: CLAUDE.md sync is best-effort, never crash
            logger.debug("CLAUDE.md removal sync failed: %s", e)

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
