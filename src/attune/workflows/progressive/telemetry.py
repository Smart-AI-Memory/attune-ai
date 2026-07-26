"""Telemetry integration for progressive workflows.

Tracks cost, tier usage, escalation patterns, and savings for progressive workflows.
"""

import logging
from datetime import datetime
from typing import Any

from attune.telemetry.usage_tracker import UsageTracker
from attune.workflows.progressive.core import ProgressiveWorkflowResult, Tier, TierResult

logger = logging.getLogger(__name__)


class ProgressiveTelemetry:
    """Telemetry tracker for progressive workflows."""

    def __init__(self, workflow_name: str, user_id: str | None = None) -> None:
        """Initialize telemetry tracker.

        Args:
            workflow_name: Name of the workflow (e.g., "test-gen")
            user_id: Optional user identifier (will be hashed)

        """
        self.workflow_name = workflow_name
        self.user_id = user_id
        self.tracker = UsageTracker.get_instance()

    def track_tier_execution(
        self,
        tier_result: TierResult,
        attempt: int,
        escalated: bool,
        escalation_reason: str | None = None,
    ) -> None:
        """Track a single tier execution.

        Args:
            tier_result: Result from tier execution
            attempt: Attempt number for this tier
            escalated: Whether this tier escalated to next
            escalation_reason: Why escalation occurred (if escalated)

        """
        # Extract token counts from tier result
        tokens = {
            "input_tokens": tier_result.tokens_used.get("input", 0),
            "output_tokens": tier_result.tokens_used.get("output", 0),
            "total_tokens": tier_result.tokens_used.get("total", 0),
        }

        # Track LLM call
        try:
            self.tracker.track_llm_call(
                workflow=self.workflow_name,
                stage=f"tier-{tier_result.tier.value}-attempt-{attempt}",
                tier=tier_result.tier.value.upper(),
                model=tier_result.model,
                provider=self._get_provider(tier_result.model),
                cost=tier_result.cost,
                tokens=tokens,
                cache_hit=False,  # Progressive workflows don't use cache
                cache_type=None,
                duration_ms=int(tier_result.duration * 1000),
                user_id=self.user_id,
            )

            logger.debug(
                f"Tracked {tier_result.tier.value} tier execution: "
                f"${tier_result.cost:.3f}, {tokens['total_tokens']} tokens",
            )

        except Exception as e:  # noqa: BLE001
            # Telemetry failure should not break workflow
            logger.warning(f"Failed to track tier execution: {e}")

    def track_workflow_completion(
        self,
        result: ProgressiveWorkflowResult,
    ) -> None:
        """Track complete workflow execution with cost savings analysis.

        Args:
            result: Final workflow result

        """
        try:
            # Calculate metrics
            total_items = len(result.final_result.generated_items)
            total_cost = result.total_cost
            total_duration_ms = int(result.total_duration * 1000)

            # Cost savings vs all-premium
            all_premium_cost = result._calculate_all_premium_cost()
            savings = all_premium_cost - total_cost
            savings_percent = (savings / all_premium_cost * 100) if all_premium_cost > 0 else 0

            # Tier distribution
            tier_breakdown = {}
            for tier_result in result.tier_results:
                tier_name = tier_result.tier.value
                if tier_name not in tier_breakdown:
                    tier_breakdown[tier_name] = {
                        "items": 0,
                        "cost": 0.0,
                        "attempts": 0,
                    }
                tier_breakdown[tier_name]["items"] += len(tier_result.generated_items)
                tier_breakdown[tier_name]["cost"] += tier_result.cost
                tier_breakdown[tier_name]["attempts"] += 1

            # Log summary
            logger.info(
                f"Progressive workflow '{self.workflow_name}' completed:\n"
                f"  Items: {total_items}\n"
                f"  Cost: ${total_cost:.3f} (saved ${savings:.3f}, {savings_percent:.0f}%)\n"
                f"  Duration: {result.total_duration:.1f}s\n"
                f"  Tiers: {list(tier_breakdown.keys())}",
            )

            # Custom telemetry event for workflow summary
            self._track_custom_event(
                event_type="progressive_workflow_completion",
                data={
                    "workflow": self.workflow_name,
                    "task_id": result.task_id,
                    "total_items": total_items,
                    "total_cost": total_cost,
                    "total_duration_ms": total_duration_ms,
                    "cost_savings": savings,
                    "savings_percent": savings_percent,
                    "all_premium_cost": all_premium_cost,
                    "tier_breakdown": tier_breakdown,
                    "success": result.success,
                    "final_cqs": (
                        result.final_result.failure_analysis.calculate_quality_score()
                        if result.final_result.failure_analysis
                        else None
                    ),
                },
            )

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to track workflow completion: {e}")

    def track_escalation(
        self,
        from_tier: Tier,
        to_tier: Tier,
        reason: str,
        item_count: int,
        current_cost: float,
    ) -> None:
        """Track tier escalation event.

        Args:
            from_tier: Source tier
            to_tier: Destination tier
            reason: Why escalation occurred
            item_count: Number of items being escalated
            current_cost: Cost accumulated so far

        """
        try:
            self._track_custom_event(
                event_type="progressive_escalation",
                data={
                    "workflow": self.workflow_name,
                    "from_tier": from_tier.value,
                    "to_tier": to_tier.value,
                    "reason": reason,
                    "item_count": item_count,
                    "current_cost": current_cost,
                },
            )

            logger.info(
                f"Escalated {item_count} items from {from_tier.value} → {to_tier.value}: {reason}",
            )

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to track escalation: {e}")

    def track_budget_exceeded(
        self,
        current_cost: float,
        max_budget: float,
        action: str,
    ) -> None:
        """Track budget exceeded event.

        Args:
            current_cost: Current cost that exceeded budget
            max_budget: Maximum budget allowed
            action: Action taken ("abort" or "warn")

        """
        try:
            self._track_custom_event(
                event_type="progressive_budget_exceeded",
                data={
                    "workflow": self.workflow_name,
                    "current_cost": current_cost,
                    "max_budget": max_budget,
                    "overage": current_cost - max_budget,
                    "action": action,
                },
            )

            logger.warning(f"Budget exceeded: ${current_cost:.3f} > ${max_budget:.3f} ({action})")

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to track budget exceeded: {e}")

    def _track_custom_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Track custom telemetry event.

        Args:
            event_type: Type of event
            data: Event data

        """
        # For now, just log to telemetry directory as JSONL
        # Future: could send to analytics service
        import json
        from pathlib import Path

        try:
            telemetry_dir = Path.home() / ".attune" / "telemetry"
            telemetry_dir.mkdir(parents=True, exist_ok=True)

            events_file = telemetry_dir / "progressive_events.jsonl"

            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id_hash": (self._hash_user_id(self.user_id) if self.user_id else "anonymous"),
                **data,
            }

            with events_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to write custom event: {e}")

    @staticmethod
    def _get_provider(model: str) -> str:
        """Infer provider from model name.

        Args:
            model: Model name

        Returns:
            Provider name

        """
        if "gpt" in model.lower():
            return "openai"
        if "claude" in model.lower():
            return "anthropic"
        if "gemini" in model.lower():
            return "google"
        return "unknown"

    @staticmethod
    def _hash_user_id(user_id: str) -> str:
        """Hash user ID for privacy.

        Args:
            user_id: User identifier

        Returns:
            SHA256 hash of user_id

        """
        import hashlib

        return hashlib.sha256(user_id.encode()).hexdigest()
