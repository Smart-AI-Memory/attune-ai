"""Trajectory Runner for Attune AI Ghost Simulator.

Executes agent trajectories across separate ghost worktree sandboxes.
Trajectories run sequentially in-process; isolation comes from each
trajectory operating in its own worktree.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

from .worktree import GhostWorktreeError, GhostWorktreeManager

logger = logging.getLogger(__name__)


class MultiTrajectoryRunner:
    """Runs execution trajectories across isolated ghost sandboxes."""

    def __init__(self, manager: GhostWorktreeManager) -> None:
        """Initialize MultiTrajectoryRunner.

        Args:
            manager: GhostWorktreeManager providing the sandboxes.
        """
        self.manager = manager

    def run_trajectories(
        self,
        trajectories: dict[str, Callable[[str], dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        """Runs given trajectory functions in ghost worktrees.

        Args:
            trajectories: Map of trajectory_id -> callable(worktree_path)
                returning a result dictionary.

        Returns:
            Map of trajectory_id -> result telemetry dictionary. A
            trajectory that raises (or whose sandbox cannot be created)
            yields ``{"success": False, "error": ...}``.
        """
        results: dict[str, dict[str, Any]] = {}

        for traj_id, func in trajectories.items():
            start_time = time.time()
            try:
                worktree_path = self.manager.create_ghost_worktree(traj_id)
            except GhostWorktreeError as exc:
                logger.error("trajectory %s: sandbox creation failed: %s", traj_id, exc)
                results[traj_id] = {
                    "success": False,
                    "error": str(exc),
                    "duration_seconds": 0.0,
                    "worktree_path": None,
                }
                continue

            try:
                res = func(worktree_path)
                res["duration_seconds"] = round(time.time() - start_time, 2)
                res["worktree_path"] = worktree_path
                results[traj_id] = res
            except Exception as exc:  # noqa: BLE001 — one bad trajectory must not kill the batch
                logger.exception("trajectory %s failed", traj_id)
                results[traj_id] = {
                    "success": False,
                    "error": str(exc),
                    "duration_seconds": round(time.time() - start_time, 2),
                    "worktree_path": worktree_path,
                }

        return results
