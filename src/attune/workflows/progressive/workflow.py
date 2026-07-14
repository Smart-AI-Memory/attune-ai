"""Base class for progressive workflows with tier escalation.

This module provides the foundation for workflows that support progressive
tier escalation, handling retry logic, escalation decisions, cost management,
and approval prompts.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any

from attune.model_tiers import resolve_model
from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    ProgressiveWorkflowResult,
    Tier,
    TierResult,
)
from attune.workflows.progressive.orchestrator import MetaOrchestrator
from attune.workflows.progressive.telemetry import ProgressiveTelemetry

logger = logging.getLogger(__name__)


def _is_interactive() -> bool:
    """Check if running interactively (not in CI).

    Returns:
        True if interactive terminal, False if CI or non-interactive.

    """
    # CI environments typically set these
    if os.getenv("CI") or os.getenv("ATTUNE_NON_INTERACTIVE"):
        return False
    # Check if stdin is a TTY
    return sys.stdin.isatty()


def _load_model_config() -> dict[str, str]:
    """Load model configuration from config/env.

    Environment variables take precedence over config file.

    Returns:
        Dict mapping tier names to model names.

    """
    # Default models
    defaults = {
        "cheap": "gpt-4o-mini",
        "capable": "claude-sonnet-5",
        "premium": resolve_model("premium"),
    }

    # Try to load from unified config
    try:
        from attune.config.loader import load_config

        config = load_config()
        if hasattr(config, "routing"):
            if config.routing.cheap_model:
                defaults["cheap"] = config.routing.cheap_model
            if config.routing.capable_model:
                defaults["capable"] = config.routing.capable_model
            if config.routing.premium_model:
                defaults["premium"] = config.routing.premium_model
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Could not load config, using defaults: {e}")

    # Environment overrides (highest priority)
    return {
        "cheap": os.getenv("ATTUNE_MODEL_CHEAP", defaults["cheap"]),
        "capable": os.getenv("ATTUNE_MODEL_CAPABLE", defaults["capable"]),
        "premium": os.getenv("ATTUNE_MODEL_PREMIUM", defaults["premium"]),
    }


class BudgetExceededError(Exception):
    """Raised when execution cost exceeds configured budget."""


class UserCancelledError(Exception):
    """Raised when user cancels execution during approval prompt."""


class ProgressiveWorkflow:
    """Base class for workflows with progressive tier escalation.

    Implements the core progressive escalation logic:
    1. Start with cheap tier
    2. Analyze results with multi-signal failure detection
    3. Escalate to capable tier if needed
    4. Use LLM-guided retries with stagnation detection
    5. Escalate to premium tier if capable tier stagnates
    6. Request human review if premium tier fails

    Subclasses should implement:
    - _execute_tier_impl(): Tier-specific execution logic
    - _analyze_item(): Item-specific quality analysis

    Example:
        class MyProgressiveWorkflow(ProgressiveWorkflow):
            def _execute_tier_impl(self, tier, items, context):
                # Generate items using appropriate model
                return generated_items

            def _analyze_item(self, item):
                # Analyze item quality
                return FailureAnalysis(...)

    Attributes:
        config: Escalation configuration
        tier_results: List of tier execution results
        meta_orchestrator: Meta-agent for orchestration decisions

    """

    def __init__(self, config: EscalationConfig | None = None, user_id: str | None = None):
        """Initialize progressive workflow.

        Args:
            config: Escalation configuration (uses defaults if None)
            user_id: Optional user identifier for telemetry (will be hashed)

        """
        self.config = config or EscalationConfig()
        self.tier_results: list[TierResult] = []
        self.meta_orchestrator = MetaOrchestrator()
        self.user_id = user_id
        self.telemetry: ProgressiveTelemetry | None = None  # Initialized per workflow

    def execute(self, **kwargs) -> ProgressiveWorkflowResult:
        """Execute workflow with progressive tier escalation.

        This is the main entry point. Subclasses typically override this
        to provide workflow-specific logic, then call _execute_progressive()
        to handle the escalation.

        Args:
            **kwargs: Workflow-specific parameters

        Returns:
            Complete workflow results with progression history

        Raises:
            BudgetExceededError: If cost exceeds budget
            UserCancelledError: If user declines approval

        """
        raise NotImplementedError("Subclasses must implement execute()")

    def _execute_progressive(
        self,
        items: list[Any],
        workflow_name: str,
        **kwargs,
    ) -> ProgressiveWorkflowResult:
        """Execute items with progressive tier escalation.

        Core progressive escalation loop:
        1. Execute at current tier
        2. Analyze results
        3. Separate successful and failed items
        4. Decide: escalate, retry, or complete
        5. Repeat with failed items at next tier

        Args:
            items: Items to process (functions, files, etc.)
            workflow_name: Name of workflow for reporting
            **kwargs: Additional parameters passed to tier execution

        Returns:
            Complete workflow results

        """
        # Initialize telemetry for this workflow
        self.telemetry = ProgressiveTelemetry(workflow_name, self.user_id)

        if not self.config.enabled:
            # Progressive escalation disabled, use default tier
            logger.info("Progressive escalation disabled, using default tier")
            return self._execute_single_tier(items, workflow_name, **kwargs)

        # Estimate cost and request approval
        estimated_cost = self._estimate_total_cost(len(items))
        if not self._request_approval(
            f"Execute {workflow_name} on {len(items)} items",
            estimated_cost,
        ):
            raise UserCancelledError("User declined to proceed")

        # Start with cheapest tier
        current_tier = self.config.tiers[0]
        remaining_items = items
        context: dict[str, Any] | None = None

        while remaining_items and current_tier:
            logger.info(f"Executing {len(remaining_items)} items at {current_tier.value} tier")

            # Execute at current tier
            tier_result = self._execute_tier(current_tier, remaining_items, context, **kwargs)

            self.tier_results.append(tier_result)

            # Track tier execution in telemetry
            if self.telemetry:
                self.telemetry.track_tier_execution(
                    tier_result=tier_result,
                    attempt=tier_result.attempt,
                    escalated=False,  # Will update if escalation happens
                )

            # Check budget
            self._check_budget()

            # Separate successful and failed items
            successful = [
                item for item in tier_result.generated_items if item.get("quality_score", 0) >= 80
            ]
            failed = [
                item for item in tier_result.generated_items if item.get("quality_score", 0) < 80
            ]

            logger.info(
                f"{current_tier.value} tier: {len(successful)}/{len(tier_result.generated_items)} "
                f"successful (CQS={tier_result.quality_score:.1f})",
            )

            # Update remaining items (partial escalation)
            remaining_items = failed

            # Decide: retry, escalate, or complete
            if not remaining_items:
                # All items successful
                break

            should_escalate, reason = self._should_escalate(
                current_tier,
                tier_result,
                attempt=tier_result.attempt,
            )

            if should_escalate:
                # Escalate to next tier
                next_tier = self._get_next_tier(current_tier)

                if next_tier is None:
                    # No higher tier available
                    logger.warning(
                        f"Cannot escalate beyond {current_tier.value} tier, "
                        f"{len(remaining_items)} items incomplete",
                    )
                    tier_result.escalated = True
                    tier_result.escalation_reason = "No higher tier available"
                    break

                logger.info(
                    f"Escalating {len(remaining_items)} items from "
                    f"{current_tier.value} to {next_tier.value}: {reason}",
                )

                # Track escalation in telemetry
                if self.telemetry:
                    current_cost = sum(r.cost for r in self.tier_results)
                    self.telemetry.track_escalation(
                        from_tier=current_tier,
                        to_tier=next_tier,
                        reason=reason,
                        item_count=len(remaining_items),
                        current_cost=current_cost,
                    )

                # Build context for next tier
                context = {
                    "previous_tier": current_tier,
                    "previous_cqs": tier_result.quality_score,
                    "failures": failed,
                    "examples": tier_result.generated_items[-3:],  # Last 3 attempts
                    "reason": reason,
                }

                # Request approval for escalation
                escalation_cost = self._estimate_tier_cost(next_tier, len(remaining_items))
                if not self._request_escalation_approval(
                    current_tier,
                    next_tier,
                    len(remaining_items),
                    escalation_cost,
                ):
                    logger.info("User declined escalation, stopping")
                    break

                tier_result.escalated = True
                tier_result.escalation_reason = reason
                current_tier = next_tier

            else:
                # No escalation needed (retry at same tier or success)
                break

        # Compile final result
        task_id = f"{workflow_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Should always have at least one tier result
        assert self.tier_results, "No tier results generated"

        result = ProgressiveWorkflowResult(
            workflow_name=workflow_name,
            task_id=task_id,
            tier_results=self.tier_results,
            final_result=self.tier_results[-1],
            total_cost=sum(r.cost for r in self.tier_results),
            total_duration=sum(r.duration for r in self.tier_results),
            success=len(remaining_items) == 0,
        )

        # Track workflow completion in telemetry
        if self.telemetry:
            self.telemetry.track_workflow_completion(result)

        return result

    def _execute_single_tier(
        self,
        items: list[Any],
        workflow_name: str,
        **kwargs,
    ) -> ProgressiveWorkflowResult:
        """Execute without progressive escalation (single tier).

        Used when progressive escalation is disabled.

        Args:
            items: Items to process
            workflow_name: Workflow name
            **kwargs: Additional parameters

        Returns:
            Workflow results with single tier

        """
        # Use middle tier (capable) as default
        default_tier = Tier.CAPABLE

        tier_result = self._execute_tier(default_tier, items, None, **kwargs)
        self.tier_results.append(tier_result)

        task_id = f"{workflow_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        return ProgressiveWorkflowResult(
            workflow_name=workflow_name,
            task_id=task_id,
            tier_results=[tier_result],
            final_result=tier_result,
            total_cost=tier_result.cost,
            total_duration=tier_result.duration,
            success=tier_result.quality_score >= 80,
        )

    def _execute_tier(
        self,
        tier: Tier,
        items: list[Any],
        context: dict[str, Any] | None,
        **kwargs,
    ) -> TierResult:
        """Execute items at a specific tier.

        Wrapper that handles timing, cost tracking, and error handling.
        Delegates actual execution to _execute_tier_impl().

        Args:
            tier: Which tier to execute at
            items: Items to process
            context: Context from previous tier (if escalating)
            **kwargs: Additional parameters

        Returns:
            Tier execution result

        """
        start_time = datetime.now()

        try:
            # Let subclass handle actual execution
            generated_items = self._execute_tier_impl(tier, items, context, **kwargs)

            # Analyze overall quality
            failure_analysis = self._analyze_tier_result(generated_items)

            # Calculate cost (placeholder - will be implemented)
            cost = self._calculate_tier_cost(tier, len(items))

            duration = (datetime.now() - start_time).total_seconds()

            return TierResult(
                tier=tier,
                model=self._get_model_for_tier(tier),
                attempt=1,  # Simplified for now
                timestamp=start_time,
                generated_items=generated_items,
                failure_analysis=failure_analysis,
                cost=cost,
                duration=duration,
            )

        except Exception as e:  # noqa: BLE001
            logger.exception(f"Error executing tier {tier.value}: {e}")
            # Return failed result
            duration = (datetime.now() - start_time).total_seconds()
            return TierResult(
                tier=tier,
                model=self._get_model_for_tier(tier),
                attempt=1,
                timestamp=start_time,
                generated_items=[],
                failure_analysis=FailureAnalysis(),
                cost=0.0,
                duration=duration,
                escalated=True,
                escalation_reason=f"Execution error: {e!s}",
            )

    def _execute_tier_impl(
        self,
        tier: Tier,
        items: list[Any],
        context: dict[str, Any] | None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Execute items at specific tier (to be implemented by subclasses).

        Args:
            tier: Which tier to execute at
            items: Items to process
            context: Context from previous tier
            **kwargs: Additional parameters

        Returns:
            List of generated items with quality scores

        """
        raise NotImplementedError("Subclasses must implement _execute_tier_impl()")

    def _analyze_tier_result(self, generated_items: list[dict[str, Any]]) -> FailureAnalysis:
        """Analyze overall quality of tier execution.

        Args:
            generated_items: Items generated at this tier

        Returns:
            Aggregated failure analysis

        """
        if not generated_items:
            return FailureAnalysis()

        # Aggregate metrics across all items
        total_items = len(generated_items)
        passed = sum(1 for item in generated_items if item.get("passed", False))
        syntax_errors = sum(len(item.get("syntax_errors", [])) for item in generated_items)

        avg_coverage = sum(item.get("coverage", 0) for item in generated_items) / total_items
        avg_assertions = sum(item.get("assertions", 0) for item in generated_items) / total_items
        avg_confidence = sum(item.get("confidence", 0) for item in generated_items) / total_items

        return FailureAnalysis(
            syntax_errors=[SyntaxError(f"Syntax error {i}") for i in range(min(syntax_errors, 10))],
            test_pass_rate=passed / total_items if total_items > 0 else 0.0,
            coverage_percent=avg_coverage,
            assertion_depth=avg_assertions,
            confidence_score=avg_confidence,
        )

    def _should_escalate(self, tier: Tier, result: TierResult, attempt: int) -> tuple[bool, str]:
        """Determine if escalation is needed.

        Uses meta-orchestrator to make intelligent escalation decisions
        based on tier, quality score, and attempt number.

        Args:
            tier: Current tier
            result: Tier execution result
            attempt: Attempt number at this tier

        Returns:
            Tuple of (should_escalate, reason)

        """
        return self.meta_orchestrator.should_escalate(tier, result, attempt, self.config)

    def _get_next_tier(self, current_tier: Tier) -> Tier | None:
        """Get the next tier in the progression.

        Args:
            current_tier: Current tier

        Returns:
            Next tier, or None if at highest tier

        """
        try:
            current_index = self.config.tiers.index(current_tier)
            if current_index < len(self.config.tiers) - 1:
                return self.config.tiers[current_index + 1]
        except ValueError:
            pass

        return None

    def _estimate_total_cost(self, item_count: int) -> float:
        """Estimate total cost with probabilistic escalation.

        Args:
            item_count: Number of items to process

        Returns:
            Estimated total cost in USD

        """
        # Base cost: all items at cheap tier
        cheap_cost = self._estimate_tier_cost(Tier.CHEAP, item_count)

        # Estimated escalation (30% to capable, 10% to premium)
        capable_cost = self._estimate_tier_cost(Tier.CAPABLE, int(item_count * 0.3))
        premium_cost = self._estimate_tier_cost(Tier.PREMIUM, int(item_count * 0.1))

        return cheap_cost + capable_cost + premium_cost

    def _estimate_tier_cost(self, tier: Tier, item_count: int) -> float:
        """Estimate cost for specific tier.

        Args:
            tier: Which tier
            item_count: Number of items

        Returns:
            Estimated cost in USD

        """
        # Cost per item (approximate, based on typical token usage)
        COST_PER_ITEM = {
            Tier.CHEAP: 0.003,  # ~$0.003 per item (gpt-4o-mini)
            Tier.CAPABLE: 0.015,  # ~$0.015 per item (claude-3-5-sonnet)
            Tier.PREMIUM: 0.05,  # ~$0.05 per item (claude-opus-4)
        }

        return COST_PER_ITEM[tier] * item_count

    def _calculate_tier_cost(
        self,
        tier: Tier,
        item_count: int,
        actual_tokens: int | None = None,
    ) -> float:
        """Calculate cost for tier execution.

        Logs whether cost is actual (from API response) or estimated.

        Args:
            tier: Which tier
            item_count: Number of items processed
            actual_tokens: Actual token count from API response (if available)

        Returns:
            Cost in USD (actual or estimated)

        """
        # Cost per 1K tokens (approximate, based on 2024-2025 pricing)
        COST_PER_1K_TOKENS = {
            Tier.CHEAP: 0.00015,  # gpt-4o-mini input
            Tier.CAPABLE: 0.003,  # claude-3-5-sonnet
            Tier.PREMIUM: 0.015,  # claude-opus-4
        }

        if actual_tokens is not None:
            cost = (actual_tokens / 1000) * COST_PER_1K_TOKENS.get(tier, 0.003)
            logger.info(f"Cost: ${cost:.4f} (actual, tokens: {actual_tokens:,})")
            return cost

        # Estimate: ~1500 tokens per item
        estimated_tokens = item_count * 1500
        cost = (estimated_tokens / 1000) * COST_PER_1K_TOKENS.get(tier, 0.003)
        logger.info(f"Cost: ${cost:.4f} (estimated, ~{estimated_tokens:,} tokens)")
        return cost

    def _request_approval(self, message: str, estimated_cost: float) -> bool:
        """Request user approval for execution.

        Supports non-interactive mode for CI environments via:
        - ATTUNE_NON_INTERACTIVE=1 env var
        - ATTUNE_AUTO_APPROVE_MAX=<amount> env var (default $1.00)
        - CI=true env var (common in CI systems)

        Args:
            message: Description of what will be executed
            estimated_cost: Estimated cost in USD

        Returns:
            True if approved, False if declined

        """
        # Check auto-approve threshold from config
        if self.config.auto_approve_under and estimated_cost <= self.config.auto_approve_under:
            logger.info(
                f"Auto-approved: ${estimated_cost:.2f} <= ${self.config.auto_approve_under:.2f}",
            )
            return True

        # Default threshold
        threshold = float(os.getenv("ATTUNE_AUTO_APPROVE_MAX", "1.00"))
        if estimated_cost <= threshold:
            logger.info(f"Auto-approved: ${estimated_cost:.2f} <= ${threshold:.2f} threshold")
            return True

        # Non-interactive mode: use policy-based approval
        if not _is_interactive():
            logger.warning(
                f"Non-interactive mode: cost ${estimated_cost:.2f} exceeds "
                f"auto-approve threshold ${threshold:.2f}. Set ATTUNE_AUTO_APPROVE_MAX "
                f"to a higher value to auto-approve, or run interactively.",
            )
            return False

        # Interactive prompt
        print("\n⚠️  Cost Estimate:")
        print(f"   {message}")
        print(f"   Estimated total: ${estimated_cost:.2f}")
        print(f"   (Exceeds threshold of ${threshold:.2f})")
        print()

        response = input("Proceed? [y/N]: ").strip().lower()
        return response == "y"

    def _request_escalation_approval(
        self,
        from_tier: Tier,
        to_tier: Tier,
        item_count: int,
        additional_cost: float,
    ) -> bool:
        """Request approval for tier escalation.

        Supports non-interactive mode for CI environments.

        Args:
            from_tier: Current tier
            to_tier: Target tier
            item_count: Number of items to escalate
            additional_cost: Additional cost for escalation

        Returns:
            True if approved, False if declined

        """
        total_cost = sum(r.cost for r in self.tier_results) + additional_cost

        # Check auto-approve from config
        if self.config.auto_approve_under and total_cost <= self.config.auto_approve_under:
            logger.info(f"Auto-approved escalation: total ${total_cost:.2f}")
            return True

        # Check auto-approve from env
        threshold = float(os.getenv("ATTUNE_AUTO_APPROVE_MAX", "1.00"))
        if total_cost <= threshold:
            logger.info(
                f"Auto-approved escalation: ${total_cost:.2f} <= ${threshold:.2f} threshold",
            )
            return True

        # Non-interactive mode
        if not _is_interactive():
            logger.warning(
                f"Non-interactive mode: escalation cost ${total_cost:.2f} exceeds "
                f"threshold ${threshold:.2f}. Declining escalation.",
            )
            return False

        # Interactive prompt
        print("\n⚠️  Escalation needed:")
        print(f"   {item_count} items from {from_tier.value} → {to_tier.value}")
        print(f"   Additional cost: ~${additional_cost:.2f}")
        print(f"   Total so far: ${sum(r.cost for r in self.tier_results):.2f}")
        print()

        response = input("Proceed? [Y/n]: ").strip().lower()
        return response != "n"

    def _check_budget(self) -> None:
        """Check if budget has been exceeded.

        Raises:
            BudgetExceededError: If abort_on_budget_exceeded is True

        """
        current_cost = sum(r.cost for r in self.tier_results)

        if current_cost > self.config.max_cost:
            # Track budget exceeded event
            if self.telemetry:
                action = "abort" if self.config.abort_on_budget_exceeded else "warn"
                self.telemetry.track_budget_exceeded(
                    current_cost=current_cost,
                    max_budget=self.config.max_cost,
                    action=action,
                )

            if self.config.abort_on_budget_exceeded:
                raise BudgetExceededError(
                    f"Cost ${current_cost:.2f} exceeds budget ${self.config.max_cost:.2f}",
                )
            if self.config.warn_on_budget_exceeded:
                logger.warning(
                    f"Cost ${current_cost:.2f} exceeds budget ${self.config.max_cost:.2f}",
                )

    def _get_model_for_tier(self, tier: Tier) -> str:
        """Get model name for specific tier.

        Model selection priority:
        1. Environment variables (ATTUNE_MODEL_CHEAP, etc.)
        2. Unified config file (routing section)
        3. Built-in defaults

        Args:
            tier: Which tier

        Returns:
            Model name (e.g., "gpt-4o-mini")

        """
        model_config = _load_model_config()
        tier_key = tier.value.lower()  # "cheap", "capable", "premium"
        return model_config.get(tier_key, "claude-sonnet-5")
