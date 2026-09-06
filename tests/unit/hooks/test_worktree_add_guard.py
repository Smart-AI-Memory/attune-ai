"""Tests for the worktree-add guard PreToolUse hook (retro 2026-09-06, R8).

A session running inside ``.claude/worktrees/<slug>/`` must not spawn a
sibling worktree — worktree_path_guard would refuse every write into it.
Covers the command classification, the session-location check, the block
decision, the escape hatch, and the fail-open paths.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "src" / "attune" / "hooks" / "scripts" / "worktree_add_guard.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_worktree_add_guard", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_worktree_add_guard"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def metrics(mod, tmp_path, monkeypatch):
    log = tmp_path / "metrics.jsonl"
    monkeypatch.setattr(mod, "METRICS_LOG", log)
    monkeypatch.delenv(mod.ALLOW_ENV, raising=False)
    monkeypatch.delenv(mod.PROJECT_DIR_ENV, raising=False)
    return log


def _ctx(command: str, tool: str = "Bash") -> dict:
    return {"tool_name": tool, "tool_input": {"command": command}}


def _worktree(tmp_path: Path) -> Path:
    root = tmp_path / ".claude" / "worktrees" / "some-slug"
    root.mkdir(parents=True)
    return root


class TestClassification:
    @pytest.mark.parametrize(
        "command",
        [
            "git worktree add ../other -b feature",
            "git -C /repo worktree add /tmp/x main",
            "echo hi; git worktree add x",
            "cd /repo && git worktree add --detach x",
        ],
    )
    def test_worktree_add_forms(self, mod, command):
        assert any(mod.is_worktree_add(a) for a in mod.git_invocations(command))

    @pytest.mark.parametrize(
        "command",
        [
            "git worktree list",
            "git worktree remove ../other",
            "git worktree prune",
            "git add worktree.txt",
            "git status",
            "ls .claude/worktrees",
        ],
    )
    def test_other_commands_are_not(self, mod, command):
        assert not any(mod.is_worktree_add(a) for a in mod.git_invocations(command))


class TestSessionLocation:
    def test_inside_a_worktree_returns_its_root(self, mod):
        p = Path("/home/u/repo/.claude/worktrees/slug/src/pkg")
        assert mod.session_worktree_root(p) == Path("/home/u/repo/.claude/worktrees/slug")

    @pytest.mark.parametrize(
        "path",
        ["/home/u/repo", "/home/u/repo/.claude/worktrees", "/home/u/.claude/other/worktrees/x"],
    )
    def test_outside_returns_none(self, mod, path):
        assert mod.session_worktree_root(Path(path)) is None


class TestDecision:
    def test_blocks_from_inside_a_worktree(self, mod, metrics, tmp_path, monkeypatch, capsys):
        root = _worktree(tmp_path)
        monkeypatch.chdir(root)
        assert mod.main(_ctx("git worktree add ../other -b feature")) == 2
        err = capsys.readouterr().err
        assert "switch branches in place" in err.lower()
        assert str(root) in err
        record = json.loads(metrics.read_text().splitlines()[-1])
        assert record["enforcement"] == "worktree-add-guard" and record["outcome"] == "fired"

    def test_blocks_when_project_dir_env_is_a_worktree(self, mod, metrics, tmp_path, monkeypatch):
        root = _worktree(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv(mod.PROJECT_DIR_ENV, str(root))
        assert mod.main(_ctx("git worktree add x")) == 2

    def test_allows_from_the_main_checkout(self, mod, metrics, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert mod.main(_ctx("git worktree add .claude/worktrees/new -b feature")) == 0
        assert json.loads(metrics.read_text())["outcome"] == "allowed"

    def test_escape_hatch(self, mod, metrics, tmp_path, monkeypatch):
        monkeypatch.chdir(_worktree(tmp_path))
        monkeypatch.setenv(mod.ALLOW_ENV, "1")
        assert mod.main(_ctx("git worktree add x")) == 0

    @pytest.mark.parametrize(
        "ctx",
        [
            _ctx("git worktree add x", tool="Edit"),
            _ctx(""),
            _ctx("git worktree list"),
            _ctx("git checkout -b feature origin/main"),
            {"tool_name": "Bash"},
        ],
    )
    def test_everything_else_passes_silently(self, mod, metrics, tmp_path, monkeypatch, ctx):
        monkeypatch.chdir(_worktree(tmp_path))
        assert mod.main(ctx) == 0
        assert not metrics.exists()

    def test_metrics_failure_never_blocks_the_decision(self, mod, metrics, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "METRICS_LOG", tmp_path / "not-a-dir" / "x" / "m.jsonl")
        (tmp_path / "not-a-dir").write_text("file, not a directory")
        monkeypatch.chdir(_worktree(tmp_path))
        assert mod.main(_ctx("git worktree add x")) == 2


def test_registered_in_project_settings():
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    bash_groups = [g for g in settings["hooks"]["PreToolUse"] if g["matcher"] == "Bash"]
    commands = [h["command"] for g in bash_groups for h in g["hooks"]]
    assert any("worktree_add_guard.py" in c for c in commands)
