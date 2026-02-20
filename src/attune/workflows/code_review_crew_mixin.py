"""Code review crew integration mixin.

Extracted from code_review.py for maintainability.

Contains:
    CrewMixin:
        _initialize_crew — lazy-initialize the CodeReviewCrew
        _crew_review     — CAPABLE 5-agent crew analysis stage

Expected host attributes (provided by BaseWorkflow / CodeReviewWorkflow):
    _crew           : Any (crew instance)
    _crew_available : bool
    _needs_architect_review : bool
    crew_config     : dict

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging

from .base import ModelTier

logger = logging.getLogger(__name__)


class CrewMixin:
    """Mixin providing CodeReviewCrew integration for code review."""

    async def _initialize_crew(self) -> None:
        """Initialize the CodeReviewCrew."""
        if self._crew is not None:
            return

        try:
            import logging

            from attune.agent_factory.crews.code_review import CodeReviewCrew

            self._crew = CodeReviewCrew()
            self._crew_available = True
            logging.getLogger(__name__).info("CodeReviewCrew initialized successfully")
        except ImportError as e:
            import logging

            logging.getLogger(__name__).warning(f"CodeReviewCrew not available: {e}")
            self._crew_available = False

    async def _crew_review(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Run CodeReviewCrew for comprehensive 5-agent analysis.

        This stage uses the CodeReviewCrew (Review Lead, Security Analyst,
        Architecture Reviewer, Quality Analyst, Performance Reviewer) for
        deep code analysis with memory graph integration.

        Falls back gracefully if CodeReviewCrew is not available.
        """
        await self._initialize_crew()

        try:
            from .code_review_adapters import (
                _check_crew_available,
                _get_crew_review,
                crew_report_to_workflow_format,
            )
        except ImportError:
            # Crew adapters removed - return fallback
            return (
                {
                    "crew_review": {
                        "available": False,
                        "fallback": True,
                        "reason": "Crew adapters not installed",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Get code to review
        diff = input_data.get("diff", "") or input_data.get("code_to_review", "")
        files_changed = input_data.get("files_changed", [])

        # Check if crew is available
        if not self._crew_available or not _check_crew_available():
            return (
                {
                    "crew_review": {
                        "available": False,
                        "fallback": True,
                        "reason": "CodeReviewCrew not installed or failed to initialize",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Run CodeReviewCrew
        report = await _get_crew_review(
            diff=diff,
            files_changed=files_changed,
            config=self.crew_config,
        )

        if report is None:
            return (
                {
                    "crew_review": {
                        "available": True,
                        "fallback": True,
                        "reason": "CodeReviewCrew review failed or timed out",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Convert crew report to workflow format
        crew_results = crew_report_to_workflow_format(report)

        # Update needs_architect_review based on crew findings
        has_blocking = crew_results.get("has_blocking_issues", False)
        critical_count = len(crew_results.get("assessment", {}).get("critical_findings", []))
        high_count = len(crew_results.get("assessment", {}).get("high_findings", []))

        if has_blocking or critical_count > 0 or high_count > 2:
            self._needs_architect_review = True

        crew_review_result = {
            "available": True,
            "fallback": False,
            "findings": crew_results.get("findings", []),
            "finding_count": crew_results.get("finding_count", 0),
            "verdict": crew_results.get("verdict", "approve"),
            "quality_score": crew_results.get("quality_score", 100),
            "has_blocking_issues": has_blocking,
            "critical_count": critical_count,
            "high_count": high_count,
            "summary": crew_results.get("summary", ""),
            "agents_used": crew_results.get("agents_used", []),
            "memory_graph_hits": crew_results.get("memory_graph_hits", 0),
            "review_duration_seconds": crew_results.get("review_duration_seconds", 0),
        }

        # Estimate tokens (crew uses internal LLM calls)
        input_tokens = len(diff) // 4
        output_tokens = len(str(crew_review_result)) // 4

        return (
            {
                "crew_review": crew_review_result,
                "needs_architect_review": self._needs_architect_review,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )
