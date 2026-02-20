"""PR Review Workflow

A comprehensive PR review workflow that combines CodeReviewCrew and
SecurityAuditCrew for thorough code and security analysis.

Features:
- Runs both crews in parallel for speed
- Merges findings from code quality and security perspectives
- Provides unified verdict and risk assessment
- Graceful fallback if crews are unavailable

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
import logging
import time
import warnings

from .pr_review_analysis import PRReviewAnalysisMixin

# Re-export public API from sub-modules so existing imports keep working:
#   from attune.workflows.pr_review import PRReviewResult
#   from attune.workflows.pr_review import format_pr_review_report
from .pr_review_formatting import format_pr_review_report, main  # noqa: F401
from .pr_review_models import PRReviewResult  # noqa: F401

logger = logging.getLogger(__name__)


class PRReviewWorkflow(PRReviewAnalysisMixin):
    """Combined code review + security audit for comprehensive PR analysis.

    Runs CodeReviewCrew and SecurityAuditCrew in parallel for maximum
    speed while providing thorough analysis from both perspectives.

    Usage:
        workflow = PRReviewWorkflow()
        result = await workflow.execute(
            diff="...",
            files_changed=["src/main.py"],
            target_path="./src",
        )
    """

    def __init__(
        self,
        provider: str = "anthropic",
        use_code_crew: bool = True,
        use_security_crew: bool = True,
        parallel: bool = True,
        code_crew_config: dict | None = None,
        security_crew_config: dict | None = None,
    ):
        """Initialize the workflow.

        .. deprecated:: 5.3.0
            Use :class:`CodeReviewWorkflow` via ``attune workflow run code-review``.
            Will be removed in v6.0.0.

        Args:
            provider: LLM provider to use (anthropic, openai, etc.)
            use_code_crew: Enable CodeReviewCrew
            use_security_crew: Enable SecurityAuditCrew
            parallel: Run crews in parallel (recommended)
            code_crew_config: Configuration for CodeReviewCrew
            security_crew_config: Configuration for SecurityAuditCrew

        """
        warnings.warn(
            "PRReviewWorkflow is deprecated since v5.3.0. "
            "Use CodeReviewWorkflow via 'attune workflow run code-review' instead. "
            "Will be removed in v6.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.provider = provider
        self.use_code_crew = use_code_crew
        self.use_security_crew = use_security_crew
        self.parallel = parallel

        # Map "hybrid" to a real provider for crews
        crew_provider = "anthropic" if provider == "hybrid" else provider

        # Inject provider into crew configs
        self.code_crew_config = {"provider": crew_provider, **(code_crew_config or {})}
        self.security_crew_config = {
            "provider": crew_provider,
            **(security_crew_config or {}),
        }

    # ------------------------------------------------------------------
    # Factory class methods
    # ------------------------------------------------------------------

    @classmethod
    def for_comprehensive_review(cls) -> "PRReviewWorkflow":
        """Factory for comprehensive PR review with all crews."""
        return cls(use_code_crew=True, use_security_crew=True, parallel=True)

    @classmethod
    def for_security_focused(cls) -> "PRReviewWorkflow":
        """Factory for security-focused review."""
        return cls(use_code_crew=False, use_security_crew=True, parallel=False)

    @classmethod
    def for_code_quality_focused(cls) -> "PRReviewWorkflow":
        """Factory for code quality-focused review."""
        return cls(use_code_crew=True, use_security_crew=False, parallel=False)

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        diff: str | None = None,
        files_changed: list[str] | None = None,
        target_path: str = ".",
        target: str | None = None,
        context: dict | None = None,
    ) -> PRReviewResult:
        """Execute comprehensive PR review with both crews.

        Args:
            diff: PR diff content (auto-generated from git if not provided)
            files_changed: List of changed files
            target_path: Path to codebase for security audit
            target: Alias for target_path (for CLI compatibility)
            context: Additional context

        Returns:
            PRReviewResult with combined analysis

        """
        start_time = time.time()
        files_changed = files_changed or []
        context = context or {}

        if target and target_path == ".":
            target_path = target

        if not diff:
            diff = self._auto_generate_diff(target_path)

        code_review: dict | None = None
        security_audit: dict | None = None
        code_findings: list[dict] = []
        security_findings: list[dict] = []
        blockers: list[str] = []
        warn_list: list[str] = []
        recommendations: list[str] = []
        agents_used: list[str] = []

        try:
            code_review, security_audit = await self._run_crews(
                diff,
                files_changed,
                target_path,
            )

            total_cost = 0.0
            total_cost, code_findings, recommendations, agents_used = self._collect_code_findings(
                code_review
            )
            sec_cost, security_findings, sec_recs, sec_agents = self._collect_security_findings(
                security_audit
            )
            total_cost += sec_cost
            recommendations.extend(sec_recs)
            agents_used.extend(sec_agents)

            all_findings = self._merge_findings(code_findings, security_findings)

            critical_count = len([f for f in all_findings if f.get("severity") == "critical"])
            high_count = len([f for f in all_findings if f.get("severity") == "high"])

            if critical_count > 0:
                blockers.append(f"{critical_count} critical issue(s) must be fixed")
            if high_count > 3:
                blockers.append(f"{high_count} high severity issues exceed threshold")

            code_quality_score = self._get_code_quality_score(code_review)
            security_risk_score = self._get_security_risk_score(security_audit)
            combined_score = self._calculate_combined_score(
                code_quality_score,
                security_risk_score,
            )

            verdict = self._determine_verdict(
                code_review,
                security_audit,
                combined_score,
                blockers,
            )
            summary = self._generate_summary(
                verdict,
                code_quality_score,
                security_risk_score,
                len(all_findings),
                critical_count,
                high_count,
            )

            if not code_review and self.use_code_crew:
                warn_list.append("CodeReviewCrew unavailable - code review limited")
            if not security_audit and self.use_security_crew:
                warn_list.append("SecurityAuditCrew unavailable - security audit limited")

            duration = time.time() - start_time

            result = PRReviewResult(
                success=True,
                verdict=verdict,
                code_quality_score=code_quality_score,
                security_risk_score=security_risk_score,
                combined_score=combined_score,
                code_review=code_review,
                security_audit=security_audit,
                all_findings=all_findings,
                code_findings=code_findings,
                security_findings=security_findings,
                critical_count=critical_count,
                high_count=high_count,
                blockers=blockers,
                warnings=warn_list,
                recommendations=recommendations[:15],
                summary=summary,
                agents_used=list(dict.fromkeys(agents_used)),
                duration_seconds=duration,
                cost=total_cost,
                metadata={
                    "files_changed": len(files_changed),
                    "total_findings": len(all_findings),
                    "code_crew_enabled": self.use_code_crew,
                    "security_crew_enabled": self.use_security_crew,
                    "parallel_execution": self.parallel,
                },
            )
            result.metadata["formatted_report"] = format_pr_review_report(result)
            return result

        except Exception as e:
            logger.error(f"PRReviewWorkflow failed: {e}")
            duration = time.time() - start_time
            return PRReviewResult(
                success=False,
                verdict="reject",
                code_quality_score=0.0,
                security_risk_score=100.0,
                combined_score=0.0,
                code_review=code_review,
                security_audit=security_audit,
                all_findings=[],
                code_findings=[],
                security_findings=[],
                critical_count=0,
                high_count=0,
                blockers=[f"Review failed: {e!s}"],
                warnings=[],
                recommendations=[],
                summary=f"PR review failed with error: {e!s}",
                agents_used=[],
                duration_seconds=duration,
                cost=0.0,
                metadata={"error": str(e)},
            )

    # ------------------------------------------------------------------
    # Crew execution helpers
    # ------------------------------------------------------------------

    async def _run_crews(
        self,
        diff: str,
        files_changed: list[str],
        target_path: str,
    ) -> tuple[dict | None, dict | None]:
        """Dispatch crew execution (parallel or sequential)."""
        if self.parallel and self.use_code_crew and self.use_security_crew:
            return await self._run_parallel(diff, files_changed, target_path)

        code_review: dict | None = None
        security_audit: dict | None = None
        if self.use_code_crew:
            code_review = await self._run_code_review(diff, files_changed)
        if self.use_security_crew:
            security_audit = await self._run_security_audit(target_path)
        return code_review, security_audit

    async def _run_parallel(
        self,
        diff: str,
        files_changed: list[str],
        target_path: str,
    ) -> tuple[dict | None, dict | None]:
        """Run both crews in parallel."""
        code_task = asyncio.create_task(
            self._run_code_review(diff, files_changed),
        )
        security_task = asyncio.create_task(
            self._run_security_audit(target_path),
        )
        results = await asyncio.gather(
            code_task,
            security_task,
            return_exceptions=True,
        )

        code_review: dict | None = results[0] if isinstance(results[0], dict) else None
        security_audit: dict | None = results[1] if isinstance(results[1], dict) else None

        if isinstance(results[0], Exception):
            logger.warning(f"Code review failed: {results[0]}")
        if isinstance(results[1], Exception):
            logger.warning(f"Security audit failed: {results[1]}")

        return code_review, security_audit

    async def _run_code_review(
        self,
        diff: str,
        files_changed: list[str],
    ) -> dict | None:
        """Run CodeReviewCrew."""
        try:
            from .code_review_adapters import (
                _check_crew_available,
                _get_crew_review,
                crew_report_to_workflow_format,
            )
        except ImportError:
            logger.info("CodeReviewCrew adapters not installed")
            return None

        if not _check_crew_available():
            logger.info("CodeReviewCrew not available")
            return None

        report = await _get_crew_review(
            diff=diff,
            files_changed=files_changed,
            config=self.code_crew_config,
        )
        if report:
            return crew_report_to_workflow_format(report)
        return None

    async def _run_security_audit(self, target_path: str) -> dict | None:
        """Run SecurityAuditCrew."""
        try:
            from .security_adapters import (
                _check_crew_available,
                _get_crew_audit,
                crew_report_to_workflow_format,
            )
        except ImportError:
            logger.info("SecurityAuditCrew adapters not installed")
            return None

        if not _check_crew_available():
            logger.info("SecurityAuditCrew not available")
            return None

        report = await _get_crew_audit(
            target=target_path,
            config=self.security_crew_config,
        )
        if report:
            return crew_report_to_workflow_format(report)
        return None

    # ------------------------------------------------------------------
    # Finding collectors
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_code_findings(
        code_review: dict | None,
    ) -> tuple[float, list[dict], list[str], list[str]]:
        """Extract findings, cost, recommendations, agents from code review.

        Returns:
            Tuple of (cost, findings, recommendations, agents_used)

        """
        if not code_review:
            return 0.0, [], [], []

        findings = code_review.get("findings", [])
        agents = list(code_review.get("agents_used", []))
        recs = [f["suggestion"] for f in findings if f.get("suggestion")]
        cost = code_review.get("cost", 0.0)
        return cost, findings, recs, agents

    @staticmethod
    def _collect_security_findings(
        security_audit: dict | None,
    ) -> tuple[float, list[dict], list[str], list[str]]:
        """Extract findings, cost, recommendations, agents from security audit.

        Returns:
            Tuple of (cost, findings, recommendations, agents_used)

        """
        if not security_audit:
            return 0.0, [], [], []

        findings = security_audit.get("findings", [])
        agents = list(security_audit.get("agents_used", []))
        recs = [f["remediation"] for f in findings if f.get("remediation")]
        cost = security_audit.get("cost", 0.0)
        return cost, findings, recs, agents


if __name__ == "__main__":
    main()
