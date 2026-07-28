"""Data models and configuration for Release Preparation Agent Team.

Enums, configuration constants, and dataclasses for agent results,
quality gates, and release readiness reports.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from attune.model_tiers import resolve_model

logger = logging.getLogger(__name__)


# =============================================================================
# Optional dependencies (graceful degradation)
# =============================================================================

try:
    import redis as redis_lib

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_lib = None  # type: ignore[assignment]

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None  # type: ignore[assignment]


# =============================================================================
# Configuration
# =============================================================================

#: Tiers whose model id is fixed (no env override path).
_STATIC_MODELS = {"cheap": "claude-haiku-4-5", "capable": "claude-sonnet-5"}


def get_model_config() -> dict[str, str]:
    """Resolve the tier -> model-id map, reading env at CALL time.

    The premium entry resolves through :mod:`attune.model_tiers`, which
    honors ``ATTUNE_MODEL_PREMIUM``. Resolving here rather than at import
    keeps this consistent with the rest of the codebase: every other
    ``ATTUNE_*`` read in ``src/`` happens inside a function (61 sites),
    and this dict was the single module-level binding that froze a
    resolver result at import.

    That freeze was a real defect, not just a testing nuisance — a
    long-lived process (MCP server, ops dashboard) could not observe a
    changed override without a restart, the effective value depended on
    import order, and a consumer doing ``from … import MODEL_CONFIG``
    captured a snapshot that ``importlib.reload`` could not refresh.
    Ruled 2026-07-28 (round table ``q-conftest-env-scrub-001``):
    ``ATTUNE_*`` overrides are observable after import.
    """
    return {**_STATIC_MODELS, "premium": resolve_model("premium")}


def __getattr__(name: str) -> object:
    """Keep ``release_models.MODEL_CONFIG`` working, resolved fresh.

    Attribute access re-resolves; it is no longer a frozen module global.
    Note that ``from … import MODEL_CONFIG`` still binds a snapshot at
    the importing module's import time — call :func:`get_model_config`
    instead when the value must track the environment.
    """
    if name == "MODEL_CONFIG":
        return get_model_config()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# LLM mode: "real" uses API calls, "simulated" uses rule-based analysis
LLM_MODE = os.getenv("RELEASE_LLM_MODE", "simulated")


class Tier(Enum):
    """Model tier for progressive escalation."""

    CHEAP = "cheap"
    CAPABLE = "capable"
    PREMIUM = "premium"


# Default quality gate thresholds
DEFAULT_QUALITY_GATES = {
    "max_critical_issues": 0,
    "min_coverage": 80.0,
    "min_quality_score": 7.0,
    "min_doc_coverage": 80.0,
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ReleaseAgentResult:
    """Result from an individual release agent.

    Attributes:
        agent_id: Unique agent identifier
        agent_role: Human-readable role name
        success: Whether the agent completed successfully
        tier_used: Final tier used (after any escalation)
        findings: Structured findings dict
        score: Numeric score (0-100 or 0-10 depending on agent)
        confidence: Confidence in the result (0.0-1.0)
        cost: LLM API cost in USD
        execution_time_ms: Wall-clock time in milliseconds
        escalated: Whether tier escalation occurred

    """

    agent_id: str
    agent_role: str
    success: bool
    tier_used: Tier
    findings: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    confidence: float = 0.0
    cost: float = 0.0
    execution_time_ms: float = 0.0
    escalated: bool = False


@dataclass
class QualityGate:
    """Quality gate threshold for release readiness.

    Attributes:
        name: Gate identifier
        threshold: Minimum/maximum acceptable value
        actual: Measured value
        passed: Whether gate passed
        critical: Whether failure blocks release
        message: Human-readable status message

    """

    name: str
    threshold: float
    actual: float = 0.0
    passed: bool = False
    critical: bool = True
    message: str = ""

    def __post_init__(self) -> None:
        """Generate message if not provided."""
        if not self.message:
            status = "PASS" if self.passed else "FAIL"
            self.message = (
                f"{self.name}: {status} "
                f"(actual: {self.actual:.1f}, threshold: {self.threshold:.1f})"
            )


@dataclass
class ReleaseReadinessReport:
    """Aggregated release readiness assessment.

    Attributes:
        approved: Overall release approval status
        confidence: Confidence level (high, medium, low)
        quality_gates: List of quality gate results
        agent_results: Individual agent outputs
        blockers: Critical issues blocking release
        warnings: Non-critical issues to address
        summary: Executive summary
        timestamp: Report generation time
        total_duration: Total execution time in seconds
        total_cost: Total LLM API cost

    """

    approved: bool
    confidence: str
    quality_gates: list[QualityGate] = field(default_factory=list)
    agent_results: list[ReleaseAgentResult] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_duration: float = 0.0
    total_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "approved": self.approved,
            "confidence": self.confidence,
            "quality_gates": [
                {
                    "name": g.name,
                    "threshold": g.threshold,
                    "actual": g.actual,
                    "passed": g.passed,
                    "critical": g.critical,
                    "message": g.message,
                }
                for g in self.quality_gates
            ],
            "agent_results": {
                r.agent_role: {
                    "success": r.success,
                    "score": r.score,
                    "confidence": r.confidence,
                    "tier_used": r.tier_used.value,
                    "cost": r.cost,
                    "findings": r.findings,
                }
                for r in self.agent_results
            },
            "blockers": self.blockers,
            "warnings": self.warnings,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "total_duration": self.total_duration,
            "total_cost": self.total_cost,
        }

    def format_console_output(self) -> str:
        """Format report for console display."""
        lines = []
        lines.append("=" * 70)
        lines.append("RELEASE READINESS REPORT (Agent Team)")
        lines.append("=" * 70)
        lines.append("")

        status_icon = "READY FOR RELEASE" if self.approved else "NOT READY"
        lines.append(f"Status: {status_icon}")
        lines.append(f"Confidence: {self.confidence.upper()}")
        lines.append(f"Duration: {self.total_duration:.2f}s")
        lines.append(f"Total Cost: ${self.total_cost:.4f}")
        lines.append("")

        lines.append("-" * 70)
        lines.append("QUALITY GATES")
        lines.append("-" * 70)
        for gate in self.quality_gates:
            icon = "PASS" if gate.passed else ("BLOCK" if gate.critical else "WARN")
            lines.append(f"  [{icon}] {gate.message}")
        lines.append("")

        if self.blockers:
            lines.append("-" * 70)
            lines.append("BLOCKERS")
            lines.append("-" * 70)
            for blocker in self.blockers:
                lines.append(f"  - {blocker}")
            lines.append("")

        if self.warnings:
            lines.append("-" * 70)
            lines.append("WARNINGS")
            lines.append("-" * 70)
            for warning in self.warnings:
                lines.append(f"  - {warning}")
            lines.append("")

        lines.append("-" * 70)
        lines.append(f"AGENTS ({len(self.agent_results)})")
        lines.append("-" * 70)
        for result in self.agent_results:
            status = "OK" if result.success else "FAIL"
            esc = " (escalated)" if result.escalated else ""
            lines.append(
                f"  [{status}] {result.agent_role}: "
                f"tier={result.tier_used.value}{esc} "
                f"[{result.execution_time_ms:.0f}ms]",
            )
        lines.append("")

        if self.summary:
            lines.append("-" * 70)
            lines.append("SUMMARY")
            lines.append("-" * 70)
            lines.append(self.summary)
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)
