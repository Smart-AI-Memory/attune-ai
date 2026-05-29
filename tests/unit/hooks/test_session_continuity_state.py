"""Tests for plugin/hooks/_state.py — session-continuity helpers.

Covers ``discover_specs``, ``git_state``, ``session_sentinel_path``,
and ``prune_stale_sentinels``. The hook scripts are loaded via
``importlib.util.spec_from_file_location`` to match the existing
plugin-hook test convention.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_state_module():
    """Load _state.py fresh — avoids cross-test sys.path leakage."""
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if "_state" in sys.modules:
        return sys.modules["_state"]
    spec = importlib.util.spec_from_file_location("_state", _HOOKS_DIR / "_state.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_state"] = module  # dataclasses-friendly registration
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def state_mod():
    return _load_state_module()


def _write_spec(
    spec_dir: Path,
    *,
    requirements_status: str | None = "approved",
    design_status: str | None = None,
    tasks_status: str | None = None,
) -> None:
    """Helper — populate a spec directory with phase files."""
    spec_dir.mkdir(parents=True, exist_ok=True)
    if requirements_status is not None:
        (spec_dir / "requirements.md").write_text(
            f"# Requirements\n\n**Status**: {requirements_status}\n",
            encoding="utf-8",
        )
    if design_status is not None:
        (spec_dir / "design.md").write_text(
            f"# Design\n\n**Status**: {design_status}\n",
            encoding="utf-8",
        )
    if tasks_status is not None:
        (spec_dir / "tasks.md").write_text(
            f"# Tasks\n\n**Status**: {tasks_status}\n",
            encoding="utf-8",
        )


# ── discover_specs ───────────────────────────────────────────


class TestDiscoverSpecs:
    def test_empty_root_returns_empty(self, tmp_path: Path, state_mod) -> None:
        assert state_mod.discover_specs([tmp_path]) == []

    def test_missing_specs_dir_tolerated(self, tmp_path: Path, state_mod) -> None:
        # No `specs/` dir exists; should still succeed.
        (tmp_path / "src").mkdir()
        assert state_mod.discover_specs([tmp_path]) == []

    def test_single_in_flight_spec(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "feat-x"
        _write_spec(spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        info = result[0]
        assert info.slug == "feat-x"
        assert info.phase == "requirements"
        assert info.status == "approved"
        assert info.layer == "workspace"

    def test_completed_tasks_excluded(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "done-feat"
        _write_spec(spec, tasks_status="complete")
        assert state_mod.discover_specs([tmp_path]) == []

    def test_tasks_phase_takes_priority_over_design(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "feat-y"
        _write_spec(
            spec,
            requirements_status="approved",
            design_status="approved",
            tasks_status="approved",
        )
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].phase == "tasks"
        assert result[0].status == "approved"

    def test_most_recent_first(self, tmp_path: Path, state_mod) -> None:
        older = tmp_path / "specs" / "older"
        newer = tmp_path / "specs" / "newer"
        _write_spec(older, requirements_status="approved")
        # Force older to have an mtime well in the past.
        old_t = time.time() - 3600
        os.utime(older / "requirements.md", (old_t, old_t))
        _write_spec(newer, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        slugs = [s.slug for s in result]
        assert slugs == ["newer", "older"]

    def test_malformed_status_line(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "feat-malformed"
        spec.mkdir(parents=True)
        # No Status: line at all
        (spec / "requirements.md").write_text("# Requirements\nno status here\n")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].status == ""

    def test_layer_specs_picked_up(self, tmp_path: Path, state_mod) -> None:
        layer_spec = tmp_path / "attune-rag" / "specs" / "rag-feat"
        _write_spec(layer_spec, requirements_status="approved")
        workspace_spec = tmp_path / "specs" / "ws-feat"
        _write_spec(workspace_spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        layers = {s.slug: s.layer for s in result}
        assert layers["ws-feat"] == "workspace"
        assert layers["rag-feat"] == "attune-rag"

    def test_skips_non_directory_entries(self, tmp_path: Path, state_mod) -> None:
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "README.md").write_text("not a spec dir")
        assert state_mod.discover_specs([tmp_path]) == []

    def test_docs_specs_at_root_is_workspace(self, tmp_path: Path, state_mod) -> None:
        # attune-rag/author/help keep specs under docs/specs/, not specs/.
        spec = tmp_path / "docs" / "specs" / "rag-feat"
        _write_spec(spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].slug == "rag-feat"
        assert result[0].layer == "workspace"

    def test_docs_specs_under_layer(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "attune-author" / "docs" / "specs" / "author-feat"
        _write_spec(spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].slug == "author-feat"
        assert result[0].layer == "attune-author"

    def test_both_conventions_coexist_without_dup(self, tmp_path: Path, state_mod) -> None:
        # A repo using specs/ and one using docs/specs/ side by side; no
        # double-counting, each attributed to the right layer.
        _write_spec(tmp_path / "specs" / "ws-feat", requirements_status="approved")
        _write_spec(
            tmp_path / "attune-rag" / "docs" / "specs" / "rag-feat",
            requirements_status="approved",
        )
        result = state_mod.discover_specs([tmp_path])
        layers = {s.slug: s.layer for s in result}
        assert layers == {"ws-feat": "workspace", "rag-feat": "attune-rag"}


# ── git_state ────────────────────────────────────────────────


class TestGitState:
    def test_non_git_dir_returns_empty(self, tmp_path: Path, state_mod) -> None:
        result = state_mod.git_state(tmp_path)
        assert result.branch == ""
        assert result.last_sha == ""
        assert result.last_subject == ""
        assert result.uncommitted == ()

    def test_clean_repo(self, tmp_path: Path, state_mod) -> None:
        _init_repo(tmp_path)
        _commit(tmp_path, "README.md", "hello\n", "feat: initial")
        result = state_mod.git_state(tmp_path)
        assert result.branch  # whatever the local default branch is
        assert len(result.last_sha) >= 7
        assert result.last_subject == "feat: initial"
        assert result.uncommitted == ()

    def test_dirty_repo_lists_uncommitted(self, tmp_path: Path, state_mod) -> None:
        _init_repo(tmp_path)
        _commit(tmp_path, "README.md", "hello\n", "feat: initial")
        (tmp_path / "new.txt").write_text("untracked\n")
        (tmp_path / "README.md").write_text("modified\n")
        result = state_mod.git_state(tmp_path)
        assert "new.txt" in result.uncommitted
        assert "README.md" in result.uncommitted


# ── session_sentinel_path ────────────────────────────────────


class TestSessionSentinelPath:
    def test_uses_override_dir(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        path = state_mod.session_sentinel_path("abc123")
        assert path == tmp_path / ".compact-warned-abc123"

    def test_falls_back_to_home_attune(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ATTUNE_AI_SENTINEL_DIR", raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        path = state_mod.session_sentinel_path("xyz")
        assert path == tmp_path / ".attune" / ".compact-warned-xyz"

    def test_sanitizes_session_id(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        path = state_mod.session_sentinel_path("../escape/attempt")
        assert path.parent == tmp_path
        assert ".." not in path.name

    def test_unknown_session_id(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        path = state_mod.session_sentinel_path(None)
        assert path.name == ".compact-warned-unknown"


# ── prune_stale_sentinels ────────────────────────────────────


class TestPruneStaleSentinels:
    def test_no_dir_returns_zero(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "absent"))
        assert state_mod.prune_stale_sentinels() == 0

    def test_removes_old_sentinels_keeps_fresh(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        old = tmp_path / ".compact-warned-old"
        fresh = tmp_path / ".compact-warned-fresh"
        unrelated = tmp_path / "other.txt"
        old.write_text("0.71")
        fresh.write_text("0.72")
        unrelated.write_text("hi")
        old_mtime = time.time() - 30 * 24 * 3600  # 30 days ago
        os.utime(old, (old_mtime, old_mtime))
        removed = state_mod.prune_stale_sentinels()
        assert removed == 1
        assert not old.exists()
        assert fresh.exists()
        assert unrelated.exists()  # untouched


# ── workspace_roots ──────────────────────────────────────────


class TestWorkspaceRoots:
    def test_override_takes_precedence(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Use os.pathsep so this test is portable: ":" on POSIX, ";" on
        # Windows. Hardcoding ":" caused Windows to split on the drive
        # letter ("C:") and shred the path.
        monkeypatch.setenv(
            "ATTUNE_AI_WORKSPACE_ROOTS",
            os.pathsep.join([str(tmp_path / "a"), str(tmp_path / "b")]),
        )
        roots = state_mod.workspace_roots(cwd=tmp_path)
        assert roots == [tmp_path / "a", tmp_path / "b"]

    def test_default_uses_cwd(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ATTUNE_AI_WORKSPACE_ROOTS", raising=False)
        # Make ~/attune absent so we get a clean single-entry result.
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "fake-home"))
        roots = state_mod.workspace_roots(cwd=tmp_path)
        assert roots[0] == tmp_path.resolve()


# ── fixtures ─────────────────────────────────────────────────


def _init_repo(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "commit.gpgsign", "false"],
        check=True,
    )


def _commit(path: Path, filename: str, content: str, message: str) -> None:
    (path / filename).write_text(content)
    subprocess.run(["git", "-C", str(path), "add", filename], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", message],
        check=True,
        capture_output=True,
    )
