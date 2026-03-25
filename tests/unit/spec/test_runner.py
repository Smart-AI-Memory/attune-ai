"""Tests for spec execution runner."""

from __future__ import annotations

from attune.spec.runner import get_pending_tasks
from attune.spec.state import SpecState
from attune.wizards.decomposer import DecomposedTask


def _make_task(task_id: str) -> DecomposedTask:
    """Build a minimal DecomposedTask."""
    return DecomposedTask(
        task_id=task_id,
        name=f"task-{task_id}",
        objective="Test",
        files_to_create=[],
        files_to_modify=[],
        validation_checks=[],
        risks=[],
        dependencies=[],
    )


class TestGetPendingTasks:
    """Tests for get_pending_tasks."""

    def test_filters_completed(self):
        """Completed task IDs are excluded."""
        tasks = [_make_task("1"), _make_task("2"), _make_task("3")]
        state = SpecState(plan_path="x", completed=["1", "2"])

        pending = get_pending_tasks(tasks, state)
        assert len(pending) == 1
        assert pending[0].task_id == "3"

    def test_empty_state_returns_all(self):
        """Empty completed list returns all tasks."""
        tasks = [_make_task("1"), _make_task("2")]
        state = SpecState(plan_path="x")

        pending = get_pending_tasks(tasks, state)
        assert len(pending) == 2

    def test_all_completed_returns_empty(self):
        """All tasks completed returns empty list."""
        tasks = [_make_task("1"), _make_task("2")]
        state = SpecState(plan_path="x", completed=["1", "2"])

        pending = get_pending_tasks(tasks, state)
        assert pending == []

    def test_preserves_order(self):
        """Pending tasks maintain original order."""
        tasks = [_make_task("3"), _make_task("1"), _make_task("2")]
        state = SpecState(plan_path="x", completed=["1"])

        pending = get_pending_tasks(tasks, state)
        assert [t.task_id for t in pending] == ["3", "2"]

    def test_stale_completed_ids_ignored(self):
        """Completed IDs not in tasks are harmlessly ignored."""
        tasks = [_make_task("1")]
        state = SpecState(plan_path="x", completed=["999"])

        pending = get_pending_tasks(tasks, state)
        assert len(pending) == 1
