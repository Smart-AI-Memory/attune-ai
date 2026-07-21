"""Trajectory Promoter for Attune AI Ghost Simulator.

Promotes winning ghost trajectory changes back into the primary
repository branch via fast-forward merge.
"""

import logging
import subprocess

from .worktree import GhostWorktreeManager

logger = logging.getLogger(__name__)


class TrajectoryPromoter:
    """Promotes winning ghost trajectory changes into the repository."""

    def __init__(self, manager: GhostWorktreeManager) -> None:
        """Initialize TrajectoryPromoter.

        Args:
            manager: GhostWorktreeManager that owns the ghost sandboxes.
        """
        self.manager = manager

    def promote(self, winning_trajectory_id: str, target_branch: str = "main") -> bool:
        """Promotes changes from the winning ghost into the target branch.

        The merge runs in the manager's repository root and only
        proceeds when that repository currently has ``target_branch``
        checked out — promoting into whatever happens to be checked
        out is how work lands on the wrong branch. On failure the
        ghost worktree is KEPT so the trajectory's work is not lost.

        Args:
            winning_trajectory_id: ID of the ghost sandbox to promote.
            target_branch: Branch the ghost changes must land on.

        Returns:
            True if promotion succeeded (ghost is cleaned up), False
            otherwise (ghost is retained for inspection).
        """
        repo = self.manager.repo_root
        current = subprocess.run(
            ["git", "-C", repo, "branch", "--show-current"],
            capture_output=True,
            text=True,
        )
        if current.returncode != 0 or current.stdout.strip() != target_branch:
            logger.error(
                "promotion refused: %s has %r checked out, not %r",
                repo,
                current.stdout.strip(),
                target_branch,
            )
            return False

        ghost_branch = f"ghost-{winning_trajectory_id}"
        merge = subprocess.run(
            ["git", "-C", repo, "merge", "--ff-only", ghost_branch],
            capture_output=True,
            text=True,
        )
        if merge.returncode != 0:
            logger.error(
                "promotion of %s failed (%s); ghost worktree retained",
                ghost_branch,
                merge.stderr.strip(),
            )
            return False

        self.manager.remove_ghost_worktree(winning_trajectory_id)
        return True
