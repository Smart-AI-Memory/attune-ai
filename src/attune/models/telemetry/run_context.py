"""Run-record context resolution (docs/specs/run-record-corpus/ RC-3).

Resolves the two provenance fields every ``WorkflowRunRecord`` carries
going forward: how the run was triggered and which project it belongs
to. Both are best-effort — resolution failure degrades to a safe value
and never raises into the workflow path.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Launchers that start a run on behalf of an ATTUNE_REC recommendation
# export this before spawning the workflow process; everything else is
# a manual run. Values outside the valid set degrade to "manual".
TRIGGER_ENV = "ATTUNE_RUN_TRIGGER"

_VALID_TRIGGERS = frozenset({"manual", "attune-rec"})


def resolve_run_trigger() -> str:
    """Return the current run's trigger: ``"manual"`` or ``"attune-rec"``.

    Reads ``ATTUNE_RUN_TRIGGER`` from the environment; unset or invalid
    values resolve to ``"manual"`` (the conservative default — manual
    runs are the STRONGER evidence class, but a false "manual" only
    overweights one record, while a false "attune-rec" would silently
    discount genuine human intent).
    """
    value = os.environ.get(TRIGGER_ENV, "").strip().lower()
    return value if value in _VALID_TRIGGERS else "manual"


def resolve_project_identity(start: Path | None = None) -> str | None:
    """Return a stable project identifier for run records, or ``None``.

    Walks up from ``start`` (default: cwd) to the enclosing repository
    root and returns its directory name. A linked worktree's ``.git``
    FILE (``gitdir: <main>/.git/worktrees/<slug>``) resolves to the MAIN
    repository, so runs from ``.claude/worktrees/*`` tag as the parent
    project rather than the worktree slug. Pure-filesystem — no ``git``
    subprocess in the workflow hot path.
    """
    try:
        current = (start or Path.cwd()).resolve()
    except OSError:
        return None
    for candidate in (current, *current.parents):
        git = candidate / ".git"
        if git.is_dir():
            return candidate.name
        if git.is_file():
            return _worktree_parent_name(git) or candidate.name
    return None


def _worktree_parent_name(git_file: Path) -> str | None:
    """Parent-repo name from a worktree's ``.git`` pointer file."""
    try:
        text = git_file.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("run_context: unreadable .git file %s: %s", git_file, exc)
        return None
    for line in text.splitlines():
        if not line.startswith("gitdir:"):
            continue
        gitdir = Path(line.split(":", 1)[1].strip())
        # Layout: <main-repo>/.git/worktrees/<slug>
        if gitdir.parent.name == "worktrees" and gitdir.parent.parent.name == ".git":
            return gitdir.parent.parent.parent.name
    return None
