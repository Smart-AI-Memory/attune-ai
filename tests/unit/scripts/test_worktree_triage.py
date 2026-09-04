"""Unit tests for scripts/worktree_triage.py.

Pins the verdict matrix, the "(empty) is never identical" rule for
patch-ids, squash-merge verification against a REAL temp repository, and
that the emitted removal script carries only REMOVE verdicts.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "worktree_triage.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_worktree_triage", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_worktree_triage"] = m  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(m)
    return m


def _git(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "HOME": str(repo),
    }
    r = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return r.stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    """main with one file; a 2-commit feature branch; a squash merge of it on main."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "a.txt").write_text("base\n")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-q", "-m", "base")
    _git(r, "checkout", "-q", "-b", "feat/two")
    (r / "b.txt").write_text("one\n")
    _git(r, "add", "b.txt")
    _git(r, "commit", "-q", "-m", "one")
    (r / "b.txt").write_text("one\ntwo\n")
    _git(r, "add", "b.txt")
    _git(r, "commit", "-q", "-m", "two")
    _git(r, "checkout", "-q", "main")
    _git(r, "merge", "--squash", "-q", "feat/two")
    _git(r, "commit", "-q", "-m", "feat: two (squash)")
    squash = _git(r, "rev-parse", "HEAD")
    _git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    return r, squash


class TestClassify:
    def _row(self, mod, **kw):
        base = {"path": "/wt", "branch": "b", "head": "abc"}
        base.update(kw)
        return mod.Row(**base)

    def test_matrix(self, mod):
        R = lambda **kw: mod.classify(self._row(mod, **kw))  # noqa: E731
        assert R(is_self=True).startswith("KEEP (this session)")
        assert R(exists=False).startswith("PRUNE-ENTRY")
        assert R(has_open_pr=True).startswith("KEEP (open PR)")
        assert R(dirty=["x"]).startswith("HOLD")
        assert R(ahead=0).startswith("REMOVE (nothing ahead)")
        assert R(ahead=1, cherry_plus=0).startswith("REMOVE (all patches")
        assert R(ahead=2, cherry_plus=2, squash_pr=42) == "REMOVE (squash-verified #42)"
        assert R(ahead=2, cherry_plus=2).startswith("REVIEW")

    def test_self_beats_everything(self, mod):
        assert mod.classify(self._row(mod, is_self=True, dirty=["x"], ahead=5)).startswith(
            "KEEP (this session)"
        )


class TestPatchId:
    def test_empty_diff_is_never_identical(self, mod):
        assert mod.patch_id("") == "(empty)"
        assert mod.patch_id("   \n") == "(empty)"

    def test_same_diff_same_id(self, mod, repo):
        r, squash = repo
        d = subprocess.run(
            ["git", "-C", str(r), "show", squash, "--format="], capture_output=True, text=True
        ).stdout
        assert mod.patch_id(d) == mod.patch_id(d) != "(empty)"


class TestSquashVerified:
    def test_squash_merged_branch_is_verified(self, mod, repo):
        r, squash = repo
        # cherry sees both feature commits as '+' (patch-ids differ per commit)...
        ch = subprocess.run(
            ["git", "-C", str(r), "cherry", "origin/main", "feat/two"],
            capture_output=True,
            text=True,
        ).stdout
        assert ch.count("+") == 2
        # ...but the whole-branch patch-id equals the squash commit's.
        assert mod.squash_verified(r, "feat/two", [(7, squash)]) == 7

    def test_unrelated_merge_commit_does_not_verify(self, mod, repo):
        r, _ = repo
        base = _git(r, "rev-list", "--max-parents=0", "HEAD")
        assert mod.squash_verified(r, "feat/two", [(9, base)]) is None

    def test_branch_rows_end_to_end(self, mod, repo):
        r, squash = repo
        rows = mod.branch_rows(r, {"feat/two": [(7, squash)]}, set())
        by = {row.branch: row for row in rows}
        assert by["feat/two"].verdict == "REMOVE (squash-verified #7)"


class TestRenderScript:
    def test_only_remove_rows_are_emitted(self, mod):
        wt = [
            mod.Row(path="/w/keep", branch="k", head="1", verdict="HOLD (dirty 2)"),
            mod.Row(path="/w/go", branch="g", head="2", verdict="REMOVE (all patches on main)"),
        ]
        br = [
            mod.Row(path="", branch="stale", head="3", verdict="REMOVE (squash-verified #5)"),
            mod.Row(path="", branch="unsure", head="4", verdict="REVIEW (+3 unverified)"),
        ]
        text = mod.render_script(Path("/repo"), wt, br)
        assert 'worktree remove "/w/go"' in text and "/w/keep" not in text
        assert 'branch -D "g"' in text and 'branch -D "stale"' in text and "unsure" not in text
        assert "worktree prune" in text
