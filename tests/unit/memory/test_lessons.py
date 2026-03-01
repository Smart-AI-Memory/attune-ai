"""Tests for quick-memory lessons manager.

Tests for LessonsManager: add, remove, list, format for prompt,
token budget, file creation, merge logic, path validation, and
CLAUDE.md bridge.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.memory.lessons import (
    _CLAUDE_MD_END,
    _CLAUDE_MD_START,
    DEFAULT_MAX_TOKENS,
    LessonsManager,
    _estimate_tokens,
)


def _make_manager(tmp_path, **kwargs):
    """Helper to create a LessonsManager with isolated paths."""
    return LessonsManager(
        project_path=kwargs.get("project_path", tmp_path / ".attune" / "lessons.md"),
        global_path=kwargs.get("global_path", tmp_path / "global" / "lessons.md"),
        sync_to_claude_md=kwargs.get("sync_to_claude_md", False),
        claude_md_path=kwargs.get("claude_md_path", tmp_path / ".claude" / "CLAUDE.md"),
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
        manager = _make_manager(tmp_path, project_path=project_file)

        result = manager.add_lesson("Always run tests before commit")

        assert project_file.exists()
        assert "Lesson saved (project)." in result
        content = project_file.read_text()
        assert "Always run tests before commit" in content
        assert "# Attune Lessons" in content

    def test_add_global_lesson(self, tmp_path) -> None:
        """Adding with global_=True writes to global file."""
        global_file = tmp_path / "global" / "lessons.md"
        manager = _make_manager(tmp_path, global_path=global_file)

        result = manager.add_lesson("Use type hints everywhere", global_=True)

        assert global_file.exists()
        assert "Lesson saved (global)." in result
        content = global_file.read_text()
        assert "Use type hints everywhere" in content

    def test_add_appends_to_existing(self, tmp_path) -> None:
        """Adding multiple lessons appends to the file."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = _make_manager(tmp_path, project_path=project_file)

        manager.add_lesson("First lesson")
        manager.add_lesson("Second lesson")

        content = project_file.read_text()
        assert "First lesson" in content
        assert "Second lesson" in content

    def test_add_empty_text_raises(self, tmp_path) -> None:
        """Empty lesson text raises ValueError."""
        manager = _make_manager(tmp_path)

        with pytest.raises(ValueError, match="cannot be empty"):
            manager.add_lesson("")

    def test_add_whitespace_only_raises(self, tmp_path) -> None:
        """Whitespace-only lesson text raises ValueError."""
        manager = _make_manager(tmp_path)

        with pytest.raises(ValueError, match="cannot be empty"):
            manager.add_lesson("   ")

    def test_add_includes_date(self, tmp_path) -> None:
        """Lesson entry includes date in **YYYY-MM-DD** format."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = _make_manager(tmp_path, project_path=project_file)

        manager.add_lesson("Test lesson")

        content = project_file.read_text()
        import re

        assert re.search(r"\*\*\d{4}-\d{2}-\d{2}\*\*", content)

    def test_add_warns_on_high_token_count(self, tmp_path) -> None:
        """Warning included when token count exceeds threshold."""
        project_file = tmp_path / ".attune" / "lessons.md"
        manager = _make_manager(tmp_path, project_path=project_file)

        # Fill file with enough text to exceed warning threshold
        project_file.parent.mkdir(parents=True, exist_ok=True)
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
        manager = _make_manager(tmp_path, project_path=project_file)
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
        manager = _make_manager(
            tmp_path,
            project_path=tmp_path / "nonexistent" / "lessons.md",
            global_path=tmp_path / "also_nonexistent" / "lessons.md",
        )

        assert manager.get_lessons() == []

    def test_project_lessons_returned(self, tmp_path) -> None:
        """Project lessons are returned with source='project'."""
        project_file = tmp_path / "lessons.md"
        manager = _make_manager(tmp_path, project_path=project_file)
        manager.add_lesson("Project lesson")

        lessons = manager.get_lessons()

        assert len(lessons) == 1
        assert lessons[0]["text"] == "Project lesson"
        assert lessons[0]["source"] == "project"
        assert lessons[0]["number"] == 1

    def test_global_lessons_returned(self, tmp_path) -> None:
        """Global lessons returned with source='global'."""
        global_file = tmp_path / "global" / "lessons.md"
        manager = _make_manager(
            tmp_path,
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
        manager = _make_manager(
            tmp_path,
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
        manager = _make_manager(
            tmp_path,
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
        manager = _make_manager(
            tmp_path,
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
        manager = _make_manager(
            tmp_path,
            project_path=tmp_path / "nonexistent.md",
            global_path=tmp_path / "also_nonexistent.md",
        )

        assert manager.format_for_prompt() is None

    def test_formats_lessons(self, tmp_path) -> None:
        """Lessons formatted as bullet points."""
        project_file = tmp_path / "lessons.md"
        manager = _make_manager(tmp_path, project_path=project_file)
        manager.add_lesson("Use pytest for testing")
        manager.add_lesson("Check edge cases")

        result = manager.format_for_prompt()

        assert result is not None
        assert "- Use pytest for testing" in result
        assert "- Check edge cases" in result

    def test_respects_token_budget(self, tmp_path) -> None:
        """Output is capped at max_tokens."""
        project_file = tmp_path / "lessons.md"
        manager = _make_manager(tmp_path, project_path=project_file)

        for i in range(200):
            manager.add_lesson(f"Lesson number {i} with enough words to consume tokens quickly")

        result = manager.format_for_prompt(max_tokens=100)

        assert result is not None
        token_count = _estimate_tokens(result)
        assert token_count <= 100

    def test_under_budget_returns_all(self, tmp_path) -> None:
        """When under budget, all lessons are returned."""
        project_file = tmp_path / "lessons.md"
        manager = _make_manager(tmp_path, project_path=project_file)
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
        evil_path = tmp_path / "evil\x00.md"
        evil_manager = _make_manager(tmp_path, project_path=evil_path)
        with pytest.raises(ValueError, match="null bytes"):
            evil_manager.add_lesson("test")

    def test_system_directory_rejected(self, tmp_path) -> None:
        """System directory paths are rejected."""
        from pathlib import Path

        manager = LessonsManager(
            project_path=Path("/etc/lessons.md"),
            global_path=Path("/tmp/global.md"),
            sync_to_claude_md=False,
            claude_md_path=tmp_path / ".claude" / "CLAUDE.md",
        )
        with pytest.raises(ValueError, match="system directory"):
            manager.add_lesson("test")


# ---------------------------------------------------------------------------
# CLAUDE.md Bridge - Sync
# ---------------------------------------------------------------------------


class TestClaudeMdSync:
    """Tests for _sync_lesson_to_claude_md()."""

    def test_sync_creates_markers_in_claude_md(self, tmp_path) -> None:
        """First sync adds markers and lesson to CLAUDE.md."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text("# Project Memory\n\nExisting content.\n")

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )
        manager.add_lesson("Always run tests")

        content = claude_md.read_text()
        assert _CLAUDE_MD_START in content
        assert _CLAUDE_MD_END in content
        assert "Always run tests" in content
        assert "## Lessons Learned" in content
        # Existing content preserved
        assert "Existing content." in content

    def test_sync_appends_within_markers(self, tmp_path) -> None:
        """Second sync adds inside existing markers."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(
            f"# Project\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"## Lessons Learned\n\n"
            f"- **2026-01-01** First lesson\n"
            f"{_CLAUDE_MD_END}\n",
        )

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )
        manager.add_lesson("Second lesson")

        content = claude_md.read_text()
        assert "First lesson" in content
        assert "Second lesson" in content
        # Markers still present exactly once
        assert content.count(_CLAUDE_MD_START) == 1
        assert content.count(_CLAUDE_MD_END) == 1

    def test_sync_skips_if_no_claude_md(self, tmp_path) -> None:
        """No error when CLAUDE.md doesn't exist."""
        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=tmp_path / "nonexistent" / "CLAUDE.md",
        )

        # Should not raise
        result = manager.add_lesson("Test lesson")
        assert "Lesson saved" in result

    def test_sync_disabled(self, tmp_path) -> None:
        """sync_to_claude_md=False skips CLAUDE.md sync."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        original = "# Project Memory\n\nOriginal content.\n"
        claude_md.write_text(original)

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=False,
            claude_md_path=claude_md,
        )
        manager.add_lesson("Should not appear in CLAUDE.md")

        # CLAUDE.md should be unchanged
        assert claude_md.read_text() == original


# ---------------------------------------------------------------------------
# CLAUDE.md Bridge - Parse
# ---------------------------------------------------------------------------


class TestClaudeMdParse:
    """Tests for _parse_claude_md_lessons()."""

    def test_parse_claude_md_lessons(self, tmp_path) -> None:
        """Reads lessons between markers."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(
            f"# Project\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"## Lessons Learned\n\n"
            f"- **2026-02-20** First lesson\n"
            f"- **2026-02-21** Second lesson\n"
            f"{_CLAUDE_MD_END}\n",
        )

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )
        parsed = manager._parse_claude_md_lessons()

        assert len(parsed) == 2
        assert parsed[0] == ("2026-02-20", "First lesson")
        assert parsed[1] == ("2026-02-21", "Second lesson")

    def test_parse_ignores_content_outside_markers(self, tmp_path) -> None:
        """Only parses between markers."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(
            f"# Project\n\n"
            f"- **2026-01-01** Outside marker lesson\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"- **2026-02-20** Inside marker lesson\n"
            f"{_CLAUDE_MD_END}\n"
            f"- **2026-03-01** After marker lesson\n",
        )

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )
        parsed = manager._parse_claude_md_lessons()

        assert len(parsed) == 1
        assert parsed[0][1] == "Inside marker lesson"

    def test_parse_returns_empty_when_no_markers(self, tmp_path) -> None:
        """Returns empty list when no markers found."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text("# Project\n\nNo lessons section here.\n")

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )
        assert manager._parse_claude_md_lessons() == []

    def test_parse_returns_empty_when_file_missing(self, tmp_path) -> None:
        """Returns empty list when CLAUDE.md doesn't exist."""
        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=tmp_path / "nonexistent" / "CLAUDE.md",
        )
        assert manager._parse_claude_md_lessons() == []


# ---------------------------------------------------------------------------
# CLAUDE.md Bridge - Integration (get_lessons merges)
# ---------------------------------------------------------------------------


class TestClaudeMdIntegration:
    """Tests for CLAUDE.md bridge integration with get_lessons()."""

    def test_get_lessons_includes_claude_md(self, tmp_path) -> None:
        """Unified list includes source='claude_md'."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(
            f"# Project\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"- **2026-02-20** Claude MD only lesson\n"
            f"{_CLAUDE_MD_END}\n",
        )

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )

        lessons = manager.get_lessons()

        assert len(lessons) == 1
        assert lessons[0]["text"] == "Claude MD only lesson"
        assert lessons[0]["source"] == "claude_md"

    def test_claude_md_deduplication(self, tmp_path) -> None:
        """Same lesson in project and CLAUDE.md appears once."""
        project_file = tmp_path / ".attune" / "lessons.md"
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)

        # Create CLAUDE.md with a lesson
        claude_md.write_text(
            f"# Project\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"- **2026-02-20** Shared lesson\n"
            f"{_CLAUDE_MD_END}\n",
        )

        manager = _make_manager(
            tmp_path,
            project_path=project_file,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )
        # Add same lesson to project
        manager.add_lesson("Shared lesson")

        lessons = manager.get_lessons()

        # Should appear once from project, deduplicated from claude_md
        matching = [lesson for lesson in lessons if lesson["text"] == "Shared lesson"]
        assert len(matching) == 1
        assert matching[0]["source"] == "project"

    def test_manually_added_claude_md_lesson_picked_up(self, tmp_path) -> None:
        """Hand-written lessons between markers are read."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)

        # Manually write a lesson (not via attune remember)
        claude_md.write_text(
            f"# Project\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"## Lessons Learned\n\n"
            f"- **2026-02-15** Hand-written by developer\n"
            f"{_CLAUDE_MD_END}\n",
        )

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )

        lessons = manager.get_lessons()

        assert len(lessons) == 1
        assert lessons[0]["text"] == "Hand-written by developer"
        assert lessons[0]["source"] == "claude_md"

    def test_remove_claude_md_sourced_lesson(self, tmp_path) -> None:
        """Remove a lesson that only exists in CLAUDE.md."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(
            f"# Project\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"## Lessons Learned\n\n"
            f"- **2026-02-20** Only in claude md\n"
            f"{_CLAUDE_MD_END}\n",
        )

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )

        # Verify it appears
        lessons = manager.get_lessons()
        assert len(lessons) == 1
        assert lessons[0]["source"] == "claude_md"

        # Remove it
        result = manager.remove_lesson("claude md")
        assert "Only in claude md" in result

        # Verify it's gone
        lessons_after = manager.get_lessons()
        assert len(lessons_after) == 0

        # Verify CLAUDE.md file was updated
        content = claude_md.read_text()
        assert "Only in claude md" not in content
        assert _CLAUDE_MD_START in content
        assert _CLAUDE_MD_END in content

    def test_remove_project_lesson_syncs_to_claude_md(self, tmp_path) -> None:
        """Removing a project lesson also removes it from CLAUDE.md."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text("# Project\n\n")

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=True,
            claude_md_path=claude_md,
        )

        # Add a lesson (syncs to both files)
        manager.add_lesson("Synced lesson")

        # Verify it's in CLAUDE.md
        content = claude_md.read_text()
        assert "Synced lesson" in content

        # Remove it
        manager.remove_lesson("Synced")

        # Verify it's gone from CLAUDE.md too
        content_after = claude_md.read_text()
        assert "Synced lesson" not in content_after

    def test_bridge_disabled_does_not_read_claude_md(self, tmp_path) -> None:
        """When sync disabled, CLAUDE.md lessons not included."""
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(
            f"# Project\n\n"
            f"{_CLAUDE_MD_START}\n"
            f"- **2026-02-20** Should not appear\n"
            f"{_CLAUDE_MD_END}\n",
        )

        manager = _make_manager(
            tmp_path,
            sync_to_claude_md=False,
            claude_md_path=claude_md,
        )

        lessons = manager.get_lessons()
        assert len(lessons) == 0
