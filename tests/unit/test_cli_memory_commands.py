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


# ---------------------------------------------------------------------------
# Personal memory commands (capture / recall / topics / forget_topic)
# ---------------------------------------------------------------------------

_PERSONAL_MEM = "attune.memory.personal.PersonalMemory"


class TestCmdMemoryCapture:
    """Tests for cmd_memory_capture."""

    @patch(_PERSONAL_MEM)
    def test_success_global(self, MockPM, capsys, tmp_path) -> None:
        """cmd_memory_capture writes to global root when project_local=False."""
        from attune.cli_commands.memory_commands import cmd_memory_capture

        dest = tmp_path / "auth-design" / "decision.md"
        MockPM.return_value.capture.return_value = dest

        args = MagicMock()
        args.topic = "auth-design"
        args.content = "Use JWT"
        args.kind = "decision"
        args.project_local = False

        result = cmd_memory_capture(args)

        assert result == 0
        # PersonalMemory must be constructed with project_root=None for global
        MockPM.assert_called_once_with(project_root=None)
        assert "Saved:" in capsys.readouterr().out

    @patch(_PERSONAL_MEM)
    def test_success_project_local(self, MockPM, capsys, tmp_path) -> None:
        """cmd_memory_capture passes project_root when project_local=True."""
        from attune.cli_commands.memory_commands import cmd_memory_capture

        dest = tmp_path / "auth-design" / "decision.md"
        MockPM.return_value.capture.return_value = dest

        args = MagicMock()
        args.topic = "auth-design"
        args.content = "Use JWT"
        args.kind = "decision"
        args.project_local = True

        result = cmd_memory_capture(args)

        assert result == 0
        # project_root must be non-None for project_local=True
        call_kwargs = MockPM.call_args[1]
        assert call_kwargs["project_root"] is not None

    @patch(_PERSONAL_MEM)
    def test_invalid_topic_returns_1(self, MockPM, capsys) -> None:
        """cmd_memory_capture returns 1 on invalid topic slug."""
        from attune.cli_commands.memory_commands import cmd_memory_capture

        MockPM.return_value.capture.side_effect = ValueError("Invalid topic slug '../etc'")

        args = MagicMock()
        args.topic = "../etc"
        args.content = "bad"
        args.kind = "decision"
        args.project_local = False

        result = cmd_memory_capture(args)

        assert result == 1
        assert "Error:" in capsys.readouterr().out

    @patch(_PERSONAL_MEM)
    def test_os_error_returns_1(self, MockPM, capsys) -> None:
        """cmd_memory_capture returns 1 on OSError."""
        from attune.cli_commands.memory_commands import cmd_memory_capture

        MockPM.return_value.capture.side_effect = OSError("disk full")

        args = MagicMock()
        args.topic = "auth-design"
        args.content = "Use JWT"
        args.kind = "decision"
        args.project_local = False

        result = cmd_memory_capture(args)

        assert result == 1
        assert "Error saving" in capsys.readouterr().out


class TestCmdMemoryRecall:
    """Tests for cmd_memory_recall."""

    @patch(_PERSONAL_MEM)
    def test_success_with_hits(self, MockPM, capsys) -> None:
        """cmd_memory_recall prints results when hits are found."""
        from attune.cli_commands.memory_commands import cmd_memory_recall

        MockPM.return_value.query.return_value = [
            {
                "path": "auth-design/decision.md",
                "score": 0.9,
                "summary": "JWT",
                "excerpt": "Use JWT",
            }
        ]

        args = MagicMock()
        args.query = "authentication"
        args.k = 3
        args.kind_filter = None
        args.json = False

        result = cmd_memory_recall(args)

        # PersonalMemory must be constructed with project_root=None
        MockPM.assert_called_once_with(project_root=None)
        assert result == 0
        assert "auth-design" in capsys.readouterr().out

    @patch(_PERSONAL_MEM)
    def test_no_results(self, MockPM, capsys) -> None:
        """cmd_memory_recall prints no-results message when list is empty."""
        from attune.cli_commands.memory_commands import cmd_memory_recall

        MockPM.return_value.query.return_value = []

        args = MagicMock()
        args.query = "nothing"
        args.k = 3
        args.kind_filter = None
        args.json = False

        result = cmd_memory_recall(args)

        assert result == 0
        assert "No results" in capsys.readouterr().out

    @patch(_PERSONAL_MEM)
    def test_json_output(self, MockPM, capsys) -> None:
        """cmd_memory_recall emits JSON when --json flag is set."""
        import json as json_mod

        from attune.cli_commands.memory_commands import cmd_memory_recall

        hits = [{"path": "auth-design/decision.md", "score": 0.9}]
        MockPM.return_value.query.return_value = hits

        args = MagicMock()
        args.query = "auth"
        args.k = 3
        args.kind_filter = None
        args.json = True

        result = cmd_memory_recall(args)

        assert result == 0
        out = capsys.readouterr().out
        parsed = json_mod.loads(out)
        assert parsed[0]["score"] == 0.9

    @patch(_PERSONAL_MEM)
    def test_json_output_survives_stdout_log_noise(self, MockPM, capsys) -> None:
        """--json stdout stays parseable when the query layer logs to stdout.

        Regression guard: the RAG layer logs via structlog's default
        PrintLogger, which writes to stdout. That polluted `--json` output
        (a `rag.run` info line ahead of the JSON), breaking machine
        consumers like `attune memory recall ... --json | jq`. The handler
        must forward that noise to stderr and keep stdout pure JSON.
        """
        import json as json_mod

        from attune.cli_commands.memory_commands import cmd_memory_recall

        hits = [{"path": "auth-design/decision.md", "score": 0.9}]

        def noisy_query(*_args, **_kwargs):
            print("2026-07-02 [info] rag.run retriever=KeywordRetriever")
            return hits

        MockPM.return_value.query.side_effect = noisy_query

        args = MagicMock()
        args.query = "auth"
        args.k = 3
        args.kind_filter = None
        args.json = True

        result = cmd_memory_recall(args)

        assert result == 0
        captured = capsys.readouterr()
        parsed = json_mod.loads(captured.out)  # raises if stdout is polluted
        assert parsed[0]["score"] == 0.9
        assert "rag.run" in captured.err  # noise forwarded, not swallowed


class TestCmdMemoryTopics:
    """Tests for cmd_memory_topics."""

    @patch(_PERSONAL_MEM)
    def test_lists_topics(self, MockPM, capsys) -> None:
        """cmd_memory_topics prints all topic slugs."""
        from attune.cli_commands.memory_commands import cmd_memory_topics

        MockPM.return_value.list_topics.return_value = ["auth-design", "retry-loop"]

        args = MagicMock()
        result = cmd_memory_topics(args)

        MockPM.assert_called_once_with(project_root=None)
        assert result == 0
        out = capsys.readouterr().out
        assert "auth-design" in out
        assert "retry-loop" in out

    @patch(_PERSONAL_MEM)
    def test_no_topics(self, MockPM, capsys) -> None:
        """cmd_memory_topics prints guidance when no topics exist."""
        from attune.cli_commands.memory_commands import cmd_memory_topics

        MockPM.return_value.list_topics.return_value = []

        args = MagicMock()
        result = cmd_memory_topics(args)

        assert result == 0
        assert "No memory topics" in capsys.readouterr().out


class TestCmdMemoryForgetTopic:
    """Tests for cmd_memory_forget_topic."""

    @patch(_PERSONAL_MEM)
    def test_deletes_topic(self, MockPM, capsys) -> None:
        """cmd_memory_forget_topic returns 0 and prints count on success."""
        from attune.cli_commands.memory_commands import cmd_memory_forget_topic

        MockPM.return_value.forget_topic.return_value = 3

        args = MagicMock()
        args.topic = "auth-design"
        args.kind = None

        result = cmd_memory_forget_topic(args)

        MockPM.assert_called_once_with(project_root=None)
        assert result == 0
        assert "Deleted 3" in capsys.readouterr().out

    @patch(_PERSONAL_MEM)
    def test_topic_not_found_returns_1(self, MockPM, capsys) -> None:
        """cmd_memory_forget_topic returns 1 when topic has no files."""
        from attune.cli_commands.memory_commands import cmd_memory_forget_topic

        MockPM.return_value.forget_topic.return_value = 0

        args = MagicMock()
        args.topic = "nonexistent"
        args.kind = None

        result = cmd_memory_forget_topic(args)

        assert result == 1
        assert "not found" in capsys.readouterr().out.lower()

    @patch(_PERSONAL_MEM)
    def test_invalid_topic_returns_1(self, MockPM, capsys) -> None:
        """cmd_memory_forget_topic returns 1 on invalid topic slug."""
        from attune.cli_commands.memory_commands import cmd_memory_forget_topic

        MockPM.return_value.forget_topic.side_effect = ValueError("Invalid topic slug '../etc'")

        args = MagicMock()
        args.topic = "../etc"
        args.kind = None

        result = cmd_memory_forget_topic(args)

        assert result == 1
        assert "Error:" in capsys.readouterr().out
