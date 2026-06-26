"""Pipeline orchestrator.

Executes an XML task spec with quality gates, per-task
testing, and code simplification. The quality gate runs the
real ``CodeReviewWorkflow`` and ``SecurityAuditWorkflow`` over
each task's target files and gates on their actual 0-100 scores.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from attune.pipeline.models import PipelineResult, TaskResult
from attune.pipeline.spec_reader import read_spec
from attune.wizards.decomposer import DecomposedTask

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Executes tasks from an XML spec with quality gates.

    The orchestrator does NOT execute the tasks themselves
    (that's Claude's job). It runs the quality enforcement
    loop: quality gate, per-task tests, and simplification.

    Args:
        spec_path: Path to a plan file with XML tasks.
        skip_gates: Skip the code-review + security-audit gate.
        skip_tests: Skip per-task test runs.
        skip_simplify: Skip code simplification.

    Example::

        orch = PipelineOrchestrator(".claude/plans/my-spec.md")
        result = await orch.run_gates_for_task(task)
        print(result)

    """

    def __init__(
        self,
        spec_path: str,
        *,
        skip_gates: bool = False,
        skip_tests: bool = False,
        skip_simplify: bool = False,
    ) -> None:
        """Initialize the pipeline orchestrator.

        Args:
            spec_path: Path to the pipeline spec markdown file.
            skip_gates: Skip quality gate checks.
            skip_tests: Skip test generation/execution.
            skip_simplify: Skip code simplification pass.
        """
        self.spec_path = spec_path
        self.tasks = read_spec(spec_path)
        self.skip_gates = skip_gates
        self.skip_tests = skip_tests
        self.skip_simplify = skip_simplify
        self.results: list[TaskResult] = []

    #: Valid decisions returned by on_task_complete callbacks.
    TaskDecision = Literal["approve", "redo", "auto", "stop"]

    #: Callback type for on_task_complete: receives (task, result),
    #: returns a decision string or None.
    TaskCallback = Callable[
        [DecomposedTask, TaskResult],
        Awaitable[TaskDecision | None],
    ]

    async def run_all(
        self,
        *,
        on_task_complete: TaskCallback | None = None,
        skip_task_ids: set[str] | None = None,
    ) -> PipelineResult:
        """Run quality gates for all tasks sequentially.

        Args:
            on_task_complete: Optional async callback called after
                each task completes. Receives ``(task, result)`` and
                returns a decision string:
                - ``"approve"`` or ``None``: continue to next task
                - ``"redo"``: re-run the same task (single retry)
                - ``"auto"``: approve and skip future callbacks
                - ``"stop"``: stop the pipeline
            skip_task_ids: Set of task IDs to skip (already
                completed). Used for resume-from-checkpoint.

        Returns:
            PipelineResult with per-task outcomes.

        """
        self.results = []  # Reset to avoid state leak on reuse
        start = time.monotonic()
        skip = skip_task_ids or set()
        auto_run = False

        for task in self.tasks:
            if task.task_id in skip:
                logger.info("Skipping completed task %s", task.task_id)
                continue

            result = await self.run_gates_for_task(task)
            self.results.append(result)

            if result.quality_gate_passed is False:
                logger.warning(
                    "Task %s failed quality gate — stopping",
                    task.task_id,
                )
                break

            # Approval callback (when provided and not in auto-run mode)
            if on_task_complete is not None and not auto_run:
                decision = await on_task_complete(task, result)
                if decision == "redo":
                    # Remove the result and re-run
                    self.results.pop()
                    result = await self.run_gates_for_task(task)
                    self.results.append(result)
                elif decision == "auto":
                    auto_run = True
                elif decision == "stop":
                    break

        duration_ms = int((time.monotonic() - start) * 1000)
        total_cost = sum(r.cost for r in self.results)

        return PipelineResult(
            spec_path=self.spec_path,
            tasks=self.results,
            total_cost=total_cost,
            duration_ms=duration_ms,
        )

    async def run_gates_for_task(
        self,
        task: DecomposedTask,
    ) -> TaskResult:
        """Run quality gate, tests, and simplify for one task.

        Args:
            task: The decomposed task to validate.

        Returns:
            TaskResult with gate/test outcomes.

        """
        result = TaskResult(
            task_id=task.task_id,
            task_name=task.name,
            executed=True,
        )

        # 1. Quality gate
        if not self.skip_gates:
            try:
                gate_passed, gate_details, cost = await self._run_quality_gate(task)
                result.quality_gate_passed = gate_passed
                result.gate_details = gate_details
                result.cost = cost

                gate_results = gate_details.get("gate_results", {})
                if gate_results:
                    result.gate_score = min(
                        (
                            v["score"]
                            for v in gate_results.values()
                            if isinstance(v, dict) and "score" in v
                        ),
                        default=None,
                    )

                if not gate_passed:
                    return result
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Quality gate failure should not crash pipeline
                logger.error(
                    "Quality gate failed for task %s: %s",
                    task.task_id,
                    e,
                )
                result.quality_gate_passed = False
                result.error = f"Gate error: {e}"
                return result

        # 2. Per-task tests
        if not self.skip_tests:
            test_files = self._find_test_files(task)
            if test_files:
                result.tests_passed = self._run_tests(test_files)
                if not result.tests_passed:
                    return result

        # 3. Simplify
        if not self.skip_simplify:
            source_files = self._get_source_files(task)
            if source_files:
                try:
                    await self._run_simplify(source_files)
                    result.simplified = True
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Simplification is optional; don't block pipeline
                    logger.warning(
                        "Simplify failed for task %s: %s",
                        task.task_id,
                        e,
                    )

        return result

    #: Minimum passing score (0-100) for each gate dimension.
    _GATE_THRESHOLD: float = 70.0
    #: Cap on files reviewed per gate to bound cost (logged when hit).
    _GATE_MAX_FILES: int = 10

    async def _run_quality_gate(
        self,
        task: DecomposedTask,
    ) -> tuple[bool, dict[str, Any], float]:
        """Gate a task with a real code-review + security-audit team.

        Builds a two-agent ``AgentTeam`` (``code-review`` +
        ``security-audit``) over the task's target files and gates on
        their actual 0-100 scores against ``_GATE_THRESHOLD``. Fails
        closed: any review error or a missing score makes the relevant
        agent unsuccessful, which fails the gate — never a fake pass.

        Returns:
            Tuple of (passed, details_dict, cost).

        """
        from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
        from attune.workflows.code_review import CodeReviewWorkflow
        from attune.workflows.security_audit import SecurityAuditWorkflow

        target_files = [f["path"] for f in task.files_to_create + task.files_to_modify]
        if not target_files:
            # No file changes — nothing to score, so the gate passes
            # trivially rather than failing closed on an empty review.
            return (True, {"reason": "no target files"}, 0.0)

        files = target_files[: self._GATE_MAX_FILES]
        if len(target_files) > self._GATE_MAX_FILES:
            logger.warning(
                "Quality gate capped at %d of %d files for task %s",
                self._GATE_MAX_FILES,
                len(target_files),
                task.task_id,
            )

        # Each agent runs its workflow over the file set and reports the
        # worst (min) score; fail-closed-on-error lives in WorkflowAgent.
        team = AgentTeam(
            agents=[
                WorkflowAgent("code-review", CodeReviewWorkflow, files=files),
                WorkflowAgent("security-audit", SecurityAuditWorkflow, files=files),
            ],
            gates=[
                GateSpec("Code Quality", "code-review", self._GATE_THRESHOLD),
                GateSpec("Security", "security-audit", self._GATE_THRESHOLD),
            ],
        )
        report = await team.run(files)

        by_key = {r.key: r for r in report.results}
        quality = by_key.get("code-review")
        security = by_key.get("security-audit")
        quality_score = quality.score if quality and quality.success else None
        security_score = security.score if security and security.success else None

        details = {
            "gate_results": {
                "min_quality": {
                    "score": quality_score if quality_score is not None else 0.0,
                    "threshold": self._GATE_THRESHOLD,
                },
                "min_security": {
                    "score": security_score if security_score is not None else 0.0,
                    "threshold": self._GATE_THRESHOLD,
                },
            },
            "files_reviewed": files,
            "scored": quality_score is not None and security_score is not None,
        }
        return (report.passed, details, report.cost)

    @classmethod
    def _extract_score(cls, result: Any) -> float | None:
        """Pull the 0-100 score from a review ``WorkflowResult``.

        Delegates to the shared ``attune.agents.team.extract_score`` (D5),
        the single canonical extractor both the team and this gate use.
        Retained as a stable entry point for callers and tests. Returns
        None when the review did not succeed or carried no score, so the
        caller fails the gate closed.
        """
        from attune.agents.team import extract_score

        return extract_score(result)

    def _find_test_files(
        self,
        task: DecomposedTask,
    ) -> list[str]:
        """Find test files related to a task's source files.

        Looks for test files matching the task's created/modified
        files using the ``tests/unit/`` convention.

        Args:
            task: Task to find tests for.

        Returns:
            List of test file paths.

        """
        test_files = []
        all_files = task.files_to_create + task.files_to_modify

        for file_entry in all_files:
            path = file_entry["path"]

            # If it's already a test file, include it
            if "test_" in Path(path).name:
                test_files.append(path)
                continue

            # Map src/attune/foo/bar.py -> tests/unit/foo/test_bar.py
            if path.startswith("src/attune/"):
                relative = path[len("src/attune/") :]
                parts = Path(relative).parts
                if len(parts) >= 1:
                    test_name = f"test_{parts[-1]}"
                    test_dir = "/".join(parts[:-1])
                    candidate = (
                        f"tests/unit/{test_dir}/{test_name}"
                        if test_dir
                        else f"tests/unit/{test_name}"
                    )
                    if Path(candidate).exists():
                        test_files.append(candidate)

        return test_files

    def _run_tests(self, test_files: list[str]) -> bool:
        """Run pytest on specific test files.

        Args:
            test_files: Paths to test files to run.

        Returns:
            True if all tests pass.

        """
        cmd = ["uv", "run", "pytest", *test_files, "-x", "-q"]
        logger.info("Running tests: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.warning("Tests failed:\n%s", result.stdout)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error("Test run timed out after 300s")
            return False

    def _get_source_files(
        self,
        task: DecomposedTask,
    ) -> list[str]:
        """Get source (non-test) files from a task.

        Args:
            task: Task to extract source files from.

        Returns:
            List of source file paths.

        """
        files = []
        for f in task.files_to_create + task.files_to_modify:
            path = f["path"]
            if path.endswith(".py") and "test_" not in Path(path).name:
                files.append(path)
        return files

    async def _run_simplify(
        self,
        source_files: list[str],
    ) -> None:
        """Run SimplifyCodeWorkflow on source files.

        Args:
            source_files: Python files to simplify.

        """
        from attune.workflows.simplify_code import (
            SimplifyCodeWorkflow,
        )

        workflow = SimplifyCodeWorkflow()
        for path in source_files:
            try:
                await workflow.execute(path=path)
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Per-file simplify failure is non-fatal
                logger.warning("Simplify failed for %s: %s", path, e)
