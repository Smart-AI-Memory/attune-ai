"""Tests for quick-memory lessons manager.

Tests for LessonsManager: add, remove, list, format for prompt,
token budget, file creation, merge logic, and path validation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.memory.lessons import (
    DEFAULT_MAX_TOKENS,
    LessonsManager,
    _estimate_tokens,
)

# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    """Tests for _estimate_tokens helper."""

    def test_empty_string(self) -> None:
        """Empty text returns 0 tokens."""
        assert _estimate_tokens("") == 0

    def test_single_word(self) -> None:
        """Single word returns 1 * 1.3 = 1."""
        assert _estimate_tokens("hello") == 1

    def test_multiple_words(self) -> None:
        """Multiple words use words * 1.3 heuristic."""
        result = _estimate_tokens("one two three four five")
        assert result == int(5 * 1.3)


# ---------------------------------------------------------------------------
# LessonsManager - Add
# ---------------------------------------------------------------------------


class TestAddLesson:
    """Tests for LessonsManager.add_lesson()."""

    def test_add_creates_project_file(self, tmp_path) -> None:
        """Adding a lesson creates the project lessons file."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global" / "lessons.md",
        )

        result = manager.add_lesson("Always run tests before commit")

        assert project_file.exists()
        assert "Lesson saved (project)." in result
        content = project_file.read_text()
        assert "Always run tests before commit" in content
        assert "# Attune Lessons" in content

    def test_add_global_lesson(self, tmp_path) -> None:
        """Adding with global_=True writes to global file."""
        global_file = tmp_path / "global" / "lessons.md"
        manager = LessonsManager(
            project_path=tmp_path / ".attune" / "lessons.md",
            global_path=global_file,
        )

        result = manager.add_lesson("Use type hints everywhere", global_=True)

        assert global_file.exists()
        assert "Lesson saved (global)." in result
        content = global_file.read_text()
        assert "Use type hints everywhere" in content

    def test_add_appends_to_existing(self, tmp_path) -> None:
        """Adding multiple lessons appends to the file."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global" / "lessons.md",
        )

        manager.add_lesson("First lesson")
        manager.add_lesson("Second lesson")

        content = project_file.read_text()
        assert "First lesson" in content
        assert "Second lesson" in content

    def test_add_empty_text_raises(self, tmp_path) -> None:
        """Empty lesson text raises ValueError."""
        manager = LessonsManager(
            project_path=tmp_path / "lessons.md",
            global_path=tmp_path / "global" / "lessons.md",
        )

        with pytest.raises(ValueError, match="cannot be empty"):
            manager.add_lesson("")

    def test_add_whitespace_only_raises(self, tmp_path) -> None:
        """Whitespace-only lesson text raises ValueError."""
        manager = LessonsManager(
            project_path=tmp_path / "lessons.md",
            global_path=tmp_path / "global" / "lessons.md",
        )

        with pytest.raises(ValueError, match="cannot be empty"):
            manager.add_lesson("   ")

    def test_add_includes_date(self, tmp_path) -> None:
        """Lesson entry includes date in **YYYY-MM-DD** format."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global" / "lessons.md",
        )

        manager.add_lesson("Test lesson")

        content = project_file.read_text()
        # Check for date pattern: **YYYY-MM-DD**
        import re

        assert re.search(r"\*\*\d{4}-\d{2}-\d{2}\*\*", content)

    def test_add_warns_on_high_token_count(self, tmp_path) -> None:
        """Warning included when token count exceeds threshold."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global" / "lessons.md",
        )

        # Fill file with enough text to exceed warning threshold
        project_file.parent.mkdir(parents=True, exist_ok=True)
        # ~2600 tokens worth of content (2000 words * 1.3)
        big_content = "# Attune Lessons\n\n"
        big_content += "- **2026-01-01** " + " ".join(["word"] * 2000) + "\n"
        project_file.write_text(big_content)

        result = manager.add_lesson("One more lesson")

        assert "Warning" in result
        assert "Consider pruning" in result


# ---------------------------------------------------------------------------
# LessonsManager - Remove
# ---------------------------------------------------------------------------


class TestRemoveLesson:
    """Tests for LessonsManager.remove_lesson()."""

    def _create_lessons(self, tmp_path):
        """Helper to create a manager with some lessons."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global" / "lessons.md",
        )
        manager.add_lesson("First lesson about tests")
        manager.add_lesson("Second lesson about security")
        manager.add_lesson("Third lesson about docs")
        return manager, project_file

    def test_remove_by_line_number(self, tmp_path) -> None:
        """Remove a lesson by its displayed line number."""
        manager, project_file = self._create_lessons(tmp_path)

        result = manager.remove_lesson("2")

        assert "Removed:" in result
        assert "security" in result
        content = project_file.read_text()
        assert "security" not in content
        assert "tests" in content
        assert "docs" in content

    def test_remove_by_keyword(self, tmp_path) -> None:
        """Remove a lesson by keyword match."""
        manager, project_file = self._create_lessons(tmp_path)

        result = manager.remove_lesson("docs")

        assert "Removed:" in result
        content = project_file.read_text()
        assert "docs" not in content
        assert "tests" in content

    def test_remove_keyword_case_insensitive(self, tmp_path) -> None:
        """Keyword matching is case-insensitive."""
        manager, _file = self._create_lessons(tmp_path)

        result = manager.remove_lesson("SECURITY")

        assert "Removed:" in result
        assert "security" in result.lower()

    def test_remove_invalid_line_number_raises(self, tmp_path) -> None:
        """Invalid line number raises ValueError."""
        manager, _file = self._create_lessons(tmp_path)

        with pytest.raises(ValueError, match="No lesson at line"):
            manager.remove_lesson("99")

    def test_remove_unknown_keyword_raises(self, tmp_path) -> None:
        """Non-matching keyword raises ValueError."""
        manager, _file = self._create_lessons(tmp_path)

        with pytest.raises(ValueError, match="No lesson matching"):
            manager.remove_lesson("nonexistent")


# ---------------------------------------------------------------------------
# LessonsManager - Get / List
# ---------------------------------------------------------------------------


class TestGetLessons:
    """Tests for LessonsManager.get_lessons()."""

    def test_no_lessons_returns_empty(self, tmp_path) -> None:
        """No lessons files returns empty list."""
        manager = LessonsManager(
            project_path=tmp_path / "nonexistent" / "lessons.md",
            global_path=tmp_path / "also_nonexistent" / "lessons.md",
        )

        assert manager.get_lessons() == []

    def test_project_lessons_returned(self, tmp_path) -> None:
        """Project lessons are returned with source='project'."""
        project_file = tmp_path / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global" / "lessons.md",
        )
        manager.add_lesson("Project lesson")

        lessons = manager.get_lessons()

        assert len(lessons) == 1
        assert lessons[0]["text"] == "Project lesson"
        assert lessons[0]["source"] == "project"
        assert lessons[0]["number"] == 1

    def test_global_lessons_returned(self, tmp_path) -> None:
        """Global lessons returned with source='global'."""
        global_file = tmp_path / "global" / "lessons.md"
        manager = LessonsManager(
            project_path=tmp_path / "nonexistent" / "lessons.md",
            global_path=global_file,
        )
        manager.add_lesson("Global lesson", global_=True)

        lessons = manager.get_lessons()

        assert len(lessons) == 1
        assert lessons[0]["source"] == "global"

    def test_merge_project_and_global(self, tmp_path) -> None:
        """Project lessons listed first, then global."""
        project_file = tmp_path / "project" / "lessons.md"
        global_file = tmp_path / "global" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=global_file,
        )
        manager.add_lesson("Project lesson")
        manager.add_lesson("Global lesson", global_=True)

        lessons = manager.get_lessons()

        assert len(lessons) == 2
        assert lessons[0]["source"] == "project"
        assert lessons[1]["source"] == "global"
        assert lessons[0]["number"] == 1
        assert lessons[1]["number"] == 2

    def test_deduplication(self, tmp_path) -> None:
        """Global lesson matching project lesson is deduplicated."""
        project_file = tmp_path / "project" / "lessons.md"
        global_file = tmp_path / "global" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=global_file,
        )
        manager.add_lesson("Same lesson text")
        manager.add_lesson("Same lesson text", global_=True)

        lessons = manager.get_lessons()

        assert len(lessons) == 1
        assert lessons[0]["source"] == "project"

    def test_global_only_flag(self, tmp_path) -> None:
        """global_only=True only returns global lessons."""
        project_file = tmp_path / "project" / "lessons.md"
        global_file = tmp_path / "global" / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=global_file,
        )
        manager.add_lesson("Project lesson")
        manager.add_lesson("Global lesson", global_=True)

        lessons = manager.get_lessons(global_only=True)

        assert len(lessons) == 1
        assert lessons[0]["source"] == "global"


# ---------------------------------------------------------------------------
# LessonsManager - Format for prompt
# ---------------------------------------------------------------------------


class TestFormatForPrompt:
    """Tests for LessonsManager.format_for_prompt()."""

    def test_no_lessons_returns_none(self, tmp_path) -> None:
        """No lessons returns None."""
        manager = LessonsManager(
            project_path=tmp_path / "nonexistent.md",
            global_path=tmp_path / "also_nonexistent.md",
        )

        assert manager.format_for_prompt() is None

    def test_formats_lessons(self, tmp_path) -> None:
        """Lessons formatted as bullet points."""
        project_file = tmp_path / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global.md",
        )
        manager.add_lesson("Use pytest for testing")
        manager.add_lesson("Check edge cases")

        result = manager.format_for_prompt()

        assert result is not None
        assert "- Use pytest for testing" in result
        assert "- Check edge cases" in result

    def test_respects_token_budget(self, tmp_path) -> None:
        """Output is capped at max_tokens."""
        project_file = tmp_path / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global.md",
        )

        # Add many lessons to exceed budget
        for i in range(200):
            manager.add_lesson(f"Lesson number {i} with enough words to consume tokens quickly")

        result = manager.format_for_prompt(max_tokens=100)

        assert result is not None
        token_count = _estimate_tokens(result)
        assert token_count <= 100

    def test_under_budget_returns_all(self, tmp_path) -> None:
        """When under budget, all lessons are returned."""
        project_file = tmp_path / "lessons.md"
        manager = LessonsManager(
            project_path=project_file,
            global_path=tmp_path / "global.md",
        )
        manager.add_lesson("Short lesson one")
        manager.add_lesson("Short lesson two")

        result = manager.format_for_prompt(max_tokens=DEFAULT_MAX_TOKENS)

        assert result is not None
        assert "Short lesson one" in result
        assert "Short lesson two" in result


# ---------------------------------------------------------------------------
# Path validation security
# ---------------------------------------------------------------------------


class TestPathValidationSecurity:
    """Security tests for file path validation."""

    def test_null_bytes_rejected(self, tmp_path) -> None:
        """Null bytes in path are rejected."""
        # The path validation happens inside add_lesson when
        # _validate_file_path is called
        evil_path = tmp_path / "evil\x00.md"
        evil_manager = LessonsManager(
            project_path=evil_path,
            global_path=tmp_path / "global.md",
        )
        with pytest.raises(ValueError, match="null bytes"):
            evil_manager.add_lesson("test")

    def test_system_directory_rejected(self) -> None:
        """System directory paths are rejected."""
        from pathlib import Path

        manager = LessonsManager(
            project_path=Path("/etc/lessons.md"),
            global_path=Path("/tmp/global.md"),
        )
        with pytest.raises(ValueError, match="system directory"):
            manager.add_lesson("test")
