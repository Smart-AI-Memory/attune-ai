"""Tests for lessons_reminder.py and format_on_save.py hook scripts.

Covers Batch 1C of the test audit plan — two hook script modules at 0% coverage.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# lessons_reminder.py
# ---------------------------------------------------------------------------


class TestAlreadyReminded:
    """Tests for already_reminded() in lessons_reminder."""

    def test_returns_false_when_sentinel_missing(self, tmp_path: Path) -> None:
        sentinel = tmp_path / ".attune" / "lessons_reminded"
        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            from attune.hooks.scripts.lessons_reminder import already_reminded

            assert already_reminded() is False

    def test_returns_true_when_sentinel_fresh(self, tmp_path: Path) -> None:
        sentinel = tmp_path / ".attune" / "lessons_reminded"
        sentinel.parent.mkdir(parents=True)
        sentinel.touch()

        import time

        fresh_mtime = time.time() - 60  # 1 minute ago — within TTL
        with (
            patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel),
            patch("attune.hooks.scripts.lessons_reminder.time") as mock_time,
        ):
            mock_time.time.return_value = fresh_mtime + 60
            from attune.hooks.scripts.lessons_reminder import already_reminded

            assert already_reminded() is True

    def test_returns_false_when_sentinel_stale(self, tmp_path: Path) -> None:
        sentinel = tmp_path / ".attune" / "lessons_reminded"
        sentinel.parent.mkdir(parents=True)
        sentinel.touch()

        mock_sentinel = MagicMock(spec=Path)
        mock_sentinel.exists.return_value = True
        mock_sentinel.stat.return_value.st_mtime = 1_000_000.0

        with (
            patch("attune.hooks.scripts.lessons_reminder.SENTINEL", mock_sentinel),
            patch("attune.hooks.scripts.lessons_reminder.time") as mock_time,
        ):
            # time.time() is way beyond mtime + TTL → stale
            mock_time.time.return_value = 1_000_000.0 + 9999
            from attune.hooks.scripts.lessons_reminder import already_reminded

            assert already_reminded() is False

    def test_returns_false_when_age_exactly_at_ttl(self) -> None:
        """Age equal to TTL is not less-than, so returns False."""
        mock_sentinel = MagicMock(spec=Path)
        mock_sentinel.exists.return_value = True
        mock_sentinel.stat.return_value.st_mtime = 1000.0

        with (
            patch("attune.hooks.scripts.lessons_reminder.SENTINEL", mock_sentinel),
            patch("attune.hooks.scripts.lessons_reminder.time") as mock_time,
        ):
            mock_time.time.return_value = 1000.0 + 3600  # age == TTL exactly
            from attune.hooks.scripts.lessons_reminder import already_reminded

            assert already_reminded() is False


class TestAlreadyRemindedUsingModuleSentinel:
    """Tests that operate by patching at the module attribute level directly."""

    def test_sentinel_missing_returns_false(self) -> None:
        mock_sentinel = MagicMock(spec=Path)
        mock_sentinel.exists.return_value = False

        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", mock_sentinel):
            from attune.hooks.scripts.lessons_reminder import already_reminded

            result = already_reminded()

        assert result is False
        mock_sentinel.stat.assert_not_called()

    def test_sentinel_present_and_fresh_returns_true(self) -> None:
        mock_sentinel = MagicMock(spec=Path)
        mock_sentinel.exists.return_value = True
        mock_sentinel.stat.return_value.st_mtime = 1_000_000.0

        with (
            patch("attune.hooks.scripts.lessons_reminder.SENTINEL", mock_sentinel),
            patch("attune.hooks.scripts.lessons_reminder.time") as mock_time,
        ):
            mock_time.time.return_value = 1_000_000.0 + 30  # 30s ago
            from attune.hooks.scripts.lessons_reminder import already_reminded

            result = already_reminded()

        assert result is True

    def test_sentinel_present_and_stale_returns_false(self) -> None:
        mock_sentinel = MagicMock(spec=Path)
        mock_sentinel.exists.return_value = True
        mock_sentinel.stat.return_value.st_mtime = 1_000_000.0

        with (
            patch("attune.hooks.scripts.lessons_reminder.SENTINEL", mock_sentinel),
            patch("attune.hooks.scripts.lessons_reminder.time") as mock_time,
        ):
            mock_time.time.return_value = 1_000_000.0 + 9999  # way past TTL
            from attune.hooks.scripts.lessons_reminder import already_reminded

            result = already_reminded()

        assert result is False


class TestMarkReminded:
    """Tests for mark_reminded() in lessons_reminder."""

    def test_creates_sentinel_parent_and_touches_file(self, tmp_path: Path) -> None:
        sentinel = tmp_path / "nested" / "dir" / "lessons_reminded"

        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            from attune.hooks.scripts.lessons_reminder import mark_reminded

            mark_reminded()

        assert sentinel.exists()

    def test_idempotent_when_called_twice(self, tmp_path: Path) -> None:
        sentinel = tmp_path / ".attune" / "lessons_reminded"

        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            from attune.hooks.scripts.lessons_reminder import mark_reminded

            mark_reminded()
            mark_reminded()  # Should not raise

        assert sentinel.exists()

    def test_uses_mock_sentinel_mkdir_and_touch(self) -> None:
        mock_sentinel = MagicMock(spec=Path)
        mock_parent = MagicMock(spec=Path)
        mock_sentinel.parent = mock_parent

        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", mock_sentinel):
            from attune.hooks.scripts.lessons_reminder import mark_reminded

            mark_reminded()

        mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_sentinel.touch.assert_called_once()


class TestHasSessionWork:
    """Tests for has_session_work() in lessons_reminder."""

    def test_returns_true_when_git_has_output(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "abc1234 feat: add something\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            from attune.hooks.scripts.lessons_reminder import has_session_work

            result = has_session_work()

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "log", "--oneline", "--since=8 hours ago"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )

    def test_returns_false_when_git_output_empty(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            from attune.hooks.scripts.lessons_reminder import has_session_work

            result = has_session_work()

        assert result is False

    def test_returns_false_when_output_whitespace_only(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n  "

        with patch("subprocess.run", return_value=mock_result):
            from attune.hooks.scripts.lessons_reminder import has_session_work

            result = has_session_work()

        assert result is False

    def test_returns_true_on_subprocess_timeout(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            from attune.hooks.scripts.lessons_reminder import has_session_work

            result = has_session_work()

        assert result is True

    def test_returns_true_on_file_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            from attune.hooks.scripts.lessons_reminder import has_session_work

            result = has_session_work()

        assert result is True

    def test_returns_true_on_generic_exception(self) -> None:
        with patch("subprocess.run", side_effect=OSError("unexpected")):
            from attune.hooks.scripts.lessons_reminder import has_session_work

            result = has_session_work()

        assert result is True


class TestLessonsReminderMain:
    """Tests for main() in lessons_reminder."""

    def test_returns_0_when_already_reminded(self) -> None:
        with (
            patch(
                "attune.hooks.scripts.lessons_reminder.already_reminded",
                return_value=True,
            ),
            patch(
                "attune.hooks.scripts.lessons_reminder.has_session_work",
                return_value=True,
            ),
            patch("attune.hooks.scripts.lessons_reminder.mark_reminded") as mock_mark,
        ):
            from attune.hooks.scripts.lessons_reminder import main

            result = main()

        assert result == 0
        mock_mark.assert_not_called()

    def test_returns_0_when_no_session_work(self) -> None:
        with (
            patch(
                "attune.hooks.scripts.lessons_reminder.already_reminded",
                return_value=False,
            ),
            patch(
                "attune.hooks.scripts.lessons_reminder.has_session_work",
                return_value=False,
            ),
            patch("attune.hooks.scripts.lessons_reminder.mark_reminded") as mock_mark,
        ):
            from attune.hooks.scripts.lessons_reminder import main

            result = main()

        assert result == 0
        mock_mark.assert_not_called()

    def test_returns_2_and_marks_when_work_exists(self, capsys: pytest.CaptureFixture) -> None:
        with (
            patch(
                "attune.hooks.scripts.lessons_reminder.already_reminded",
                return_value=False,
            ),
            patch(
                "attune.hooks.scripts.lessons_reminder.has_session_work",
                return_value=True,
            ),
            patch("attune.hooks.scripts.lessons_reminder.mark_reminded") as mock_mark,
        ):
            from attune.hooks.scripts.lessons_reminder import main

            result = main()

        assert result == 2
        mock_mark.assert_called_once()

    def test_reminder_printed_to_stderr(self, capsys: pytest.CaptureFixture) -> None:
        with (
            patch(
                "attune.hooks.scripts.lessons_reminder.already_reminded",
                return_value=False,
            ),
            patch(
                "attune.hooks.scripts.lessons_reminder.has_session_work",
                return_value=True,
            ),
            patch("attune.hooks.scripts.lessons_reminder.mark_reminded"),
        ):
            from attune.hooks.scripts.lessons_reminder import main

            main()

        captured = capsys.readouterr()
        assert "attune.docs_outbox write" in captured.err
        assert captured.out == ""

    def test_returns_0_when_already_reminded_short_circuits_work_check(self) -> None:
        """already_reminded=True must not call has_session_work (short-circuit)."""
        with (
            patch(
                "attune.hooks.scripts.lessons_reminder.already_reminded",
                return_value=True,
            ),
            patch("attune.hooks.scripts.lessons_reminder.has_session_work") as mock_work,
        ):
            from attune.hooks.scripts.lessons_reminder import main

            result = main()

        # Python's `or` short-circuits: already_reminded()=True -> not called
        # Actually: `if already_reminded() or not has_session_work()` — if the
        # first is True the whole condition is True, so has_session_work IS still
        # evaluated because of `or not`. Re-read the source: the expression is:
        # `already_reminded() or not has_session_work()`. Short-circuit means
        # has_session_work() is NOT called when already_reminded() is True.
        assert result == 0
        mock_work.assert_not_called()


# ---------------------------------------------------------------------------
# format_on_save.py — _get_file_path
# ---------------------------------------------------------------------------


class TestGetFilePath:
    """Tests for _get_file_path() in format_on_save."""

    def test_returns_file_path_key(self) -> None:
        from attune.hooks.scripts.format_on_save import _get_file_path

        data = {"tool_input": {"file_path": "src/attune/foo.py"}}
        assert _get_file_path(data) == "src/attune/foo.py"

    def test_returns_path_key_when_file_path_absent(self) -> None:
        from attune.hooks.scripts.format_on_save import _get_file_path

        data = {"tool_input": {"path": "src/attune/bar.py"}}
        assert _get_file_path(data) == "src/attune/bar.py"

    def test_file_path_takes_precedence_over_path(self) -> None:
        from attune.hooks.scripts.format_on_save import _get_file_path

        data = {"tool_input": {"file_path": "primary.py", "path": "secondary.py"}}
        assert _get_file_path(data) == "primary.py"

    def test_returns_none_when_neither_key_present(self) -> None:
        from attune.hooks.scripts.format_on_save import _get_file_path

        data = {"tool_input": {"command": "ls"}}
        assert _get_file_path(data) is None

    def test_returns_none_when_tool_input_missing(self) -> None:
        from attune.hooks.scripts.format_on_save import _get_file_path

        assert _get_file_path({}) is None

    def test_returns_falsy_when_both_keys_are_empty_string(self) -> None:
        from attune.hooks.scripts.format_on_save import _get_file_path

        # `file_path=""` is falsy so `or` falls through to `path=""` which is
        # also falsy — result is "" (falsy), not None.  main() treats any
        # falsy value from _get_file_path as "no path", so this is correct.
        data = {"tool_input": {"file_path": "", "path": ""}}
        result = _get_file_path(data)
        assert not result  # falsy: either None or ""


# ---------------------------------------------------------------------------
# format_on_save.py — _is_python_file
# ---------------------------------------------------------------------------


class TestIsPythonFile:
    """Tests for _is_python_file() in format_on_save."""

    @pytest.mark.parametrize(
        "path",
        [
            "src/attune/foo.py",
            "test_bar.py",
            "/absolute/path/module.py",
            "just_a_name.py",
        ],
    )
    def test_returns_true_for_py_files(self, path: str) -> None:
        from attune.hooks.scripts.format_on_save import _is_python_file

        assert _is_python_file(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "src/attune/foo.ts",
            "README.md",
            "script.sh",
            "data.json",
            "no_extension",
            "src/attune/foo.pyx",
        ],
    )
    def test_returns_false_for_non_py_files(self, path: str) -> None:
        from attune.hooks.scripts.format_on_save import _is_python_file

        assert _is_python_file(path) is False

    def test_returns_false_for_py_in_directory_name(self) -> None:
        from attune.hooks.scripts.format_on_save import _is_python_file

        # "src.py/foo.txt" has .txt suffix, not .py
        assert _is_python_file("src.py/foo.txt") is False


# ---------------------------------------------------------------------------
# format_on_save.py — _run_formatter
# ---------------------------------------------------------------------------


class TestRunFormatter:
    """Tests for _run_formatter() in format_on_save."""

    def test_runs_subprocess_with_cmd_and_path(self) -> None:
        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch("subprocess.run") as mock_run:
            _run_formatter(["black", "--quiet"], "src/foo.py")

        mock_run.assert_called_once_with(
            ["black", "--quiet", "src/foo.py"],
            capture_output=True,
            timeout=10,
        )

    def test_swallows_timeout_expired(self) -> None:
        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(["black"], 10),
        ):
            _run_formatter(["black", "--quiet"], "src/foo.py")  # Must not raise

    def test_swallows_file_not_found(self) -> None:
        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch("subprocess.run", side_effect=FileNotFoundError("black")):
            _run_formatter(["black", "--quiet"], "src/foo.py")  # Must not raise

    def test_swallows_oserror(self) -> None:
        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch("subprocess.run", side_effect=OSError("broken pipe")):
            _run_formatter(["ruff", "check", "--fix"], "src/foo.py")  # Must not raise

    def test_multi_arg_command_prepended_correctly(self) -> None:
        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch("subprocess.run") as mock_run:
            _run_formatter(["ruff", "check", "--fix", "--quiet"], "myfile.py")

        args = mock_run.call_args[0][0]
        assert args == ["ruff", "check", "--fix", "--quiet", "myfile.py"]


# ---------------------------------------------------------------------------
# format_on_save.py — main()
# ---------------------------------------------------------------------------


class TestFormatOnSaveMain:
    """Tests for main() in format_on_save."""

    # ------------------------------------------------------------------
    # Early-exit paths (no formatting)
    # ------------------------------------------------------------------

    def test_returns_early_on_empty_stdin(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        with (
            patch("sys.stdin", io.StringIO("")),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_on_whitespace_only_stdin(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        with (
            patch("sys.stdin", io.StringIO("   \n  ")),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_on_invalid_json(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        with (
            patch("sys.stdin", io.StringIO("not-valid-json!!")),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_for_non_write_edit_tool(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "src/foo.py"}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_for_bash_tool(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_when_no_file_path(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        payload = json.dumps({"tool_name": "Write", "tool_input": {}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_for_non_python_file(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "README.md"}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_when_validate_file_path_raises(self) -> None:
        from attune.hooks.scripts.format_on_save import main

        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/etc/passwd.py"}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                side_effect=ValueError("system directory"),
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_when_import_error_for_validate(self, tmp_path: Path) -> None:
        """Simulate ImportError from _validate_file_path by patching at source."""
        from attune.hooks.scripts.format_on_save import main

        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "src/foo.py"}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                side_effect=ImportError("no module"),
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    def test_returns_early_when_validated_file_does_not_exist(self, tmp_path: Path) -> None:
        from attune.hooks.scripts.format_on_save import main

        nonexistent = tmp_path / "ghost.py"
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(nonexistent)}})
        # _validate_file_path is a lazy import inside main(); patch at source.
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=nonexistent,
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        mock_run.assert_not_called()

    # ------------------------------------------------------------------
    # Happy path — formatters run
    # ------------------------------------------------------------------

    def test_runs_black_and_ruff_for_write_py_file(self, tmp_path: Path) -> None:
        from attune.hooks.scripts.format_on_save import main

        target = tmp_path / "foo.py"
        target.write_text("x=1\n", encoding="utf-8")

        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=target,
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        assert mock_run.call_count == 2
        first_call_cmd = mock_run.call_args_list[0][0][0]
        second_call_cmd = mock_run.call_args_list[1][0][0]
        assert first_call_cmd[0] == "black"
        assert second_call_cmd[0] == "ruff"

    def test_runs_black_and_ruff_for_edit_py_file(self, tmp_path: Path) -> None:
        from attune.hooks.scripts.format_on_save import main

        target = tmp_path / "bar.py"
        target.write_text("y = 2\n", encoding="utf-8")

        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(target)}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=target,
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        assert mock_run.call_count == 2

    def test_black_called_with_correct_flags(self, tmp_path: Path) -> None:
        from attune.hooks.scripts.format_on_save import main

        target = tmp_path / "mod.py"
        target.write_text("pass\n", encoding="utf-8")

        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=target,
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        black_call = mock_run.call_args_list[0][0][0]
        assert black_call == [
            "black",
            "--quiet",
            "--line-length=100",
            str(target),
        ]

    def test_ruff_called_with_correct_flags(self, tmp_path: Path) -> None:
        from attune.hooks.scripts.format_on_save import main

        target = tmp_path / "mod.py"
        target.write_text("pass\n", encoding="utf-8")

        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(target)}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=target,
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        ruff_call = mock_run.call_args_list[1][0][0]
        assert ruff_call == ["ruff", "check", "--fix", "--quiet", str(target)]

    def test_uses_path_key_when_file_path_absent(self, tmp_path: Path) -> None:
        from attune.hooks.scripts.format_on_save import main

        target = tmp_path / "via_path.py"
        target.write_text("z = 3\n", encoding="utf-8")

        payload = json.dumps({"tool_name": "Write", "tool_input": {"path": str(target)}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=target,
            ),
            patch("subprocess.run") as mock_run,
        ):
            main()

        assert mock_run.call_count == 2

    def test_main_always_returns_none(self, tmp_path: Path) -> None:
        """main() has no return statement — must return None."""
        from attune.hooks.scripts.format_on_save import main

        payload = json.dumps({"tool_name": "Read", "tool_input": {}})
        with patch("sys.stdin", io.StringIO(payload)):
            result = main()

        assert result is None

    def test_validate_file_path_called_with_extracted_path(self, tmp_path: Path) -> None:
        from attune.hooks.scripts.format_on_save import main

        target = tmp_path / "check.py"
        target.write_text("1\n", encoding="utf-8")
        path_str = str(target)

        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": path_str}})
        with (
            patch("sys.stdin", io.StringIO(payload)),
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=target,
            ) as mock_validate,
            patch("subprocess.run"),
        ):
            main()

        mock_validate.assert_called_once_with(path_str)


class TestHasSessionWorkGitFailure:
    """Non-zero git exit is a 'can't check' case, not 'no work'."""

    def test_returns_true_when_git_exits_nonzero(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 128  # e.g. not a git repository
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            from attune.hooks.scripts.lessons_reminder import has_session_work

            assert has_session_work() is True
