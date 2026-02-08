"""Tests for attune.tools - interactive user prompting tools."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import attune.tools as tools_module
from attune.tools import (
    AskUserQuestion,
    _ask_via_claude_code_ipc,
    _is_running_in_claude_code,
    set_ask_user_question_handler,
)


@pytest.fixture(autouse=True)
def reset_custom_ask_function():
    """Reset _custom_ask_function to None before and after each test."""
    tools_module._custom_ask_function = None
    yield
    tools_module._custom_ask_function = None


SAMPLE_QUESTIONS = [
    {
        "header": "Pattern",
        "question": "Which pattern to use?",
        "multiSelect": False,
        "options": [
            {"label": "sequential", "description": "One after another"},
            {"label": "parallel", "description": "All at once"},
        ],
    }
]


class TestSetAskUserQuestionHandler:
    """Tests for set_ask_user_question_handler."""

    def test_set_ask_user_question_handler(self) -> None:
        """Set handler, verify it's stored and called."""
        call_log: list[list] = []

        def my_handler(questions: list) -> dict:
            call_log.append(questions)
            return {"Pattern": "sequential"}

        set_ask_user_question_handler(my_handler)

        assert tools_module._custom_ask_function is my_handler

        result = tools_module._custom_ask_function(SAMPLE_QUESTIONS)
        assert result == {"Pattern": "sequential"}
        assert len(call_log) == 1
        assert call_log[0] is SAMPLE_QUESTIONS


class TestAskUserQuestion:
    """Tests for AskUserQuestion."""

    def test_ask_user_question_custom_handler(self) -> None:
        """Set handler, call AskUserQuestion, verify it delegates and returns."""

        def handler(questions: list) -> dict:
            return {"Pattern": questions[0]["options"][1]["label"]}

        set_ask_user_question_handler(handler)

        result = AskUserQuestion(SAMPLE_QUESTIONS)
        assert result == {"Pattern": "parallel"}

    @patch("attune.tools._is_running_in_claude_code", return_value=False)
    def test_ask_user_question_no_handler_no_claude_code(
        self, mock_check: object
    ) -> None:
        """Should raise NotImplementedError when no handler and not in Claude Code."""
        with pytest.raises(NotImplementedError, match="AskUserQuestion requires"):
            AskUserQuestion(SAMPLE_QUESTIONS)

    @patch("attune.tools._is_running_in_claude_code", return_value=True)
    @patch("attune.tools._ask_via_claude_code_ipc")
    def test_ask_user_question_claude_code_mode(
        self, mock_ipc: object, mock_check: object
    ) -> None:
        """Should delegate to IPC when in Claude Code and no custom handler."""
        mock_ipc.return_value = {"Pattern": "sequential"}

        result = AskUserQuestion(SAMPLE_QUESTIONS)
        assert result == {"Pattern": "sequential"}
        mock_ipc.assert_called_once_with(SAMPLE_QUESTIONS)


class TestIsRunningInClaudeCode:
    """Tests for _is_running_in_claude_code."""

    def test_is_running_in_claude_code_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No env vars and no marker file should return False."""
        monkeypatch.delenv("CLAUDE_CODE_SESSION", raising=False)
        monkeypatch.delenv("CLAUDE_AGENT_MODE", raising=False)

        with patch.object(Path, "exists", return_value=False):
            assert _is_running_in_claude_code() is False

    def test_is_running_in_claude_code_session_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLAUDE_CODE_SESSION set should return True."""
        monkeypatch.setenv("CLAUDE_CODE_SESSION", "1")
        monkeypatch.delenv("CLAUDE_AGENT_MODE", raising=False)

        assert _is_running_in_claude_code() is True

    def test_is_running_in_claude_code_agent_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLAUDE_AGENT_MODE set should return True."""
        monkeypatch.delenv("CLAUDE_CODE_SESSION", raising=False)
        monkeypatch.setenv("CLAUDE_AGENT_MODE", "1")

        assert _is_running_in_claude_code() is True

    def test_is_running_in_claude_code_marker_file(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Marker file /tmp/.claude-code exists should return True."""
        monkeypatch.delenv("CLAUDE_CODE_SESSION", raising=False)
        monkeypatch.delenv("CLAUDE_AGENT_MODE", raising=False)

        with patch.object(Path, "exists", return_value=True):
            assert _is_running_in_claude_code() is True


class TestAskViaClaudeCodeIpc:
    """Tests for _ask_via_claude_code_ipc."""

    def test_ask_via_claude_code_ipc_timeout(self, tmp_path: Path) -> None:
        """Should raise RuntimeError when response file never appears."""
        # The function does `import time` locally, so we patch the time module
        # functions directly rather than the attune.tools namespace.
        time_values = iter([0.0, 0.0, 61.0])

        with (
            patch("tempfile.gettempdir", return_value=str(tmp_path)),
            patch("time.time", side_effect=lambda: next(time_values)),
            patch("time.sleep", return_value=None),
        ):
            # The timeout RuntimeError is caught by the outer except block
            # and re-raised as "Claude Code IPC failed: Timeout waiting..."
            with pytest.raises(RuntimeError, match="Claude Code IPC failed.*Timeout"):
                _ask_via_claude_code_ipc(SAMPLE_QUESTIONS)

    def test_ask_via_claude_code_ipc_success(self, tmp_path: Path) -> None:
        """Should return answers when response file is written."""
        ipc_dir = tmp_path / ".claude-code-ipc"
        ipc_dir.mkdir(parents=True, exist_ok=True)

        call_count = 0
        original_exists = Path.exists

        def fake_response_exists(path_self: Path) -> bool:
            """On second call to response file .exists(), write the response and return True."""
            nonlocal call_count
            if "ask-response-" in str(path_self):
                call_count += 1
                if call_count >= 1:
                    # Write the response file so the function can read it
                    response_data = {
                        "answers": {"Pattern": "sequential"},
                    }
                    path_self.parent.mkdir(parents=True, exist_ok=True)
                    path_self.write_text(json.dumps(response_data))
                    return True
            return original_exists(path_self)

        with (
            patch("tempfile.gettempdir", return_value=str(tmp_path)),
            patch.object(Path, "exists", fake_response_exists),
        ):
            result = _ask_via_claude_code_ipc(SAMPLE_QUESTIONS)

        assert result == {"Pattern": "sequential"}
