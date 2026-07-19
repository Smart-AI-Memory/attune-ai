"""Telemetry service for workflows.

Standalone service extracted from TelemetryMixin. Tracks LLM call metrics
and workflow execution records.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.models import TelemetryBackend

logger = logging.getLogger(__name__)

# Try to import UsageTracker
try:
    from attune.telemetry import UsageTracker

    _TELEMETRY_AVAILABLE = True
except ImportError:
    _TELEMETRY_AVAILABLE = False
    UsageTracker = None  # type: ignore


class TelemetryService:
    """Service for tracking workflow telemetry.

    Records LLM call metrics and workflow execution records for cost analysis
    and usage monitoring.

    Args:
        workflow_name: Name of the workflow
        provider: Provider string identifier (e.g., "anthropic")
        backend: Optional telemetry backend for storing records.
            Defaults to TelemetryStore (JSONL file backend).

    Example:
        >>> telemetry = TelemetryService("code-review", "anthropic")
        >>> telemetry.track_call(
        ...     stage="analysis", tier=tier, model="claude-3-haiku",
        ...     cost=0.001, tokens={"input": 500, "output": 200},
        ...     cache_hit=False, duration_ms=1200,
        ... )

    """

    def __init__(
        self,
        workflow_name: str,
        provider: str = "unknown",
        backend: TelemetryBackend | None = None,
    ) -> None:
        """Initialize the telemetry service.

        Args:
            workflow_name: Name of the workflow to track.
            provider: Provider identifier (e.g., "anthropic").
            backend: Optional telemetry backend; defaults to JSONL store.
        """
        self._workflow_name = workflow_name
        self._provider = provider
        self._backend = backend
        self._tracker: Any = None
        self._enabled: bool = True
        self._run_id: str | None = None

        self._init_backend()
        self._init_tracker()

    def _init_backend(self) -> None:
        """Initialize telemetry backend."""
        if self._backend is None:
            from attune.models import get_telemetry_store

            self._backend = get_telemetry_store()

    def _init_tracker(self) -> None:
        """Initialize usage tracker."""
        if _TELEMETRY_AVAILABLE and UsageTracker is not None:
            try:
                self._tracker = UsageTracker.get_instance()
            except (OSError, PermissionError) as e:
                logger.debug(f"Failed to initialize telemetry tracker (file system): {e}")
                self._enabled = False
            except (AttributeError, TypeError, ValueError) as e:
                logger.debug(f"Failed to initialize telemetry tracker (config): {e}")
                self._enabled = False

    @property
    def run_id(self) -> str | None:
        """Current run ID for telemetry correlation."""
        return self._run_id

    def generate_run_id(self) -> str:
        """Generate a new run ID for telemetry correlation.

        Returns:
            A new UUID string for the run

        """
        self._run_id = str(uuid.uuid4())
        return self._run_id

    def track_call(
        self,
        stage: str,
        tier: Any,
        model: str,
        cost: float,
        tokens: dict[str, int],
        cache_hit: bool,
        cache_type: str | None = None,
        duration_ms: int = 0,
        prompt_cache_creation_tokens: int = 0,
        prompt_cache_read_tokens: int = 0,
    ) -> None:
        """Track telemetry for an LLM call.

        Args:
            stage: Stage name
            tier: Model tier used (ModelTier enum)
            model: Model ID used
            cost: Cost in USD
            tokens: Dictionary with "input" and "output" token counts
            cache_hit: Whether this was a workflow-level cache hit
            cache_type: Cache type if cache_hit is True
            duration_ms: Duration in milliseconds
            prompt_cache_creation_tokens: Tokens written to Anthropic's
                prompt cache (zero unless reported by the provider).
            prompt_cache_read_tokens: Tokens read from Anthropic's prompt
                cache (zero unless reported by the provider).
        """
        if not self._enabled or self._tracker is None:
            return

        try:
            self._tracker.track_llm_call(
                workflow=self._workflow_name,
                stage=stage,
                tier=tier.value.upper() if hasattr(tier, "value") else str(tier).upper(),
                model=model,
                provider=self._provider,
                cost=cost,
                tokens=tokens,
                cache_hit=cache_hit,
                cache_type=cache_type,
                duration_ms=duration_ms,
                prompt_cache_hit=prompt_cache_read_tokens > 0,
                prompt_cache_creation_tokens=prompt_cache_creation_tokens,
                prompt_cache_read_tokens=prompt_cache_read_tokens,
            )
        except (AttributeError, TypeError, ValueError) as e:
            logger.debug(f"Failed to track telemetry (config/data): {e}")
        except (OSError, PermissionError) as e:
            logger.debug(f"Failed to track telemetry (file system): {e}")

    def emit_call_record(
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
            workflow_name=self._workflow_name,
            step_name=step_name,
            task_type=task_type,
            provider=self._provider,
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
            if self._backend is not None:
                self._backend.log_call(record)
        except (AttributeError, ValueError, TypeError):
            logger.debug("Failed to log call telemetry (backend error)")
        except OSError:
            logger.debug("Failed to log call telemetry (file system error)")
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Telemetry is optional diagnostics - never crash workflow
            logger.debug("Unexpected error logging call telemetry")

    def emit_workflow_record(
        self,
        result: Any,
        model_for_tier_fn: Any = None,
    ) -> None:
        """Emit a WorkflowRunRecord to the telemetry backend.

        Args:
            result: The WorkflowResult to record
            model_for_tier_fn: Optional callable to resolve model name for a tier

        """
        from attune.models import WorkflowRunRecord, WorkflowStageRecord

        stages = [
            WorkflowStageRecord(
                stage_name=s.name,
                tier=s.tier.value if hasattr(s.tier, "value") else str(s.tier),
                model_id=(model_for_tier_fn(s.tier) if model_for_tier_fn else "unknown"),
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

        from attune.models.telemetry.run_context import (
            resolve_project_identity,
            resolve_run_trigger,
        )

        record = WorkflowRunRecord(
            run_id=self._run_id or str(uuid.uuid4()),
            workflow_name=self._workflow_name,
            trigger=resolve_run_trigger(),
            project=resolve_project_identity(),
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
            providers_used=[self._provider],
            tiers_used=list(result.cost_report.by_tier.keys()),
        )
        try:
            if self._backend is not None:
                self._backend.log_workflow(record)
        except (AttributeError, ValueError, TypeError):
            logger.debug("Failed to log workflow telemetry (backend error)")
        except OSError:
            logger.debug("Failed to log workflow telemetry (file system error)")
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Telemetry is optional diagnostics - never crash workflow
            logger.debug("Unexpected error logging workflow telemetry")
