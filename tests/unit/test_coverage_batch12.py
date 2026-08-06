# Licensed under the Apache License, Version 2.0
# Copyright 2025 Smart AI Memory, LLC
"""Tests for hooks scripts — Batch 12.

Covers: hooks/scripts/lessons_reminder, hooks/scripts/format_on_save,
hooks/scripts/pre_compact, security/path_validation.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

# === Module: hooks/scripts/lessons_reminder.py ===


class TestLessonsReminder:
    def test_already_reminded_false_when_no_sentinel(self, tmp_path):
        from attune.hooks.scripts.lessons_reminder import already_reminded

        sentinel = tmp_path / "lessons_reminded"
        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            assert already_reminded() is False

    def test_already_reminded_true_when_recent_sentinel(self, tmp_path):
        from attune.hooks.scripts.lessons_reminder import already_reminded

        sentinel = tmp_path / "lessons_reminded"
        sentinel.touch()
        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            assert already_reminded() is True

    def test_already_reminded_false_when_old_sentinel(self, tmp_path):
        from attune.hooks.scripts.lessons_reminder import already_reminded

        sentinel = tmp_path / "lessons_reminded"
        sentinel.touch()
        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            with patch("attune.hooks.scripts.lessons_reminder.SENTINEL_TTL", 0):
                # TTL=0 means any age is "too old"
                # advance time artificially by patching time.time
                with patch("attune.hooks.scripts.lessons_reminder.time") as mock_time:
                    mock_time.time.return_value = time.time() + 7200
                    assert already_reminded() is False

    def test_mark_reminded_creates_sentinel(self, tmp_path):
        from attune.hooks.scripts.lessons_reminder import mark_reminded

        sentinel = tmp_path / "subdir" / "lessons_reminded"
        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            mark_reminded()
        assert sentinel.exists()

    def test_has_session_work_true_on_commits(self):
        from attune.hooks.scripts.lessons_reminder import has_session_work

        mock_result = MagicMock()
        mock_result.stdout = "abc1234 some commit\n"
        with patch("subprocess.run", return_value=mock_result):
            assert has_session_work() is True

    def test_has_session_work_false_on_no_commits(self):
        from attune.hooks.scripts.lessons_reminder import has_session_work

        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            assert has_session_work() is False

    def test_has_session_work_true_on_exception(self):
        from attune.hooks.scripts.lessons_reminder import has_session_work

        with patch("subprocess.run", side_effect=Exception("no git")):
            assert has_session_work() is True

    def test_main_returns_zero_when_already_reminded(self, tmp_path):
        from attune.hooks.scripts.lessons_reminder import main

        with patch("attune.hooks.scripts.lessons_reminder.already_reminded", return_value=True):
            assert main() == 0

    def test_main_returns_zero_when_no_session_work(self, tmp_path):
        from attune.hooks.scripts.lessons_reminder import main

        with patch("attune.hooks.scripts.lessons_reminder.already_reminded", return_value=False):
            with patch(
                "attune.hooks.scripts.lessons_reminder.has_session_work", return_value=False
            ):
                assert main() == 0

    def test_main_returns_two_with_session_work(self, tmp_path, capsys):
        from attune.hooks.scripts.lessons_reminder import main

        sentinel = tmp_path / "lessons_reminded"
        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            with patch(
                "attune.hooks.scripts.lessons_reminder.already_reminded", return_value=False
            ):
                with patch(
                    "attune.hooks.scripts.lessons_reminder.has_session_work", return_value=True
                ):
                    result = main()
        assert result == 2

    def test_reminder_routes_lessons_through_outbox(self, tmp_path, capsys):
        """Drift guard for docs-outbox R2: the Stop reminder points at
        the outbox writer, never at direct lessons.md appends."""
        from attune.hooks.scripts.lessons_reminder import main

        sentinel = tmp_path / "lessons_reminded"
        with patch("attune.hooks.scripts.lessons_reminder.SENTINEL", sentinel):
            with patch(
                "attune.hooks.scripts.lessons_reminder.already_reminded", return_value=False
            ):
                with patch(
                    "attune.hooks.scripts.lessons_reminder.has_session_work", return_value=True
                ):
                    main()
        err = capsys.readouterr().err
        assert "attune.docs_outbox write" in err
        assert "do NOT append .claude/lessons.md directly" in err
        assert "merge now" in err  # decisions.md rulings keep the old flow


# === Module: hooks/scripts/format_on_save.py ===


class TestFormatOnSave:
    def test_get_file_path_from_file_path_key(self):
        from attune.hooks.scripts.format_on_save import _get_file_path

        data = {"tool_input": {"file_path": "/tmp/foo.py"}}
        assert _get_file_path(data) == "/tmp/foo.py"

    def test_get_file_path_from_path_key(self):
        from attune.hooks.scripts.format_on_save import _get_file_path

        data = {"tool_input": {"path": "/tmp/bar.py"}}
        assert _get_file_path(data) == "/tmp/bar.py"

    def test_get_file_path_none_when_missing(self):
        from attune.hooks.scripts.format_on_save import _get_file_path

        assert _get_file_path({"tool_input": {}}) is None
        assert _get_file_path({}) is None

    def test_is_python_file_true(self):
        from attune.hooks.scripts.format_on_save import _is_python_file

        assert _is_python_file("/some/path/foo.py") is True

    def test_is_python_file_false_for_non_py(self):
        from attune.hooks.scripts.format_on_save import _is_python_file

        assert _is_python_file("/some/path/foo.js") is False
        assert _is_python_file("/some/path/foo.md") is False
        assert _is_python_file("/some/path/foo") is False

    def test_run_formatter_calls_subprocess(self):
        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch("subprocess.run") as mock_run:
            _run_formatter(["black", "--quiet"], "/tmp/foo.py")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "black" in args
        assert "/tmp/foo.py" in args

    def test_run_formatter_ignores_timeout(self):
        import subprocess

        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("black", 10)):
            # Should not raise
            _run_formatter(["black"], "/tmp/foo.py")

    def test_run_formatter_ignores_file_not_found(self):
        from attune.hooks.scripts.format_on_save import _run_formatter

        with patch("subprocess.run", side_effect=FileNotFoundError("black not found")):
            _run_formatter(["black"], "/tmp/foo.py")

    def test_main_skips_non_write_edit(self):
        import io

        from attune.hooks.scripts.format_on_save import main

        payload = '{"tool_name": "Read", "tool_input": {"file_path": "/tmp/foo.py"}}'
        with patch("sys.stdin", io.StringIO(payload)):
            with patch("subprocess.run") as mock_run:
                main()
        mock_run.assert_not_called()

    def test_main_skips_non_python(self):
        import io

        from attune.hooks.scripts.format_on_save import main

        payload = '{"tool_name": "Write", "tool_input": {"file_path": "/tmp/foo.js"}}'
        with patch("sys.stdin", io.StringIO(payload)):
            with patch("subprocess.run") as mock_run:
                main()
        mock_run.assert_not_called()

    def test_main_empty_stdin_no_error(self):
        import io

        from attune.hooks.scripts.format_on_save import main

        with patch("sys.stdin", io.StringIO("")):
            main()  # Should not raise

    def test_main_invalid_json_no_error(self):
        import io

        from attune.hooks.scripts.format_on_save import main

        with patch("sys.stdin", io.StringIO("not-json")):
            main()  # Should not raise


# === Module: hooks/scripts/pre_compact.py ===


class TestPreCompact:
    def test_run_pre_compact_no_state_returns_failure(self):
        from attune.hooks.scripts.pre_compact import run_pre_compact

        result = run_pre_compact({})
        assert result["state_saved"] is False
        assert result["restoration_available"] is False

    def test_run_pre_compact_with_state_saves(self):
        from attune.hooks.scripts.pre_compact import run_pre_compact

        mock_state = MagicMock()
        mock_cm = MagicMock()
        mock_compact = MagicMock()
        mock_compact.trust_level = 0.8
        mock_compact.empathy_level = "guided"
        mock_compact.detected_patterns = []
        mock_compact.pending_handoff = None
        mock_cm.save_for_compaction.return_value = "/tmp/state.json"
        mock_cm.extract_compact_state.return_value = mock_compact

        result = run_pre_compact({"collaboration_state": mock_state, "context_manager": mock_cm})
        assert result["state_saved"] is True
        assert result["restoration_available"] is True
        assert result["trust_level"] == 0.8

    def test_run_pre_compact_exception_returns_failure(self):
        from attune.hooks.scripts.pre_compact import run_pre_compact

        mock_state = MagicMock()
        mock_cm = MagicMock()
        mock_cm.save_for_compaction.side_effect = RuntimeError("disk full")

        result = run_pre_compact({"collaboration_state": mock_state, "context_manager": mock_cm})
        assert result["state_saved"] is False
        assert "disk full" in result["error"]

    def test_run_pre_compact_sets_session_id(self):
        from attune.hooks.scripts.pre_compact import run_pre_compact

        mock_state = MagicMock()
        mock_cm = MagicMock()
        mock_compact = MagicMock()
        mock_compact.trust_level = 0.5
        mock_compact.empathy_level = "reactive"
        mock_compact.detected_patterns = []
        mock_compact.pending_handoff = None
        mock_cm.save_for_compaction.return_value = "/tmp/state.json"
        mock_cm.extract_compact_state.return_value = mock_compact

        run_pre_compact(
            {
                "collaboration_state": mock_state,
                "context_manager": mock_cm,
                "session_id": "sess-123",
                "current_phase": "testing",
            }
        )
        assert mock_cm.session_id == "sess-123"
        assert mock_cm.current_phase == "testing"

    def test_generate_compaction_summary_basic(self):
        from attune.hooks.scripts.pre_compact import generate_compaction_summary

        mock_state = MagicMock()
        mock_state.user_id = "user1"
        mock_state.trust_level = 0.75
        mock_state.current_level = "proactive"
        mock_state.interactions = ["a", "b", "c"]
        mock_state.detected_patterns = []
        mock_state.preferences = {}

        summary = generate_compaction_summary(mock_state)
        assert "user1" in summary
        assert "0.75" in summary
        assert "proactive" in summary

    def test_generate_compaction_summary_with_patterns(self):
        from attune.hooks.scripts.pre_compact import generate_compaction_summary

        mock_pattern = MagicMock()
        mock_pattern.trigger = "debug"
        mock_pattern.action = "add logs"
        mock_pattern.confidence = 0.9

        mock_state = MagicMock()
        mock_state.user_id = "user1"
        mock_state.trust_level = 0.5
        mock_state.current_level = "reactive"
        mock_state.interactions = []
        mock_state.detected_patterns = [mock_pattern]
        mock_state.preferences = {}

        summary = generate_compaction_summary(mock_state, include_patterns=True)
        assert "debug" in summary
        assert "add logs" in summary


# === Module: security/path_validation.py ===


class TestPathValidation:
    def test_validates_normal_path(self, tmp_path):
        from attune.security.path_validation import _validate_file_path

        target = tmp_path / "file.txt"
        result = _validate_file_path(str(target))
        assert result is not None

    def test_raises_for_empty_path(self):
        from attune.security.path_validation import _validate_file_path

        with pytest.raises(ValueError, match="non-empty"):
            _validate_file_path("")

    def test_raises_for_none_path(self):
        from attune.security.path_validation import _validate_file_path

        with pytest.raises((ValueError, TypeError)):
            _validate_file_path(None)  # type: ignore[arg-type]

    def test_raises_for_null_bytes(self):
        from attune.security.path_validation import _validate_file_path

        with pytest.raises(ValueError, match="null bytes"):
            _validate_file_path("/tmp/foo\x00bar")

    def test_raises_for_outside_allowed_dir(self, tmp_path):
        from attune.security.path_validation import _validate_file_path

        allowed = tmp_path / "workspace"
        allowed.mkdir()
        target = tmp_path / "other" / "file.txt"

        with pytest.raises(ValueError, match="outside allowed"):
            _validate_file_path(str(target), allowed_dir=str(allowed))

    def test_allowed_path_within_dir(self, tmp_path):
        from attune.security.path_validation import _validate_file_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        target = workspace / "file.txt"

        result = _validate_file_path(str(target), allowed_dir=str(workspace))
        assert result is not None

    def test_raises_for_etc_path(self):
        import sys

        from attune.security.path_validation import _validate_file_path

        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        with pytest.raises(ValueError, match="system directory"):
            _validate_file_path("/etc/passwd")

    def test_raises_for_proc_path(self):
        import sys

        from attune.security.path_validation import _validate_file_path

        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        with pytest.raises(ValueError, match="system directory"):
            _validate_file_path("/proc/cpuinfo")

    def test_returns_path_object(self, tmp_path):
        from pathlib import Path

        from attune.security.path_validation import _validate_file_path

        target = tmp_path / "test.txt"
        result = _validate_file_path(str(target))
        assert isinstance(result, Path)
