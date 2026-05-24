"""Execution state persistence for spec-driven development.

Reads and writes execution state as an HTML comment inside
plan files (``.claude/plans/*.md``). The comment is invisible
in rendered markdown and ignored by ``read_spec()`` which
only parses ``<task>`` elements.

Format::

    <!-- spec-state: {"schema_version":1,"completed":["1","2"],...} -->

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_PATTERN = re.compile(r"<!-- spec-state:\s*(\{.*?\})\s*-->")

# Bump when on-disk shape changes. ``load_state`` accepts older
# versions for back-compat; ``save_state`` always writes the current
# version. Keeping the field reserved now (while there are no
# consumers branching on it) is cheap; retrofitting it after a real
# migration is not.
_CURRENT_SCHEMA_VERSION = 1


@dataclass
class SpecState:
    """Execution state for a spec plan.

    Args:
        plan_path: Path to the plan file.
        completed: Task IDs that have been approved.
        current: Task ID currently being executed.
        auto_run: Whether to skip approval for remaining tasks.
        last_updated: ISO UTC timestamp of last state change.
        schema_version: On-disk format version. Defaults to the
            current writer version; loaders may set this lower
            when reading a back-compat payload.

    """

    plan_path: str
    completed: list[str] = field(default_factory=list)
    current: str | None = None
    auto_run: bool = False
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    schema_version: int = _CURRENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-safe dict (excludes plan_path)."""
        return {
            "schema_version": self.schema_version,
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
        Returns None for malformed JSON, type-invalid payloads,
        and unreadable files (a warning is logged so callers can
        observe the failure even though the contract is None).

    Raises:
        ValueError: If ``plan_path`` fails path validation.

    """
    # Deferred to avoid circular import: attune.security depends on
    # attune.spec via the workflows registry; importing it at module
    # load time would create a cycle. The lookup cost is amortized
    # since CPython caches sys.modules entries.
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

    if not isinstance(data, dict):
        logger.warning(
            "spec-state in %s is not a JSON object (got %s)",
            plan_path,
            type(data).__name__,
        )
        return None

    completed_raw = data.get("completed", [])
    if not isinstance(completed_raw, list) or not all(
        isinstance(item, str) for item in completed_raw
    ):
        logger.warning(
            "spec-state 'completed' in %s is not list[str]; ignoring",
            plan_path,
        )
        return None

    current_raw = data.get("current")
    if current_raw is not None and not isinstance(current_raw, str):
        logger.warning(
            "spec-state 'current' in %s is not str|None; ignoring",
            plan_path,
        )
        return None

    return SpecState(
        plan_path=plan_path,
        completed=list(completed_raw),
        current=current_raw,
        auto_run=bool(data.get("auto_run", False)),
        last_updated=str(data.get("last_updated", "")),
        schema_version=int(data.get("schema_version", 0)),
    )


def save_state(state: SpecState) -> None:
    """Write or update the spec-state comment in a plan file.

    Replaces an existing comment if present, otherwise appends to
    the end of the file. The write goes through a sibling temp
    file and ``os.replace`` so a concurrent reader never observes
    a half-written plan and so a mid-write crash never leaves the
    plan corrupted.

    Args:
        state: SpecState to persist. ``state.last_updated`` is
            mutated as a side effect — callers that need to keep
            the prior timestamp should copy first.

    Raises:
        ValueError: If ``state.plan_path`` fails path validation.
        OSError: If the read, temp-write, or atomic replace fails.

    """
    # Deferred to avoid circular import — see load_state comment.
    from attune.security.path_validation import _validate_file_path

    state.last_updated = datetime.now(timezone.utc).isoformat()
    state.schema_version = _CURRENT_SCHEMA_VERSION
    validated = _validate_file_path(state.plan_path)

    content = validated.read_text(encoding="utf-8")
    comment = f"<!-- spec-state: {json.dumps(state.to_dict())} -->"

    if _STATE_PATTERN.search(content):
        content = _STATE_PATTERN.sub(comment, content)
    else:
        content = content.rstrip() + f"\n\n{comment}\n"

    _atomic_write_text(validated, content)


def clear_state(plan_path: str) -> None:
    """Remove the spec-state comment from a plan file.

    Args:
        plan_path: Path to the plan file.

    Raises:
        ValueError: If ``plan_path`` fails path validation.
        OSError: If the read, temp-write, or atomic replace fails.

    """
    # Deferred to avoid circular import — see load_state comment.
    from attune.security.path_validation import _validate_file_path

    validated = _validate_file_path(plan_path)
    content = validated.read_text(encoding="utf-8")

    if not _STATE_PATTERN.search(content):
        return

    content = _STATE_PATTERN.sub("", content).rstrip() + "\n"
    _atomic_write_text(validated, content)


def find_resumable_plans(plans_dir: str = ".claude/plans") -> list[SpecState]:
    """Find plan files with incomplete execution state.

    Scans for plans that have a spec-state comment with
    fewer completed tasks than total tasks in the spec.

    Args:
        plans_dir: Directory to scan for plan files. Validated
            through ``_validate_file_path`` and required to be
            an existing directory.

    Returns:
        List of SpecState objects for resumable plans. Plans that
        fail to parse via ``read_spec`` are logged at WARNING and
        skipped — they do not abort the scan.

    Raises:
        ValueError: If ``plans_dir`` fails path validation.

    """
    # Deferred to avoid circular import: pipeline.spec_reader sits
    # below spec.state in the layering we want but currently
    # imports through here. The architectural fix (extract a
    # plans/ package that both depend on) is tracked separately.
    from attune.pipeline.spec_reader import read_spec
    from attune.security.path_validation import _validate_file_path

    plans_path = _validate_file_path(plans_dir)
    if not plans_path.exists() or not plans_path.is_dir():
        return []

    resumable: list[SpecState] = []
    for md_file in plans_path.glob("*.md"):
        state = load_state(str(md_file))
        if state is None:
            continue

        # Check if there are still pending tasks
        try:
            tasks = read_spec(str(md_file))
        except (FileNotFoundError, ValueError) as e:
            logger.warning(
                "skipping resumable-plan candidate %s: %s",
                md_file,
                e,
            )
            continue

        if not tasks:
            continue

        task_ids = {t.task_id for t in tasks}
        completed_ids = set(state.completed)
        if completed_ids < task_ids:
            resumable.append(state)

    return resumable


def _atomic_write_text(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` atomically.

    Uses ``tempfile.mkstemp`` in the same directory followed by
    ``os.replace`` so a concurrent reader never sees a partial
    file. Matches the pattern used elsewhere in the codebase
    (``ops.dismiss_store._write_atomic``).

    Raises:
        OSError: If the temp-write or replace fails. The temp
            file is cleaned up before re-raising.

    """
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_name, target)
    except OSError:
        # Best-effort cleanup of the partial temp file. We intentionally
        # swallow this inner OSError (the temp file may already be gone
        # if the first failure was mid-replace) and re-raise the outer
        # one so the caller learns the write didn't happen — but log the
        # cleanup failure at debug so it stays observable in noisy runs.
        try:
            os.unlink(tmp_name)
        except OSError as cleanup_err:
            logger.debug(
                "Failed to unlink temp file %s after write error: %s",
                tmp_name,
                cleanup_err,
            )
        raise
