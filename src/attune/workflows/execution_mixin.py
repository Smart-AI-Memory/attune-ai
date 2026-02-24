"""Execution Mixin for BaseWorkflow.

Facade that composes the three execution sub-mixins:
- TierFallbackExecutionMixin: CHEAP -> CAPABLE -> PREMIUM fallback
- StandardExecutionMixin: Routing strategy / tier_map execution
- ExecutionFinalizeMixin: Result building, history, heartbeat cleanup

Provides the main execute() method and delegates to the sub-mixins.

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

from .execution_finalize import ExecutionFinalizeMixin
from .execution_standard import StandardExecutionMixin
from .execution_tier_fallback import TierFallbackExecutionMixin

if TYPE_CHECKING:
    from .data_classes import WorkflowResult

logger = logging.getLogger(__name__)


class ExecutionMixin(
    TierFallbackExecutionMixin,
    StandardExecutionMixin,
    ExecutionFinalizeMixin,
):
    """Mixin providing the main workflow execution method.

    Composes three sub-mixins for tier-fallback execution,
    standard execution, and result finalization.
    """

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
            error = f"Workflow execution failed: {type(e).__name__}: {e}"
            if self._progress_tracker:
                self._progress_tracker.fail_workflow(error)

        result = self._finalize_execution(
            kwargs=kwargs,
            started_at=started_at,
            error=error,
            heartbeat_coordinator=heartbeat_coordinator,
            routing_record=routing_record,
            WorkflowResult=WorkflowResult,
            _save_workflow_run=_save_workflow_run,
        )

        # Run post-simplification scan after successful execution (PostSimplificationMixin)
        # Pipeline: execute stages → simplify → verify → self-correct → re-verify
        if error is None:
            result = await self._run_post_simplification(result, kwargs)

        # Run verification loop after successful execution (VerificationMixin)
        if error is None:
            result, _verification_result = await self._run_verification_loop(result, kwargs)

        return result
