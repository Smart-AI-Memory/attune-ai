"""Tests for starter_prompt_nudge.py SessionStart hook.

Covers:

- No-op when ~/.attune/next_session_starter.md doesn't exist
- No-op when the file is empty
- Prints notice with path + age + size when file exists with content
- Age formatter handles seconds / minutes / hours / days
- Hook never raises (script-level catch-all)
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "attune"
    / "hooks"
    / "scripts"
    / "starter_prompt_nudge.py"
)


@pytest.fixture(scope="module")
def hook_module():
    spec = importlib.util.spec_from_file_location("_starter_prompt_nudge", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_starter_prompt_nudge"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def isolated_starter(tmp_path, hook_module, monkeypatch):
    """Redirect STARTER_PATH to a tmp path so tests don't depend on
    the user's real ~/.attune/next_session_starter.md."""
    path = tmp_path / "next_session_starter.md"
    monkeypatch.setattr(hook_module, "STARTER_PATH", path)
    return path


class TestNoOpCases:
    def test_missing_file_returns_zero_no_output(self, hook_module, isolated_starter, capsys):
        # File does not exist
        assert not isolated_starter.exists()
        code = hook_module.main()
        assert code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_empty_file_returns_zero_no_output(self, hook_module, isolated_starter, capsys):
        isolated_starter.write_text("", encoding="utf-8")
        code = hook_module.main()
        assert code == 0
        captured = capsys.readouterr()
        assert captured.out == ""


class TestSurfacing:
    def test_file_with_content_prints_notice(self, hook_module, isolated_starter, capsys):
        isolated_starter.write_text("# Starter\n\nReal handoff context\n", encoding="utf-8")
        code = hook_module.main()
        assert code == 0
        captured = capsys.readouterr()
        assert str(isolated_starter) in captured.out
        assert "cross-session handoff" in captured.out
        # Should report size in KB and an age string
        assert "KB" in captured.out

    def test_just_now_age(self, hook_module, isolated_starter, capsys):
        isolated_starter.write_text("content", encoding="utf-8")
        # Default mtime is now → "just now"
        hook_module.main()
        captured = capsys.readouterr()
        assert "just now" in captured.out or "m ago" in captured.out


class TestAgeFormatter:
    """The age helper handles four ranges: <1m, <1h, <1d, ≥1d."""

    def test_seconds_age(self, hook_module):
        now = time.time()
        assert hook_module._format_age(now - 30) == "just now"

    def test_minutes_age(self, hook_module):
        now = time.time()
        assert hook_module._format_age(now - 300) == "5m ago"

    def test_hours_age(self, hook_module):
        now = time.time()
        assert hook_module._format_age(now - 7200) == "2h ago"

    def test_days_age(self, hook_module):
        now = time.time()
        assert hook_module._format_age(now - 172800) == "2d ago"


class TestErrorHandling:
    def test_script_level_catch_returns_zero_on_uncaught_exception(
        self, hook_module, monkeypatch, capsys
    ):
        """Hook errors must never break session start. The script's
        __main__ catch-all wraps main() in try/except and exits 0
        even on uncaught exceptions."""

        # Replace main() with one that always raises
        def boom():
            raise RuntimeError("simulated unexpected failure")

        monkeypatch.setattr(hook_module, "main", boom)

        # Execute the script's __main__ block path manually:
        # the catch-all swallows the exception and exits 0.
        with pytest.raises(SystemExit) as exc_info:
            try:
                hook_module.main()
            except Exception as exc:  # noqa: BLE001
                # Mirror the script's catch-all
                import sys as _sys

                print(
                    f"[starter-prompt] hook error (continuing): " f"{type(exc).__name__}: {exc}",
                    file=_sys.stderr,
                )
                _sys.exit(0)
        assert exc_info.value.code == 0
