"""Workflow Batch Runner for non-interactive workflow orchestration.

Runs multiple workflows in sequence or parallel with curated presets,
cost tracking, and result aggregation. All workflows run autonomously
without user interaction.

Curated Presets:
- daily-quality: security-audit + bug-predict + dependency-check
- pre-release: security-audit + dependency-check + perf-audit
- coverage-boost: test-gen-parallel with aggressive settings
- full-audit: all analysis workflows

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class WorkflowSpec:
    """Specification for a single workflow in a batch.

    Attributes:
        workflow_id: Registry name (e.g., "security-audit")
        config: Workflow constructor kwargs
        input_data: Workflow execute() kwargs

    """

    workflow_id: str
    config: dict[str, Any] = field(default_factory=dict)
    input_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowBatchResult:
    """Result from a single workflow execution in a batch.

    Attributes:
        workflow_id: Which workflow ran
        success: Whether it completed without error
        result: WorkflowResult output (if success)
        error: Error message (if failed)
        duration_seconds: Wall-clock time
        cost: Estimated cost in USD

    """

    workflow_id: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_seconds: float = 0.0
    cost: float = 0.0


@dataclass
class BatchRunReport:
    """Aggregated report from a batch run.

    Attributes:
        preset: Preset name used (or "custom")
        results: Per-workflow results
        total_duration: Total wall-clock time
        total_cost: Sum of all workflow costs
        success_count: Number of successful workflows
        failure_count: Number of failed workflows

    """

    preset: str
    results: list[WorkflowBatchResult] = field(default_factory=list)
    total_duration: float = 0.0
    total_cost: float = 0.0
    success_count: int = 0
    failure_count: int = 0

    def format_summary(self) -> str:
        """Format a human-readable summary of the batch run."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"BATCH RUN: {self.preset}")
        lines.append("=" * 60)
        lines.append(
            f"Workflows: {self.success_count} passed, "
            f"{self.failure_count} failed, "
            f"{len(self.results)} total",
        )
        lines.append(f"Duration: {self.total_duration:.1f}s")
        lines.append(f"Est. Cost: ${self.total_cost:.4f}")
        lines.append("")

        for r in self.results:
            status = "OK" if r.success else "FAIL"
            lines.append(
                f"  [{status}] {r.workflow_id} ({r.duration_seconds:.1f}s, ${r.cost:.4f})",
            )
            if r.error:
                lines.append(f"         Error: {r.error}")

        lines.append("=" * 60)
        return "\n".join(lines)


# =============================================================================
# Curated Presets
# =============================================================================

BATCH_PRESETS: dict[str, list[WorkflowSpec]] = {
    "daily-quality": [
        WorkflowSpec(
            workflow_id="security-audit",
            config={"skip_remediate_if_clean": True},
            input_data={"path": "src/"},
        ),
        WorkflowSpec(
            workflow_id="bug-predict",
            config={"risk_threshold": 0.7},
            input_data={"path": "src/"},
        ),
        WorkflowSpec(
            workflow_id="dependency-check",
            input_data={"path": "."},
        ),
    ],
    "pre-release": [
        WorkflowSpec(
            workflow_id="security-audit",
            config={"skip_remediate_if_clean": False},
            input_data={"path": "src/"},
        ),
        WorkflowSpec(
            workflow_id="dependency-check",
            input_data={"path": "."},
        ),
        WorkflowSpec(
            workflow_id="perf-audit",
            config={"min_hotspots_for_premium": 3},
            input_data={"path": "src/"},
        ),
    ],
    "coverage-boost": [
        WorkflowSpec(
            workflow_id="test-gen-parallel",
            input_data={"path": "src/", "top_n": 100, "parallel": 5},
        ),
    ],
    "full-audit": [
        WorkflowSpec(
            workflow_id="security-audit",
            config={"skip_remediate_if_clean": True},
            input_data={"path": "src/"},
        ),
        WorkflowSpec(
            workflow_id="bug-predict",
            config={"risk_threshold": 0.5},
            input_data={"path": "src/"},
        ),
        WorkflowSpec(
            workflow_id="perf-audit",
            config={"min_hotspots_for_premium": 5},
            input_data={"path": "src/"},
        ),
        WorkflowSpec(
            workflow_id="dependency-check",
            input_data={"path": "."},
        ),
    ],
}


# =============================================================================
# Batch Runner
# =============================================================================


class WorkflowBatchRunner:
    """Orchestrates multiple workflow executions with cost tracking.

    Runs curated or custom workflow batches serially or in parallel.
    All workflows must be non-interactive (batch-safe).

    Example:
        >>> runner = WorkflowBatchRunner()
        >>> report = await runner.run_preset("daily-quality")
        >>> print(report.format_summary())

        >>> # Custom batch
        >>> specs = [
        ...     WorkflowSpec("security-audit", input_data={"path": "src/"}),
        ...     WorkflowSpec("bug-predict", input_data={"path": "src/"}),
        ... ]
        >>> report = await runner.run_batch(specs)

    Attributes:
        max_parallel: Max concurrent workflows (0 = serial)
        timeout_per_workflow: Per-workflow timeout in seconds

    """

    # Workflows verified as batch-safe (no interactive prompts)
    BATCH_SAFE_WORKFLOWS = frozenset(
        {
            "bug-predict",
            "security-audit",
            "perf-audit",
            "dependency-check",
            "test-gen",
            "test-gen-parallel",
            "doc-gen",
            "code-review",
            "refactor-plan",
            "release-prep",
            "research-synthesis",
            "orchestrated-health-check",
            "secure-release",
            "test-maintenance",
        },
    )

    def __init__(
        self,
        max_parallel: int = 1,
        timeout_per_workflow: int = 600,
    ):
        """Initialize batch runner.

        Args:
            max_parallel: Max concurrent workflows. 1 = serial (default).
                Use 2-3 for parallel execution.
            timeout_per_workflow: Per-workflow timeout in seconds.

        """
        self.max_parallel = max_parallel
        self.timeout_per_workflow = timeout_per_workflow

    async def run_preset(
        self,
        preset_name: str,
        path_override: str | None = None,
    ) -> BatchRunReport:
        """Run a curated preset batch.

        Args:
            preset_name: One of: daily-quality, pre-release,
                coverage-boost, full-audit
            path_override: Override the default path for all workflows

        Returns:
            BatchRunReport with aggregated results

        Raises:
            ValueError: If preset_name is not recognized

        """
        if preset_name not in BATCH_PRESETS:
            available = ", ".join(sorted(BATCH_PRESETS.keys()))
            raise ValueError(f"Unknown preset '{preset_name}'. Available: {available}")

        specs = BATCH_PRESETS[preset_name]

        if path_override:
            specs = [
                WorkflowSpec(
                    workflow_id=s.workflow_id,
                    config=s.config,
                    input_data={**s.input_data, "path": path_override},
                )
                for s in specs
            ]

        return await self.run_batch(specs, preset_name=preset_name)

    async def run_batch(
        self,
        specs: list[WorkflowSpec],
        preset_name: str = "custom",
    ) -> BatchRunReport:
        """Run a batch of workflow specifications.

        Args:
            specs: List of WorkflowSpec defining what to run
            preset_name: Label for the report

        Returns:
            BatchRunReport with per-workflow results

        """
        self._validate_specs(specs)

        start_time = time.monotonic()
        results: list[WorkflowBatchResult] = []

        if self.max_parallel <= 1:
            # Serial execution
            for spec in specs:
                result = await self._execute_one(spec)
                results.append(result)
        else:
            # Parallel execution with semaphore
            semaphore = asyncio.Semaphore(self.max_parallel)

            async def run_with_semaphore(spec: WorkflowSpec) -> WorkflowBatchResult:
                async with semaphore:
                    return await self._execute_one(spec)

            tasks = [run_with_semaphore(spec) for spec in specs]
            results = await asyncio.gather(*tasks)
            results = list(results)

        total_duration = time.monotonic() - start_time
        total_cost = sum(r.cost for r in results)
        success_count = sum(1 for r in results if r.success)
        failure_count = sum(1 for r in results if not r.success)

        return BatchRunReport(
            preset=preset_name,
            results=results,
            total_duration=total_duration,
            total_cost=total_cost,
            success_count=success_count,
            failure_count=failure_count,
        )

    def _validate_specs(self, specs: list[WorkflowSpec]) -> None:
        """Validate that all specs reference batch-safe workflows.

        Args:
            specs: Workflow specifications to validate

        Raises:
            ValueError: If any workflow is not batch-safe or unknown

        """
        if not specs:
            raise ValueError("specs cannot be empty")

        for spec in specs:
            if spec.workflow_id not in self.BATCH_SAFE_WORKFLOWS:
                raise ValueError(
                    f"Workflow '{spec.workflow_id}' is not in the "
                    f"batch-safe allowlist. Available: "
                    f"{', '.join(sorted(self.BATCH_SAFE_WORKFLOWS))}",
                )

    async def _execute_one(self, spec: WorkflowSpec) -> WorkflowBatchResult:
        """Execute a single workflow with timeout and error handling.

        Args:
            spec: Workflow specification

        Returns:
            WorkflowBatchResult with outcome

        """
        start_time = time.monotonic()

        try:
            workflow = self._create_workflow(spec)

            result = await asyncio.wait_for(
                workflow.execute(**spec.input_data),
                timeout=self.timeout_per_workflow,
            )

            duration = time.monotonic() - start_time
            cost = getattr(result, "total_cost", 0.0)
            if hasattr(result, "cost_report") and result.cost_report:
                cost = result.cost_report.get("total_cost", cost)

            return WorkflowBatchResult(
                workflow_id=spec.workflow_id,
                success=True,
                result=result,
                duration_seconds=duration,
                cost=cost,
            )

        except asyncio.TimeoutError:
            duration = time.monotonic() - start_time
            logger.error(
                f"Workflow '{spec.workflow_id}' timed out after {self.timeout_per_workflow}s",
            )
            return WorkflowBatchResult(
                workflow_id=spec.workflow_id,
                success=False,
                error=f"Timed out after {self.timeout_per_workflow}s",
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.monotonic() - start_time
            logger.exception(f"Workflow '{spec.workflow_id}' failed: {e}")
            return WorkflowBatchResult(
                workflow_id=spec.workflow_id,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    def _create_workflow(self, spec: WorkflowSpec) -> Any:
        """Create a workflow instance from the registry.

        Args:
            spec: Workflow specification with ID and config

        Returns:
            Workflow instance ready for execution

        Raises:
            ValueError: If workflow ID is not found in registry

        """
        from attune.workflows import get_workflow

        try:
            workflow_class = get_workflow(spec.workflow_id)
        except KeyError:
            raise ValueError(f"Workflow '{spec.workflow_id}' not found in registry")

        # Filter config to only valid constructor params
        try:
            return workflow_class(**spec.config)
        except TypeError:
            # Some workflows don't accept extra kwargs
            logger.warning(
                f"Workflow '{spec.workflow_id}' doesn't accept "
                f"config params {list(spec.config.keys())}, "
                f"using defaults",
            )
            return workflow_class()

    @staticmethod
    def list_presets() -> dict[str, str]:
        """List available presets with descriptions.

        Returns:
            Dict mapping preset name to description

        """
        return {
            "daily-quality": (
                "Security audit + bug prediction + dependency check. Quick daily health check."
            ),
            "pre-release": (
                "Security audit + dependency check + performance audit. "
                "Pre-release validation gate."
            ),
            "coverage-boost": (
                "Parallel test generation for coverage improvement. "
                "Generates tests for uncovered code."
            ),
            "full-audit": (
                "All analysis workflows: security, bugs, performance, "
                "dependencies. Comprehensive project audit."
            ),
        }

    @staticmethod
    def list_batch_safe_workflows() -> list[str]:
        """List all workflows verified as batch-safe.

        Returns:
            Sorted list of batch-safe workflow IDs

        """
        return sorted(WorkflowBatchRunner.BATCH_SAFE_WORKFLOWS)
