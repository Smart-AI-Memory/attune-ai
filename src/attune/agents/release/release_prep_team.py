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
from datetime import datetime
from typing import Any

from attune.workflows.base import BaseWorkflow
from attune.workflows.compat import ModelTier
from attune.workflows.data_classes import WorkflowResult
from attune.workflows.output import (
    CalloutSection,
    ListSection,
    NextAction,
    NextStepsSection,
    Section,
    TableSection,
    WorkflowReport,
)
from attune.workflows.validation import InputSchema

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
    REDIS_AVAILABLE,
    QualityGate,
    ReleaseAgentResult,
    ReleaseReadinessReport,
    Tier,
    anthropic,
    get_model_config,
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
        loop = asyncio.get_running_loop()
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

        # Security gate: no critical issues. A FAILED (or absent)
        # auditor can never satisfy the gate — unknown is not clean;
        # the -1 sentinel stays as the display value so the gates
        # table shows the auditor never produced a count.
        security_ran = bool(security and security.success)
        critical_issues = -1
        if security_ran:
            critical_issues = security.findings.get("critical_issues", 0)
        elif security:
            critical_issues = security.findings.get("critical_issues", -1)

        gates.append(
            QualityGate(
                name="Security",
                threshold=float(self.quality_gates["max_critical_issues"]),
                actual=float(critical_issues),
                passed=security_ran
                and critical_issues <= self.quality_gates["max_critical_issues"],
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
            if not result.success:
                # A failed agent ALWAYS blocks — a failure that carries
                # no diagnostic must not read as quieter than one that
                # does (the -1-sentinel bug's other half).
                reason = result.findings.get("error") or "failed without diagnostic output"
                blockers.append(f"Agent {result.agent_role} failed: {reason}")

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

    input_schema = InputSchema(
        optional_fields={"path": str, "context": dict},
    )

    async def execute(
        self,
        path: str = ".",
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> WorkflowResult:
        """Execute release preparation workflow.

        Args:
            path: Path to codebase to analyze
            context: Additional context (unused, for compatibility)
            **kwargs: Extra parameters (target, etc.)

        Returns:
            WorkflowResult whose ``final_output`` carries the serialized
            :class:`~attune.workflows.output.WorkflowReport` (design D2);
            the voice layer / CLI render it. ``success`` reflects that
            the assessment RAN — the release verdict lives in the report
            (``metadata["approved"]``), so a BLOCKED release still exits 0.

        """
        # Map 'target' to 'path' for VSCode/CLI compatibility
        if "target" in kwargs and path == ".":
            path = kwargs["target"]

        team = ReleasePrepTeam(
            quality_gates=self.quality_gates,
        )

        started_at = datetime.now()
        report = await team.assess_readiness(codebase_path=path)
        completed_at = datetime.now()

        return WorkflowResult(
            success=True,
            stages=[],
            final_output=_to_workflow_report(report).to_dict(),
            cost_report=None,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            summary=report.summary,
            metadata={"approved": report.approved, "confidence": report.confidence},
        )


def _to_workflow_report(report: ReleaseReadinessReport) -> WorkflowReport:
    """Convert the team's bespoke report to the universal WorkflowReport.

    Design D2 (workflow-result-formatting): the converter is co-located
    with the workflow that owns the semantics; the bespoke type stays
    rendering-free. Content tiers per the proposal — verdict, gates,
    blockers/warnings, and next steps are essential; the per-agent
    breakdown is detail (collapsed in summary mode).

    Args:
        report: The team's consolidated readiness assessment.

    Returns:
        WorkflowReport ready for ``to_dict()`` into ``final_output``.

    """
    verdict = "APPROVED" if report.approved else "BLOCKED"
    passed = sum(1 for g in report.quality_gates if g.passed)

    sections: list[Section] = [
        CalloutSection(
            title="Verdict",
            tier="essential",
            text=f"Release **{verdict}** — confidence: {report.confidence}",
            emphasis="ok" if report.approved else "danger",
        ),
        TableSection(
            title=f"Quality gates ({passed}/{len(report.quality_gates)} passed)",
            tier="essential",
            columns=["Gate", "Actual", "Threshold", "Pass"],
            rows=[
                {
                    "Gate": g.name,
                    "Actual": f"{g.actual:.1f}",
                    "Threshold": f"{g.threshold:.1f}",
                    "Pass": "✓" if g.passed else "✗",
                }
                for g in report.quality_gates
            ],
        ),
        TableSection(
            title="Per-agent breakdown",
            tier="detail",
            columns=["Agent", "Score", "Confidence", "Tier", "Time"],
            rows=[
                {
                    "Agent": r.agent_role,
                    "Score": f"{r.score:.1f}",
                    "Confidence": f"{r.confidence:.2f}",
                    "Tier": r.tier_used.value,
                    "Time": f"{r.execution_time_ms / 1000:.1f}s",
                }
                for r in report.agent_results
            ],
        ),
    ]
    if report.blockers:
        sections.append(
            ListSection(title="Blockers", tier="essential", items=list(report.blockers))
        )
    if report.warnings:
        sections.append(
            ListSection(title="Warnings", tier="essential", items=list(report.warnings))
        )

    if report.approved:
        next_actions = [
            NextAction(
                text="All gates pass — run the composite security pipeline next.",
                command="attune workflow run secure-release",
            )
        ]
    else:
        next_actions = [
            NextAction(text=f"Resolve blocker: {blocker}") for blocker in report.blockers
        ]
    sections.append(NextStepsSection(title="Next steps", tier="essential", items=next_actions))

    return WorkflowReport(
        title="Release readiness",
        summary=report.summary or f"Release {verdict} — confidence: {report.confidence}",
        metadata={
            "cost_usd": report.total_cost,
            "duration_s": report.total_duration,
            "approved": report.approved,
            "confidence": report.confidence,
        },
        sections=sections,
    )
