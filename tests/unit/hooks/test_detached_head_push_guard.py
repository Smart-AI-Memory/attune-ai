"""Tests for the detached-HEAD push guard PreToolUse hook.

Covers the push classification, the block decision against a REAL git
repository in both states, the explicit-refspec and tag carve-outs, and
the fail-open paths.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "src" / "attune" / "hooks" / "scripts" / "detached_head_push_guard.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_detached_head_push_guard", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_detached_head_push_guard"] = m
    spec.loader.exec_module(m)
    return m


def _ctx(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _git(repo: Path, *args: str) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "HOME": str(repo),
    }
    subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
        env=env,
        timeout=30,
    )


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "commit", "--allow-empty", "-q", "-m", "one")
    _git(r, "commit", "--allow-empty", "-q", "-m", "two")
    monkeypatch.chdir(r)
    monkeypatch.delenv("ATTUNE_ALLOW_DETACHED_PUSH", raising=False)
    return r


class TestClassification:
    @pytest.mark.parametrize(
        "cmd",
        [
            "git push",
            "git push origin main",
            "git push -u origin feat/x",
            "git push --force-with-lease origin feat/x",
        ],
    )
    def test_branch_pushes(self, mod, cmd):
        assert mod.is_branch_push(mod._load_git_invocations()(cmd)[0]) is True

    @pytest.mark.parametrize(
        "cmd",
        [
            "git push origin HEAD:feat/x",
            "git push --tags",
            "git push origin refs/tags/v1.0.0",
            "git status",
            "git pull",
        ],
    )
    def test_carve_outs_and_non_pushes(self, mod, cmd):
        invs = mod._load_git_invocations()(cmd)
        assert not any(mod.is_branch_push(a) for a in invs)

    def test_push_behind_a_harmless_command_is_still_seen(self, mod):
        invs = mod._load_git_invocations()("git status && git push origin main")
        assert any(mod.is_branch_push(a) for a in invs)


class TestDecision:
    def test_attached_head_allows(self, mod, repo):
        assert mod.detached_head(repo) is False
        assert mod.main(_ctx("git push origin main")) == 0

    def test_detached_head_blocks(self, mod, repo, capsys):
        _git(repo, "checkout", "-q", "--detach")
        assert mod.detached_head(repo) is True
        assert mod.main(_ctx("git push origin main")) == 2
        err = capsys.readouterr().err
        assert "HEAD is detached" in err and "checkout -B" in err

    def test_detached_head_allows_explicit_refspec(self, mod, repo):
        _git(repo, "checkout", "-q", "--detach")
        assert mod.main(_ctx("git push origin HEAD:main")) == 0

    def test_escape_hatch(self, mod, repo, monkeypatch):
        _git(repo, "checkout", "-q", "--detach")
        monkeypatch.setenv("ATTUNE_ALLOW_DETACHED_PUSH", "1")
        assert mod.main(_ctx("git push origin main")) == 0

    def test_non_bash_tool_is_ignored(self, mod, repo):
        _git(repo, "checkout", "-q", "--detach")
        assert mod.main({"tool_name": "Edit", "tool_input": {}}) == 0


class TestFailOpen:
    def test_outside_a_repo_allows(self, mod, tmp_path, monkeypatch):
        plain = tmp_path / "plain"
        plain.mkdir()
        monkeypatch.chdir(plain)
        assert mod.detached_head(plain) is None
        assert mod.main(_ctx("git push origin main")) == 0

    def test_unparseable_command_allows(self, mod, repo):
        _git(repo, "checkout", "-q", "--detach")
        assert mod.main(_ctx('git push "unbalanced')) == 0
