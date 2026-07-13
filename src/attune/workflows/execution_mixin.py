"""Execution Mixin for BaseWorkflow.

Provides the main execute() method and all execution helpers:
- Standard execution: routing strategy / tier_map execution
- Tier fallback: CHEAP -> CAPABLE -> PREMIUM with validation
- Finalization: result building, history, heartbeat cleanup

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

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from attune.model_tiers import ModelRefusalError
from attune.resilience.retry import RetryConfig, retry_with_backoff

if TYPE_CHECKING:
    from .data_classes import WorkflowResult, WorkflowStage

logger = logging.getLogger(__name__)


class ExecutionMixin:
    """Mixin providing the main workflow execution method.

    Includes standard execution, tier-fallback execution,
    and result finalization.
    """

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    description: str
    stages: list[str]
    # _stage_index is a cached_property on TierRoutingMixin (BaseWorkflow
    # inherits both), resolved via MRO. Documented here as a contract.
    _stage_index: dict[str, int]
    _enable_tier_tracking: bool
    _enable_heartbeat_tracking: bool
    _agent_id: str | None

    def _create_routing_record(self, kwargs: dict[str, Any]) -> Any:
        """Create a TaskRoutingRecord and log it to telemetry.

        Args:
            kwargs: Workflow input kwargs for complexity assessment

        Returns:
            TaskRoutingRecord instance

        """
        from attune.models import TaskRoutingRecord

        routing_id = f"routing-{self._run_id}"
        routing_record = TaskRoutingRecord(
            routing_id=routing_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            task_description=f"{self.name}: {self.description}",
            task_type=self.name,
            task_complexity=self._assess_complexity(kwargs),
            assigned_agent=self.name,
            assigned_tier=getattr(self, "_provider_str", "unknown"),
            routing_strategy="rule_based",
            confidence_score=1.0,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            if self._telemetry_backend is not None:
                self._telemetry_backend.log_task_routing(routing_record)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Telemetry logging is optional diagnostics
            logger.debug("Failed to log task routing: %s", e)

        return routing_record

    def _setup_tier_tracking(self, kwargs: dict[str, Any]) -> None:
        """Initialize tier tracking and show recommendation if available.

        Args:
            kwargs: Workflow input kwargs

        """
        try:
            from .tier_tracking import WorkflowTierTracker

            self._tier_tracker = WorkflowTierTracker(self.name, self.description)
            files_affected = kwargs.get("files_affected") or kwargs.get("path")
            if files_affected and not isinstance(files_affected, list):
                files_affected = [str(files_affected)]
            self._tier_tracker.show_recommendation(files_affected)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Tier tracking is optional diagnostics
            logger.debug("Tier tracking disabled: %s", e)
            self._enable_tier_tracking = False

    def _setup_progress_tracking(self) -> None:
        """Initialize progress tracker with rich or console reporter."""
        from .progress import (
            RICH_AVAILABLE,
            ConsoleProgressReporter,
            ProgressTracker,
            RichProgressReporter,
        )

        self._progress_tracker = ProgressTracker(
            workflow_name=self.name,
            workflow_id=self._run_id,
            stage_names=self.stages,
        )

        if self._progress_callback:
            self._progress_tracker.add_callback(self._progress_callback)

        if self._enable_rich_progress and RICH_AVAILABLE and sys.stdout.isatty():
            try:
                self._rich_reporter = RichProgressReporter(self.name, self.stages)
                self._progress_tracker.add_callback(self._rich_reporter.report)
                self._rich_reporter.start()
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Rich progress display is optional
                logger.debug("Rich progress unavailable: %s", e)
                self._rich_reporter = None
                console_reporter = ConsoleProgressReporter(verbose=False)
                self._progress_tracker.add_callback(console_reporter.report)
        else:
            console_reporter = ConsoleProgressReporter(verbose=False)
            self._progress_tracker.add_callback(console_reporter.report)

        self._progress_tracker.start_workflow()

    def _start_heartbeat(self, heartbeat_coordinator: Any) -> None:
        """Start heartbeat tracking if coordinator is available.

        Args:
            heartbeat_coordinator: Heartbeat coordinator instance or None

        """
        if not heartbeat_coordinator:
            return
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
                "heartbeat_started: workflow=%s agent_id=%s",
                self.name,
                self._agent_id,
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Heartbeat tracking is optional
            logger.warning("Failed to start heartbeat tracking: %s", e)
            self._enable_heartbeat_tracking = False

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the full workflow.

        Args:
            **kwargs: Initial input data for the workflow

        Returns:
            WorkflowResult with stages, output, and cost report

        """
        from .compat import ModelTier
        from .data_classes import WorkflowResult, WorkflowStage
        from .history_utils import _save_workflow_run

        # Set up cache (one-time setup with user prompt if needed)
        self._maybe_setup_cache()

        # Validate inputs against schema (strict by default)
        self.validate_input(kwargs)

        # Set run ID for telemetry correlation
        self._run_id = str(uuid.uuid4())

        # Record workflow start in state store (Phase 4 - state persistence)
        self._state_record_workflow_start()

        routing_record = self._create_routing_record(kwargs)

        if self._enable_tier_tracking:
            self._setup_tier_tracking(kwargs)

        # Initialize agent ID for heartbeat/coordination (Pattern 1 & 2)
        if self._agent_id is None:
            self._agent_id = f"{self.name}-{self._run_id[:8]}"

        heartbeat_coordinator = self._get_heartbeat_coordinator()
        self._start_heartbeat(heartbeat_coordinator)

        started_at = datetime.now(timezone.utc)
        self._stages_run: list[WorkflowStage] = []
        current_data = kwargs
        error = None

        self._setup_progress_tracking()

        try:
            if self._enable_tier_fallback:
                current_data = await self._execute_tier_fallback(
                    current_data,
                    heartbeat_coordinator,
                    ModelTier,
                    WorkflowStage,
                )
            else:
                current_data = await self._execute_standard(
                    current_data,
                    WorkflowStage,
                )

        except ModelRefusalError as e:
            # The whole fable -> opus server-side fallback chain refused:
            # record the fable_refusal telemetry event and error the run —
            # never a silent skip (docs/specs/fable-premium-tier design §5).
            from attune.models.telemetry import log_fable_refusal

            log_fable_refusal(e, workflow=self.name)
            error = f"Workflow execution error (model refusal): {e}"
            logger.error(error)
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)
        except (ValueError, TypeError, KeyError) as e:
            error = f"Workflow execution error (data/config): {e}"
            logger.error(error)
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)
        except (TimeoutError, RuntimeError, ConnectionError) as e:
            error = f"Workflow execution error (timeout/API/connection): {e}"
            logger.error(error)
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)
        except (OSError, PermissionError) as e:
            error = f"Workflow execution error (file system): {e}"
            logger.error(error)
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Workflow orchestration - catch all to report failure
            logger.exception("Unexpected error in workflow execution: %s", type(e).__name__)
            error = f"Workflow execution failed: {type(e).__name__}: {e}"
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)

        result: WorkflowResult = self._finalize_execution(
            kwargs=kwargs,
            started_at=started_at,
            error=error,
            heartbeat_coordinator=heartbeat_coordinator,
            routing_record=routing_record,
            WorkflowResult=WorkflowResult,
            _save_workflow_run=_save_workflow_run,
        )

        # Post-simplification scan after successful execution
        if error is None:
            result = await self._run_post_simplification(result, kwargs)

        # Verification loop after successful execution
        if error is None:
            result, _verification_result = await self._run_verification_loop(result, kwargs)

        # Generate project-aware guidance suggestions (v3.5)
        try:
            from .suggestions import generate_suggestions

            result.suggestions = generate_suggestions(self.name, result)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Suggestions are optional -- never crash workflow
            logger.debug("Suggestion generation skipped: %s", e)

        return result

    # -----------------------------------------------------------------
    # Standard execution
    # -----------------------------------------------------------------

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
        total_budget = 100.0
        budget_spent = 0.0

        for stage_name in self.stages:
            budget_remaining = total_budget - budget_spent
            tier = self._get_tier_with_routing(
                stage_name,
                current_data if isinstance(current_data, dict) else {},
                budget_remaining,
            )
            stage_start = datetime.now(timezone.utc)

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
                if self._progress_tracker:
                    self._progress_tracker.skip_stage(stage_name, skip_reason or "")
                continue

            model_id = self.get_model_for_tier(tier)
            if self._progress_tracker:
                self._progress_tracker.start_stage(stage_name, tier.value, model_id)

            self._state_record_stage_start(stage_name)

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

            stage_end = datetime.now(timezone.utc)
            duration_ms = int((stage_end - stage_start).total_seconds() * 1000)
            cost = self._calculate_cost(tier, input_tokens, output_tokens)

            self._state_record_stage_complete(stage_name, cost, duration_ms, tier.value)
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

            if self._progress_tracker:
                self._progress_tracker.complete_stage(
                    stage_name,
                    cost=cost,
                    tokens_in=input_tokens,
                    tokens_out=output_tokens,
                )

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

            stage_output = output if isinstance(output, dict) else {"result": output}
            self.validate_contract(stage_name, stage_output)
            current_data = stage_output

        return current_data

    # -----------------------------------------------------------------
    # Tier fallback execution
    # -----------------------------------------------------------------

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
            should_skip, skip_reason = self.should_skip_stage(stage_name, current_data)
            if should_skip:
                self._handle_stage_skip(stage_name, skip_reason, WorkflowStage)
                continue

            self._state_record_stage_start(stage_name)
            stage_succeeded = False

            for tier_index, tier in enumerate(tier_chain):
                stage_start = datetime.now(timezone.utc)
                model_id = self.get_model_for_tier(tier)

                self._report_stage_progress(stage_name, tier, tier_index, tier_chain, model_id)
                self._update_heartbeat(heartbeat_coordinator, stage_name, tier, offset=0)

                try:
                    output, input_tokens, output_tokens = await self.run_stage(
                        stage_name,
                        tier,
                        current_data,
                    )

                    duration_ms = int(
                        (datetime.now(timezone.utc) - stage_start).total_seconds() * 1000
                    )
                    cost = self._calculate_cost(tier, input_tokens, output_tokens)
                    stage_output = output if isinstance(output, dict) else {"result": output}

                    is_valid, failure_reason = self.validate_output(stage_output)

                    if is_valid:
                        self.validate_contract(stage_name, stage_output)
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

                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Catch-all for tier escalation; log and try next tier
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
        """Send a heartbeat update with current stage progress."""
        if not heartbeat_coordinator:
            return
        try:
            # _stage_index is a cached_property on BaseWorkflow — O(1)
            # vs the prior O(n) self.stages.index(stage_name) call on
            # every heartbeat. Missing key raises KeyError, caught by
            # the broad except below; behavior matches the previous
            # ValueError-from-.index() path (skip heartbeat, debug log).
            stage_index = self._stage_index[stage_name] + offset
            progress = stage_index / len(self.stages)
            task_label = "Completed" if offset else "Running"
            heartbeat_coordinator.beat(
                status="running",
                progress=progress,
                current_task=f"{task_label} stage: {stage_name}"
                + (f" ({tier.value})" if not offset else ""),
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Heartbeat update is best-effort
            logger.debug("Heartbeat update failed: %s", e)

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
        suffix = "quality validation " if level == "info" else ""
        log_fn(
            "Stage %s failed %swith %s: %s",
            stage_name,
            suffix,
            tier.value,
            reason,
        )

        if tier_index < len(tier_chain) - 1:
            logger.info("Retrying with higher tier...")
        else:
            logger.error("All tiers exhausted for %s", stage_name)

    # -----------------------------------------------------------------
    # Finalization
    # -----------------------------------------------------------------

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
        completed_at = datetime.now(timezone.utc)
        total_duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        final_output = None
        for stage in reversed(self._stages_run):
            if not stage.skipped and stage.result is not None:
                final_output = stage.result
                break

        error_type = None
        transient = False
        if error:
            error_type, transient = _classify_error(error)

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

        if self._progress_tracker and error is None:
            self._progress_tracker.complete_workflow()

        if self._rich_reporter:
            try:
                self._rich_reporter.stop()
            except Exception:  # noqa: BLE001
                pass  # INTENTIONAL: Best effort cleanup
            self._rich_reporter = None

        try:
            _save_workflow_run(self.name, provider_str, result)
        except (OSError, PermissionError):
            logger.warning("Failed to save workflow history (file system error)")
        except (ValueError, TypeError, KeyError):
            logger.warning("Failed to save workflow history (serialization error)")
        except Exception:  # noqa: BLE001
            # INTENTIONAL: History save is optional diagnostics
            logger.exception("Unexpected error saving workflow history")

        self._emit_workflow_telemetry(result)

        total_cost = sum(s.cost for s in self._stages_run if not s.skipped)
        self._state_record_workflow_complete(
            success=result.success,
            total_cost=total_cost,
            execution_time_ms=float(total_duration_ms),
            error=error,
        )

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
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Heartbeat cleanup is best-effort
                logger.warning("Failed to stop heartbeat tracking: %s", e)

        self._save_tier_progression(kwargs, result)
        _update_routing_record(self, routing_record, result)

        return result

    def _save_tier_progression(self, kwargs: dict[str, Any], result: Any) -> None:
        """Save tier progression data if tier tracking is enabled."""
        if not (self._enable_tier_tracking and self._tier_tracker):
            return

        try:
            files_affected = kwargs.get("files_affected") or kwargs.get("path")
            if files_affected and not isinstance(files_affected, list):
                files_affected = [str(files_affected)]

            bug_type_map = {
                "code-review": "code_quality",
                "bug-predict": "bug_prediction",
                "security-audit": "security_issue",
                "test-gen": "test_coverage",
                "refactor-plan": "refactoring",
                "health-check": "health_check",
            }
            bug_type = bug_type_map.get(self.name, "workflow_run")

            tier_progression_data = self._tier_progression if self._enable_tier_fallback else None

            self._tier_tracker.save_progression(
                workflow_result=result,
                files_affected=files_affected,
                bug_type=bug_type,
                tier_progression=tier_progression_data,
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Tier progression save is optional diagnostics
            logger.debug("Failed to save tier progression: %s", e)


# =====================================================================
# Module-level helpers (used by ExecutionMixin and tests)
# =====================================================================


def _classify_error(error: str) -> tuple[str, bool]:
    """Classify an error message into type and transient status.

    Args:
        error: Error message string

    Returns:
        Tuple of (error_type, is_transient)

    """
    error_lower = error.lower()
    if "timeout" in error_lower or "timed out" in error_lower:
        return "timeout", True
    if "config" in error_lower or "configuration" in error_lower:
        return "config", False
    if "api" in error_lower or "rate limit" in error_lower or "quota" in error_lower:
        return "provider", True
    if "validation" in error_lower or "invalid" in error_lower:
        return "validation", False
    return "runtime", False


def _update_routing_record(workflow: Any, routing_record: Any, result: Any) -> None:
    """Update routing record with completion status.

    Args:
        workflow: The workflow instance (for telemetry backend access)
        routing_record: TaskRoutingRecord to update
        result: WorkflowResult instance

    """
    routing_record.status = "completed" if result.success else "failed"
    routing_record.completed_at = datetime.now(timezone.utc).isoformat()
    routing_record.success = result.success
    routing_record.actual_cost = sum(s.cost for s in result.stages)

    if not result.success and result.error:
        routing_record.error_type = result.error_type or "unknown"
        routing_record.error_message = result.error

    try:
        if workflow._telemetry_backend is not None:
            workflow._telemetry_backend.log_task_routing(routing_record)
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Telemetry logging is optional diagnostics
        logger.debug("Failed to log task routing completion: %s", e)
