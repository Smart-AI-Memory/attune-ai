"""Execution Mixin for BaseWorkflow.

Extracted from BaseWorkflow to improve maintainability.
Provides the main execute() method and its helper logic.

Expected attributes on the host class:
    name (str): Workflow name
    description (str): Workflow description
    stages (list[str]): Stage names
    tier_map (dict): Stage to tier mapping
    cost_tracker (CostTracker): Cost tracker instance
    provider (ModelProvider): Model provider enum
    _provider_str (str): Provider string identifier
    _config (WorkflowConfig | None): Workflow configuration
    _run_id (str): Run ID for telemetry
    _stages_run (list[WorkflowStage]): Stages run
    _progress_callback: Optional progress callback
    _progress_tracker: Optional progress tracker
    _enable_rich_progress (bool): Rich progress flag
    _rich_reporter: Optional Rich reporter
    _executor: Optional LLM executor
    _cache: Optional cache instance
    _enable_cache (bool): Cache enable flag
    _enable_tier_tracking (bool): Tier tracking flag
    _tier_tracker: Optional tier tracker
    _enable_tier_fallback (bool): Tier fallback flag
    _tier_progression (list): Tier progression records
    _routing_strategy: Optional routing strategy
    _enable_adaptive_routing (bool): Adaptive routing flag
    _enable_heartbeat_tracking (bool): Heartbeat flag
    _enable_coordination (bool): Coordination flag
    _agent_id (str | None): Agent identifier
    _telemetry_backend: Telemetry backend

    Inherited methods:
    _maybe_setup_cache(): From CachingMixin
    _assess_complexity(input_data): From LLMMixin
    should_skip_stage(stage_name, input_data): From LLMMixin
    get_tier_for_stage(stage_name): From BaseWorkflow
    get_model_for_tier(tier): From LLMMixin
    run_stage(stage_name, tier, input_data): Abstract from BaseWorkflow
    _calculate_cost(tier, in_tokens, out_tokens): From CostTrackingMixin
    validate_output(stage_output): From LLMMixin
    _track_telemetry(...): From TelemetryMixin
    _emit_workflow_telemetry(result): From TelemetryMixin
    _generate_cost_report(): From CostTrackingMixin
    _get_tier_with_routing(stage, data, budget): From TierRoutingMixin
    _get_heartbeat_coordinator(): From CoordinationMixin

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from attune.resilience.retry import RetryConfig, retry_with_backoff

if TYPE_CHECKING:
    from .data_classes import WorkflowResult

logger = logging.getLogger(__name__)


class ExecutionMixin:
    """Mixin providing the main workflow execution method."""

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    description: str
    stages: list[str]

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the full workflow.

        Args:
            **kwargs: Initial input data for the workflow

        Returns:
            WorkflowResult with stages, output, and cost report

        """
        from attune.models import TaskRoutingRecord

        from .compat import ModelTier
        from .data_classes import WorkflowResult, WorkflowStage
        from .history_utils import _save_workflow_run
        from .progress import (
            RICH_AVAILABLE,
            ConsoleProgressReporter,
            ProgressTracker,
            RichProgressReporter,
        )

        # Set up cache (one-time setup with user prompt if needed)
        self._maybe_setup_cache()

        # Set run ID for telemetry correlation
        self._run_id = str(uuid.uuid4())

        # Record workflow start in state store (Phase 4 - state persistence)
        self._state_record_workflow_start()

        # Log task routing (Tier 1 automation monitoring)
        routing_id = f"routing-{self._run_id}"
        routing_record = TaskRoutingRecord(
            routing_id=routing_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            task_description=f"{self.name}: {self.description}",
            task_type=self.name,
            task_complexity=self._assess_complexity(kwargs),
            assigned_agent=self.name,
            assigned_tier=getattr(self, "_provider_str", "unknown"),
            routing_strategy="rule_based",
            confidence_score=1.0,
            status="running",
            started_at=datetime.utcnow().isoformat() + "Z",
        )

        # Log routing start
        try:
            if self._telemetry_backend is not None:
                self._telemetry_backend.log_task_routing(routing_record)
        except Exception as e:
            logger.debug(f"Failed to log task routing: {e}")

        # Auto tier recommendation
        if self._enable_tier_tracking:
            try:
                from .tier_tracking import WorkflowTierTracker

                self._tier_tracker = WorkflowTierTracker(self.name, self.description)
                files_affected = kwargs.get("files_affected") or kwargs.get("path")
                if files_affected and not isinstance(files_affected, list):
                    files_affected = [str(files_affected)]
                self._tier_tracker.show_recommendation(files_affected)
            except Exception as e:
                logger.debug(f"Tier tracking disabled: {e}")
                self._enable_tier_tracking = False

        # Initialize agent ID for heartbeat/coordination (Pattern 1 & 2)
        if self._agent_id is None:
            # Auto-generate agent ID from workflow name and run ID
            self._agent_id = f"{self.name}-{self._run_id[:8]}"

        # Start heartbeat tracking (Pattern 1)
        heartbeat_coordinator = self._get_heartbeat_coordinator()
        if heartbeat_coordinator:
            try:
                heartbeat_coordinator.start_heartbeat(
                    agent_id=self._agent_id,
                    metadata={
                        "workflow": self.name,
                        "run_id": self._run_id,
                        "provider": getattr(self, "_provider_str", "unknown"),
                        "stages": len(self.stages),
                    },
                )
                logger.debug(
                    "heartbeat_started",
                    workflow=self.name,
                    agent_id=self._agent_id,
                    message="Agent heartbeat tracking started",
                )
            except Exception as e:
                logger.warning(f"Failed to start heartbeat tracking: {e}")
                self._enable_heartbeat_tracking = False

        started_at = datetime.now()
        self._stages_run = []
        current_data = kwargs
        error = None

        # Initialize progress tracker
        # Always show progress by default (IDE-friendly console output)
        # Rich live display only when explicitly enabled AND in TTY
        self._progress_tracker = ProgressTracker(
            workflow_name=self.name,
            workflow_id=self._run_id,
            stage_names=self.stages,
        )

        # Add user's callback if provided
        if self._progress_callback:
            self._progress_tracker.add_callback(self._progress_callback)

        # Rich progress: only when explicitly enabled AND in a TTY
        if self._enable_rich_progress and RICH_AVAILABLE and sys.stdout.isatty():
            try:
                self._rich_reporter = RichProgressReporter(self.name, self.stages)
                self._progress_tracker.add_callback(self._rich_reporter.report)
                self._rich_reporter.start()
            except Exception as e:
                # Fall back to console reporter
                logger.debug(f"Rich progress unavailable: {e}")
                self._rich_reporter = None
                console_reporter = ConsoleProgressReporter(verbose=False)
                self._progress_tracker.add_callback(console_reporter.report)
        else:
            # Default: use console reporter (works in IDEs, terminals, everywhere)
            console_reporter = ConsoleProgressReporter(verbose=False)
            self._progress_tracker.add_callback(console_reporter.report)

        self._progress_tracker.start_workflow()

        try:
            # Tier fallback mode: try CHEAP -> CAPABLE -> PREMIUM with validation
            if self._enable_tier_fallback:
                current_data = await self._execute_tier_fallback(
                    current_data,
                    heartbeat_coordinator,
                    ModelTier,
                    WorkflowStage,
                )

            # Standard mode: use routing strategy or tier_map (backward compatible)
            else:
                current_data = await self._execute_standard(
                    current_data,
                    WorkflowStage,
                )

        except (ValueError, TypeError, KeyError) as e:
            # Data validation or configuration errors
            error = f"Workflow execution error (data/config): {e}"
            logger.error(error)
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)
        except (TimeoutError, RuntimeError, ConnectionError) as e:
            # Timeout, API errors, or connection failures
            error = f"Workflow execution error (timeout/API/connection): {e}"
            logger.error(error)
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)
        except (OSError, PermissionError) as e:
            # File system or permission errors
            error = f"Workflow execution error (file system): {e}"
            logger.error(error)
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)
        except Exception as e:
            # INTENTIONAL: Workflow orchestration - catch all errors to report failure gracefully
            logger.exception(f"Unexpected error in workflow execution: {type(e).__name__}")
            error = f"Workflow execution failed: {type(e).__name__}"
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)

        return self._finalize_execution(
            kwargs=kwargs,
            started_at=started_at,
            error=error,
            heartbeat_coordinator=heartbeat_coordinator,
            routing_record=routing_record,
            WorkflowResult=WorkflowResult,
            _save_workflow_run=_save_workflow_run,
        )

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

    def _finalize_execution(
        self,
        kwargs: dict[str, Any],
        started_at: datetime,
        error: str | None,
        heartbeat_coordinator: Any,
        routing_record: Any,
        WorkflowResult: Any,
        _save_workflow_run: Any,
    ) -> WorkflowResult:
        """Finalize workflow execution: build result, save history, stop heartbeat.

        Args:
            kwargs: Original workflow kwargs
            started_at: Execution start time
            error: Error message or None
            heartbeat_coordinator: Heartbeat coordinator or None
            routing_record: TaskRoutingRecord instance
            WorkflowResult: WorkflowResult class
            _save_workflow_run: History save function

        Returns:
            WorkflowResult instance

        """
        completed_at = datetime.now()
        total_duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Get final output from last non-skipped stage
        final_output = None
        for stage in reversed(self._stages_run):
            if not stage.skipped and stage.result is not None:
                final_output = stage.result
                break

        # Classify error type and transient status
        error_type = None
        transient = False
        if error:
            error_lower = error.lower()
            if "timeout" in error_lower or "timed out" in error_lower:
                error_type = "timeout"
                transient = True
            elif "config" in error_lower or "configuration" in error_lower:
                error_type = "config"
                transient = False
            elif "api" in error_lower or "rate limit" in error_lower or "quota" in error_lower:
                error_type = "provider"
                transient = True
            elif "validation" in error_lower or "invalid" in error_lower:
                error_type = "validation"
                transient = False
            else:
                error_type = "runtime"
                transient = False

        provider_str = getattr(self, "_provider_str", "unknown")
        result = WorkflowResult(
            success=error is None,
            stages=self._stages_run,
            final_output=final_output,
            cost_report=self._generate_cost_report(),
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=total_duration_ms,
            provider=provider_str,
            error=error,
            error_type=error_type,
            transient=transient,
        )

        # Report workflow completion to progress tracker
        if self._progress_tracker and error is None:
            self._progress_tracker.complete_workflow()

        # Stop Rich progress display if active
        if self._rich_reporter:
            try:
                self._rich_reporter.stop()
            except Exception:
                pass  # Best effort cleanup
            self._rich_reporter = None

        # Save to workflow history for dashboard
        try:
            _save_workflow_run(self.name, provider_str, result)
        except (OSError, PermissionError):
            # File system errors saving history - log but don't crash workflow
            logger.warning("Failed to save workflow history (file system error)")
        except (ValueError, TypeError, KeyError):
            # Data serialization errors - log but don't crash workflow
            logger.warning("Failed to save workflow history (serialization error)")
        except Exception:
            # INTENTIONAL: History save is optional diagnostics - never crash workflow
            logger.exception("Unexpected error saving workflow history")

        # Emit workflow telemetry to backend
        self._emit_workflow_telemetry(result)

        # Record workflow completion in state store (Phase 4)
        total_cost = sum(s.cost for s in self._stages_run if not s.skipped)
        self._state_record_workflow_complete(
            success=result.success,
            total_cost=total_cost,
            execution_time_ms=float(total_duration_ms),
            error=error,
        )

        # Stop heartbeat tracking (Pattern 1)
        if heartbeat_coordinator:
            try:
                final_status = "completed" if result.success else "failed"
                heartbeat_coordinator.stop_heartbeat(final_status=final_status)
                logger.debug(
                    "heartbeat_stopped",
                    workflow=self.name,
                    agent_id=self._agent_id,
                    status=final_status,
                    message="Agent heartbeat tracking stopped",
                )
            except Exception as e:
                logger.warning(f"Failed to stop heartbeat tracking: {e}")

        # Auto-save tier progression
        if self._enable_tier_tracking and self._tier_tracker:
            try:
                files_affected = kwargs.get("files_affected") or kwargs.get("path")
                if files_affected and not isinstance(files_affected, list):
                    files_affected = [str(files_affected)]

                # Determine bug type from workflow name
                bug_type_map = {
                    "code-review": "code_quality",
                    "bug-predict": "bug_prediction",
                    "security-audit": "security_issue",
                    "test-gen": "test_coverage",
                    "refactor-plan": "refactoring",
                    "health-check": "health_check",
                }
                bug_type = bug_type_map.get(self.name, "workflow_run")

                # Pass tier_progression data if tier fallback was enabled
                tier_progression_data = (
                    self._tier_progression if self._enable_tier_fallback else None
                )

                self._tier_tracker.save_progression(
                    workflow_result=result,
                    files_affected=files_affected,
                    bug_type=bug_type,
                    tier_progression=tier_progression_data,
                )
            except Exception as e:
                logger.debug(f"Failed to save tier progression: {e}")

        # Update routing record with completion status (Tier 1 automation monitoring)
        routing_record.status = "completed" if result.success else "failed"
        routing_record.completed_at = datetime.utcnow().isoformat() + "Z"
        routing_record.success = result.success
        routing_record.actual_cost = sum(s.cost for s in result.stages)

        if not result.success and result.error:
            routing_record.error_type = result.error_type or "unknown"
            routing_record.error_message = result.error

        # Log routing completion
        try:
            if self._telemetry_backend is not None:
                self._telemetry_backend.log_task_routing(routing_record)
        except Exception as e:
            logger.debug(f"Failed to log task routing completion: {e}")

        return result
