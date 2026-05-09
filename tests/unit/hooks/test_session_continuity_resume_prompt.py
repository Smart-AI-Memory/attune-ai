"""Tests for plugin/hooks/_resume_prompt.py — resume-prompt format.

Pure formatting tests: feed dataclasses in, assert the rendered
markdown blockquote matches expectations. Covers the active-spec
case, the generic fallback, current-task derivation, and the
truncation/4kB cap behaviors.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def state_mod():
    return _load_module("_state")


@pytest.fixture(scope="module")
def resume_mod(state_mod):  # noqa: ARG001 — load order matters
    return _load_module("_resume_prompt")


def _make_spec(state_mod, tmp_path: Path, *, tasks_md: str | None = None) -> object:
    spec_path = tmp_path / "specs" / "feat-x"
    spec_path.mkdir(parents=True)
    if tasks_md is not None:
        (spec_path / "tasks.md").write_text(tasks_md, encoding="utf-8")
    return state_mod.SpecInfo(
        slug="feat-x",
        path=spec_path,
        layer="workspace",
        phase="tasks",
        status="approved",
        mtime=0.0,
    )


def _make_git(state_mod, *, branch="feat/x", uncommitted=()) -> object:
    return state_mod.GitState(
        branch=branch,
        last_sha="abc1234",
        last_subject="feat: do the thing",
        uncommitted=tuple(uncommitted),
    )


# ── full resume prompt with active spec ──────────────────────


class TestResumePromptWithSpec:
    def test_full_format(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec = _make_spec(state_mod, tmp_path)
        git = _make_git(state_mod)
        out = resume_mod.build_resume_prompt(spec, git)
        assert "**Resume prompt for a fresh session:**" in out
        assert "> Resume work in worktree `~/attune` on branch `feat/x`." in out
        assert "> Last commit: `abc1234 feat: do the thing`." in out
        assert "specs/feat-x/" in out
        assert "Phase 3 (Tasks)" in out
        assert "Status: approved" in out

    def test_uncommitted_files_listed(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec = _make_spec(state_mod, tmp_path)
        git = _make_git(state_mod, uncommitted=("src/foo.py", "tests/test_foo.py"))
        out = resume_mod.build_resume_prompt(spec, git)
        assert ">   - src/foo.py" in out
        assert ">   - tests/test_foo.py" in out
        assert "> Uncommitted:" in out

    def test_uncommitted_truncated_at_20(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec = _make_spec(state_mod, tmp_path)
        many = tuple(f"file_{i}.py" for i in range(25))
        git = _make_git(state_mod, uncommitted=many)
        out = resume_mod.build_resume_prompt(spec, git)
        assert ">   - file_0.py" in out
        assert ">   - file_19.py" in out
        assert "+5 more" in out
        assert "file_20.py" not in out

    def test_workspace_path_override(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec = _make_spec(state_mod, tmp_path)
        git = _make_git(state_mod)
        out = resume_mod.build_resume_prompt(spec, git, workspace_path="~/projects/attune")
        assert "`~/projects/attune`" in out


# ── current-task derivation ─────────────────────────────────


class TestCurrentTask:
    def test_explicit_todo_summary_wins(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec = _make_spec(
            state_mod,
            tmp_path,
            tasks_md=(
                "# Tasks\n\n**Status**: approved\n\n"
                "| # | Task | Status | Notes |\n"
                "|---|------|--------|-------|\n"
                "| 1 | **first task** | completed | done |\n"
            ),
        )
        git = _make_git(state_mod)
        out = resume_mod.build_resume_prompt(spec, git, todo_summary="hand-typed live task")
        assert "Current task: hand-typed live task" in out
        assert "first task" not in out

    def test_falls_back_to_completed_row(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec = _make_spec(
            state_mod,
            tmp_path,
            tasks_md=(
                "# Tasks\n\n**Status**: approved\n\n"
                "| # | Task | Status | Notes |\n"
                "|---|------|--------|-------|\n"
                "| 1 | **early task** | completed | n/a |\n"
                "| 2 | **second task** | completed | most-recent |\n"
                "| 3 | next task | pending | upcoming |\n"
            ),
        )
        git = _make_git(state_mod)
        out = resume_mod.build_resume_prompt(spec, git)
        assert "Current task: second task" in out

    def test_no_tasks_md_no_current_task_line(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec_path = tmp_path / "specs" / "feat-x"
        spec_path.mkdir(parents=True)
        spec = state_mod.SpecInfo(
            slug="feat-x",
            path=spec_path,
            layer="workspace",
            phase="design",
            status="approved",
            mtime=0.0,
        )
        git = _make_git(state_mod)
        out = resume_mod.build_resume_prompt(spec, git)
        assert "Current task" not in out


# ── generic fallback ────────────────────────────────────────


class TestGenericFallback:
    def test_no_spec_emits_fallback(self, state_mod, resume_mod) -> None:
        git = _make_git(state_mod)
        out = resume_mod.build_resume_prompt(None, git)
        assert "No active spec" in out
        assert "feat/x" in out

    def test_fallback_with_todo_summary(self, state_mod, resume_mod) -> None:
        git = _make_git(state_mod)
        out = resume_mod.build_resume_prompt(None, git, todo_summary="WIP item")
        assert "Current task: WIP item" in out

    def test_no_branch_no_commit(self, state_mod, resume_mod) -> None:
        git = state_mod.GitState(branch="", last_sha="", last_subject="", uncommitted=())
        out = resume_mod.build_resume_prompt(None, git)
        assert "branch `<unknown>`" in out
        assert "Last commit:" not in out


# ── 4 kB hard cap ───────────────────────────────────────────


class TestSizeCap:
    def test_truncates_at_4kb(self, state_mod, resume_mod, tmp_path: Path) -> None:
        spec = _make_spec(state_mod, tmp_path)
        # Inflate uncommitted with absurdly long paths to exceed 4 kB.
        many = tuple(f"path/{'x' * 500}/{i}.py" for i in range(25))
        git = _make_git(state_mod, uncommitted=many)
        out = resume_mod.build_resume_prompt(spec, git)
        assert len(out.encode("utf-8")) <= 4096
        assert "(truncated)" in out
