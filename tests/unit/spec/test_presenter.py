"""Tests for spec task presenter."""

from __future__ import annotations

from attune.pipeline.models import TaskResult
from attune.spec.presenter import (
    format_progress_bar,
    present_task_detail,
    present_task_result,
    present_tasks,
)
from attune.spec.state import SpecState
from attune.wizards.decomposer import DecomposedTask


def _make_task(
    task_id: str = "1",
    name: str = "test-task",
    objective: str = "Do something useful",
    **kwargs,
) -> DecomposedTask:
    """Build a minimal DecomposedTask."""
    defaults = {
        "task_id": task_id,
        "name": name,
        "objective": objective,
        "files_to_create": [],
        "files_to_modify": [],
        "validation_checks": [],
        "risks": [],
        "dependencies": [],
    }
    defaults.update(kwargs)
    return DecomposedTask(**defaults)


class TestPresentTasks:
    """Tests for the task table formatter."""

    def test_basic_table(self):
        """Renders a markdown table with all tasks."""
        tasks = [_make_task("1", "first"), _make_task("2", "second")]
        output = present_tasks(tasks)
        assert "| ... | 1 | first |" in output
        assert "| ... | 2 | second |" in output
        assert "Status" in output

    def test_with_state_marks_completed(self):
        """Completed tasks show 'done' status."""
        tasks = [_make_task("1"), _make_task("2")]
        state = SpecState(plan_path="x", completed=["1"], current="2")
        output = present_tasks(tasks, state)
        assert "| done | 1 |" in output
        assert "| >>> | 2 |" in output

    def test_truncates_long_objectives(self):
        """Objectives longer than 60 chars are truncated."""
        long_obj = "x" * 80
        tasks = [_make_task(objective=long_obj)]
        output = present_tasks(tasks)
        assert "..." in output

    def test_no_state_all_pending(self):
        """Without state, all tasks show pending."""
        tasks = [_make_task("1"), _make_task("2")]
        output = present_tasks(tasks)
        assert output.count("| ... |") == 2


class TestPresentTaskDetail:
    """Tests for the task detail view."""

    def test_shows_objective(self):
        """Detail view includes objective."""
        task = _make_task(objective="Build the auth module")
        output = present_task_detail(task)
        assert "Build the auth module" in output

    def test_shows_files_to_create(self):
        """Detail view lists files to create."""
        task = _make_task(
            files_to_create=[{"path": "src/auth.py", "description": "Auth module"}],
        )
        output = present_task_detail(task)
        assert "`src/auth.py`" in output
        assert "Auth module" in output

    def test_shows_files_to_modify(self):
        """Detail view lists files to modify."""
        task = _make_task(
            files_to_modify=[{"path": "src/app.py", "description": "Wire auth"}],
        )
        output = present_task_detail(task)
        assert "`src/app.py`" in output

    def test_shows_risks(self):
        """Detail view lists risks with severity."""
        task = _make_task(
            risks=[{"severity": "medium", "description": "Breaking change"}],
        )
        output = present_task_detail(task)
        assert "[medium]" in output
        assert "Breaking change" in output

    def test_shows_dependencies(self):
        """Detail view lists dependencies."""
        task = _make_task(dependencies=["1", "2"])
        output = present_task_detail(task)
        assert "1, 2" in output

    def test_shows_validation_checks(self):
        """Detail view lists validation checks."""
        task = _make_task(validation_checks=["Run pytest", "Check imports"])
        output = present_task_detail(task)
        assert "Run pytest" in output


class TestPresentTaskResult:
    """Tests for task result formatting."""

    def test_passed_gate(self):
        """Shows PASSED for successful quality gate."""
        task = _make_task()
        result = TaskResult(task_id="1", task_name="t", quality_gate_passed=True)
        output = present_task_result(task, result)
        assert "**PASSED**" in output

    def test_failed_gate_high_severity(self):
        """Shows HIGH SEVERITY for low-scoring gate failure."""
        task = _make_task()
        result = TaskResult(
            task_id="1",
            task_name="t",
            quality_gate_passed=False,
            gate_score=30,
            gate_details={"quality": "below threshold"},
        )
        output = present_task_result(task, result)
        assert "HIGH SEVERITY" in output
        assert "below threshold" in output
        assert "needs to be fixed" in output

    def test_failed_gate_medium_severity(self):
        """Shows WARNING for medium-scoring gate failure."""
        task = _make_task()
        result = TaskResult(
            task_id="1",
            task_name="t",
            quality_gate_passed=False,
            gate_score=55,
        )
        output = present_task_result(task, result)
        assert "**WARNING**" in output
        assert "not blocking" in output

    def test_shows_cost(self):
        """Shows cost when non-zero."""
        task = _make_task()
        result = TaskResult(task_id="1", task_name="t", cost=0.0123)
        output = present_task_result(task, result)
        assert "$0.0123" in output

    def test_shows_error(self):
        """Shows error message when present."""
        task = _make_task()
        result = TaskResult(task_id="1", task_name="t", error="Timeout")
        output = present_task_result(task, result)
        assert "Timeout" in output

    def test_skipped_gate(self):
        """Shows skipped when gate is None."""
        task = _make_task()
        result = TaskResult(task_id="1", task_name="t")
        output = present_task_result(task, result)
        assert "skipped" in output


class TestFormatProgressBar:
    """Tests for the progress bar."""

    def test_empty(self):
        """Zero progress shows all dots."""
        assert format_progress_bar(0, 8) == "[........] 0/8 tasks"

    def test_half(self):
        """Half progress shows half filled."""
        assert format_progress_bar(4, 8) == "[####....] 4/8 tasks"

    def test_complete(self):
        """Full progress shows all filled."""
        assert format_progress_bar(8, 8) == "[########] 8/8 tasks"

    def test_zero_total(self):
        """Zero total doesn't divide by zero."""
        assert format_progress_bar(0, 0) == "[........] 0/0 tasks"

    def test_partial(self):
        """Non-even fractions round down."""
        result = format_progress_bar(1, 3)
        assert result.startswith("[##")
        assert "1/3" in result
