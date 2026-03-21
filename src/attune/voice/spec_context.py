"""Spec-aware lifecycle context for the voice layer.

Reads active spec files from ``.claude/plans/`` and maps the
current workflow to the next stage in the spec's lifecycle.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune.workflows.data_classes import NextAction

logger = logging.getLogger(__name__)

# Lifecycle stage ordering — maps workflow names to their
# position in a typical development lifecycle.
_LIFECYCLE_ORDER: list[str] = [
    "code-review",
    "security-audit",
    "bug-predict",
    "test-gen",
    "perf-audit",
    "refactor-plan",
    "simplify-code",
    "dependency-check",
    "doc-gen",
    "release-prep",
]


def get_spec_next_action(
    workflow_name: str,
    workspace_root: Path | None = None,
) -> list[NextAction]:
    """Get the next lifecycle action based on active specs.

    Scans ``.claude/plans/`` for spec files with XML task blocks.
    If an active spec exists and contains task definitions, suggests
    the next logical workflow based on lifecycle ordering.

    Args:
        workflow_name: The workflow that just completed.
        workspace_root: Project root directory. Defaults to cwd.

    Returns:
        List containing 0 or 1 NextAction for the next
        lifecycle stage. Empty if no spec is active or the
        workflow isn't in the lifecycle.

    """
    from attune.workflows.data_classes import NextAction

    root = workspace_root or Path.cwd()
    plans_dir = root / ".claude" / "plans"
    if not plans_dir.exists():
        return []

    # Determine next lifecycle stage
    try:
        idx = _LIFECYCLE_ORDER.index(workflow_name)
    except ValueError:
        return []
    next_idx = idx + 1
    if next_idx >= len(_LIFECYCLE_ORDER):
        return []
    next_workflow = _LIFECYCLE_ORDER[next_idx]

    # Find the most recently modified spec with tasks
    active_spec = _find_active_spec(plans_dir)
    if active_spec is None:
        return []

    return [
        NextAction(
            workflow_name=next_workflow,
            description=(
                f"Your spec ({active_spec.stem}) has work remaining "
                f"— {next_workflow} is the next stage."
            ),
            reasoning=f"Active spec detected in {active_spec.name}.",
            priority="high",
            confidence=0.9,
        ),
    ]


def _find_active_spec(plans_dir: Path) -> Path | None:
    """Find the most recent spec file with XML task blocks.

    Args:
        plans_dir: Path to .claude/plans/ directory.

    Returns:
        Path to the most recent spec file, or None.

    """
    from attune.security.path_validation import _validate_file_path

    best: tuple[float, Path] | None = None
    for md_file in plans_dir.glob("*.md"):
        try:
            _validate_file_path(str(md_file), allowed_dir=str(plans_dir))
            content = md_file.read_text(encoding="utf-8")
            if "<task " in content:
                mtime = md_file.stat().st_mtime
                if best is None or mtime > best[0]:
                    best = (mtime, md_file)
        except (OSError, ValueError) as e:
            logger.debug("Could not read spec %s: %s", md_file, e)

    return best[1] if best else None
