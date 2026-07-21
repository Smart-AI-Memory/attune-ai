"""Ghost Simulator sandbox for attune-ai.

Ephemeral git worktrees for speculative parallel trajectories, with
comparison and fast-forward promotion of the winner.
"""

from .comparator import TrajectoryComparator
from .promoter import TrajectoryPromoter
from .runner import MultiTrajectoryRunner
from .worktree import GhostWorktreeError, GhostWorktreeManager

__all__ = [
    "GhostWorktreeError",
    "GhostWorktreeManager",
    "MultiTrajectoryRunner",
    "TrajectoryComparator",
    "TrajectoryPromoter",
]
