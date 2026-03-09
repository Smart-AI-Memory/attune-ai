"""Release Preparation Agent Team.

A multi-agent system for automated release readiness assessment with
Redis coordination, progressive tier escalation, and robust output parsing.

Agents:
    - SecurityAuditorAgent: Runs bandit, classifies vulnerabilities by severity
    - TestCoverageAgent: Runs pytest --cov, parses coverage report
    - CodeQualityAgent: Runs ruff, checks type hints and complexity
    - DocumentationAgent: Counts docstrings, checks README/CHANGELOG

Collaboration: Parallel execution via asyncio.gather + run_in_executor
Tier Strategy: Progressive (CHEAP -> CAPABLE -> PREMIUM)
Redis: Optional — graceful degradation when unavailable

IMPORTANT: This module re-exports all public symbols from submodules for
backward compatibility. All symbols remain importable from
attune.agents.release.release_prep_team.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from attune.workflows.base import BaseWorkflow
from attune.workflows.compat import ModelTier

# Re-export agent classes and helpers
from .release_agents import (  # noqa: F401
    CodeQualityAgent,
    DocumentationAgent,
    ReleaseAgent,
    SecurityAuditorAgent,
    TestCoverageAgent,
    _run_command,
)

# Re-export data models, configuration, and optional dependencies
from .release_models import (  # noqa: F401
    ANTHROPIC_AVAILABLE,
    DEFAULT_QUALITY_GATES,
    LLM_MODE,
    MODEL_CONFIG,
    REDIS_AVAILABLE,
    QualityGate,
    ReleaseAgentResult,
    ReleaseReadinessReport,
    Tier,
    anthropic,
    redis_lib,
)

# Re-export response parsing
from .release_parsing import _parse_response  # noqa: F401

logger = logging.getLogger(__name__)


# =============================================================================
# Team Coordinator
# =============================================================================


class ReleasePrepTeam:
    """Coordinates parallel execution of release preparation agents.

    Features:
        - Parallel agent execution via asyncio.gather
        - Progressive tier escalation per agent
        - Configurable quality gates
        - Optional Redis coordination
        - Cost tracking across all agents

    Args:
        quality_gates: Custom quality gate thresholds
        redis_url: Optional Redis URL for coordination

    """

    def __init__(
        self,
        quality_gates: dict[str, Any] | None = None,
        redis_url: str | None = None,
    ) -> None:
        """Initialize the release preparation team.

        Args:
            quality_gates: Custom quality gate thresholds.
            redis_url: Optional Redis URL for agent coordination.
        """
        self.quality_gates = {**DEFAULT_QUALITY_GATES}
        if quality_gates:
            self.quality_gates.update(quality_gates)

        # Connect to Redis if available
        self.redis: Any | None = None
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis = redis_lib.from_url(redis_url)
                self.redis.ping()
                logger.info("Release team connected to Redis")
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Redis is optional for local development
                logger.info(f"Redis not available (non-fatal): {e}")
                self.redis = None
        elif REDIS_AVAILABLE:
            # Try default localhost Redis
            try:
                self.redis = redis_lib.Redis(host="localhost", port=6379, decode_responses=True)
                self.redis.ping()
                logger.info("Release team connected to local Redis")
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Redis is optional
                self.redis = None

        # Initialize agents
        self.agents: list[ReleaseAgent] = [
            SecurityAuditorAgent(redis_client=self.redis),
            TestCoverageAgent(redis_client=self.redis),
            CodeQualityAgent(redis_client=self.redis),
            DocumentationAgent(redis_client=self.redis),
        ]

    def get_total_cost(self) -> float:
        """Get total LLM cost across all agents."""
        return sum(agent.total_cost for agent in self.agents)

    async def assess_readiness(
        self,
        codebase_path: str = ".",
    ) -> ReleaseReadinessReport:
        """Assess release readiness with all agents in parallel.

        Args:
            codebase_path: Path to the codebase to analyze

        Returns:
            ReleaseReadinessReport with consolidated results

        """
        start = time.time()
        logger.info(f"Starting release readiness assessment: {codebase_path}")

        # Execute all agents in parallel
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, agent.process, codebase_path) for agent in self.agents]
        results: list[ReleaseAgentResult] = await asyncio.gather(*tasks)

        elapsed = time.time() - start

        # Evaluate quality gates
        quality_gates = self._evaluate_quality_gates(results)

        # Identify blockers and warnings
        blockers, warnings = self._identify_issues(quality_gates, results)

        # Determine approval
        critical_failures = [g for g in quality_gates if g.critical and not g.passed]
        approved = len(critical_failures) == 0 and len(blockers) == 0

        # Determine confidence
        if approved and len(warnings) == 0:
            confidence = "high"
        elif approved:
            confidence = "medium"
        else:
            confidence = "low"

        summary = self._generate_summary(approved, quality_gates, results)

        return ReleaseReadinessReport(
            approved=approved,
            confidence=confidence,
            quality_gates=quality_gates,
            agent_results=results,
            blockers=blockers,
            warnings=warnings,
            summary=summary,
            total_duration=elapsed,
            total_cost=self.get_total_cost(),
        )

    def _evaluate_quality_gates(self, results: list[ReleaseAgentResult]) -> list[QualityGate]:
        """Evaluate quality gates based on agent results.

        Args:
            results: Results from all agents

        Returns:
            List of evaluated QualityGate objects

        """
        gates: list[QualityGate] = []

        # Find agent results by role
        security = next((r for r in results if "Security" in r.agent_role), None)
        coverage = next((r for r in results if "Coverage" in r.agent_role), None)
        quality = next((r for r in results if "Quality" in r.agent_role), None)
        docs = next((r for r in results if "Documentation" in r.agent_role), None)

        # Security gate: no critical issues
        critical_issues = 0
        if security and security.success:
            critical_issues = security.findings.get("critical_issues", 0)
        elif security:
            critical_issues = security.findings.get("critical_issues", -1)

        gates.append(
            QualityGate(
                name="Security",
                threshold=float(self.quality_gates["max_critical_issues"]),
                actual=float(critical_issues),
                passed=critical_issues <= self.quality_gates["max_critical_issues"],
                critical=True,
            ),
        )

        # Coverage gate
        coverage_pct = 0.0
        if coverage:
            coverage_pct = coverage.findings.get("coverage_percent", 0.0)

        gates.append(
            QualityGate(
                name="Test Coverage",
                threshold=self.quality_gates["min_coverage"],
                actual=coverage_pct,
                passed=coverage_pct >= self.quality_gates["min_coverage"],
                critical=True,
            ),
        )

        # Quality gate
        quality_score = 0.0
        if quality:
            quality_score = quality.findings.get(
                "quality_score",
                quality.findings.get("score", 0.0),
            )

        gates.append(
            QualityGate(
                name="Code Quality",
                threshold=self.quality_gates["min_quality_score"],
                actual=quality_score,
                passed=quality_score >= self.quality_gates["min_quality_score"],
                critical=True,
            ),
        )

        # Documentation gate (non-critical — warning only)
        doc_coverage = 0.0
        if docs:
            doc_coverage = docs.findings.get("coverage_percent", 0.0)

        gates.append(
            QualityGate(
                name="Documentation",
                threshold=self.quality_gates["min_doc_coverage"],
                actual=doc_coverage,
                passed=doc_coverage >= self.quality_gates["min_doc_coverage"],
                critical=False,
            ),
        )

        return gates

    def _identify_issues(
        self,
        quality_gates: list[QualityGate],
        results: list[ReleaseAgentResult],
    ) -> tuple[list[str], list[str]]:
        """Identify blockers and warnings.

        Args:
            quality_gates: Evaluated quality gates
            results: Agent results

        Returns:
            Tuple of (blockers, warnings)

        """
        blockers: list[str] = []
        warnings: list[str] = []

        for gate in quality_gates:
            if not gate.passed:
                if gate.critical:
                    blockers.append(f"{gate.name} failed: {gate.message}")
                else:
                    warnings.append(f"{gate.name} below threshold: {gate.message}")

        for result in results:
            if not result.success and result.findings.get("error"):
                blockers.append(f"Agent {result.agent_role} failed: {result.findings['error']}")

        return blockers, warnings

    def _generate_summary(
        self,
        approved: bool,
        quality_gates: list[QualityGate],
        results: list[ReleaseAgentResult],
    ) -> str:
        """Generate executive summary.

        Args:
            approved: Overall approval status
            quality_gates: Quality gate results
            results: Agent results

        Returns:
            Summary text

        """
        lines: list[str] = []

        if approved:
            lines.append("RELEASE APPROVED")
            lines.append("All critical quality gates passed.")
        else:
            lines.append("RELEASE NOT APPROVED")
            lines.append("Critical quality gates failed. Address blockers before release.")

        lines.append("")

        passed_count = sum(1 for g in quality_gates if g.passed)
        lines.append(f"Quality Gates: {passed_count}/{len(quality_gates)} passed")

        failed_gates = [g for g in quality_gates if not g.passed]
        if failed_gates:
            lines.append("Failed gates:")
            for gate in failed_gates:
                lines.append(
                    f"  - {gate.name}: {gate.actual:.1f} vs threshold {gate.threshold:.1f}",
                )

        lines.append("")
        lines.append(f"Agents: {len(results)} executed")

        for result in results:
            status = "OK" if result.success else "FAIL"
            lines.append(f"  [{status}] {result.agent_role} (score={result.score:.1f})")

        return "\n".join(lines)


# =============================================================================
# BaseWorkflow Adapter (for CLI/registry integration)
# =============================================================================


class ReleasePrepTeamWorkflow(BaseWorkflow):
    """Workflow wrapper that integrates ReleasePrepTeam with the CLI registry.

    This class provides the same interface as OrchestratedReleasePrepWorkflow
    so the workflow registry can use it as a drop-in replacement.

    Attributes:
        name: Workflow name for registry
        description: Human-readable description
        stages: Stage names for workflow registry
        tier_map: Tier mapping for workflow registry

    """

    name = "release-prep"
    description = "Release readiness assessment using parallel agent team"
    stages = ["triage", "parallel-validation", "synthesis", "decision"]
    tier_map: dict[str, Any] = {}  # Populated dynamically

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: Any) -> Any:
        """Not used — this workflow overrides execute() directly."""
        raise NotImplementedError("ReleasePrepTeamWorkflow uses execute(), not run_stage()")

    def __init__(
        self,
        quality_gates: dict[str, float] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize workflow.

        Args:
            quality_gates: Custom quality gate thresholds
            **kwargs: Extra CLI parameters (absorbed for compatibility)

        """
        super().__init__()
        self.quality_gates = quality_gates
        self._kwargs = kwargs

    async def execute(
        self,
        path: str = ".",
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ReleaseReadinessReport:
        """Execute release preparation workflow.

        Args:
            path: Path to codebase to analyze
            context: Additional context (unused, for compatibility)
            **kwargs: Extra parameters (target, etc.)

        Returns:
            ReleaseReadinessReport with consolidated results

        """
        # Map 'target' to 'path' for VSCode/CLI compatibility
        if "target" in kwargs and path == ".":
            path = kwargs["target"]

        team = ReleasePrepTeam(
            quality_gates=self.quality_gates,
        )

        report = await team.assess_readiness(codebase_path=path)

        # Print formatted output for CLI users
        print(report.format_console_output())

        return report
