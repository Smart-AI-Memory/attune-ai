"""Tests for security_guard.py — PreToolUse hook script.

Covers validate_bash_command, validate_file_path, main(), _is_search_command,
and _read_stdin_context.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest

from attune.hooks.scripts.security_guard import (
    DANGEROUS_BASH_PATTERNS,
    SYSTEM_DIRECTORIES,
    _is_search_command,
    _read_stdin_context,
    main,
    validate_bash_command,
    validate_file_path,
)

# ---------------------------------------------------------------------------
# _is_search_command
# ---------------------------------------------------------------------------


class TestIsSearchCommand:
    """Tests for _is_search_command()."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "grep -r 'eval(' src/",
            "rg 'exec(' src/",
            "ack eval src/",
            "ag __import__ src/",
            "git grep eval",
            "git log --oneline",
            "git diff HEAD",
        ],
    )
    def test_recognizes_search_commands(self, cmd: str) -> None:
        assert _is_search_command(cmd) is True

    @pytest.mark.parametrize(
        "cmd",
        [
            "python -c 'eval(1)'",
            "echo eval(",
            "ls -la",
        ],
    )
    def test_rejects_non_search_commands(self, cmd: str) -> None:
        assert _is_search_command(cmd) is False

    def test_piped_search_command(self) -> None:
        assert _is_search_command("grep eval src/ | head -10") is True


# ---------------------------------------------------------------------------
# validate_bash_command
# ---------------------------------------------------------------------------


class TestValidateBashCommand:
    """Tests for validate_bash_command()."""

    def test_empty_command_allowed(self) -> None:
        allowed, reason = validate_bash_command("")
        assert allowed is True
        assert reason == ""

    def test_safe_command_allowed(self) -> None:
        allowed, reason = validate_bash_command("ls -la")
        assert allowed is True

    def test_blocks_eval(self) -> None:
        allowed, reason = validate_bash_command("python -c 'eval(input())'")
        assert allowed is False
        assert "eval()" in reason

    def test_blocks_exec(self) -> None:
        allowed, reason = validate_bash_command("python -c 'exec(code)'")
        assert allowed is False
        assert "exec()" in reason

    def test_blocks_dunder_import(self) -> None:
        allowed, reason = validate_bash_command("python -c '__import__(\"os\")'")
        assert allowed is False
        assert "__import__()" in reason

    def test_blocks_subprocess_shell_true(self) -> None:
        allowed, reason = validate_bash_command("python -c 'subprocess.call(\"ls\", shell=True)'")
        assert allowed is False
        assert "shell=True" in reason

    def test_blocks_rm_rf_root(self) -> None:
        allowed, reason = validate_bash_command("rm -rf /")
        assert allowed is False
        assert "rm -rf" in reason

    def test_allows_rm_rf_specific_dir(self) -> None:
        allowed, reason = validate_bash_command("rm -rf /tmp/testdir")
        assert allowed is True

    def test_allows_grep_for_eval(self) -> None:
        """Search commands looking for eval should be allowed."""
        allowed, reason = validate_bash_command("grep -r 'eval(' src/")
        assert allowed is True


# ---------------------------------------------------------------------------
# validate_file_path
# ---------------------------------------------------------------------------


class TestValidateFilePath:
    """Tests for validate_file_path()."""

    def test_empty_path_allowed(self) -> None:
        allowed, reason = validate_file_path("")
        assert allowed is True

    def test_safe_path_allowed(self) -> None:
        allowed, reason = validate_file_path("src/attune/config.py")
        assert allowed is True

    def test_blocks_null_bytes(self) -> None:
        allowed, reason = validate_file_path("src/config\x00.py")
        assert allowed is False
        assert "null bytes" in reason

    @pytest.mark.parametrize(
        "path",
        [
            "/etc/passwd",
            "/sys/kernel/debug",
            "/proc/self/mem",
            "/dev/null",
            "/boot/vmlinuz",
            "/sbin/init",
            "/usr/sbin/nologin",
        ],
    )
    def test_blocks_system_directories(self, path: str) -> None:
        allowed, reason = validate_file_path(path)
        assert allowed is False
        assert "system directory" in reason

    def test_safe_tmp_path(self) -> None:
        allowed, reason = validate_file_path("/tmp/test_output.json")
        assert allowed is True


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for main() hook entry point."""

    def test_missing_tool_name_allows(self) -> None:
        result = main({})
        assert result["allowed"] is True
        # No reason key when fail-open

    def test_allows_safe_bash(self) -> None:
        result = main({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        assert result["allowed"] is True

    def test_blocks_dangerous_bash(self) -> None:
        result = main({"tool_name": "Bash", "tool_input": {"command": "python -c 'eval(x)'"}})
        assert result["allowed"] is False

    def test_allows_safe_edit(self) -> None:
        result = main({"tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}})
        assert result["allowed"] is True

    def test_blocks_edit_to_system_dir(self) -> None:
        result = main({"tool_name": "Edit", "tool_input": {"file_path": "/etc/passwd"}})
        assert result["allowed"] is False

    def test_allows_safe_write(self) -> None:
        result = main({"tool_name": "Write", "tool_input": {"file_path": "src/new.py"}})
        assert result["allowed"] is True

    def test_blocks_write_null_bytes(self) -> None:
        result = main({"tool_name": "Write", "tool_input": {"file_path": "src/\x00bad.py"}})
        assert result["allowed"] is False

    def test_allows_unknown_tool(self) -> None:
        """Unknown tools (Read, Grep, etc.) should be allowed."""
        result = main({"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}})
        assert result["allowed"] is True

    def test_empty_tool_input(self) -> None:
        result = main({"tool_name": "Bash", "tool_input": {}})
        assert result["allowed"] is True


# ---------------------------------------------------------------------------
# _read_stdin_context
# ---------------------------------------------------------------------------


class TestReadStdinContext:
    """Tests for _read_stdin_context()."""

    def test_returns_empty_when_tty(self) -> None:
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = _read_stdin_context()
        assert result == {}

    def test_parses_valid_json(self) -> None:
        data = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        with patch("sys.stdin", StringIO(json.dumps(data))):
            result = _read_stdin_context()
        assert result == data

    def test_returns_parse_error_on_bad_json(self) -> None:
        with patch("sys.stdin", StringIO("not json")):
            result = _read_stdin_context()
        assert result.get("_parse_error") is True

    def test_returns_parse_error_on_empty(self) -> None:
        with patch("sys.stdin", StringIO("")):
            result = _read_stdin_context()
        # Empty string -> no raw -> returns {"_parse_error": True}
        # Actually, empty strip -> falsy -> goes to return below
        # Let's check: raw = "".strip() => "" => falsy => skips json.loads
        # falls through to return {"_parse_error": True}
        assert result.get("_parse_error") is True


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify important constants are set correctly."""

    def test_system_directories_contains_etc(self) -> None:
        assert "/etc" in SYSTEM_DIRECTORIES

    def test_dangerous_patterns_not_empty(self) -> None:
        assert len(DANGEROUS_BASH_PATTERNS) > 0


# ---------------------------------------------------------------------------
# __main__ exit code wiring
# ---------------------------------------------------------------------------


class TestMainEntryPointExitCodes:
    """Tests for the __main__ block exit code behavior."""

    def test_blocked_tool_exits_with_code_2(self) -> None:
        """When main() returns allowed=False, the script must exit(2)."""
        import subprocess
        import sys

        blocked_input = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "python -c 'eval(x)'"}}
        )
        result = subprocess.run(
            [sys.executable, "src/attune/hooks/scripts/security_guard.py"],
            input=blocked_input,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "eval()" in result.stderr

    def test_allowed_tool_exits_with_code_0(self) -> None:
        """When main() returns allowed=True, the script must exit(0)."""
        import subprocess
        import sys

        safe_input = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        result = subprocess.run(
            [sys.executable, "src/attune/hooks/scripts/security_guard.py"],
            input=safe_input,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


class TestMalformedPayloadFailsOpen:
    """Library-review L1/L4: a blocking guard must fail OPEN (exit 0),
    never crash to exit 1, on any parsed-but-malformed stdin."""

    @pytest.mark.parametrize(
        "payload",
        [
            "[1,2,3]",
            "42",
            "null",
            '{"tool_name":123,"tool_input":{"command":"x"}}',
            '{"tool_name":"Bash","tool_input":[1,2]}',
            '{"tool_name":"Bash","tool_input":{"command":999}}',
            '{"tool_name":"Bash","tool_input":null}',
            '{"tool_name":"Write","tool_input":{"file_path":123}}',
        ],
    )
    def test_malformed_stdin_exits_0(self, payload: str) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "src/attune/hooks/scripts/security_guard.py"],
            input=payload,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{payload!r} -> exit {result.returncode}"

    def test_deeply_nested_json_exits_0(self) -> None:
        import subprocess
        import sys

        payload = '{"a":' * 3000 + "1" + "}" * 3000
        result = subprocess.run(
            [sys.executable, "src/attune/hooks/scripts/security_guard.py"],
            input=payload,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_real_block_still_fires_after_guard(self) -> None:
        """The fail-open hardening must NOT neuter a real block."""
        import subprocess
        import sys

        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "python -c 'ev" + "al(x)'"}}
        )
        result = subprocess.run(
            [sys.executable, "src/attune/hooks/scripts/security_guard.py"],
            input=payload,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
