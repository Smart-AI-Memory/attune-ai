"""Solution-materializer tests (round-table V2-P3).

Real git repos and worktrees in tmp — no mocked git. Security tests
for the path validator are REQUIRED (critical rules: file-op code
ships security tests). TAC-4 receipts: a failing candidate carries
its receipts; it is never silently dropped or laundered green.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from attune.roundtable.solutions import (
    Candidate,
    ProposalError,
    diff_against_base,
    discard,
    materialize,
    parse_proposal,
    validate,
)


@pytest.fixture
def repo(tmp_path):
    """A tiny real git repo with one committed file."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("config", "commit.gpgsign", "false")
    (repo / "hello.py").write_text('GREETING = "hello"\n')
    git("add", "hello.py")
    git("commit", "-q", "-m", "seed")
    return repo


def _block(path: str, body: str) -> str:
    return f"--- file: {path}\n```\n{body}\n```"


class TestPathSecurity:
    @pytest.mark.parametrize(
        "bad",
        [
            "/etc/passwd",
            "../outside.py",
            "a/../../outside.py",
            ".git/hooks/pre-commit",
            "~/x.py",
            "C:evil.py",
        ],
    )
    def test_dangerous_paths_rejected(self, bad: str) -> None:
        with pytest.raises(ProposalError):
            parse_proposal(_block(bad, "x = 1"))

    def test_diff_with_traversal_target_rejected(self, repo, tmp_path) -> None:
        diff = "--- a/../evil.py\n+++ b/../evil.py\n@@ -0,0 +1 @@\n+x\n"
        with pytest.raises(ProposalError):
            materialize(diff, repo, scratch_root=tmp_path / "scratch")
        assert (
            not list((tmp_path / "scratch").glob("*")) if (tmp_path / "scratch").exists() else True
        )

    def test_safe_relative_path_accepted(self) -> None:
        files = parse_proposal(_block("pkg/mod.py", "x = 1"))
        assert files == {"pkg/mod.py": "x = 1"}


class TestMaterialize:
    def test_file_block_lands_in_isolated_worktree(self, repo, tmp_path) -> None:
        cand = materialize(
            _block("pkg/new.py", "VALUE = 42"), repo, scratch_root=tmp_path / "scratch"
        )
        try:
            assert cand.files == ["pkg/new.py"]
            assert (cand.worktree / "pkg" / "new.py").read_text() == "VALUE = 42\n"
            # Isolation: the source repo itself is untouched.
            assert not (repo / "pkg").exists()
        finally:
            discard(cand)

    def test_unified_diff_applies(self, repo, tmp_path) -> None:
        diff = (
            "diff --git a/hello.py b/hello.py\n"
            "--- a/hello.py\n"
            "+++ b/hello.py\n"
            "@@ -1 +1 @@\n"
            '-GREETING = "hello"\n'
            '+GREETING = "bonjour"\n'
        )
        cand = materialize(diff, repo, scratch_root=tmp_path / "scratch")
        try:
            assert cand.files == ["hello.py"]
            assert "bonjour" in (cand.worktree / "hello.py").read_text()
            assert "bonjour" in diff_against_base(cand, repo)
        finally:
            discard(cand)

    def test_non_applying_diff_fails_clean_and_cleans_up(self, repo, tmp_path) -> None:
        diff = (
            "diff --git a/hello.py b/hello.py\n"
            "--- a/hello.py\n"
            "+++ b/hello.py\n"
            "@@ -1 +1 @@\n"
            "-NOT_THE_REAL_LINE\n"
            "+whatever\n"
        )
        scratch = tmp_path / "scratch"
        with pytest.raises(ProposalError, match="does not apply"):
            materialize(diff, repo, scratch_root=scratch)
        assert not any(scratch.glob("rt-candidate-*")) if scratch.exists() else True

    def test_empty_proposal_rejected(self, repo, tmp_path) -> None:
        with pytest.raises(ProposalError):
            materialize("just prose, no blocks, no diff", repo, scratch_root=tmp_path / "s")


class TestValidateReceipts:
    def test_green_candidate_carries_passing_receipts(self, repo, tmp_path) -> None:
        cand = materialize(_block("ok.py", "X = 1"), repo, scratch_root=tmp_path / "scratch")
        try:
            validate(cand, [("compile", [sys.executable, "-m", "py_compile", "ok.py"])])
            assert cand.green
            assert cand.receipts[0].passed and cand.receipts[0].label == "compile"
        finally:
            discard(cand)

    def test_failing_candidate_is_failed_with_receipts_not_dropped(self, repo, tmp_path) -> None:
        """TAC-4: the failure is presented with its receipt — never green."""
        cand = materialize(
            _block("broken.py", "def oops(:\n    pass"), repo, scratch_root=tmp_path / "s"
        )
        try:
            validate(cand, [("compile", [sys.executable, "-m", "py_compile", "broken.py"])])
            assert not cand.green
            assert cand.receipts[0].exit_code != 0
            assert cand.receipts[0].tail  # the evidence travels with it
        finally:
            discard(cand)

    def test_no_checks_is_not_green(self, repo, tmp_path) -> None:
        """Zero receipts must not read as success."""
        cand = materialize(_block("a.py", "A = 1"), repo, scratch_root=tmp_path / "s")
        try:
            assert not cand.green
        finally:
            discard(cand)

    def test_missing_check_binary_is_a_failed_receipt(self, repo, tmp_path) -> None:
        cand = materialize(_block("a.py", "A = 1"), repo, scratch_root=tmp_path / "s")
        try:
            validate(cand, [("ghost", ["definitely-not-a-binary-xyz"])])
            assert not cand.green and cand.receipts[0].exit_code == 127
        finally:
            discard(cand)


class TestDiscard:
    def test_discard_removes_worktree_and_registration(self, repo, tmp_path) -> None:
        cand = materialize(_block("a.py", "A = 1"), repo, scratch_root=tmp_path / "s")
        discard(cand)
        assert not cand.worktree.exists()
        listing = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list"], capture_output=True, text=True
        )
        assert "rt-candidate-" not in listing.stdout

    def test_discard_is_idempotent(self, repo, tmp_path) -> None:
        cand = materialize(_block("a.py", "A = 1"), repo, scratch_root=tmp_path / "s")
        discard(cand)
        discard(cand)  # second call must not raise
        discard(Candidate(worktree=tmp_path / "never-existed", files=[]))
