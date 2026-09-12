"""Behavioral receipts for ``scripts/salvage_worktree_diff.sh``.

The script lifts a stranded worktree's uncommitted diff onto a fresh
branch in another checkout, read-only on the source. Every case here
builds a throwaway repo (primary checkout + bare ``origin`` + a linked
worktree), dirties the worktree, and drives the real script through
``bash`` from the primary checkout — no mocks, no network.

Fixture commits never invoke GPG: every git call carries
``-c commit.gpgsign=false`` and runs against a scratch
``GIT_CONFIG_GLOBAL`` / ``HOME`` (a signing fixture hangs on pinentry;
lesson 2026-08-26).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "salvage_worktree_diff.sh"

# A POSIX/bash ops helper: on Windows runners a bare `bash` is the WSL
# stub, which exits before the script runs. Same guard as land_pr.sh.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="salvage_worktree_diff.sh is a POSIX/bash ops helper",
)


@dataclass
class Repos:
    env: dict[str, str]
    primary: Path
    source: Path


def _hermetic_env(scratch: Path) -> dict[str, str]:
    home = scratch / "home"
    home.mkdir()
    cfg = scratch / "gitconfig"
    cfg.write_text(
        "[user]\n\tname = t\n\temail = t@example.invalid\n"
        "[commit]\n\tgpgsign = false\n[tag]\n\tgpgsign = false\n",
        encoding="utf-8",
    )
    system = scratch / "gitconfig-system"
    system.write_text("", encoding="utf-8")
    return {
        **os.environ,
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(cfg),
        "GIT_CONFIG_SYSTEM": str(system),
    }


def _git(repos: Repos, cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=str(cwd),
        env=repos.env,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout


@pytest.fixture
def repos(tmp_path: Path) -> Repos:
    r = Repos(env=_hermetic_env(tmp_path), primary=tmp_path / "primary", source=tmp_path / "src")
    origin = tmp_path / "origin.git"
    _git(r, tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    r.primary.mkdir()
    _git(r, r.primary, "init", "-q", "-b", "main")
    (r.primary / "base.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (r.primary / "keep.txt").write_text("keep\n", encoding="utf-8")
    _git(r, r.primary, "add", ".")
    _git(r, r.primary, "commit", "-q", "-m", "base")
    _git(r, r.primary, "remote", "add", "origin", str(origin))
    _git(r, r.primary, "push", "-q", "-u", "origin", "main")
    _git(r, r.primary, "worktree", "add", "-q", "-b", "stranded", str(r.source))
    return r


def _dirty(source: Path) -> None:
    """A tracked edit plus a nested untracked file — the stranded shape."""
    (source / "base.txt").write_text("one\ntwo-edited\nthree\nfour\n", encoding="utf-8")
    (source / "new_dir").mkdir()
    (source / "new_dir" / "new_file.txt").write_bytes(b"brand new\x00bytes\n")


def _run(repos: Repos, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=str(cwd or repos.primary),
        env=repos.env,
        capture_output=True,
        text=True,
    )


def _normalize(patch: str) -> list[str]:
    return [ln for ln in patch.splitlines() if not ln.startswith(("index ", "@@ "))]


def _source_snapshot(repos: Repos) -> tuple[str, str, dict[str, bytes]]:
    status = _git(repos, repos.source, "status", "--porcelain", "--untracked-files=all")
    head = _git(repos, repos.source, "rev-parse", "HEAD")
    files = {
        str(p.relative_to(repos.source)): p.read_bytes()
        for p in repos.source.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }
    return status, head, files


def test_happy_path_salvages_onto_fresh_branch_and_leaves_source_untouched(repos: Repos) -> None:
    _dirty(repos.source)
    before = _source_snapshot(repos)
    expected_patch = _git(repos, repos.source, "diff", "HEAD")

    res = _run(repos, str(repos.source), "salvage/x")

    assert res.returncode == 0, res.stderr
    assert _git(repos, repos.primary, "branch", "--show-current").strip() == "salvage/x"
    # Tracked diff landed and is identical modulo index lines / hunk headers.
    got_patch = _git(repos, repos.primary, "diff", "HEAD")
    assert _normalize(got_patch) == _normalize(expected_patch)
    assert (repos.primary / "base.txt").read_text(encoding="utf-8") == (
        repos.source / "base.txt"
    ).read_text(encoding="utf-8")
    # Untracked file copied byte-for-byte into the same relative path.
    copied = repos.primary / "new_dir" / "new_file.txt"
    assert copied.read_bytes() == (repos.source / "new_dir" / "new_file.txt").read_bytes()
    assert "identity: IDENTICAL" in res.stdout
    assert "new_dir/new_file.txt" in res.stdout
    assert "UNTOUCHED" in res.stdout
    # The source is the backup: status, HEAD, and every file byte unchanged.
    assert _source_snapshot(repos) == before
    assert _git(repos, repos.source, "branch", "--show-current").strip() == "stranded"


def test_refuses_to_run_inside_the_source(repos: Repos) -> None:
    _dirty(repos.source)

    res = _run(repos, str(repos.source), "salvage/x", cwd=repos.source)

    assert res.returncode == 1, res.stderr
    assert "source worktree" in res.stderr
    assert _git(repos, repos.source, "branch", "--show-current").strip() == "stranded"
    assert _git(repos, repos.primary, "branch", "--list", "salvage/x").strip() == ""


def test_refuses_dirty_current_checkout(repos: Repos) -> None:
    _dirty(repos.source)
    (repos.primary / "scratch.txt").write_text("unrelated\n", encoding="utf-8")

    res = _run(repos, str(repos.source), "salvage/x")

    assert res.returncode == 1, res.stderr
    assert "dirty" in res.stderr
    assert _git(repos, repos.primary, "branch", "--show-current").strip() == "main"


def test_clean_source_is_nothing_to_salvage(repos: Repos) -> None:
    res = _run(repos, str(repos.source), "salvage/x")

    assert res.returncode == 2, res.stderr
    assert "nothing to salvage" in res.stderr
    assert _git(repos, repos.primary, "branch", "--show-current").strip() == "main"


@pytest.mark.parametrize(
    "argv",
    [
        (),
        ("only-source",),
        ("src", "branch", "extra-positional"),
        ("src", "branch", "--bogus"),
        ("src", "branch", "--base"),
    ],
)
def test_usage_errors_exit_64(repos: Repos, argv: tuple[str, ...]) -> None:
    args = tuple(str(repos.source) if a == "src" else a for a in argv)

    res = _run(repos, *args)

    assert res.returncode == 64, res.stderr
    assert "usage:" in res.stderr


def test_untracked_file_colliding_with_tracked_file_here_is_refused(repos: Repos) -> None:
    # The stranded branch committed a deletion of keep.txt, then a fresh
    # untracked keep.txt appeared. On the base, keep.txt is still tracked.
    _git(repos, repos.source, "rm", "-q", "keep.txt")
    _git(repos, repos.source, "commit", "-q", "-m", "drop keep")
    (repos.source / "keep.txt").write_text("would clobber\n", encoding="utf-8")

    res = _run(repos, str(repos.source), "salvage/x")

    assert res.returncode == 1, res.stderr
    assert "keep.txt" in res.stderr
    assert (repos.primary / "keep.txt").read_text(encoding="utf-8") == "keep\n"
    assert _git(repos, repos.primary, "status", "--porcelain") == ""
