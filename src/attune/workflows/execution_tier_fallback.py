"""Tier Fallback Execution Mixin.

Extracted from ExecutionMixin to reduce file size.
Provides the _execute_tier_fallback() method that tries
CHEAP -> CAPABLE -> PREMIUM with quality validation at each tier.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class TierFallbackExecutionMixin:
    """Mixin providing tier-fallback stage execution logic."""

    async def _execute_tier_fallback(
        self,
        current_data: Any,
        heartbeat_coordinator: Any,
        ModelTier: Any,
        WorkflowStage: Any,
    ) -> Any:
        """Execute stages with tier fallback (CHEAP -> CAPABLE -> PREMIUM).

        Args:
            current_data: Current workflow data
            heartbeat_coordinator: Heartbeat coordinator instance or None
            ModelTier: ModelTier enum class
            WorkflowStage: WorkflowStage data class

        Returns:
            Updated current_data after all stages

        """
        tier_chain = [ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM]

        for stage_name in self.stages:
            # Check if stage should be skipped
            should_skip, skip_reason = self.should_skip_stage(stage_name, current_data)

            if should_skip:
                self._handle_stage_skip(stage_name, skip_reason, WorkflowStage)
                continue

            # Record stage start in state store (Phase 4)
            self._state_record_stage_start(stage_name)

            # Try each tier in fallback chain
            stage_succeeded = False

            for tier_index, tier in enumerate(tier_chain):
                stage_start = datetime.now()
                model_id = self.get_model_for_tier(tier)

                self._report_stage_progress(stage_name, tier, tier_index, tier_chain, model_id)
                self._update_heartbeat(heartbeat_coordinator, stage_name, tier, offset=0)

                try:
                    output, input_tokens, output_tokens = await self.run_stage(
                        stage_name,
                        tier,
                        current_data,
                    )

                    duration_ms = int((datetime.now() - stage_start).total_seconds() * 1000)
                    cost = self._calculate_cost(tier, input_tokens, output_tokens)
                    stage_output = output if isinstance(output, dict) else {"result": output}

                    is_valid, failure_reason = self.validate_output(stage_output)

                    if is_valid:
                        self._record_stage_success(
                            stage_name,
                            tier,
                            model_id,
                            WorkflowStage,
                            input_tokens,
                            output_tokens,
                            cost,
                            output,
                            duration_ms,
                            heartbeat_coordinator,
                        )
                        current_data = stage_output
                        stage_succeeded = True
                        break

                    self._log_tier_failure(
                        stage_name,
                        tier,
                        tier_index,
                        tier_chain,
                        reason=failure_reason,
                        level="info",
                    )

                except Exception as e:
                    self._log_tier_failure(
                        stage_name,
                        tier,
                        tier_index,
                        tier_chain,
                        reason=f"{type(e).__name__}: {e}",
                        level="warning",
                    )

            if not stage_succeeded:
                error_msg = f"Stage {stage_name} failed with all tiers: CHEAP, CAPABLE, PREMIUM"
                if self._progress_tracker:
                    self._progress_tracker.fail_stage(stage_name, error_msg)
                raise ValueError(error_msg)

        return current_data

    def _handle_stage_skip(
        self,
        stage_name: str,
        skip_reason: str | None,
        WorkflowStage: Any,
    ) -> None:
        """Record a skipped stage and notify progress tracker."""
        tier = self.get_tier_for_stage(stage_name)
        stage = WorkflowStage(
            name=stage_name,
            tier=tier,
            description=f"Stage: {stage_name}",
            skipped=True,
            skip_reason=skip_reason,
        )
        self._stages_run.append(stage)

        if self._progress_tracker:
            self._progress_tracker.skip_stage(stage_name, skip_reason or "")

    def _report_stage_progress(
        self,
        stage_name: str,
        tier: Any,
        tier_index: int,
        tier_chain: list,
        model_id: str,
    ) -> None:
        """Report stage start or tier upgrade to progress tracker."""
        if not self._progress_tracker:
            return

        if tier_index == 0:
            self._progress_tracker.start_stage(stage_name, tier.value, model_id)
        else:
            prev_tier = tier_chain[tier_index - 1].value
            self._progress_tracker.update_tier(stage_name, tier.value, f"{prev_tier}_failed")

    def _update_heartbeat(
        self,
        heartbeat_coordinator: Any,
        stage_name: str,
        tier: Any,
        offset: int = 0,
    ) -> None:
        """Send a heartbeat update with current stage progress.

        Args:
            heartbeat_coordinator: Coordinator instance or None
            stage_name: Current stage name
            tier: Current tier being attempted
            offset: 0 for stage start, 1 for stage completion

        """
        if not heartbeat_coordinator:
            return

        try:
            stage_index = self.stages.index(stage_name) + offset
            progress = stage_index / len(self.stages)
            task_label = "Completed" if offset else "Running"
            heartbeat_coordinator.beat(
                status="running",
                progress=progress,
                current_task=f"{task_label} stage: {stage_name}"
                + (f" ({tier.value})" if not offset else ""),
            )
        except Exception as e:
            logger.debug(f"Heartbeat update failed: {e}")

    def _record_stage_success(
        self,
        stage_name: str,
        tier: Any,
        model_id: str,
        WorkflowStage: Any,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        output: Any,
        duration_ms: int,
        heartbeat_coordinator: Any,
    ) -> None:
        """Record all bookkeeping for a successful stage execution."""
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

        if self._progress_tracker:
            self._progress_tracker.complete_stage(
                stage_name,
                cost=cost,
                tokens_in=input_tokens,
                tokens_out=output_tokens,
            )

        self._update_heartbeat(heartbeat_coordinator, stage_name, tier, offset=1)

        self.cost_tracker.log_request(
            model=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            task_type=f"workflow:{self.name}:{stage_name}",
        )

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

        self._tier_progression.append((stage_name, tier.value, True))
        self._state_record_stage_complete(stage_name, cost, duration_ms, tier.value)

    def _log_tier_failure(
        self,
        stage_name: str,
        tier: Any,
        tier_index: int,
        tier_chain: list,
        reason: str,
        level: str = "info",
    ) -> None:
        """Log a tier failure and record it in progression history."""
        self._tier_progression.append((stage_name, tier.value, False))

        log_fn = getattr(logger, level, logger.info)
        log_fn(
            f"Stage {stage_name} failed "
            f"{'quality validation ' if level == 'info' else ''}"
            f"with {tier.value}: {reason}",
        )

        if tier_index < len(tier_chain) - 1:
            logger.info("Retrying with higher tier...")
        else:
            logger.error(f"All tiers exhausted for {stage_name}")
