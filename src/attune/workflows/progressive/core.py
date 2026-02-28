"""Core data structures for progressive tier escalation.

This module defines the fundamental data structures used throughout the
progressive escalation system, including failure analysis, quality metrics,
tier results, and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Tier(Enum):
    """Model tier levels for progressive escalation.

    Attributes:
        CHEAP: Low-cost models (e.g., gpt-4o-mini, claude-3-haiku)
        CAPABLE: Mid-tier models (e.g., claude-3-5-sonnet, gpt-4o)
        PREMIUM: High-end models (e.g., claude-opus-4, o1)

    """

    CHEAP = "cheap"
    CAPABLE = "capable"
    PREMIUM = "premium"

    def __lt__(self, other: "Tier") -> bool:
        """Compare tiers for ordering (CHEAP < CAPABLE < PREMIUM)."""
        order = {Tier.CHEAP: 0, Tier.CAPABLE: 1, Tier.PREMIUM: 2}
        return order[self] < order[other]


@dataclass
class FailureAnalysis:
    """Multi-signal failure detection and quality analysis.

    Combines multiple signals to provide robust failure detection:
    1. Syntax errors in generated code
    2. Execution failures (test pass rate)
    3. Quality metrics (coverage, assertion depth)
    4. LLM confidence signals

    The composite quality score (CQS) provides an objective measure
    that combines all signals with appropriate weighting.

    Attributes:
        syntax_errors: List of syntax errors found in generated code
        test_failures: List of test execution failures
        test_pass_rate: Percentage of tests that passed (0.0-1.0)
        coverage_percent: Code coverage percentage (0.0-100.0)
        assertion_depth: Average number of assertions per test
        confidence_score: LLM confidence level (0.0-1.0)
        llm_uncertainty_signals: Uncertainty phrases detected in LLM response

    Example:
        >>> analysis = FailureAnalysis(
        ...     test_pass_rate=0.85,
        ...     coverage_percent=78.0,
        ...     assertion_depth=5.2,
        ...     confidence_score=0.92
        ... )
        >>> analysis.calculate_quality_score()
        87.7
        >>> analysis.should_escalate
        False

    """

    syntax_errors: list[SyntaxError] = field(default_factory=list)
    test_failures: list[dict[str, Any]] = field(default_factory=list)
    test_pass_rate: float = 0.0
    coverage_percent: float = 0.0
    assertion_depth: float = 0.0
    confidence_score: float = 0.0
    llm_uncertainty_signals: list[str] = field(default_factory=list)

    def calculate_quality_score(self) -> float:
        """Calculate composite quality score (CQS) from 0-100.

        Formula:
            CQS = (
                0.40 × test_pass_rate +
                0.25 × code_coverage +
                0.20 × assertion_quality +
                0.15 × llm_confidence
            ) × syntax_error_penalty

        Weights:
            - Test pass rate: 40% (most important - functionality must work)
            - Code coverage: 25% (thoroughness matters)
            - Assertion quality: 20% (test depth is important)
            - LLM confidence: 15% (signals potential brittleness)

        Penalties:
            - Syntax errors: 50% penalty (halves the score)

        Returns:
            Quality score from 0.0 (worst) to 100.0 (perfect)

        Example:
            >>> analysis = FailureAnalysis(
            ...     test_pass_rate=0.90,
            ...     coverage_percent=85.0,
            ...     assertion_depth=6.0,
            ...     confidence_score=0.95
            ... )
            >>> analysis.calculate_quality_score()
            91.25

        """
        # Component scores (convert to 0-100 scale)
        pass_rate_score = self.test_pass_rate * 100
        coverage_score = self.coverage_percent

        # Assertion quality: cap at 100% (10 assertions = 100%)
        assertion_quality_score = min(self.assertion_depth * 10, 100)

        confidence_score_scaled = self.confidence_score * 100

        # Weighted composite
        cqs = (
            0.40 * pass_rate_score
            + 0.25 * coverage_score
            + 0.20 * assertion_quality_score
            + 0.15 * confidence_score_scaled
        )

        # Apply syntax error penalty
        if len(self.syntax_errors) > 0:
            cqs *= 0.5  # Halve score for any syntax errors

        return min(cqs, 100.0)

    @property
    def should_escalate(self) -> bool:
        """Determine if this result should trigger escalation.

        Multi-criteria decision based on:
        - Low CQS (<70)
        - Multiple syntax errors (>3)
        - Low test pass rate (<70%)
        - Low coverage (<60%)

        Returns:
            True if escalation is recommended, False otherwise

        Example:
            >>> analysis = FailureAnalysis(test_pass_rate=0.50)
            >>> analysis.should_escalate
            True

        """
        cqs = self.calculate_quality_score()
        return (
            cqs < 70
            or len(self.syntax_errors) > 3
            or self.test_pass_rate < 0.7
            or self.coverage_percent < 60
        )

    @property
    def failure_severity(self) -> str:
        """Determine severity level of failures.

        Returns:
            "CRITICAL": Severe failures, consider skipping to Premium
            "HIGH": Significant failures, escalate to next tier
            "MODERATE": Minor failures, retry at current tier
            "LOW": Acceptable quality, no escalation needed

        Example:
            >>> analysis = FailureAnalysis(test_pass_rate=0.25)
            >>> analysis.failure_severity
            'CRITICAL'

        """
        cqs = self.calculate_quality_score()

        if len(self.syntax_errors) > 5 or self.test_pass_rate < 0.3:
            return "CRITICAL"
        if cqs < 70 or self.test_pass_rate < 0.5:
            return "HIGH"
        if cqs < 80 or self.test_pass_rate < 0.7:
            return "MODERATE"
        return "LOW"


@dataclass
class TierResult:
    """Results from a single tier execution attempt.

    Captures all information about a tier's execution including
    generated artifacts, quality analysis, cost, and escalation decision.

    Attributes:
        tier: Which tier executed (CHEAP, CAPABLE, or PREMIUM)
        model: Specific model used (e.g., "gpt-4o-mini")
        attempt: Attempt number at this tier (1-based)
        timestamp: When this execution occurred
        generated_items: Generated artifacts (tests, code, etc.)
        failure_analysis: Quality and failure analysis
        cost: Cost in USD for this execution
        duration: Execution time in seconds
        escalated: Whether this result triggered escalation
        escalation_reason: Human-readable reason for escalation

    Example:
        >>> result = TierResult(
        ...     tier=Tier.CHEAP,
        ...     model="gpt-4o-mini",
        ...     attempt=1,
        ...     timestamp=datetime.now(),
        ...     generated_items=[{"code": "test_foo()"}],
        ...     failure_analysis=FailureAnalysis(test_pass_rate=0.65),
        ...     cost=0.15,
        ...     duration=12.5
        ... )
        >>> result.quality_score
        65.0

    """

    tier: Tier
    model: str
    attempt: int
    timestamp: datetime

    # Generated artifacts
    generated_items: list[dict[str, Any]] = field(default_factory=list)

    # Analysis
    failure_analysis: FailureAnalysis = field(default_factory=FailureAnalysis)
    cost: float = 0.0
    duration: float = 0.0
    tokens_used: dict[str, int] = field(default_factory=dict)

    # Decision
    escalated: bool = False
    escalation_reason: str = ""

    @property
    def quality_score(self) -> float:
        """Get composite quality score for this tier result.

        Returns:
            CQS from 0.0 to 100.0

        """
        return self.failure_analysis.calculate_quality_score()

    @property
    def success_count(self) -> int:
        """Count of successfully generated items (CQS >= 80).

        Returns:
            Number of items meeting quality threshold

        """
        return sum(1 for item in self.generated_items if item.get("quality_score", 0) >= 80)

    @property
    def success_rate(self) -> float:
        """Percentage of items successfully generated.

        Returns:
            Success rate from 0.0 to 1.0

        """
        if not self.generated_items:
            return 0.0
        return self.success_count / len(self.generated_items)


@dataclass
class ProgressiveWorkflowResult:
    """Complete results from a progressive workflow execution.

    Captures the full progression history across all tiers, including
    costs, quality metrics, and escalation decisions.

    Attributes:
        workflow_name: Name of the workflow (e.g., "test-gen")
        task_id: Unique identifier for this execution
        tier_results: Chronological list of tier execution results
        final_result: The last tier result (may be successful or failed)
        total_cost: Total cost in USD across all tiers
        total_duration: Total execution time in seconds
        success: Whether the workflow completed successfully

    Example:
        >>> result = ProgressiveWorkflowResult(
        ...     workflow_name="test-gen",
        ...     task_id="test-gen-20260117-143022",
        ...     tier_results=[cheap_result, capable_result],
        ...     final_result=capable_result,
        ...     total_cost=0.75,
        ...     total_duration=45.2,
        ...     success=True
        ... )
        >>> print(result.generate_report())
        🎯 PROGRESSIVE ESCALATION REPORT
        ...

    """

    workflow_name: str
    task_id: str
    tier_results: list[TierResult]

    final_result: TierResult
    total_cost: float
    total_duration: float
    success: bool

    def generate_report(self) -> str:
        """Generate human-readable progression report.

        Creates a detailed report showing:
        - Tier-by-tier breakdown
        - Quality scores and success rates
        - Cost analysis and savings
        - Escalation decisions

        Returns:
            Formatted report string

        """
        # Implementation will be in reports.py module
        from attune.workflows.progressive.reports import generate_progression_report

        return generate_progression_report(self)

    def save_to_disk(self, storage_path: str) -> None:
        """Save detailed results to disk.

        Creates a directory with:
        - summary.json: High-level metrics
        - tier_N_<tier_name>.json: Detailed tier results
        - report.txt: Human-readable report

        Args:
            storage_path: Base path for saving results

        """
        from attune.workflows.progressive.reports import save_results_to_disk

        save_results_to_disk(self, storage_path)

    def _calculate_all_premium_cost(self) -> float:
        """Calculate hypothetical cost if all items used Premium tier.

        Used by telemetry to calculate cost savings from progressive escalation.

        Returns:
            Estimated cost in USD if all items were processed at Premium tier

        """
        total_items = sum(len(r.generated_items) for r in self.tier_results)
        # Assume Premium costs ~$0.05 per item (conservative estimate)
        return total_items * 0.05

    @property
    def cost_savings(self) -> float:
        """Calculate cost savings vs running all items at Premium tier.

        Returns:
            Dollar amount saved by using progressive escalation

        """
        all_premium_cost = self._calculate_all_premium_cost()
        savings = all_premium_cost - self.total_cost
        return max(savings, 0.0)

    @property
    def cost_savings_percent(self) -> float:
        """Calculate percentage of cost saved.

        Returns:
            Savings percentage (0-100)

        """
        all_premium_cost = self._calculate_all_premium_cost()

        if all_premium_cost == 0:
            return 0.0

        return (self.cost_savings / all_premium_cost) * 100


@dataclass
class EscalationConfig:
    """Configuration for progressive tier escalation.

    Controls all aspects of the escalation system including retry logic,
    thresholds, cost management, and storage.

    Attributes:
        enabled: Whether progressive escalation is active
        tiers: Ordered list of tiers to use (default: all three)

        Retry configuration:
            cheap_min_attempts: Minimum attempts at cheap tier
            cheap_max_attempts: Maximum attempts at cheap tier
            capable_min_attempts: Minimum attempts at capable tier
            capable_max_attempts: Maximum attempts at capable tier
            premium_max_attempts: Maximum attempts at premium tier

        Thresholds (Cheap → Capable):
            cheap_to_capable_failure_rate: Max failure rate before escalation
            cheap_to_capable_min_cqs: Min quality score to avoid escalation
            cheap_to_capable_max_syntax_errors: Max syntax errors allowed

        Thresholds (Capable → Premium):
            capable_to_premium_failure_rate: Max failure rate before escalation
            capable_to_premium_min_cqs: Min quality score to avoid escalation
            capable_to_premium_max_syntax_errors: Max syntax errors allowed

        Stagnation detection:
            improvement_threshold: Min CQS improvement to avoid stagnation (%)
            consecutive_stagnation_limit: Consecutive stagnations before escalation

        Cost management:
            max_cost: Maximum total cost in USD
            auto_approve_under: Auto-approve escalations under this cost
            warn_on_budget_exceeded: Print warning if budget exceeded
            abort_on_budget_exceeded: Abort execution if budget exceeded

        Storage:
            save_tier_results: Whether to save tier results to disk
            storage_path: Directory for saving results

    Example:
        >>> config = EscalationConfig(
        ...     enabled=True,
        ...     max_cost=10.00,
        ...     auto_approve_under=5.00,
        ...     cheap_min_attempts=2,
        ...     capable_max_attempts=6
        ... )

    """

    # Global settings
    enabled: bool = False
    tiers: list[Tier] = field(default_factory=lambda: [Tier.CHEAP, Tier.CAPABLE, Tier.PREMIUM])

    # Retry configuration
    cheap_min_attempts: int = 2
    cheap_max_attempts: int = 3
    capable_min_attempts: int = 2
    capable_max_attempts: int = 6
    premium_max_attempts: int = 1

    # Thresholds: Cheap → Capable
    cheap_to_capable_failure_rate: float = 0.30
    cheap_to_capable_min_cqs: float = 70.0
    cheap_to_capable_max_syntax_errors: int = 3

    # Thresholds: Capable → Premium
    capable_to_premium_failure_rate: float = 0.20
    capable_to_premium_min_cqs: float = 80.0
    capable_to_premium_max_syntax_errors: int = 1

    # Stagnation detection
    improvement_threshold: float = 5.0  # 5% CQS improvement required
    consecutive_stagnation_limit: int = 2

    # Cost management
    max_cost: float = 5.00
    auto_approve_under: float | None = None
    warn_on_budget_exceeded: bool = True
    abort_on_budget_exceeded: bool = False

    # Storage
    save_tier_results: bool = True
    storage_path: str = ".attune/progressive_runs"

    def get_max_attempts(self, tier: Tier) -> int:
        """Get maximum attempts for a specific tier.

        Args:
            tier: The tier to query

        Returns:
            Maximum number of attempts allowed

        """
        if tier == Tier.CHEAP:
            return self.cheap_max_attempts
        if tier == Tier.CAPABLE:
            return self.capable_max_attempts
        # PREMIUM
        return self.premium_max_attempts

    def get_min_attempts(self, tier: Tier) -> int:
        """Get minimum attempts for a specific tier.

        Args:
            tier: The tier to query

        Returns:
            Minimum number of attempts required

        """
        if tier == Tier.CHEAP:
            return self.cheap_min_attempts
        if tier == Tier.CAPABLE:
            return self.capable_min_attempts
        # PREMIUM
        return 1  # Premium always gets exactly 1 attempt
