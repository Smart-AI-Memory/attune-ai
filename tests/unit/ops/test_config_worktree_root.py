"""Worktree-aware default project root (``_default_project_root``).

Launching the ops dashboard from a linked git worktree without
``--project-root`` must resolve the MAIN checkout, not the worktree —
the PROJECT label and every project-scoped surface (specs, docs gates)
read from ``cfg.project_root``. Real git repos in tmp_path, no mocks.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from attune.ops.config import _default_project_root, build_config


def _git(args: list[str], cwd: Path) -> None:
    # Inherit the environment (Windows lanes have git on PATH, not at
    # POSIX locations); identity + signing set per-command via -c so no
    # global config is touched.
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """A real main checkout plus a linked worktree."""
    main = tmp_path / "mainrepo"
    main.mkdir()
    _git(["init", "-q", "-b", "main"], main)
    (main / "README.md").write_text("x\n", encoding="utf-8")
    _git(["add", "README.md"], main)
    _git(["commit", "-q", "-m", "init"], main)
    worktree = tmp_path / "wt"
    _git(["worktree", "add", "-q", str(worktree), "-b", "branch-a"], main)
    return main, worktree


class TestDefaultProjectRoot:
    def test_worktree_resolves_to_main_checkout(
        self, repo_with_worktree: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main, worktree = repo_with_worktree
        monkeypatch.chdir(worktree)
        assert _default_project_root().resolve() == main.resolve()

    def test_main_checkout_resolves_to_itself(
        self, repo_with_worktree: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main, _ = repo_with_worktree
        monkeypatch.chdir(main)
        assert _default_project_root().resolve() == main.resolve()

    def test_non_repo_dir_falls_back_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        monkeypatch.chdir(plain)
        assert _default_project_root().resolve() == plain.resolve()

    def test_build_config_uses_worktree_aware_default(
        self, repo_with_worktree: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main, worktree = repo_with_worktree
        monkeypatch.chdir(worktree)
        cfg = build_config()
        assert cfg.project_root == main.resolve()

    def test_explicit_project_root_still_wins(
        self, repo_with_worktree: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _, worktree = repo_with_worktree
        monkeypatch.chdir(worktree)
        explicit = tmp_path / "explicit"
        explicit.mkdir()
        cfg = build_config(project_root=explicit)
        assert cfg.project_root == explicit.resolve()
