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
                tier = self.get_tier_for_stage(stage_name)
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

            # Record stage start in state store (Phase 4)
            self._state_record_stage_start(stage_name)

            # Try each tier in fallback chain
            stage_succeeded = False
            tier_index = 0

            for tier in tier_chain:
                stage_start = datetime.now()

                # Report stage start to progress tracker with current tier
                model_id = self.get_model_for_tier(tier)
                if self._progress_tracker:
                    # On first attempt, start stage. On retry, update tier.
                    if tier_index == 0:
                        self._progress_tracker.start_stage(stage_name, tier.value, model_id)
                    else:
                        # Show tier upgrade (e.g., CHEAP -> CAPABLE)
                        prev_tier = tier_chain[tier_index - 1].value
                        self._progress_tracker.update_tier(
                            stage_name, tier.value, f"{prev_tier}_failed"
                        )

                # Update heartbeat at stage start (Pattern 1)
                if heartbeat_coordinator:
                    try:
                        stage_index = self.stages.index(stage_name)
                        progress = stage_index / len(self.stages)
                        heartbeat_coordinator.beat(
                            status="running",
                            progress=progress,
                            current_task=f"Running stage: {stage_name} ({tier.value})",
                        )
                    except Exception as e:
                        logger.debug(f"Heartbeat update failed: {e}")

                try:
                    # Run the stage at current tier
                    output, input_tokens, output_tokens = await self.run_stage(
                        stage_name,
                        tier,
                        current_data,
                    )

                    stage_end = datetime.now()
                    duration_ms = int((stage_end - stage_start).total_seconds() * 1000)
                    cost = self._calculate_cost(tier, input_tokens, output_tokens)

                    # Create stage output dict for validation
                    stage_output = output if isinstance(output, dict) else {"result": output}

                    # Validate output quality
                    is_valid, failure_reason = self.validate_output(stage_output)

                    if is_valid:
                        # Success - record stage and move to next
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

                        # Update heartbeat after stage completion (Pattern 1)
                        if heartbeat_coordinator:
                            try:
                                stage_index = self.stages.index(stage_name) + 1
                                progress = stage_index / len(self.stages)
                                heartbeat_coordinator.beat(
                                    status="running",
                                    progress=progress,
                                    current_task=f"Completed stage: {stage_name}",
                                )
                            except Exception as e:
                                logger.debug(f"Heartbeat update failed: {e}")

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

                        # Record successful tier usage
                        self._tier_progression.append((stage_name, tier.value, True))
                        stage_succeeded = True

                        # Record stage completion in state store (Phase 4)
                        self._state_record_stage_complete(stage_name, cost, duration_ms, tier.value)

                        # Pass output to next stage
                        current_data = stage_output
                        break  # Success - move to next stage

                    else:
                        # Quality gate failed - try next tier
                        self._tier_progression.append((stage_name, tier.value, False))
                        logger.info(
                            f"Stage {stage_name} failed quality validation with {tier.value}: "
                            f"{failure_reason}"
                        )

                        # Check if more tiers available
                        if tier_index < len(tier_chain) - 1:
                            logger.info("Retrying with higher tier...")
                        else:
                            logger.error(f"All tiers exhausted for {stage_name}")

                except Exception as e:
                    # Exception during stage execution - try next tier
                    self._tier_progression.append((stage_name, tier.value, False))
                    logger.warning(
                        f"Stage {stage_name} error with {tier.value}: {type(e).__name__}: {e}"
                    )

                    # Check if more tiers available
                    if tier_index < len(tier_chain) - 1:
                        logger.info("Retrying with higher tier...")
                    else:
                        logger.error(f"All tiers exhausted for {stage_name}")

                tier_index += 1

            # Check if stage succeeded with any tier
            if not stage_succeeded:
                error_msg = f"Stage {stage_name} failed with all tiers: CHEAP, CAPABLE, PREMIUM"
                if self._progress_tracker:
                    self._progress_tracker.fail_stage(stage_name, error_msg)
                raise ValueError(error_msg)

        return current_data
