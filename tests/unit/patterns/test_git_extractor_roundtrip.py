"""Non-mocked round-trip tests for the git subprocess seam in GitPatternExtractor.

The existing ``test_git_extractor.py`` mocks ``subprocess`` heavily, so it
proves the parsing logic but NOT that the real ``git log``/``git diff``
invocations and their output parsing actually work end-to-end. These tests
run the extractor against a REAL temporary git repo through the real
subprocess seam — the receipt that the boundary works, not just the mock.

Git is a hard dependency of the dev/test environment, so no skip gate is
needed; the repo is created fresh in ``tmp_path`` for determinism.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from attune.patterns.git_extractor import GitPatternExtractor

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


def _git(repo, *args: str) -> str:
    """Run a git command in ``repo`` and return stdout (test setup helper)."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def real_repo(tmp_path):
    """A real git repo with one fix commit (deterministic, isolated)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tester@example.com")
    _git(repo, "config", "user.name", "Round Trip Tester")
    # A global commit.gpgsign=true has no pinentry under launchd/CI.
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "app.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "fix: handle null input in f")
    return repo


def test_get_commit_info_reads_real_commit(real_repo, monkeypatch):
    """_get_commit_info parses real `git log` output for the actual commit."""
    monkeypatch.chdir(real_repo)
    full_hash = _git(real_repo, "rev-parse", "HEAD")

    extractor = GitPatternExtractor(patterns_dir=str(real_repo / "patterns"))
    info = extractor._get_commit_info("HEAD")

    assert info is not None, "real git commit not read through the subprocess seam"
    assert info["hash"] == full_hash[:8]
    assert info["message"] == "fix: handle null input in f"
    assert info["author"] == "Round Trip Tester"
    assert info["date"]  # ISO date string, non-empty


def test_get_staged_diff_reads_real_staged_change(real_repo, monkeypatch):
    """_get_staged_diff returns the real `git diff --cached` output."""
    monkeypatch.chdir(real_repo)
    (real_repo / "app.py").write_text("def f(x):\n    return x or 0\n", encoding="utf-8")
    _git(real_repo, "add", "app.py")

    extractor = GitPatternExtractor(patterns_dir=str(real_repo / "patterns"))
    diff = extractor._get_staged_diff()

    assert "return x or 0" in diff, "staged change not seen through the subprocess seam"
    assert diff.startswith("diff --git"), "output is not a real unified git diff"


def test_get_commit_info_returns_none_outside_repo(tmp_path, monkeypatch):
    """Outside a git repo, the seam degrades to None (real failure path)."""
    monkeypatch.chdir(tmp_path)  # tmp_path itself is not a git repo
    extractor = GitPatternExtractor(patterns_dir=str(tmp_path / "patterns"))
    assert extractor._get_commit_info("HEAD") is None


def test_extract_from_recent_commits_runs_on_real_repo(real_repo, monkeypatch):
    """End-to-end: the public extractor runs over a real repo without error."""
    monkeypatch.chdir(real_repo)
    extractor = GitPatternExtractor(patterns_dir=str(real_repo / "patterns"))
    result = extractor.extract_from_recent_commits(num_commits=1)
    assert isinstance(result, list)  # real round-trip completes; content is best-effort
