"""Regression tests for ``scripts/audit_worktrees.sh``.

Two bugs this guards against, both of which silently produced a
*wrong worktree count* (the audit's entire reason to exist):

1. **CWD leak** — the script used bare ``git worktree list`` (no
   ``-C``/``cd``), so it audited the caller's ``$PWD`` instead of the
   repo it ships in. Run from the umbrella workspace, it reported the
   umbrella's 3 worktrees while attune-ai's 33 stayed invisible.
2. **Main-checkout on a feature branch** — main-checkout detection
   keyed on ``branch refs/heads/main``; when the primary checkout sat
   on a feature branch it wasn't recognized and got counted as a
   linked worktree (off-by-one).

The tests build throwaway git repos so they assert behavior, not the
live worktree layout of this repo (which changes constantly).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "audit_worktrees.sh"

# Hermetic git: no global config (GPG signing, hooks), deterministic
# identity, no system config bleed.
_GIT_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**_os_environ(), **_GIT_ENV},
    )


def _os_environ() -> dict[str, str]:
    import os

    return os.environ.copy()


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "main")
    (path / "seed.txt").write_text("seed\n")
    _git(path, "add", ".")
    _git(path, "-c", "commit.gpgsign=false", "commit", "-m", "init")


def _add_worktree(repo: Path, wt_path: Path, branch: str) -> None:
    _git(repo, "worktree", "add", "-b", branch, str(wt_path))


def _run_audit(script: Path, cwd: Path) -> dict:
    """Run the audit in --json mode from ``cwd``; return parsed JSON."""
    result = subprocess.run(
        ["bash", str(script), "--json"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env={**_os_environ(), **_GIT_ENV},
        timeout=30,
    )
    assert result.returncode == 0, f"audit exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout)


@pytest.fixture
def home_repo(tmp_path: Path) -> Path:
    """A repo with the script vendored in and exactly one linked worktree."""
    home = tmp_path / "home_repo"
    _init_repo(home)
    (home / "scripts").mkdir()
    shutil.copy(SCRIPT, home / "scripts" / "audit_worktrees.sh")
    _add_worktree(home, tmp_path / "home_wt", "home-feature")
    return home


def test_audits_script_repo_not_cwd(home_repo: Path, tmp_path: Path) -> None:
    """Run from an unrelated repo's CWD; must audit the script's repo."""
    caller = tmp_path / "caller_repo"
    _init_repo(caller)
    _add_worktree(caller, tmp_path / "caller_wt_1", "caller-a")
    _add_worktree(caller, tmp_path / "caller_wt_2", "caller-b")

    audit = _run_audit(home_repo / "scripts" / "audit_worktrees.sh", cwd=caller)

    # The script's repo (home) has exactly 1 linked worktree.
    assert audit["total"] == 1, audit
    branches = {
        wt["branch"] for bucket in ("active", "safe", "risk") for wt in audit.get(bucket, [])
    }
    assert "home-feature" in branches
    assert "caller-a" not in branches and "caller-b" not in branches


def test_main_checkout_excluded_on_feature_branch(tmp_path: Path) -> None:
    """Main checkout on a non-``main`` branch must not be miscounted."""
    home = tmp_path / "fb_repo"
    _init_repo(home)
    (home / "scripts").mkdir()
    shutil.copy(SCRIPT, home / "scripts" / "audit_worktrees.sh")
    # Move the MAIN checkout off `main` onto a feature branch.
    _git(home, "checkout", "-b", "primary-feature")
    _add_worktree(home, tmp_path / "linked_wt", "linked-feature")

    audit = _run_audit(home / "scripts" / "audit_worktrees.sh", cwd=home)

    # Only the linked worktree counts; the main checkout is excluded
    # even though it is on a feature branch (not `main`).
    assert audit["total"] == 1, audit
    branches = {
        wt["branch"] for bucket in ("active", "safe", "risk") for wt in audit.get(bucket, [])
    }
    assert "linked-feature" in branches
    assert "primary-feature" not in branches


def test_audit_repo_env_override(home_repo: Path, tmp_path: Path) -> None:
    """``AUDIT_REPO`` points the audit at an explicit repo."""
    other = tmp_path / "other_repo"
    _init_repo(other)
    _add_worktree(other, tmp_path / "other_wt_1", "other-a")
    _add_worktree(other, tmp_path / "other_wt_2", "other-b")

    import os

    result = subprocess.run(
        ["bash", str(home_repo / "scripts" / "audit_worktrees.sh"), "--json"],
        cwd=str(home_repo),
        capture_output=True,
        text=True,
        env={**os.environ, **_GIT_ENV, "AUDIT_REPO": str(other)},
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    audit = json.loads(result.stdout)
    assert audit["total"] == 2, audit  # other_repo has 2 linked worktrees
