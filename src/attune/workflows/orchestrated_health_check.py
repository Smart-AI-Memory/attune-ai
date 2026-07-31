"""Orchestrated Health Check Workflow

Uses meta-orchestration to perform comprehensive project health
assessments with configurable depth levels (daily, weekly, release).

This workflow demonstrates adaptive agent composition based on
execution mode, intelligent health scoring, and historical trend
tracking.

Architecture:
    - MetaOrchestrator selects agents based on mode
    - ParallelStrategy for daily/weekly (fast validation)
    - RefinementStrategy for release (deep multi-stage analysis)
    - Health score calculation with weighted criteria
    - Trend tracking for historical comparisons

Modes:
    - daily: Quick parallel check (security, coverage, quality)
    - weekly: Comprehensive parallel (+ performance, docs, deps)
    - release: Deep sequential refinement (multi-stage validation)

Quality Criteria (weighted):
    - Security: 30% (critical issues, vulnerability count)
    - Coverage: 25% (test coverage percentage)
    - Quality: 20% (code quality score)
    - Performance: 15% (bottleneck count, response times)
    - Documentation: 10% (completeness percentage)

Example:
    >>> workflow = OrchestratedHealthCheckWorkflow(mode="weekly")
    >>> report = await workflow.execute(path=".")
    >>> print(f"{report.overall_health_score}/100 ({report.grade})")
    85/100 (B)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

import asyncio
import logging
import time
import warnings
from pathlib import Path
from typing import Any

from ..orchestration.agent_templates import AgentTemplate, get_template
from ..orchestration.execution_strategies import ParallelStrategy, StrategyResult
from .base import BaseWorkflow
from .health_check_models import CategoryScore, HealthCheckReport
from .health_check_scoring import (
    CATEGORY_WEIGHTS,
    GRADE_THRESHOLDS,
    assign_grade,
    calculate_category_scores,
    calculate_overall_score,
    generate_recommendations,
)
from .health_check_tracking import (
    get_trend_comparison,
    save_health_json,
    save_tracking_history,
)
from .validation import InputSchema

# Re-export public API for backward compatibility
__all__ = [
    "CategoryScore",
    "HealthCheckReport",
    "OrchestratedHealthCheckWorkflow",
    "main",
]

logger = logging.getLogger(__name__)


class OrchestratedHealthCheckWorkflow(BaseWorkflow):
    """Health check workflow using meta-orchestration.

    This workflow performs comprehensive project health assessment
    using intelligent agent composition based on execution mode.

    Modes:
        - daily: Fast parallel check (security, coverage,
          quality) with CHEAP/CAPABLE agents
        - weekly: Comprehensive parallel (adds performance,
          docs, deps) with all tiers
        - release: Deep sequential refinement with premium
          agents

    Health Score Calculation:
        Weighted average of category scores:
        - Security: 30%
        - Coverage: 25%
        - Quality: 20%
        - Performance: 15%
        - Documentation: 10%

    Example:
        >>> workflow = OrchestratedHealthCheckWorkflow(
        ...     mode="weekly"
        ... )
        >>> report = await workflow.execute(path=".")
        >>> if report.overall_health_score >= 80:
        ...     print("Project is healthy!")

    """

    name = "orchestrated-health-check"
    description = "Comprehensive project health assessment using meta-orchestration"

    # Category weights for overall score
    CATEGORY_WEIGHTS = CATEGORY_WEIGHTS

    # Agent sets by mode
    MODE_AGENTS = {
        "daily": [
            "security_auditor",
            "test_coverage_analyzer",
            "code_reviewer",
        ],
        "weekly": [
            "security_auditor",
            "test_coverage_analyzer",
            "code_reviewer",
            "performance_optimizer",
            "documentation_writer",
        ],
        "release": [
            "security_auditor",
            "test_coverage_analyzer",
            "code_reviewer",
            "performance_optimizer",
            "documentation_writer",
            "architecture_analyst",
        ],
    }

    # Grade thresholds
    GRADE_THRESHOLDS = GRADE_THRESHOLDS

    def __init__(
        self,
        mode: str = "daily",
        project_root: str = ".",
        **kwargs: Any,
    ) -> None:
        """Initialize health check workflow.

        Args:
            mode: Execution mode ("daily", "weekly", "release")
            project_root: Project root directory
            **kwargs: Extra parameters (ignored, for CLI
                compatibility)

        Raises:
            ValueError: If mode is invalid

        """
        super().__init__()

        if mode not in self.MODE_AGENTS:
            raise ValueError(
                f"Invalid mode: {mode}. Must be one of {list(self.MODE_AGENTS.keys())}",
            )

        self.mode = mode
        self.project_root = Path(project_root).resolve()

        # Tracking directory
        self.tracking_dir = self.project_root / ".attune" / "health_tracking"
        self.tracking_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "OrchestratedHealthCheckWorkflow initialized: mode=%s, root=%s",
            mode,
            project_root,
        )

    input_schema = InputSchema(
        optional_fields={"path": str, "project_root": str, "context": dict},
    )

    async def execute(
        self,
        path: str | None = None,
        *,
        project_root: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> HealthCheckReport:
        """Execute health check workflow.

        Args:
            path: Optional project root (overrides init value).
                Replaces the deprecated `project_root=` kwarg.
            project_root: Deprecated alias for `path`. Emits
                `DeprecationWarning`; will be removed in v7.0.
            context: Additional context for agents
            **kwargs: Extra parameters (ignored, for VSCode/CLI
                compatibility). The `target=` kwarg is still
                accepted as an alias for `path=`.

        Returns:
            HealthCheckReport with comprehensive health
            assessment

        Raises:
            ValueError: If path is invalid

        """
        # Migrate the deprecated `project_root=` kwarg → `path=`.
        if project_root is not None and path is None:
            warnings.warn(
                "OrchestratedHealthCheckWorkflow.execute(project_root=...) "
                "is deprecated; use execute(path=...) instead. "
                "The legacy kwarg will be removed in v7.0.",
                DeprecationWarning,
                stacklevel=2,
            )
            path = project_root
        elif project_root is not None and path is not None:
            warnings.warn(
                "OrchestratedHealthCheckWorkflow.execute(): both "
                "`path=` and `project_root=` supplied; `path=` "
                "takes precedence and `project_root=` is deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Map 'target' to 'path' for VSCode compat.
        if "target" in kwargs and path is None:
            path = kwargs["target"]
        if path is not None:
            self.project_root = Path(path).resolve()

        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")

        logger.info("Starting health check: mode=%s, root=%s", self.mode, self.project_root)
        start_time = time.perf_counter()

        # Prepare context
        full_context = {
            "project_root": str(self.project_root),
            "mode": self.mode,
            **(context or {}),
        }

        # Get agents for mode
        agent_ids = self.MODE_AGENTS[self.mode]
        agents: list[AgentTemplate] = []
        for agent_id in agent_ids:
            template = get_template(agent_id)
            if template:
                agents.append(template)
            else:
                logger.warning("Agent template not found: %s", agent_id)

        if not agents:
            raise ValueError(f"No agents available for mode: {self.mode}")

        logger.info("Selected %s agents: %s", len(agents), [a.id for a in agents])

        # Execute agents using parallel strategy
        strategy = ParallelStrategy()
        strategy_result = await strategy.execute(agents, full_context)

        # Create health report
        report = await self._create_report(strategy_result, agents)

        # Set execution time
        report.execution_time = time.perf_counter() - start_time

        # Save to tracking history
        self._save_tracking_history(report)

        # Save to .attune/health.json for VS Code extension
        self._save_health_json(report)

        logger.info(
            "Health check completed: score=%.1f, grade=%s, duration=%.2fs",
            report.overall_health_score,
            report.grade,
            report.execution_time,
        )

        return report

    async def _create_report(
        self,
        strategy_result: StrategyResult,
        agents: list[AgentTemplate],
    ) -> HealthCheckReport:
        """Create health check report from agent results.

        Args:
            strategy_result: Results from strategy execution
            agents: Agents that were executed

        Returns:
            HealthCheckReport with all findings

        """
        # Extract agent results
        agent_results: dict[str, dict[str, Any]] = {}
        for result in strategy_result.outputs:
            agent_results[result.agent_id] = {
                "success": result.success,
                "output": result.output,
                "confidence": result.confidence,
                "duration": result.duration_seconds,
                "error": result.error,
            }

        # Calculate category scores
        category_scores = self._calculate_category_scores(agent_results)

        # Calculate overall health score
        overall_score = self._calculate_overall_score(category_scores)

        # Assign grade
        grade = self._assign_grade(overall_score)

        # Collect all issues
        issues: list[str] = []
        for category in category_scores:
            issues.extend(category.issues)

        # Generate recommendations
        recommendations = self._generate_recommendations(category_scores)

        # Get trend comparison
        trend = self._get_trend_comparison(overall_score)

        return HealthCheckReport(
            overall_health_score=overall_score,
            grade=grade,
            category_scores=category_scores,
            issues=issues,
            recommendations=recommendations,
            trend=trend,
            mode=self.mode,
            agents_executed=len(agents),
            success=strategy_result.success,
        )

    def _calculate_category_scores(
        self,
        agent_results: dict[str, dict[str, Any]],
    ) -> list[CategoryScore]:
        """Calculate health scores for each category.

        Args:
            agent_results: Results from all agents

        Returns:
            List of CategoryScore objects

        """
        return calculate_category_scores(agent_results, self.CATEGORY_WEIGHTS)

    def _calculate_overall_score(self, category_scores: list[CategoryScore]) -> float:
        """Calculate weighted overall health score.

        Args:
            category_scores: Category scores

        Returns:
            Overall score 0-100

        """
        return calculate_overall_score(category_scores)

    def _assign_grade(self, score: float) -> str:
        """Assign letter grade based on score.

        Args:
            score: Overall health score 0-100

        Returns:
            Letter grade (A/B/C/D/F)

        """
        return assign_grade(score, self.GRADE_THRESHOLDS)

    def _generate_recommendations(self, category_scores: list[CategoryScore]) -> list[str]:
        """Generate actionable recommendations.

        Args:
            category_scores: Category scores

        Returns:
            List of recommendations with commands to run

        """
        return generate_recommendations(category_scores)

    def _get_trend_comparison(self, current_score: float) -> str:
        """Compare current score with last check.

        Args:
            current_score: Current health score

        Returns:
            Trend description

        """
        return get_trend_comparison(current_score, self.tracking_dir)

    def _save_tracking_history(self, report: HealthCheckReport) -> None:
        """Save health check report to tracking history.

        Args:
            report: Health check report to save

        """
        save_tracking_history(report, self.tracking_dir)

    def _save_health_json(self, report: HealthCheckReport) -> None:
        """Save health check report to .attune/health.json.

        Args:
            report: Health check report to save

        """
        save_health_json(report, self.project_root)


async def main() -> None:
    """CLI entry point for orchestrated health check."""
    import sys

    # Parse arguments
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    project_root = sys.argv[2] if len(sys.argv) > 2 else "."

    # Create workflow
    workflow = OrchestratedHealthCheckWorkflow(mode=mode, project_root=project_root)

    # Execute
    report = await workflow.execute()

    # Print report
    print(report.format_console_output())

    # Exit with appropriate code
    sys.exit(0 if report.overall_health_score >= 70 else 1)


if __name__ == "__main__":
    asyncio.run(main())
