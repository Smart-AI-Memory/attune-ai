"""Telemetry Mixin for Workflow LLM Call Tracking

Extracted from BaseWorkflow to improve maintainability and reusability.
Provides telemetry tracking for LLM calls and workflow executions.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.models import (
        TelemetryBackend,
    )

logger = logging.getLogger(__name__)

# Try to import UsageTracker
try:
    from attune.telemetry import UsageTracker

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    UsageTracker = None  # type: ignore


class TelemetryMixin:
    """Mixin that provides telemetry tracking for workflow LLM calls.

    This mixin extracts telemetry logic from BaseWorkflow to improve
    maintainability and enable reuse in other contexts.

    Attributes:
        _telemetry_backend: Backend for storing telemetry records
        _telemetry_tracker: UsageTracker singleton for tracking
        _enable_telemetry: Whether telemetry is enabled
        _run_id: Current workflow run ID for correlation

    Usage:
        class MyWorkflow(TelemetryMixin, BaseWorkflow):
            pass

        # TelemetryMixin methods are now available
        workflow._track_telemetry(...)
        workflow._emit_call_telemetry(...)
        workflow._emit_workflow_telemetry(...)

    """

    # Instance variables (set by __init__ or subclass)
    _telemetry_backend: TelemetryBackend | None = None
    _telemetry_tracker: UsageTracker | None = None
    _enable_telemetry: bool = True
    _run_id: str | None = None

    # These must be provided by the class using this mixin
    name: str = "unknown"
    _provider_str: str = "unknown"

    def _init_telemetry(self, telemetry_backend: TelemetryBackend | None = None) -> None:
        """Initialize telemetry tracking.

        Call this from __init__ to set up telemetry.

        Args:
            telemetry_backend: Optional backend for storing telemetry records.
                             Defaults to TelemetryStore (JSONL file backend).

        """
        from attune.models import get_telemetry_store

        self._telemetry_backend = telemetry_backend or get_telemetry_store()
        self._telemetry_tracker = None
        self._enable_telemetry = True

        if TELEMETRY_AVAILABLE and UsageTracker is not None:
            try:
                self._telemetry_tracker = UsageTracker.get_instance()
            except (OSError, PermissionError) as e:
                # File system errors - log but disable telemetry
                logger.debug(f"Failed to initialize telemetry tracker (file system error): {e}")
                self._enable_telemetry = False
            except (AttributeError, TypeError, ValueError) as e:
                # Configuration or initialization errors
                logger.debug(f"Failed to initialize telemetry tracker (config error): {e}")
                self._enable_telemetry = False

    def _track_telemetry(
        self,
        stage: str,
        tier: Any,  # ModelTier
        model: str,
        cost: float,
        tokens: dict[str, int],
        cache_hit: bool,
        cache_type: str | None,
        duration_ms: int,
    ) -> None:
        """Track telemetry for an LLM call.

        Args:
            stage: Stage name
            tier: Model tier used (ModelTier enum)
            model: Model ID used
            cost: Cost in USD
            tokens: Dictionary with "input" and "output" token counts
            cache_hit: Whether this was a cache hit
            cache_type: Cache type if cache hit
            duration_ms: Duration in milliseconds

        """
        if not self._enable_telemetry or self._telemetry_tracker is None:
            return

        try:
            provider_str = getattr(self, "_provider_str", "unknown")
            self._telemetry_tracker.track_llm_call(
                workflow=self.name,
                stage=stage,
                tier=tier.value.upper() if hasattr(tier, "value") else str(tier).upper(),
                model=model,
                provider=provider_str,
                cost=cost,
                tokens=tokens,
                cache_hit=cache_hit,
                cache_type=cache_type,
                duration_ms=duration_ms,
            )
        except (AttributeError, TypeError, ValueError) as e:
            # INTENTIONAL: Telemetry tracking failures should never crash workflows
            logger.debug(f"Failed to track telemetry (config/data error): {e}")
        except (OSError, PermissionError) as e:
            # File system errors - log but never crash workflow
            logger.debug(f"Failed to track telemetry (file system error): {e}")

    def _emit_call_telemetry(
        self,
        step_name: str,
        task_type: str,
        tier: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        success: bool = True,
        error_message: str | None = None,
        fallback_used: bool = False,
    ) -> None:
        """Emit an LLMCallRecord to the telemetry backend.

        Args:
            step_name: Name of the workflow step
            task_type: Task type used for routing
            tier: Model tier used
            model_id: Model ID used
            input_tokens: Input token count
            output_tokens: Output token count
            cost: Estimated cost
            latency_ms: Latency in milliseconds
            success: Whether the call succeeded
            error_message: Error message if failed
            fallback_used: Whether fallback was used

        """
        from attune.models import LLMCallRecord

        record = LLMCallRecord(
            call_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            workflow_name=self.name,
            step_name=step_name,
            task_type=task_type,
            provider=getattr(self, "_provider_str", "unknown"),
            tier=tier,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            fallback_used=fallback_used,
            metadata={"run_id": self._run_id},
        )
        try:
            if self._telemetry_backend is not None:
                self._telemetry_backend.log_call(record)
        except (AttributeError, ValueError, TypeError):
            # Telemetry backend errors - log but don't crash workflow
            logger.debug("Failed to log call telemetry (backend error)")
        except OSError:
            # File system errors - log but don't crash workflow
            logger.debug("Failed to log call telemetry (file system error)")
        except Exception:
            # INTENTIONAL: Telemetry is optional diagnostics - never crash workflow
            logger.debug("Unexpected error logging call telemetry")

    def _emit_workflow_telemetry(self, result: Any) -> None:
        """Emit a WorkflowRunRecord to the telemetry backend.

        Args:
            result: The WorkflowResult to record

        """
        from attune.models import WorkflowRunRecord, WorkflowStageRecord

        # Build stage records
        stages = [
            WorkflowStageRecord(
                stage_name=s.name,
                tier=s.tier.value if hasattr(s.tier, "value") else str(s.tier),
                model_id=(
                    self.get_model_for_tier(s.tier)
                    if hasattr(self, "get_model_for_tier")
                    else "unknown"
                ),
                input_tokens=s.input_tokens,
                output_tokens=s.output_tokens,
                cost=s.cost,
                latency_ms=s.duration_ms,
                success=not s.skipped and result.error is None,
                skipped=s.skipped,
                skip_reason=s.skip_reason,
            )
            for s in result.stages
        ]

        record = WorkflowRunRecord(
            run_id=self._run_id or str(uuid.uuid4()),
            workflow_name=self.name,
            started_at=result.started_at.isoformat(),
            completed_at=result.completed_at.isoformat(),
            stages=stages,
            total_input_tokens=sum(s.input_tokens for s in result.stages if not s.skipped),
            total_output_tokens=sum(s.output_tokens for s in result.stages if not s.skipped),
            total_cost=result.cost_report.total_cost,
            baseline_cost=result.cost_report.baseline_cost,
            savings=result.cost_report.savings,
            savings_percent=result.cost_report.savings_percent,
            total_duration_ms=result.total_duration_ms,
            success=result.success,
            error=result.error,
            providers_used=[getattr(self, "_provider_str", "unknown")],
            tiers_used=list(result.cost_report.by_tier.keys()),
        )
        try:
            if self._telemetry_backend is not None:
                self._telemetry_backend.log_workflow(record)
        except (AttributeError, ValueError, TypeError):
            # Telemetry backend errors - log but don't crash workflow
            logger.debug("Failed to log workflow telemetry (backend error)")
        except OSError:
            # File system errors - log but don't crash workflow
            logger.debug("Failed to log workflow telemetry (file system error)")
        except Exception:
            # INTENTIONAL: Telemetry is optional diagnostics - never crash workflow
            logger.debug("Unexpected error logging workflow telemetry")

    def _generate_run_id(self) -> str:
        """Generate a new run ID for telemetry correlation.

        Returns:
            A new UUID string for the run

        """
        self._run_id = str(uuid.uuid4())
        return self._run_id
