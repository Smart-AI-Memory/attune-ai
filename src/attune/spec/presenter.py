"""Human-readable task presentation for spec-driven development.

Formats tasks from plan files into markdown tables,
detail views, and progress indicators for the ``/spec``
command's review and execute stages.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune.pipeline.models import TaskResult
    from attune.spec.state import SpecState
    from attune.wizards.decomposer import DecomposedTask


def present_tasks(
    tasks: list[DecomposedTask],
    state: SpecState | None = None,
) -> str:
    """Format all tasks as a human-readable markdown table.

    Args:
        tasks: List of DecomposedTask from read_spec().
        state: Optional execution state for status markers.

    Returns:
        Markdown table with Status, ID, Name, and Objective.

    """
    completed = set(state.completed) if state else set()
    current = state.current if state else None

    lines = [
        "| Status | ID | Name | Objective |",
        "|--------|----|------|-----------|",
    ]

    for task in tasks:
        if task.task_id in completed:
            status = "done"
        elif task.task_id == current:
            status = ">>>"
        else:
            status = "..."
        objective = task.objective[:60] + ("..." if len(task.objective) > 60 else "")
        lines.append(f"| {status} | {task.task_id} | {task.name} | {objective} |")

    return "\n".join(lines)


def present_task_detail(task: DecomposedTask) -> str:
    """Format a single task with full details.

    Args:
        task: DecomposedTask to display.

    Returns:
        Markdown-formatted detail view.

    """
    lines = [
        f"### Task {task.task_id}: {task.name}",
        "",
        f"**Objective:** {task.objective}",
    ]

    if task.files_to_create:
        lines.append("")
        lines.append("**Files to create:**")
        for f in task.files_to_create:
            lines.append(f"- `{f.get('path', 'unknown')}` — {f.get('description', '')}")

    if task.files_to_modify:
        lines.append("")
        lines.append("**Files to modify:**")
        for f in task.files_to_modify:
            lines.append(f"- `{f.get('path', 'unknown')}` — {f.get('description', '')}")

    if task.validation_checks:
        lines.append("")
        lines.append("**Validation:**")
        for check in task.validation_checks:
            lines.append(f"- {check}")

    if task.risks:
        lines.append("")
        lines.append("**Risks:**")
        for risk in task.risks:
            severity = risk.get("severity", "unknown")
            desc = risk.get("description", "")
            lines.append(f"- [{severity}] {desc}")

    if task.dependencies:
        lines.append("")
        lines.append(f"**Depends on:** {', '.join(task.dependencies)}")

    return "\n".join(lines)


def present_task_result(
    task: DecomposedTask,
    gate_result: TaskResult,
) -> str:
    """Format a task's execution result with quality gate status.

    Args:
        task: The task that was executed.
        gate_result: TaskResult from the quality gate.

    Returns:
        Markdown-formatted result summary.

    """
    lines = [f"### Result: Task {task.task_id} — {task.name}", ""]

    severity = gate_result.severity
    if gate_result.quality_gate_passed is True:
        lines.append("Quality gate: **PASSED**")
    elif gate_result.quality_gate_passed is False:
        score_str = (
            f" (score: {gate_result.gate_score:.0f})" if gate_result.gate_score is not None else ""
        )
        if severity == "high":
            lines.append(f"Quality gate: **FAILED — HIGH SEVERITY**{score_str}")
            lines.append("This needs to be fixed before continuing.")
        else:
            lines.append(f"Quality gate: **WARNING**{score_str}")
            lines.append("Findings detected but not blocking.")
        if gate_result.gate_details:
            for key, value in gate_result.gate_details.items():
                lines.append(f"  - {key}: {value}")
    else:
        lines.append("Quality gate: skipped")

    if gate_result.tests_passed is True:
        lines.append("Tests: **PASSED**")
    elif gate_result.tests_passed is False:
        lines.append("Tests: **FAILED**")
    elif gate_result.tests_passed is None:
        lines.append("Tests: skipped")

    if gate_result.cost > 0:
        lines.append(f"Cost: ${gate_result.cost:.4f}")

    if gate_result.error:
        lines.append(f"Error: {gate_result.error}")

    return "\n".join(lines)


def format_progress_bar(completed: int, total: int) -> str:
    """Visual progress indicator for task execution.

    Args:
        completed: Number of completed tasks.
        total: Total number of tasks.

    Returns:
        Progress bar string like ``[####....] 4/8 tasks``.

    """
    if total <= 0:
        return "[........] 0/0 tasks"

    filled = int(8 * completed / total)
    empty = 8 - filled
    return f"[{'#' * filled}{'.' * empty}] {completed}/{total} tasks"
