"""Ghost Worktree Manager for Attune AI.

Manages isolated, ephemeral Git worktrees under ``.attune/ghosts/`` for
speculative execution. All git operations are scoped to an explicit
repository root — never the process CWD — and failures are loud: a
ghost that cannot be created as a real worktree raises instead of
silently degrading to a plain directory.
"""

import logging
import os
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)

_GHOST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Commit refs are passed as a positional argument to `git worktree add`.
# First char must be alphanumeric — a leading '-' would be parsed as a
# git flag (argument injection). Covers HEAD~2, v1.0.0, feature/x, a@{u}.
_COMMIT_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@^~{}-]*$")


class GhostWorktreeError(RuntimeError):
    """Raised when a ghost worktree cannot be created or removed."""


class GhostWorktreeManager:
    """Manages ephemeral Git worktrees for parallel agent sandboxing."""

    def __init__(self, repo_root: str, base_dir: str | None = None) -> None:
        """Initialize GhostWorktreeManager.

        Args:
            repo_root: Root of the git repository ghosts are based on.
            base_dir: Root directory for ghost worktrees. Defaults to
                ``<repo_root>/.attune/ghosts`` (gitignored via .attune/).
        """
        self.repo_root = os.path.abspath(repo_root)
        self.base_dir = (
            os.path.abspath(base_dir)
            if base_dir
            else os.path.join(self.repo_root, ".attune", "ghosts")
        )

    def create_ghost_worktree(self, ghost_id: str, commit_ref: str = "HEAD") -> str:
        """Creates an isolated ghost worktree.

        Args:
            ghost_id: Unique identifier for the ghost sandbox
                (alphanumeric plus ``._-``).
            commit_ref: Git commit or ref to base the worktree on.

        Returns:
            Absolute path to the created ghost worktree directory.

        Raises:
            GhostWorktreeError: If the id is invalid or git cannot
                create the worktree.
        """
        if not _GHOST_ID_PATTERN.match(ghost_id):
            raise GhostWorktreeError(f"invalid ghost id: {ghost_id!r}")
        if not _COMMIT_REF_PATTERN.match(commit_ref):
            raise GhostWorktreeError(f"invalid commit ref: {commit_ref!r}")

        target_path = os.path.join(self.base_dir, ghost_id)
        os.makedirs(self.base_dir, exist_ok=True)

        if os.path.exists(target_path):
            self.remove_ghost_worktree(ghost_id)

        proc = subprocess.run(
            [
                "git",
                "-C",
                self.repo_root,
                "worktree",
                "add",
                "-b",
                f"ghost-{ghost_id}",
                target_path,
                commit_ref,
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise GhostWorktreeError(
                f"git worktree add failed for {ghost_id!r}: {proc.stderr.strip()}"
            )

        return target_path

    def remove_ghost_worktree(self, ghost_id: str) -> bool:
        """Removes a ghost worktree and its branch.

        Args:
            ghost_id: Identifier of the ghost sandbox to prune.

        Returns:
            True if a worktree existed and was removed, False if there
            was nothing to remove.
        """
        target_path = os.path.join(self.base_dir, ghost_id)
        if not os.path.exists(target_path):
            return False

        proc = subprocess.run(
            ["git", "-C", self.repo_root, "worktree", "remove", "--force", target_path],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            logger.warning(
                "ghost %s: git worktree remove failed (%s); falling back to rmtree",
                ghost_id,
                proc.stderr.strip(),
            )
            shutil.rmtree(target_path, ignore_errors=True)
            subprocess.run(
                ["git", "-C", self.repo_root, "worktree", "prune"],
                capture_output=True,
                text=True,
            )

        branch_proc = subprocess.run(
            ["git", "-C", self.repo_root, "branch", "-D", f"ghost-{ghost_id}"],
            capture_output=True,
            text=True,
        )
        if branch_proc.returncode != 0:
            logger.debug(
                "ghost %s: branch delete skipped: %s",
                ghost_id,
                branch_proc.stderr.strip(),
            )

        return True
