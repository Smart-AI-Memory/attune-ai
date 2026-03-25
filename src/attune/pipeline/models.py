"""Pipeline result models.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskResult:
    """Result of executing a single pipeline task.

    Args:
        task_id: Unique task identifier from the spec.
        task_name: Short task name from the spec.
        executed: Whether the task was executed.
        quality_gate_passed: Whether the quality gate passed
            (None if not run).
        tests_passed: Whether per-task tests passed
            (None if not run).
        simplified: Whether simplification was applied.
        gate_details: Quality gate findings from agent team.
        gate_score: Minimum score across gate results
            (None if gates were not run).
        error: Error message if the task failed.
        cost: Cost in USD for this task's gate execution.

    """

    task_id: str
    task_name: str
    executed: bool = False
    quality_gate_passed: bool | None = None
    tests_passed: bool | None = None
    simplified: bool = False
    gate_details: dict | None = None
    gate_score: float | None = None
    error: str | None = None
    cost: float = 0.0

    @property
    def severity(self) -> str:
        """Classify gate result severity.

        Returns:
            ``"high"`` if gate score < 50 or gate failed
            with no score, ``"medium"`` if score 50-69,
            ``"low"`` if score >= 70 or gate passed/skipped.

        """
        if self.quality_gate_passed is True:
            return "low"
        if self.quality_gate_passed is None:
            return "low"
        if self.gate_score is not None:
            if self.gate_score < 50:
                return "high"
            if self.gate_score < 70:
                return "medium"
            return "low"
        return "high"


@dataclass
class PipelineResult:
    """Aggregated result from a full pipeline run.

    Args:
        spec_path: Path to the spec file that was executed.
        tasks: Results for each task in the spec.
        total_cost: Total cost in USD across all tasks.
        duration_ms: Total execution time in milliseconds.

    """

    spec_path: str
    tasks: list[TaskResult] = field(default_factory=list)
    total_cost: float = 0.0
    duration_ms: int = 0

    @property
    def success(self) -> bool:
        """Whether all tasks executed and passed gates."""
        return all(t.executed and t.quality_gate_passed is not False for t in self.tasks)

    @property
    def summary(self) -> str:
        """Human-readable summary of the pipeline run."""
        passed = sum(1 for t in self.tasks if t.quality_gate_passed)
        failed = sum(1 for t in self.tasks if t.quality_gate_passed is False)
        skipped = sum(1 for t in self.tasks if not t.executed)
        return (
            f"{len(self.tasks)} tasks: "
            f"{passed} passed, {failed} failed, "
            f"{skipped} skipped | "
            f"${self.total_cost:.4f} | "
            f"{self.duration_ms}ms"
        )
