"""Fixture repo for handoff tests: main + feature branch, one diff."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from attune.memory import session_stash


@pytest.fixture(autouse=True)
def memory_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handoff unit tests never touch a real memory backend.

    Defaults every test to the unreachable-backend state so the D5
    linkage degrades to a stated skip; tests that want a backend
    override with a fake (see ``test_memory_link.backend``).
    """
    monkeypatch.setattr(session_stash, "resolve_backend", lambda b=None: None)
    monkeypatch.setattr(
        session_stash,
        "backend_status",
        lambda: {"ok": False, "backend": None, "reason": "no_backend"},
    )


def git(repo: Path, *args: str) -> str:
    """Run git in the fixture repo with signing/hooks disabled."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.email=fixture@test",
            "-c",
            "user.name=Fixture",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Repo with ``main`` (base) and ``feature/x`` (+1 commit)."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "base.txt").write_text("base\n", encoding="utf-8")
    git(root, "add", "base.txt")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "feature/x")
    (root / "feat.txt").write_text("feature\n", encoding="utf-8")
    git(root, "add", "feat.txt")
    git(root, "commit", "-q", "-m", "feature work")
    return root
