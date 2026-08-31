"""Spec-driven development for Attune AI.

Provides state persistence, task presentation, and
execution with per-task approval for the ``/spec`` command.

Public API::

    from attune.spec import (
        SpecState, load_state, save_state, find_resumable_plans,
        present_tasks, present_task_detail, present_task_result,
        get_pending_tasks,
    )

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from .presenter import (
    format_progress_bar,
    present_task_detail,
    present_task_result,
    present_tasks,
)
from .runner import get_pending_tasks
from .state import (
    SpecState,
    clear_state,
    find_resumable_plans,
    load_state,
    save_state,
)
from .workspace import (
    SpecArtifactReceipt,
    SpecLifecycleReceipt,
    SpecTaskGateReceipt,
    SpecWorkspaceAdapter,
    SpecWorkspaceState,
)

__all__ = [
    "SpecState",
    "SpecArtifactReceipt",
    "SpecLifecycleReceipt",
    "SpecTaskGateReceipt",
    "SpecWorkspaceAdapter",
    "SpecWorkspaceState",
    "clear_state",
    "find_resumable_plans",
    "format_progress_bar",
    "get_pending_tasks",
    "load_state",
    "present_task_detail",
    "present_task_result",
    "present_tasks",
    "save_state",
]
