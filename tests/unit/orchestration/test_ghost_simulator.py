"""Tests for the Ghost Simulator sandbox.

The worktree/promoter tests are non-mocked round trips through a real
temporary git repository — creating a plain directory and calling it a
worktree is exactly the failure mode these guard against.
"""

import subprocess
from pathlib import Path

import pytest

from attune.orchestration.ghosts import (
    GhostWorktreeError,
    GhostWorktreeManager,
    MultiTrajectoryRunner,
    TrajectoryComparator,
    TrajectoryPromoter,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture()
def temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _git(repo, "config", "user.email", "ghost@test.local")
    _git(repo, "config", "user.name", "Ghost Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "hello.txt").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "hello.txt")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


class TestGhostWorktreeManager:
    """Real-git round trips for worktree lifecycle."""

    def test_creates_a_real_git_worktree(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        path = Path(manager.create_ghost_worktree("t1"))

        assert path.exists()
        # It must be a REAL worktree: on branch ghost-t1 with the base
        # commit's content, not a bare directory.
        head = _git(path, "branch", "--show-current").stdout.strip()
        assert head == "ghost-t1"
        assert (path / "hello.txt").read_text(encoding="utf-8") == "hello\n"

    def test_removal_deletes_worktree_and_branch(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        path = Path(manager.create_ghost_worktree("t2"))

        assert manager.remove_ghost_worktree("t2") is True
        assert not path.exists()
        branches = _git(temp_repo, "branch", "--list", "ghost-t2").stdout
        assert "ghost-t2" not in branches
        assert manager.remove_ghost_worktree("t2") is False

    def test_invalid_ghost_id_rejected(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        with pytest.raises(GhostWorktreeError):
            manager.create_ghost_worktree("../escape")

    def test_recreate_over_existing_ghost_gives_fresh_sandbox(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        first = Path(manager.create_ghost_worktree("re"))
        (first / "scratch.txt").write_text("scratch\n", encoding="utf-8")

        second = Path(manager.create_ghost_worktree("re"))

        assert second == first
        assert not (second / "scratch.txt").exists()  # fresh, not reused
        head = _git(second, "branch", "--show-current").stdout.strip()
        assert head == "ghost-re"

    def test_remove_falls_back_to_rmtree_for_non_worktree_dir(self, temp_repo: Path) -> None:
        # A stray directory under base_dir that git doesn't know about:
        # `git worktree remove` fails, the rmtree fallback must still
        # clear it and report removal.
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        stray = Path(manager.base_dir) / "stray"
        stray.mkdir(parents=True)
        (stray / "junk.txt").write_text("junk\n", encoding="utf-8")

        assert manager.remove_ghost_worktree("stray") is True
        assert not stray.exists()

    def test_non_repo_raises_instead_of_fake_directory(self, tmp_path: Path) -> None:
        # Regression: the original silently fell back to a bare
        # directory when git failed, faking a sandbox.
        not_repo = tmp_path / "not-a-repo"
        not_repo.mkdir()
        manager = GhostWorktreeManager(repo_root=str(not_repo))
        with pytest.raises(GhostWorktreeError):
            manager.create_ghost_worktree("t3")


class TestMultiTrajectoryRunner:
    """Runner behavior across real sandboxes."""

    def test_run_trajectories_isolated_paths(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        runner = MultiTrajectoryRunner(manager=manager)

        def traj(path: str) -> dict:
            return {"success": True, "tests_passed": 10, "tests_total": 10}

        results = runner.run_trajectories({"a": traj, "b": traj})

        assert results["a"]["success"] is True
        assert results["b"]["success"] is True
        assert results["a"]["worktree_path"] != results["b"]["worktree_path"]

    def test_raising_trajectory_reported_not_fatal(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        runner = MultiTrajectoryRunner(manager=manager)

        def boom(path: str) -> dict:
            raise ValueError("trajectory exploded")

        def ok(path: str) -> dict:
            return {"success": True}

        results = runner.run_trajectories({"boom": boom, "ok": ok})
        assert results["boom"]["success"] is False
        assert "trajectory exploded" in results["boom"]["error"]
        assert results["ok"]["success"] is True

    def test_sandbox_creation_failure_reported_not_fatal(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        runner = MultiTrajectoryRunner(manager=manager)

        def ok(path: str) -> dict:
            return {"success": True}

        # "bad/id" fails ghost-id validation → sandbox creation raises;
        # the batch must record the failure and keep running.
        results = runner.run_trajectories({"bad/id": ok, "good": ok})

        assert results["bad/id"]["success"] is False
        assert "invalid ghost id" in results["bad/id"]["error"]
        assert results["bad/id"]["worktree_path"] is None
        assert results["bad/id"]["duration_seconds"] == 0.0
        assert results["good"]["success"] is True


class TestTrajectoryComparator:
    """Comparator scoring."""

    def test_comparison_selects_best_pass_rate(self) -> None:
        comparator = TrajectoryComparator()
        results = {
            "a": {
                "success": True,
                "tests_passed": 10,
                "tests_total": 10,
                "duration_seconds": 2.0,
            },
            "b": {
                "success": True,
                "tests_passed": 5,
                "tests_total": 10,
                "duration_seconds": 1.0,
            },
        }
        res = comparator.compare(results)
        assert res["recommended_trajectory"] == "a"
        assert len(res["comparison_matrix"]) == 2

    def test_all_failed_recommends_none(self) -> None:
        # Regression: the original recommended a FAILED trajectory
        # when every trajectory failed.
        comparator = TrajectoryComparator()
        res = comparator.compare({"a": {"success": False}, "b": {"success": False}})
        assert res["recommended_trajectory"] is None


class TestTrajectoryPromoter:
    """Real-git promotion round trips."""

    def test_promote_lands_ghost_commit_on_target(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        ghost = Path(manager.create_ghost_worktree("win"))

        (ghost / "feature.txt").write_text("ghost work\n", encoding="utf-8")
        _git(ghost, "add", "feature.txt")
        _git(ghost, "commit", "-q", "-m", "ghost feature")

        promoter = TrajectoryPromoter(manager=manager)
        assert promoter.promote("win", target_branch="main") is True

        assert (temp_repo / "feature.txt").read_text(encoding="utf-8") == "ghost work\n"
        assert not ghost.exists()  # cleaned up after success

    def test_promote_refused_on_wrong_branch(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        manager.create_ghost_worktree("w2")
        promoter = TrajectoryPromoter(manager=manager)
        assert promoter.promote("w2", target_branch="release") is False

    def test_failed_promotion_keeps_ghost_worktree(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        ghost = Path(manager.create_ghost_worktree("div"))

        # Diverge: commit on main AND on the ghost → ff-only must fail.
        (temp_repo / "main.txt").write_text("main moved\n", encoding="utf-8")
        _git(temp_repo, "add", "main.txt")
        _git(temp_repo, "commit", "-q", "-m", "main moves")
        (ghost / "ghost.txt").write_text("ghost work\n", encoding="utf-8")
        _git(ghost, "add", "ghost.txt")
        _git(ghost, "commit", "-q", "-m", "ghost diverges")

        promoter = TrajectoryPromoter(manager=manager)
        assert promoter.promote("div", target_branch="main") is False
        # Regression: the original deleted the worktree on failure,
        # destroying the winning trajectory's work.
        assert ghost.exists()


class TestCommitRefValidation:
    """Regression: commit_ref is a trailing positional to `git worktree
    add` — a leading '-' would be parsed as a git flag (argument
    injection, code-review Low security finding)."""

    def test_leading_dash_ref_rejected_before_git_runs(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        with pytest.raises(GhostWorktreeError, match="invalid commit ref"):
            manager.create_ghost_worktree("t9", commit_ref="--upload-pack=/bin/sh")

    def test_whitespace_and_empty_refs_rejected(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        for bad in ("", "HEAD; rm -rf x", "a b"):
            with pytest.raises(GhostWorktreeError, match="invalid commit ref"):
                manager.create_ghost_worktree("t9", commit_ref=bad)

    def test_normal_refs_still_work(self, temp_repo: Path) -> None:
        manager = GhostWorktreeManager(repo_root=str(temp_repo))
        path = Path(manager.create_ghost_worktree("refok", commit_ref="HEAD"))
        assert path.exists()
