"""Tests for the dirty-switch guard PreToolUse hook.

Covers the pure command classification (which git invocations are
branch-changing or destructive), the block decision against a REAL git
repository, and the fail-open paths — a hook bug must never block work.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "src" / "attune" / "hooks" / "scripts" / "dirty_switch_guard.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_dirty_switch_guard", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_dirty_switch_guard"] = m
    spec.loader.exec_module(m)
    return m


def _ctx(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class TestBranchSwitchClassification:
    """Only branch-CHANGING checkouts count."""

    @pytest.mark.parametrize(
        "command",
        [
            "git checkout main",
            "git switch main",
            "git checkout claude/some-branch",
        ],
    )
    def test_plain_switches_are_branch_switches(self, mod, command):
        args = mod.git_invocations(command)[0]
        assert mod.is_branch_switch(args) is True

    @pytest.mark.parametrize(
        "command",
        [
            "git checkout -b new-branch",
            "git switch -c new-branch",
            "git checkout -B existing",
            # Carrying changes onto a NEW branch is the normal recovery.
        ],
    )
    def test_new_branch_creation_is_allowed(self, mod, command):
        args = mod.git_invocations(command)[0]
        assert mod.is_branch_switch(args) is False

    @pytest.mark.parametrize(
        "command",
        [
            "git checkout -- src/file.py",
            "git checkout main -- src/file.py",
        ],
    )
    def test_path_scoped_restore_is_not_a_switch(self, mod, command):
        args = mod.git_invocations(command)[0]
        assert mod.is_branch_switch(args) is False

    def test_explicit_force_is_allowed(self, mod):
        args = mod.git_invocations("git checkout --force main")[0]
        assert mod.is_branch_switch(args) is False

    def test_bare_checkout_changes_nothing(self, mod):
        args = mod.git_invocations("git checkout")[0]
        assert mod.is_branch_switch(args) is False

    def test_non_git_commands_yield_no_invocations(self, mod):
        assert mod.git_invocations("echo git checkout main") == []
        assert mod.git_invocations("ls -la") == []


class TestHardResetClassification:
    def test_hard_reset_detected(self, mod):
        args = mod.git_invocations("git reset --hard HEAD~1")[0]
        assert mod.is_hard_reset(args) is True

    def test_soft_and_mixed_resets_are_not_destructive(self, mod):
        assert mod.is_hard_reset(mod.git_invocations("git reset --soft HEAD~1")[0]) is False
        assert mod.is_hard_reset(mod.git_invocations("git reset HEAD~1")[0]) is False


class TestChainedCommands:
    """A dangerous invocation must not hide behind a harmless one."""

    def test_switch_after_a_harmless_command_is_still_seen(self, mod):
        invocations = mod.git_invocations("git status && git checkout main")
        assert any(mod.is_branch_switch(a) for a in invocations)

    def test_reset_after_a_semicolon_is_still_seen(self, mod):
        invocations = mod.git_invocations("echo hi; git reset --hard HEAD~1")
        assert any(mod.is_hard_reset(a) for a in invocations)

    def test_unparseable_command_degrades_to_no_invocations(self, mod):
        assert mod.git_invocations('git checkout "unbalanced') == []


class TestAgainstRealRepository:
    """The decision is only useful if it reads real git state."""

    @pytest.fixture
    def repo(self, tmp_path, monkeypatch):
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.invalid"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "f.txt").write_text("one")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "--no-gpg-sign", "-m", "first"], cwd=tmp_path, check=True
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv(mod_allow_env(), raising=False)
        return tmp_path

    def test_clean_tree_allows_the_switch(self, mod, repo):
        assert mod.main(_ctx("git checkout main")) == 0

    def test_dirty_tree_blocks_the_switch(self, mod, repo):
        (repo / "f.txt").write_text("uncommitted edit")
        assert mod.main(_ctx("git checkout main")) == 2

    def test_dirty_tree_blocks_a_hard_reset(self, mod, repo):
        (repo / "new.txt").write_text("unsaved work")
        assert mod.main(_ctx("git reset --hard HEAD~1")) == 2

    def test_dirty_tree_still_allows_new_branch_creation(self, mod, repo):
        (repo / "f.txt").write_text("uncommitted edit")
        assert mod.main(_ctx("git checkout -b rescue")) == 0

    def test_dirty_tree_allows_unrelated_commands(self, mod, repo):
        (repo / "f.txt").write_text("uncommitted edit")
        assert mod.main(_ctx("git status")) == 0
        assert mod.main(_ctx("pytest tests")) == 0

    def test_escape_hatch_allows_a_dirty_switch(self, mod, repo, monkeypatch):
        (repo / "f.txt").write_text("uncommitted edit")
        monkeypatch.setenv(mod_allow_env(), "1")
        assert mod.main(_ctx("git checkout main")) == 0

    def test_block_message_names_the_files(self, mod, repo):
        (repo / "f.txt").write_text("uncommitted edit")
        paths = mod.dirty_paths()
        message = mod.block_message("switch", paths)
        assert "f.txt" in message
        assert "follow you onto the other branch" in message

    def test_reset_message_says_destroyed(self, mod, repo):
        message = mod.block_message("reset", ["a.py"])
        assert "DESTROYED" in message


class TestFailsOpen:
    """A guard that crashes must never block real work."""

    def test_non_bash_tools_pass_through(self, mod):
        assert mod.main({"tool_name": "Edit", "tool_input": {"file_path": "x"}}) == 0

    def test_empty_command_passes_through(self, mod):
        assert mod.main(_ctx("")) == 0

    def test_outside_a_git_tree_degrades_to_allow(self, mod, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # not a repo
        monkeypatch.delenv(mod_allow_env(), raising=False)
        assert mod.main(_ctx("git checkout main")) == 0

    def test_dirty_paths_returns_none_outside_a_repo(self, mod, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert mod.dirty_paths() is None


def mod_allow_env() -> str:
    """The escape-hatch variable name, kept in one place."""
    return "ATTUNE_ALLOW_DIRTY_SWITCH"
