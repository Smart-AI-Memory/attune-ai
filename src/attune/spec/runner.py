"""Spec execution runner with approval loop.

Provides helpers for filtering pending tasks and running
a spec with per-task approval. The command file (``/spec``)
drives the interactive loop via ``AskUserQuestion``; this
module provides the programmatic API for CLI/automation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune.pipeline.models import PipelineResult
    from attune.spec.state import SpecState
    from attune.wizards.decomposer import DecomposedTask

logger = logging.getLogger(__name__)


def get_pending_tasks(
    tasks: list[DecomposedTask],
    state: SpecState,
) -> list[DecomposedTask]:
    """Filter tasks to only those not yet completed.

    Args:
        tasks: All tasks from the spec.
        state: Current execution state.

    Returns:
        Tasks whose IDs are not in state.completed.

    """
    completed = set(state.completed)
    return [t for t in tasks if t.task_id not in completed]


async def execute_with_approval(
    spec_path: str,
    on_task_complete: object,
    *,
    skip_gates: bool = False,
    skip_tests: bool = False,
    skip_simplify: bool = False,
) -> PipelineResult:
    """Execute a spec with per-task approval.

    Wraps ``PipelineOrchestrator.run_all()`` with state
    persistence. Loads existing state for resume support.

    Args:
        spec_path: Path to the plan file.
        on_task_complete: Async callback ``(task, result)``
            returning ``"approve"`` / ``"redo"`` / ``"auto"``
            / ``"stop"``.
        skip_gates: Skip quality gate checks.
        skip_tests: Skip per-task tests.
        skip_simplify: Skip code simplification.

    Returns:
        PipelineResult with all task outcomes.

    """
    from attune.pipeline.orchestrator import PipelineOrchestrator
    from attune.spec.state import SpecState, load_state, save_state

    # Load existing state for resume
    state = load_state(spec_path) or SpecState(plan_path=spec_path)
    skip_ids = set(state.completed)

    orch = PipelineOrchestrator(
        spec_path,
        skip_gates=skip_gates,
        skip_tests=skip_tests,
        skip_simplify=skip_simplify,
    )

    async def _wrapped_callback(task: object, result: object) -> str:
        """Wrap user callback with state persistence."""
        state.current = task.task_id  # type: ignore[union-attr]
        save_state(state)

        decision = await on_task_complete(task, result)  # type: ignore[misc]

        if decision in ("approve", "auto", None):
            state.completed.append(task.task_id)  # type: ignore[union-attr]
            if decision == "auto":
                state.auto_run = True
            state.current = None
            save_state(state)

        return decision or "approve"

    result = await orch.run_all(
        on_task_complete=_wrapped_callback,
        skip_task_ids=skip_ids,
    )

    return result
