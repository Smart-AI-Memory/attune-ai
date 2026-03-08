"""Pipeline orchestrator.

Executes an XML task spec with quality gates, per-task
testing, and code simplification. Delegates to existing
infrastructure (DynamicTeam, WorkflowComposer, agent
templates) rather than reimplementing.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from attune.orchestration.team_builder import DynamicTeamBuilder
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
        skip_gates: Skip quality gate agent teams.
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

    async def run_all(self) -> PipelineResult:
        """Run quality gates for all tasks sequentially.

        Returns:
            PipelineResult with per-task outcomes.

        """
        start = time.monotonic()

        for task in self.tasks:
            result = await self.run_gates_for_task(task)
            self.results.append(result)

            if result.quality_gate_passed is False:
                logger.warning(
                    "Task %s failed quality gate — stopping",
                    task.task_id,
                )
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

    async def _run_quality_gate(
        self,
        task: DecomposedTask,
    ) -> tuple[bool, dict[str, Any], float]:
        """Run code_reviewer + security_auditor in parallel.

        Returns:
            Tuple of (passed, details_dict, cost).

        """
        target_files = [f["path"] for f in task.files_to_create + task.files_to_modify]

        plan = {
            "name": f"pipeline-gate:{task.task_id}",
            "agents": [
                {"template_id": "code_reviewer"},
                {"template_id": "security_auditor"},
            ],
            "strategy": "parallel",
            "quality_gates": {
                "min_quality": {
                    "agent_role": "Code Quality Reviewer",
                    "metric": "score",
                    "threshold": 70.0,
                    "required": True,
                },
                "min_security": {
                    "agent_role": "Security Auditor",
                    "metric": "score",
                    "threshold": 70.0,
                    "required": True,
                },
            },
        }

        builder = DynamicTeamBuilder()
        team = builder.build_from_plan(plan)

        input_data = {
            "task_id": task.task_id,
            "task_name": task.name,
            "objective": task.objective,
            "files": target_files,
        }

        team_result = await team.execute(input_data)

        details = {
            "team_success": team_result.success,
            "gate_results": team_result.quality_gate_results,
            "agent_count": len(team_result.agent_results),
            "execution_time_ms": team_result.execution_time_ms,
        }

        return (
            team_result.success,
            details,
            team_result.total_cost,
        )

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

        for path in source_files:
            try:
                workflow = SimplifyCodeWorkflow()
                await workflow.execute(path=path)
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Per-file simplify failure is non-fatal
                logger.warning("Simplify failed for %s: %s", path, e)
