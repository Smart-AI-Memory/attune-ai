"""Tests for pipeline result models."""

from attune.pipeline.models import PipelineResult, TaskResult


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_defaults(self):
        """TaskResult has sensible defaults."""
        r = TaskResult(task_id="1", task_name="test")
        assert not r.executed
        assert r.quality_gate_passed is None
        assert r.tests_passed is None
        assert not r.simplified
        assert r.error is None
        assert r.cost == 0.0

    def test_all_fields(self):
        """TaskResult stores all provided fields."""
        r = TaskResult(
            task_id="2",
            task_name="build",
            executed=True,
            quality_gate_passed=True,
            tests_passed=True,
            simplified=True,
            gate_details={"score": 95},
            gate_score=95.0,
            cost=0.05,
        )
        assert r.executed
        assert r.quality_gate_passed
        assert r.gate_details == {"score": 95}
        assert r.gate_score == 95.0
        assert r.cost == 0.05


class TestTaskResultSeverity:
    """Tests for TaskResult.severity property."""

    def test_passed_gate_is_low(self):
        """Passed gate is always low severity."""
        r = TaskResult(task_id="1", task_name="t", quality_gate_passed=True)
        assert r.severity == "low"

    def test_skipped_gate_is_low(self):
        """Skipped gate (None) is low severity."""
        r = TaskResult(task_id="1", task_name="t", quality_gate_passed=None)
        assert r.severity == "low"

    def test_failed_no_score_is_high(self):
        """Failed gate with no score is high severity."""
        r = TaskResult(task_id="1", task_name="t", quality_gate_passed=False)
        assert r.severity == "high"

    def test_failed_low_score_is_high(self):
        """Failed gate with score < 50 is high severity."""
        r = TaskResult(
            task_id="1",
            task_name="t",
            quality_gate_passed=False,
            gate_score=30,
        )
        assert r.severity == "high"

    def test_failed_medium_score(self):
        """Failed gate with score 50-69 is medium severity."""
        r = TaskResult(
            task_id="1",
            task_name="t",
            quality_gate_passed=False,
            gate_score=55,
        )
        assert r.severity == "medium"

    def test_failed_high_score_is_low(self):
        """Failed gate with score >= 70 is low severity."""
        r = TaskResult(
            task_id="1",
            task_name="t",
            quality_gate_passed=False,
            gate_score=75,
        )
        assert r.severity == "low"

    def test_boundary_50_is_medium(self):
        """Score exactly 50 is medium, not high."""
        r = TaskResult(
            task_id="1",
            task_name="t",
            quality_gate_passed=False,
            gate_score=50,
        )
        assert r.severity == "medium"

    def test_boundary_70_is_low(self):
        """Score exactly 70 is low, not medium."""
        r = TaskResult(
            task_id="1",
            task_name="t",
            quality_gate_passed=False,
            gate_score=70,
        )
        assert r.severity == "low"


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_success_all_passed(self):
        """Success is True when all tasks pass."""
        result = PipelineResult(
            spec_path="test.md",
            tasks=[
                TaskResult("1", "a", executed=True, quality_gate_passed=True),
                TaskResult("2", "b", executed=True, quality_gate_passed=True),
            ],
        )
        assert result.success

    def test_success_with_none_gate(self):
        """Success is True when gates were skipped (None)."""
        result = PipelineResult(
            spec_path="test.md",
            tasks=[
                TaskResult("1", "a", executed=True, quality_gate_passed=None),
            ],
        )
        assert result.success

    def test_failure_gate_failed(self):
        """Success is False when any gate fails."""
        result = PipelineResult(
            spec_path="test.md",
            tasks=[
                TaskResult("1", "a", executed=True, quality_gate_passed=True),
                TaskResult("2", "b", executed=True, quality_gate_passed=False),
            ],
        )
        assert not result.success

    def test_failure_not_executed(self):
        """Success is False when a task wasn't executed."""
        result = PipelineResult(
            spec_path="test.md",
            tasks=[
                TaskResult("1", "a", executed=False),
            ],
        )
        assert not result.success

    def test_empty_tasks_is_success(self):
        """Empty task list counts as success (vacuous truth)."""
        result = PipelineResult(spec_path="test.md")
        assert result.success

    def test_summary(self):
        """Summary includes counts and cost."""
        result = PipelineResult(
            spec_path="test.md",
            tasks=[
                TaskResult("1", "a", executed=True, quality_gate_passed=True),
                TaskResult("2", "b", executed=True, quality_gate_passed=False),
                TaskResult("3", "c", executed=False),
            ],
            total_cost=0.123,
            duration_ms=5000,
        )
        s = result.summary
        assert "1 passed" in s
        assert "1 failed" in s
        assert "1 skipped" in s
        assert "$0.1230" in s
