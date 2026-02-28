"""Execution Finalization Mixin.

Extracted from ExecutionMixin to reduce file size.
Provides the _finalize_execution() method that builds the WorkflowResult,
saves history, stops heartbeat, and updates routing telemetry.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_classes import WorkflowResult

logger = logging.getLogger(__name__)


class ExecutionFinalizeMixin:
    """Mixin providing workflow execution finalization logic."""

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
        self._save_tier_progression(kwargs, result)

        # Update routing record with completion status (Tier 1 automation monitoring)
        _update_routing_record(self, routing_record, result)

        return result

    def _save_tier_progression(self, kwargs: dict[str, Any], result: Any) -> None:
        """Save tier progression data if tier tracking is enabled.

        Args:
            kwargs: Original workflow kwargs
            result: WorkflowResult instance

        """
        if not (self._enable_tier_tracking and self._tier_tracker):
            return

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
            tier_progression_data = self._tier_progression if self._enable_tier_fallback else None

            self._tier_tracker.save_progression(
                workflow_result=result,
                files_affected=files_affected,
                bug_type=bug_type,
                tier_progression=tier_progression_data,
            )
        except Exception as e:
            logger.debug(f"Failed to save tier progression: {e}")


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
    routing_record.completed_at = datetime.utcnow().isoformat() + "Z"
    routing_record.success = result.success
    routing_record.actual_cost = sum(s.cost for s in result.stages)

    if not result.success and result.error:
        routing_record.error_type = result.error_type or "unknown"
        routing_record.error_message = result.error

    # Log routing completion
    try:
        if workflow._telemetry_backend is not None:
            workflow._telemetry_backend.log_task_routing(routing_record)
    except Exception as e:
        logger.debug(f"Failed to log task routing completion: {e}")
