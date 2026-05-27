"""Tests for the git_state source reader.

These tests build a real git repo in tmp_path so subprocess calls
exercise the same code path production uses — no mocks needed for
the happy paths.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from attune.curator.sources import git_state as git_source

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


def _git(cwd: Path, *args: str, check: bool = True) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=check,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def empty_repo(tmp_path):
    """A real git repo with one initial commit on `main`."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "README.md").write_text("init\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_non_repo_returns_empty(tmp_path):
    summary = git_source.read(project_root=tmp_path)
    assert summary.source_id == "git-state"
    assert summary.items == []


def test_clean_repo_has_no_signals(empty_repo):
    summary = git_source.read(project_root=empty_repo)
    # No origin/main → diverged signal silent. Clean working tree → no
    # uncommitted signal. No untracked files → no secrets signal.
    assert summary.items == []


def test_uncommitted_signal_fires_above_threshold(empty_repo):
    for i in range(15):
        (empty_repo / f"file_{i}.txt").write_text(f"x{i}\n", encoding="utf-8")
    summary = git_source.read(project_root=empty_repo)
    uncommitted = [i for i in summary.items if i.metadata["signal"] == "uncommitted"]
    assert len(uncommitted) == 1
    assert int(uncommitted[0].metadata["count"]) >= 15


def test_uncommitted_signal_silent_below_threshold(empty_repo):
    for i in range(5):
        (empty_repo / f"file_{i}.txt").write_text("x\n", encoding="utf-8")
    summary = git_source.read(project_root=empty_repo)
    assert not any(i.metadata["signal"] == "uncommitted" for i in summary.items)


def test_secrets_shape_files_surface(empty_repo):
    (empty_repo / ".env.production").write_text("API_KEY=xxx\n", encoding="utf-8")
    (empty_repo / "credentials.json").write_text("{}\n", encoding="utf-8")
    (empty_repo / "README.txt").write_text("safe\n", encoding="utf-8")
    summary = git_source.read(project_root=empty_repo)
    secret_items = [item for item in summary.items if item.metadata["signal"] == "secret_shape"]
    paths = {item.metadata["path"] for item in secret_items}
    assert ".env.production" in paths
    assert "credentials.json" in paths
    # README.txt does NOT match a credential pattern.
    assert "README.txt" not in paths


def test_state_hash_deterministic(empty_repo):
    (empty_repo / ".env").write_text("X=1\n", encoding="utf-8")
    a = git_source.read(project_root=empty_repo).state_hash
    b = git_source.read(project_root=empty_repo).state_hash
    assert a == b


def test_subprocess_failure_returns_empty(empty_repo, monkeypatch):
    """If git binary is reported missing mid-call, return empty."""
    monkeypatch.setattr(git_source.shutil, "which", lambda _: None)
    summary = git_source.read(project_root=empty_repo)
    assert summary.items == []


def test_git_timeout_does_not_raise(empty_repo, monkeypatch):
    """A hung git invocation collapses to no-signal, never an exception."""

    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=5)

    monkeypatch.setattr(git_source.subprocess, "run", boom)
    summary = git_source.read(project_root=empty_repo)
    assert summary.source_id == "git-state"
    # No signals emitted — but no traceback either.
    assert summary.items == []


def test_diverged_signal_fires_when_head_is_stale(empty_repo, monkeypatch):
    """If origin/main is >3 days ahead of HEAD, emit a diverged item."""
    from datetime import datetime, timedelta, timezone

    head = datetime.now(timezone.utc) - timedelta(days=10)
    main = datetime.now(timezone.utc)

    def fake_commit_date(project_root, ref):  # noqa: ANN001
        if ref == "HEAD":
            return head
        if ref == "origin/main":
            return main
        return None

    monkeypatch.setattr(git_source, "_commit_date", fake_commit_date)
    summary = git_source.read(project_root=empty_repo)
    diverged = [i for i in summary.items if i.metadata["signal"] == "diverged"]
    assert len(diverged) == 1
    assert int(diverged[0].metadata["days_behind"]) >= 3


def test_diverged_signal_silent_when_head_caught_up(empty_repo, monkeypatch):
    """Within 3 days of origin/main, no diverged item fires."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)

    def fake_commit_date(project_root, ref):  # noqa: ANN001
        if ref == "HEAD":
            return now - timedelta(hours=12)
        if ref == "origin/main":
            return now
        return None

    monkeypatch.setattr(git_source, "_commit_date", fake_commit_date)
    summary = git_source.read(project_root=empty_repo)
    assert not any(i.metadata.get("signal") == "diverged" for i in summary.items)


def test_secrets_signal_caps_at_10(empty_repo):
    """Even with 20 matching files only 10 secret-shape items surface."""
    for i in range(20):
        (empty_repo / f"secret{i}.key").write_text("x\n", encoding="utf-8")
    summary = git_source.read(project_root=empty_repo)
    secret_items = [item for item in summary.items if item.metadata["signal"] == "secret_shape"]
    assert len(secret_items) == 10


def test_secrets_signal_ignores_blank_ls_files_lines(empty_repo, monkeypatch):
    """Blank lines in ls-files output don't crash or false-fire."""
    real_run_git = git_source._run_git

    def stub(project_root, argv):  # noqa: ANN001
        if argv[0] == "ls-files":
            return "\n\n.env\n\n"
        return real_run_git(project_root, argv)

    monkeypatch.setattr(git_source, "_run_git", stub)
    summary = git_source.read(project_root=empty_repo)
    secret_items = [i for i in summary.items if i.metadata["signal"] == "secret_shape"]
    assert any(item.metadata["path"] == ".env" for item in secret_items)


def test_commit_date_returns_none_on_empty_output(empty_repo, monkeypatch):
    """When git log returns whitespace-only stdout, _commit_date is None."""
    monkeypatch.setattr(git_source, "_run_git", lambda root, argv: "   \n")
    assert git_source._commit_date(empty_repo, "HEAD") is None


def test_commit_date_returns_none_on_bad_iso(empty_repo, monkeypatch):
    """If git log emits unparseable ISO, _commit_date returns None."""
    monkeypatch.setattr(git_source, "_run_git", lambda root, argv: "not-an-iso\n")
    assert git_source._commit_date(empty_repo, "HEAD") is None


def test_commit_date_coerces_naive_to_utc(empty_repo, monkeypatch):
    """A naive ISO string (no tz) gets stamped UTC."""
    monkeypatch.setattr(
        git_source,
        "_run_git",
        lambda root, argv: "2026-05-26T12:00:00\n",
    )
    dt = git_source._commit_date(empty_repo, "HEAD")
    assert dt is not None and dt.tzinfo is not None
