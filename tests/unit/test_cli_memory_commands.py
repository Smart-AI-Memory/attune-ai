"""Tests for CLI memory commands (remember, forget, lessons).

Tests for the CLI argument parsing and command routing for
the quick-memory lesson system.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.cli_commands.memory_commands import (
    cmd_forget,
    cmd_lessons,
    cmd_remember,
)
from attune.cli_minimal import create_parser, main

_CLI = "attune.cli_minimal"
_LESSONS_MGR = "attune.memory.lessons.LessonsManager"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestParserMemoryCommands:
    """Tests for memory command argument parsing."""

    @pytest.fixture
    def parser(self):
        return create_parser()

    def test_remember_parses_text(self, parser) -> None:
        """Remember command parses lesson text."""
        args = parser.parse_args(["remember", "Always run tests"])
        assert args.command == "remember"
        assert args.lesson_text == "Always run tests"

    def test_remember_global_flag(self, parser) -> None:
        """Remember --global flag is parsed."""
        args = parser.parse_args(["remember", "--global", "Global lesson"])
        assert args.command == "remember"
        assert getattr(args, "global") is True

    def test_forget_parses_identifier(self, parser) -> None:
        """Forget command parses identifier."""
        args = parser.parse_args(["forget", "3"])
        assert args.command == "forget"
        assert args.identifier == "3"

    def test_forget_keyword(self, parser) -> None:
        """Forget command accepts keyword string."""
        args = parser.parse_args(["forget", "security"])
        assert args.command == "forget"
        assert args.identifier == "security"

    def test_lessons_default(self, parser) -> None:
        """Lessons command with no flags."""
        args = parser.parse_args(["lessons"])
        assert args.command == "lessons"
        assert getattr(args, "global") is False

    def test_lessons_global_flag(self, parser) -> None:
        """Lessons --global flag is parsed."""
        args = parser.parse_args(["lessons", "--global"])
        assert args.command == "lessons"
        assert getattr(args, "global") is True


# ---------------------------------------------------------------------------
# Command routing in main()
# ---------------------------------------------------------------------------


class TestMainRouting:
    """Tests for main() routing to memory commands."""

    def test_remember_routes(self, monkeypatch, tmp_path) -> None:
        """main() routes 'remember' to cmd_remember."""
        monkeypatch.chdir(tmp_path)
        result = main(["remember", "Test lesson"])
        assert result == 0

    def test_forget_routes(self, monkeypatch, tmp_path) -> None:
        """main() routes 'forget' to cmd_forget."""
        monkeypatch.chdir(tmp_path)
        result = main(["forget", "1"])
        # Returns 0 or 1 depending on whether lessons exist
        assert result in (0, 1)

    def test_lessons_routes(self, monkeypatch, tmp_path) -> None:
        """main() routes 'lessons' to cmd_lessons."""
        monkeypatch.chdir(tmp_path)
        result = main(["lessons"])
        assert result == 0


# ---------------------------------------------------------------------------
# cmd_remember
# ---------------------------------------------------------------------------


class TestCmdRemember:
    """Tests for cmd_remember handler."""

    @patch(_LESSONS_MGR)
    def test_success(self, MockManager, capsys) -> None:
        """cmd_remember prints success message on success."""
        mock_mgr = MockManager.return_value
        mock_mgr.add_lesson.return_value = "Lesson saved (project)."

        args = MagicMock()
        args.lesson_text = "Test lesson"

        result = cmd_remember(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Lesson saved" in captured.out

    @patch(_LESSONS_MGR)
    def test_value_error(self, MockManager, capsys) -> None:
        """cmd_remember returns 1 on ValueError."""
        mock_mgr = MockManager.return_value
        mock_mgr.add_lesson.side_effect = ValueError("empty")

        args = MagicMock()
        args.lesson_text = ""

        result = cmd_remember(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out

    @patch(_LESSONS_MGR)
    def test_os_error(self, MockManager, capsys) -> None:
        """cmd_remember returns 1 on OSError."""
        mock_mgr = MockManager.return_value
        mock_mgr.add_lesson.side_effect = OSError("disk full")

        args = MagicMock()
        args.lesson_text = "test"

        result = cmd_remember(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error saving" in captured.out


# ---------------------------------------------------------------------------
# cmd_forget
# ---------------------------------------------------------------------------


class TestCmdForget:
    """Tests for cmd_forget handler."""

    @patch(_LESSONS_MGR)
    def test_success(self, MockManager, capsys) -> None:
        """cmd_forget prints confirmation on success."""
        mock_mgr = MockManager.return_value
        mock_mgr.remove_lesson.return_value = "Removed: test lesson"

        args = MagicMock()
        args.identifier = "1"

        result = cmd_forget(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Removed:" in captured.out

    @patch(_LESSONS_MGR)
    def test_not_found(self, MockManager, capsys) -> None:
        """cmd_forget returns 1 when no match."""
        mock_mgr = MockManager.return_value
        mock_mgr.remove_lesson.side_effect = ValueError("No lesson at line 99")

        args = MagicMock()
        args.identifier = "99"

        result = cmd_forget(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out


# ---------------------------------------------------------------------------
# cmd_lessons
# ---------------------------------------------------------------------------


class TestCmdLessons:
    """Tests for cmd_lessons handler."""

    @patch(_LESSONS_MGR)
    def test_lists_lessons(self, MockManager, capsys) -> None:
        """cmd_lessons prints lesson list."""
        mock_mgr = MockManager.return_value
        mock_mgr.get_lessons.return_value = [
            {"number": 1, "date": "2026-02-23", "text": "Test lesson", "source": "project"},
        ]

        args = MagicMock(spec=[])
        args.configure_mock(**{"global": False})

        result = cmd_lessons(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Test lesson" in captured.out
        assert "1 lesson(s) total" in captured.out

    @patch(_LESSONS_MGR)
    def test_no_lessons(self, MockManager, capsys) -> None:
        """cmd_lessons shows helpful message when no lessons."""
        mock_mgr = MockManager.return_value
        mock_mgr.get_lessons.return_value = []

        args = MagicMock(spec=[])
        args.configure_mock(**{"global": False})

        result = cmd_lessons(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No lessons found" in captured.out

    @patch(_LESSONS_MGR)
    def test_os_error(self, MockManager, capsys) -> None:
        """cmd_lessons returns 1 on OSError."""
        mock_mgr = MockManager.return_value
        mock_mgr.get_lessons.side_effect = OSError("permission denied")

        args = MagicMock(spec=[])
        args.configure_mock(**{"global": False})

        result = cmd_lessons(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error reading" in captured.out
