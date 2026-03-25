"""Execution state persistence for spec-driven development.

Reads and writes execution state as an HTML comment inside
plan files (``.claude/plans/*.md``). The comment is invisible
in rendered markdown and ignored by ``read_spec()`` which
only parses ``<task>`` elements.

Format::

    <!-- spec-state: {"completed":["1","2"],...} -->

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_PATTERN = re.compile(r"<!-- spec-state:\s*(\{.*?\})\s*-->")


@dataclass
class SpecState:
    """Execution state for a spec plan.

    Args:
        plan_path: Path to the plan file.
        completed: Task IDs that have been approved.
        current: Task ID currently being executed.
        auto_run: Whether to skip approval for remaining tasks.
        last_updated: ISO UTC timestamp of last state change.

    """

    plan_path: str
    completed: list[str] = field(default_factory=list)
    current: str | None = None
    auto_run: bool = False
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict (excludes plan_path)."""
        return {
            "completed": self.completed,
            "current": self.current,
            "auto_run": self.auto_run,
            "last_updated": self.last_updated,
        }


def load_state(plan_path: str) -> SpecState | None:
    """Read spec-state from an HTML comment in a plan file.

    Args:
        plan_path: Path to a ``.claude/plans/*.md`` file.

    Returns:
        SpecState if a state comment was found, None otherwise.

    """
    from attune.security.path_validation import _validate_file_path

    validated = _validate_file_path(plan_path)
    try:
        content = validated.read_text(encoding="utf-8")
    except OSError as e:
        logger.debug("Could not read plan file %s: %s", plan_path, e)
        return None

    match = _STATE_PATTERN.search(content)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.warning("Malformed spec-state in %s: %s", plan_path, e)
        return None

    return SpecState(
        plan_path=plan_path,
        completed=data.get("completed", []),
        current=data.get("current"),
        auto_run=data.get("auto_run", False),
        last_updated=data.get("last_updated", ""),
    )


def save_state(state: SpecState) -> None:
    """Write or update the spec-state comment in a plan file.

    Replaces an existing comment if present, otherwise
    appends to the end of the file.

    Args:
        state: SpecState to persist.

    """
    from attune.security.path_validation import _validate_file_path

    state.last_updated = datetime.now(timezone.utc).isoformat()
    validated = _validate_file_path(state.plan_path)

    content = validated.read_text(encoding="utf-8")
    comment = f"<!-- spec-state: {json.dumps(state.to_dict())} -->"

    if _STATE_PATTERN.search(content):
        content = _STATE_PATTERN.sub(comment, content)
    else:
        content = content.rstrip() + f"\n\n{comment}\n"

    validated.write_text(content, encoding="utf-8")


def clear_state(plan_path: str) -> None:
    """Remove the spec-state comment from a plan file.

    Args:
        plan_path: Path to the plan file.

    """
    from attune.security.path_validation import _validate_file_path

    validated = _validate_file_path(plan_path)
    content = validated.read_text(encoding="utf-8")

    if _STATE_PATTERN.search(content):
        content = _STATE_PATTERN.sub("", content).rstrip() + "\n"
        validated.write_text(content, encoding="utf-8")


def find_resumable_plans(plans_dir: str = ".claude/plans") -> list[SpecState]:
    """Find plan files with incomplete execution state.

    Scans for plans that have a spec-state comment with
    fewer completed tasks than total tasks in the spec.

    Args:
        plans_dir: Directory to scan for plan files.

    Returns:
        List of SpecState objects for resumable plans.

    """
    from attune.pipeline.spec_reader import read_spec

    plans_path = Path(plans_dir)
    if not plans_path.exists():
        return []

    resumable: list[SpecState] = []
    for md_file in plans_path.glob("*.md"):
        state = load_state(str(md_file))
        if state is None:
            continue

        # Check if there are still pending tasks
        try:
            tasks = read_spec(str(md_file))
        except (FileNotFoundError, ValueError):
            continue

        if not tasks:
            continue

        task_ids = {t.task_id for t in tasks}
        completed_ids = set(state.completed)
        if completed_ids < task_ids:
            resumable.append(state)

    return resumable
