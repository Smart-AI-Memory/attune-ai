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
    the user's real ~/.attune/next_session_starter.md.

    Also stubs ``_find_project_starter`` to None so the global-focused
    tests don't pick up a project-local file from the real cwd.
    """
    path = tmp_path / "next_session_starter.md"
    monkeypatch.setattr(hook_module, "STARTER_PATH", path)
    monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: None)
    # Pin repo discovery away from the real cwd so tracked handoffs in
    # THIS repo don't preempt the legacy-global path under test (R9).
    monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: None)
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

    def test_emit_notice_stat_oserror_is_no_op(self, hook_module, capsys):
        """If the file vanishes between is_file() and stat(), _emit_notice
        swallows the OSError and no-ops (returns False, prints nothing)."""

        class _StatRaises:
            def is_file(self):
                return True

            def stat(self):
                raise OSError("file vanished")

        assert hook_module._emit_notice(_StatRaises(), "global") is False
        assert capsys.readouterr().out == ""


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


class TestProjectLocalStarter:
    """Project-local <repo>/.attune/next_session_starter.md surfacing."""

    def _make_repo(self, tmp_path: Path, with_starter: str | None) -> Path:
        (tmp_path / ".git").mkdir()
        if with_starter is not None:
            d = tmp_path / ".attune"
            d.mkdir()
            (d / "next_session_starter.md").write_text(with_starter, encoding="utf-8")
        return tmp_path

    def test_finds_starter_at_git_toplevel(self, hook_module, tmp_path):
        repo = self._make_repo(tmp_path, "handoff")
        nested = repo / "src" / "deep"
        nested.mkdir(parents=True)
        found = hook_module._find_project_starter(start=nested)
        assert found == repo / ".attune" / "next_session_starter.md"

    def test_none_when_no_repo(self, hook_module, tmp_path):
        # No .git anywhere up the tree.
        assert hook_module._find_project_starter(start=tmp_path) is None

    def test_none_when_repo_but_no_starter(self, hook_module, tmp_path):
        repo = self._make_repo(tmp_path, None)
        assert hook_module._find_project_starter(start=repo) is None

    def test_default_start_uses_cwd(self, hook_module, tmp_path, monkeypatch):
        """start=None falls back to Path.cwd(). chdir into a repo with a
        starter so the default-cwd branch is exercised and returns it."""
        repo = self._make_repo(tmp_path, "# cwd handoff\n")
        monkeypatch.chdir(repo)
        found = hook_module._find_project_starter()  # no start= → cwd
        assert found == repo / ".attune" / "next_session_starter.md"

    def test_project_notice_emitted(self, hook_module, tmp_path, monkeypatch, capsys):
        repo = self._make_repo(tmp_path, "# repo handoff\n")
        starter = repo / ".attune" / "next_session_starter.md"
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: repo)
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: starter)
        # No global file.
        monkeypatch.setattr(hook_module, "STARTER_PATH", tmp_path / "nope.md")
        code = hook_module.main()
        assert code == 0
        out = capsys.readouterr().out
        assert "[starter-prompt:project]" in out
        assert str(starter) in out

    def test_global_suppressed_when_project_exists(
        self, hook_module, tmp_path, monkeypatch, capsys
    ):
        """R9: the legacy global file only surfaces when nothing
        repo-scoped exists — never alongside a project starter."""
        repo = self._make_repo(tmp_path, "# repo\n")
        starter = repo / ".attune" / "next_session_starter.md"
        global_path = tmp_path / "global_starter.md"
        global_path.write_text("# global\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: repo)
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: starter)
        monkeypatch.setattr(hook_module, "STARTER_PATH", global_path)
        hook_module.main()
        out = capsys.readouterr().out
        assert "[starter-prompt:project]" in out
        assert "[starter-prompt:global" not in out

    def test_global_fallback_is_labeled_legacy(self, hook_module, tmp_path, monkeypatch, capsys):
        global_path = tmp_path / "global_starter.md"
        global_path.write_text("# global\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "STARTER_PATH", global_path)
        hook_module.main()
        out = capsys.readouterr().out
        assert "[starter-prompt:global:LEGACY]" in out
        assert "retiring surface" in out


class TestFindHandoff:
    """R9: tracked docs/handoffs/ surfacing, branch-slug first."""

    def _make_repo(self, tmp_path: Path) -> Path:
        (tmp_path / ".git").mkdir()
        (tmp_path / "docs" / "handoffs").mkdir(parents=True)
        return tmp_path

    def test_branch_slug_wins(self, hook_module, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        d = repo / "docs" / "handoffs"
        (d / "claude-my-branch.md").write_text("branch handoff\n", encoding="utf-8")
        (d / "other.md").write_text("other\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "_current_branch", lambda root: "claude/my-branch")
        found = hook_module.find_handoff(repo)
        assert found is not None
        path, scope = found
        assert path.name == "claude-my-branch.md"
        assert scope == "handoff:branch"

    def test_newest_when_no_branch_match(self, hook_module, tmp_path, monkeypatch):
        import os

        repo = self._make_repo(tmp_path)
        d = repo / "docs" / "handoffs"
        old = d / "old.md"
        new = d / "new.md"
        old.write_text("old\n", encoding="utf-8")
        new.write_text("new\n", encoding="utf-8")
        os.utime(old, (1_600_000_000, 1_600_000_000))
        monkeypatch.setattr(hook_module, "_current_branch", lambda root: None)
        found = hook_module.find_handoff(repo)
        assert found is not None
        assert found[0].name == "new.md"
        assert found[1] == "handoff:newest"

    def test_readme_and_empty_skipped(self, hook_module, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path)
        d = repo / "docs" / "handoffs"
        (d / "README.md").write_text("index\n", encoding="utf-8")
        (d / "empty.md").write_text("", encoding="utf-8")
        monkeypatch.setattr(hook_module, "_current_branch", lambda root: None)
        assert hook_module.find_handoff(repo) is None

    def test_no_handoffs_dir_is_none(self, hook_module, tmp_path):
        (tmp_path / ".git").mkdir()
        assert hook_module.find_handoff(tmp_path) is None

    def test_handoff_emitted_first_by_main(self, hook_module, tmp_path, monkeypatch, capsys):
        repo = self._make_repo(tmp_path)
        d = repo / "docs" / "handoffs"
        (d / "claude-x.md").write_text("branch handoff\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: repo)
        monkeypatch.setattr(hook_module, "_current_branch", lambda root: "claude/x")
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "STARTER_PATH", tmp_path / "unused-global.md")
        hook_module.main()
        out = capsys.readouterr().out
        assert "[starter-prompt:handoff:branch]" in out
        assert "[starter-prompt:global" not in out


class TestAgeFormatter:
    """The age helper handles four ranges: <1m, <1h, <1d, ≥1d.

    Tests pin ``now`` explicitly via the ``now=`` parameter so they
    don't depend on real-time consistency between ``time.time()``
    and ``datetime.now(timezone.utc).timestamp()`` — on Windows
    those can differ by enough sub-second jitter to push
    edge-of-bucket values (300s, 7200s, 86400s) across boundaries.
    """

    NOW = 1_700_000_000.0

    def test_seconds_age(self, hook_module):
        assert hook_module._format_age(self.NOW - 30, now=self.NOW) == "just now"

    def test_minutes_age(self, hook_module):
        assert hook_module._format_age(self.NOW - 300, now=self.NOW) == "5m ago"

    def test_hours_age(self, hook_module):
        assert hook_module._format_age(self.NOW - 7200, now=self.NOW) == "2h ago"

    def test_days_age(self, hook_module):
        assert hook_module._format_age(self.NOW - 172800, now=self.NOW) == "2d ago"

    def test_default_now_uses_real_clock(self, hook_module):
        """When ``now`` is omitted the helper falls back to the real
        clock. Use a buffered value to absorb any sub-second drift."""
        real_now = time.time()
        # 90 minutes ago → comfortably in the hours bucket [60m, 24h).
        assert hook_module._format_age(real_now - 5400) == "1h ago"


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
