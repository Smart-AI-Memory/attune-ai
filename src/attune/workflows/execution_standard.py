"""Standard Execution Mixin.

Extracted from ExecutionMixin to reduce file size.
Provides the _execute_standard() method that runs stages using
routing strategy or tier_map with retry support.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from attune.resilience.retry import RetryConfig, retry_with_backoff

logger = logging.getLogger(__name__)


class StandardExecutionMixin:
    """Mixin providing standard (non-fallback) stage execution logic."""

    async def _execute_standard(
        self,
        current_data: Any,
        WorkflowStage: Any,
    ) -> Any:
        """Execute stages in standard mode using routing strategy or tier_map.

        Args:
            current_data: Current workflow data
            WorkflowStage: WorkflowStage data class

        Returns:
            Updated current_data after all stages

        """
        # Track budget for routing decisions
        total_budget = 100.0  # Default budget in USD
        budget_spent = 0.0

        for stage_name in self.stages:
            # Use routing strategy if available, otherwise fall back to tier_map
            budget_remaining = total_budget - budget_spent
            tier = self._get_tier_with_routing(
                stage_name,
                current_data if isinstance(current_data, dict) else {},
                budget_remaining,
            )
            stage_start = datetime.now()

            # Check if stage should be skipped
            should_skip, skip_reason = self.should_skip_stage(stage_name, current_data)

            if should_skip:
                stage = WorkflowStage(
                    name=stage_name,
                    tier=tier,
                    description=f"Stage: {stage_name}",
                    skipped=True,
                    skip_reason=skip_reason,
                )
                self._stages_run.append(stage)

                # Report skip to progress tracker
                if self._progress_tracker:
                    self._progress_tracker.skip_stage(stage_name, skip_reason or "")

                continue

            # Report stage start to progress tracker
            model_id = self.get_model_for_tier(tier)
            if self._progress_tracker:
                self._progress_tracker.start_stage(stage_name, tier.value, model_id)

            # Record stage start in state store (Phase 4)
            self._state_record_stage_start(stage_name)

            # Run the stage with retry for transient failures
            async def _run_this_stage(_stage=stage_name, _tier=tier, _data=current_data):
                return await self.run_stage(_stage, _tier, _data)

            _retry_cfg = RetryConfig(
                max_attempts=2,
                initial_delay=1.0,
                backoff_factor=2.0,
                retryable_exceptions=(TimeoutError, ConnectionError, RuntimeError),
            )
            output, input_tokens, output_tokens = await retry_with_backoff(
                _run_this_stage,
                config=_retry_cfg,
            )

            stage_end = datetime.now()
            duration_ms = int((stage_end - stage_start).total_seconds() * 1000)
            cost = self._calculate_cost(tier, input_tokens, output_tokens)

            # Record stage completion in state store (Phase 4)
            self._state_record_stage_complete(stage_name, cost, duration_ms, tier.value)

            # Update budget spent for routing decisions
            budget_spent += cost

            stage = WorkflowStage(
                name=stage_name,
                tier=tier,
                description=f"Stage: {stage_name}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                result=output,
                duration_ms=duration_ms,
            )
            self._stages_run.append(stage)

            # Report stage completion to progress tracker
            if self._progress_tracker:
                self._progress_tracker.complete_stage(
                    stage_name,
                    cost=cost,
                    tokens_in=input_tokens,
                    tokens_out=output_tokens,
                )

            # Log to cost tracker
            self.cost_tracker.log_request(
                model=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                task_type=f"workflow:{self.name}:{stage_name}",
            )

            # Track telemetry for this stage
            self._track_telemetry(
                stage=stage_name,
                tier=tier,
                model=model_id,
                cost=cost,
                tokens={"input": input_tokens, "output": output_tokens},
                cache_hit=False,
                cache_type=None,
                duration_ms=duration_ms,
            )

            # Pass output to next stage
            current_data = output if isinstance(output, dict) else {"result": output}

        return current_data
