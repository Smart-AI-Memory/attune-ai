"""Meta-orchestrator for progressive tier escalation decisions.

The MetaOrchestrator is responsible for:
1. Analyzing tier execution results
2. Making escalation decisions
3. Creating specialized agent teams
4. Building XML-enhanced prompts with failure context
5. Detecting stagnation patterns
"""

import logging
from typing import Any

from attune.workflows.progressive.core import EscalationConfig, Tier, TierResult
from attune.workflows.progressive.orchestrator_prompts import TierPromptMixin

logger = logging.getLogger(__name__)


class MetaOrchestrator(TierPromptMixin):
    """Meta-agent that orchestrates progressive tier decisions.

    The MetaOrchestrator acts as a higher-level intelligence that:
    - Analyzes tier results objectively
    - Decides when to escalate vs retry
    - Detects stagnation patterns
    - Creates specialized agent teams per tier
    - Builds context-aware prompts

    This separates escalation logic from workflow logic, allowing
    workflows to focus on their domain-specific tasks.

    Example:
        >>> orchestrator = MetaOrchestrator()
        >>> should_esc, reason = orchestrator.should_escalate(
        ...     tier=Tier.CHEAP,
        ...     result=cheap_result,
        ...     attempt=2,
        ...     config=config
        ... )
        >>> if should_esc:
        ...     print(f"Escalating: {reason}")

    """

    def __init__(self) -> None:
        """Initialize meta-orchestrator."""
        self.tier_history: dict[Tier, list[float]] = {
            Tier.CHEAP: [],
            Tier.CAPABLE: [],
            Tier.PREMIUM: [],
        }

    def should_escalate(
        self,
        tier: Tier,
        result: TierResult,
        attempt: int,
        config: EscalationConfig,
    ) -> tuple[bool, str]:
        """Determine if tier should escalate to next tier.

        Multi-criteria decision based on:
        - Quality score vs thresholds
        - Syntax errors
        - Failure rate
        - Attempt count
        - Stagnation detection (for CAPABLE tier)

        Args:
            tier: Current tier
            result: Execution result
            attempt: Attempt number at this tier
            config: Escalation configuration

        Returns:
            Tuple of (should_escalate, reason)

        Example:
            >>> should_esc, reason = orchestrator.should_escalate(
            ...     Tier.CHEAP, result, 2, config
            ... )
            >>> # (True, "Quality score 65 below threshold 70")

        """
        cqs = result.quality_score

        # Track CQS history for stagnation detection
        self.tier_history[tier].append(cqs)

        # Check if we've met minimum attempts
        min_attempts = config.get_min_attempts(tier)
        if attempt < min_attempts:
            return False, f"Only {attempt}/{min_attempts} attempts completed"

        # Tier-specific threshold checks
        if tier == Tier.CHEAP:
            return self._check_cheap_escalation(result, config)
        if tier == Tier.CAPABLE:
            return self._check_capable_escalation(result, attempt, config)
        # PREMIUM
        # Premium doesn't escalate (highest tier)
        return False, "Premium tier is final"

    def _check_cheap_escalation(
        self,
        result: TierResult,
        config: EscalationConfig,
    ) -> tuple[bool, str]:
        """Check if cheap tier should escalate to capable.

        Args:
            result: Cheap tier result
            config: Escalation configuration

        Returns:
            Tuple of (should_escalate, reason)

        """
        cqs = result.quality_score
        failure_rate = 1.0 - result.success_rate
        syntax_error_count = len(result.failure_analysis.syntax_errors)

        # Check severity first (critical failures)
        if result.failure_analysis.failure_severity == "CRITICAL":
            return True, "Critical failures detected (consider skipping to Premium)"

        # Check syntax errors (prioritize over CQS)
        if syntax_error_count > config.cheap_to_capable_max_syntax_errors:
            return (
                True,
                f"{syntax_error_count} syntax errors exceeds limit {config.cheap_to_capable_max_syntax_errors}",
            )

        # Check failure rate
        if failure_rate > config.cheap_to_capable_failure_rate:
            return (
                True,
                f"Failure rate {failure_rate:.1%} exceeds threshold {config.cheap_to_capable_failure_rate:.1%}",
            )

        # Check CQS threshold
        if cqs < config.cheap_to_capable_min_cqs:
            return (
                True,
                f"Quality score {cqs:.1f} below threshold {config.cheap_to_capable_min_cqs}",
            )

        # All checks passed, no escalation needed
        return False, f"Quality acceptable (CQS={cqs:.1f})"

    def _check_capable_escalation(
        self,
        result: TierResult,
        attempt: int,
        config: EscalationConfig,
    ) -> tuple[bool, str]:
        """Check if capable tier should escalate to premium.

        Includes stagnation detection: if improvement is <5% for 2 consecutive
        attempts, escalate even if quality is borderline acceptable.

        Args:
            result: Capable tier result
            attempt: Attempt number
            config: Escalation configuration

        Returns:
            Tuple of (should_escalate, reason)

        """
        cqs = result.quality_score
        failure_rate = 1.0 - result.success_rate
        syntax_error_count = len(result.failure_analysis.syntax_errors)

        # Check max attempts first
        if attempt >= config.capable_max_attempts:
            return (
                True,
                f"Max attempts ({config.capable_max_attempts}) reached without achieving target quality",
            )

        # Check syntax errors (strict for capable tier)
        if syntax_error_count > config.capable_to_premium_max_syntax_errors:
            return (
                True,
                f"{syntax_error_count} syntax errors exceeds limit {config.capable_to_premium_max_syntax_errors}",
            )

        # Check failure rate
        if failure_rate > config.capable_to_premium_failure_rate:
            return (
                True,
                f"Failure rate {failure_rate:.1%} exceeds threshold {config.capable_to_premium_failure_rate:.1%}",
            )

        # Check stagnation (consecutive runs with <5% improvement)
        # Only check if we have enough history
        if len(self.tier_history[Tier.CAPABLE]) >= config.consecutive_stagnation_limit + 1:
            is_stagnant, stagnation_reason = self._detect_stagnation(
                self.tier_history[Tier.CAPABLE],
                config.improvement_threshold,
                config.consecutive_stagnation_limit,
            )

            if is_stagnant:
                return True, f"Stagnation detected: {stagnation_reason}"

        # Check CQS threshold (after stagnation check)
        if cqs < config.capable_to_premium_min_cqs and attempt >= config.capable_min_attempts:
            return (
                True,
                f"Quality score {cqs:.1f} below threshold {config.capable_to_premium_min_cqs}",
            )

        # No escalation needed
        return False, f"Quality acceptable (CQS={cqs:.1f}), continuing improvement"

    def _detect_stagnation(
        self,
        cqs_history: list[float],
        improvement_threshold: float,
        consecutive_limit: int,
    ) -> tuple[bool, str]:
        """Detect if improvement has stagnated.

        Stagnation is defined as N consecutive attempts with <X% improvement.

        Args:
            cqs_history: List of CQS scores (chronological)
            improvement_threshold: Min improvement % to avoid stagnation
            consecutive_limit: Number of consecutive stagnations before escalating

        Returns:
            Tuple of (is_stagnant, reason)

        """
        if len(cqs_history) < consecutive_limit + 1:
            return False, "Insufficient history for stagnation detection"

        # Check last N improvements
        consecutive_stagnations = 0

        for i in range(len(cqs_history) - 1, 0, -1):
            current = cqs_history[i]
            previous = cqs_history[i - 1]

            improvement = current - previous

            if improvement < improvement_threshold:
                consecutive_stagnations += 1

                if consecutive_stagnations >= consecutive_limit:
                    return True, (
                        f"{consecutive_stagnations} consecutive runs with "
                        f"<{improvement_threshold}% improvement"
                    )
            else:
                # Improvement above threshold, reset counter
                break

        return False, "No stagnation detected"

    def create_agent_team(
        self,
        tier: Tier,
        failure_context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Create specialized agent team for tier.

        Different tiers get different agent compositions:
        - CHEAP: Single generator agent
        - CAPABLE: Generator + Analyzer
        - PREMIUM: Generator + Analyzer + Reviewer

        Args:
            tier: Which tier
            failure_context: Context from previous tier

        Returns:
            List of agent types to create

        """
        if tier == Tier.CHEAP:
            return ["generator"]
        if tier == Tier.CAPABLE:
            return ["generator", "analyzer"]
        # PREMIUM
        return ["generator", "analyzer", "reviewer"]

    def analyze_failure_patterns(self, failures: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze failure patterns to inform next tier.

        Groups failures by type and identifies common issues.

        Args:
            failures: List of failed items with error details

        Returns:
            Failure pattern analysis

        """
        # Group by error type
        error_types: dict[str, int] = {}

        for failure in failures:
            error = failure.get("error", "unknown")

            # Categorize error
            if "async" in error.lower() or "await" in error.lower():
                error_types["async_errors"] = error_types.get("async_errors", 0) + 1
            elif "mock" in error.lower():
                error_types["mocking_errors"] = error_types.get("mocking_errors", 0) + 1
            elif "syntax" in error.lower():
                error_types["syntax_errors"] = error_types.get("syntax_errors", 0) + 1
            else:
                error_types["other_errors"] = error_types.get("other_errors", 0) + 1

        return {
            "total_failures": len(failures),
            "error_types": error_types,
            "primary_issue": (
                max(error_types.items(), key=lambda x: x[1])[0] if error_types else "unknown"
            ),
        }
