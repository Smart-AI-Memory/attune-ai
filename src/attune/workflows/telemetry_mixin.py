"""Telemetry Mixin for Workflow LLM Call Tracking

Extracted from BaseWorkflow to improve maintainability and reusability.
Provides telemetry tracking for LLM calls and workflow executions.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from attune.workflows.agent_sdk_adapter import AgentRunResult

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


def is_workflow_result_shaped(result: Any) -> bool:
    """True when ``result`` carries the ``WorkflowResult`` surface.

    The full run-record builder reads ``stages``, ``cost_report`` and
    the ``started_at``/``completed_at`` datetimes. Orchestrator and
    agent-team workflows return report objects (``HealthCheckReport``,
    ``OrchestratorResult``, ``SecureReleaseResult``) that lack these —
    they get :func:`build_fallback_run_record` instead (run-record-corpus
    RC-2 follow-up).
    """
    return all(
        hasattr(result, attr) for attr in ("stages", "cost_report", "started_at", "completed_at")
    )


def build_fallback_run_record(
    *,
    run_id: str,
    workflow_name: str,
    provider: str,
    result: Any,
    started_at: datetime | None,
    completed_at: datetime | None,
) -> Any:
    """Build a degraded ``WorkflowRunRecord`` for a report-shaped result.

    Stage/cost detail is unavailable on these results, so the record
    carries identity, provenance, timing and outcome only — enough for
    the run-record corpus miner (sequence, name, time, success), with
    token/cost totals honestly zero rather than guessed.

    ``started_at``/``completed_at`` come from the caller's wall clock
    (the ``BaseWorkflow`` execute-wrapper); both default to now.
    """
    from attune.models import WorkflowRunRecord
    from attune.models.telemetry.run_context import (
        resolve_project_identity,
        resolve_run_trigger,
    )

    now = datetime.now(timezone.utc)
    start = started_at or now
    end = completed_at or now
    # ``is not False``: report objects without a ``success`` field count
    # as success — the run returned a result without raising.
    success = getattr(result, "success", True) is not False
    error_raw = getattr(result, "error", None)
    error = error_raw if isinstance(error_raw, str) and error_raw else None
    return WorkflowRunRecord(
        run_id=run_id,
        workflow_name=workflow_name,
        trigger=resolve_run_trigger(),
        project=resolve_project_identity(),
        started_at=start.isoformat(),
        completed_at=end.isoformat(),
        total_duration_ms=max(0, int((end - start).total_seconds() * 1000)),
        success=success,
        error=error,
        providers_used=[provider],
    )


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
                (skipped the LLM call entirely)
            cache_type: Cache type if cache_hit is True
            duration_ms: Duration in milliseconds
            prompt_cache_creation_tokens: Tokens written to Anthropic's
                prompt cache during this call (zero unless the provider
                reported it; non-Anthropic providers always pass zero).
            prompt_cache_read_tokens: Tokens read from Anthropic's prompt
                cache during this call (zero unless reported).
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
                prompt_cache_hit=prompt_cache_read_tokens > 0,
                prompt_cache_creation_tokens=prompt_cache_creation_tokens,
                prompt_cache_read_tokens=prompt_cache_read_tokens,
            )
        except (AttributeError, TypeError, ValueError) as e:
            # INTENTIONAL: Telemetry tracking failures should never crash workflows
            logger.debug(f"Failed to track telemetry (config/data error): {e}")
        except (OSError, PermissionError) as e:
            # File system errors - log but never crash workflow
            logger.debug(f"Failed to track telemetry (file system error): {e}")

    def _track_sdk_run_telemetry(
        self,
        stage: str,
        agent_run_result: AgentRunResult,
    ) -> None:
        """Record telemetry for an SDK-native workflow run.

        SDK workflows call ``claude_agent_sdk.query()`` directly, bypassing
        the legacy ``llm_mixin`` path that calls ``_track_telemetry()``. As
        a result, ``usage.jsonl`` was never written for SDK runs and the
        dashboard's home / telemetry KPIs went stale after the SDK migration.

        Call this once per run, after the message-collection loop completes
        and the ``AgentRunResult`` has been populated from the final
        ``ResultMessage``. Failed runs (``is_error=True``) and zero-cost
        runs (typically startup failures) are skipped.

        Args:
            stage: Stage name to record (e.g. ``"agent"``, ``"predict"``).
            agent_run_result: Aggregated result from ``collect_agent_output``.
        """
        if not self._enable_telemetry or self._telemetry_tracker is None:
            return
        if agent_run_result.is_error:
            return
        cost = agent_run_result.total_cost_usd or 0.0
        if cost <= 0:
            return
        usage = agent_run_result.usage or {}
        self._track_telemetry(
            stage=stage,
            tier="SDK",
            model="agent-sdk",
            cost=cost,
            tokens={
                "input": int(usage.get("input_tokens", 0) or 0),
                "output": int(usage.get("output_tokens", 0) or 0),
            },
            cache_hit=False,
            cache_type=None,
            duration_ms=agent_run_result.duration_ms or 0,
            prompt_cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0) or 0),
            prompt_cache_read_tokens=int(usage.get("cache_read_input_tokens", 0) or 0),
        )

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
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Telemetry is optional diagnostics - never crash workflow
            logger.debug("Unexpected error logging call telemetry")

    def _emit_workflow_telemetry(
        self,
        result: Any,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Emit a WorkflowRunRecord to the telemetry backend.

        Args:
            result: The WorkflowResult (or report object) to record
            started_at: Wall-clock start from the execute-wrapper; used
                only for report-shaped results without own timestamps.
            completed_at: Wall-clock end, same caveat as ``started_at``.

        """
        from attune.models import WorkflowRunRecord, WorkflowStageRecord
        from attune.models.telemetry.run_context import (
            resolve_project_identity,
            resolve_run_trigger,
        )

        # Idempotence guard (run-record-corpus RC-2): the BaseWorkflow
        # execute-wrapper AND ExecutionMixin's epilogue both call this;
        # if a future override chains through super().execute(), only
        # the first emission for a given result object records.
        # ``is True`` (not truthiness): a MagicMock result fabricates a
        # truthy attr on access; only OUR literal marker counts.
        if result is None or getattr(result, "_run_record_emitted", False) is True:
            return
        try:
            result._run_record_emitted = True
        except (AttributeError, TypeError):
            pass  # non-standard result object — emit unguarded

        # Report-shaped results (orchestrator/agent-team workflows) lack
        # the WorkflowResult surface — emit the degraded record instead
        # of dying on ``result.stages`` (run-record-corpus RC-2).
        if not is_workflow_result_shaped(result):
            self._log_run_record(
                build_fallback_run_record(
                    run_id=self._run_id or str(uuid.uuid4()),
                    workflow_name=self.name,
                    provider=getattr(self, "_provider_str", "unknown"),
                    result=result,
                    started_at=started_at,
                    completed_at=completed_at,
                )
            )
            return

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
            providers_used=[getattr(self, "_provider_str", "unknown")],
            tiers_used=list(result.cost_report.by_tier.keys()),
        )
        self._log_run_record(record)

    def _log_run_record(self, record: Any) -> None:
        """Write a run record to the backend — never raises."""
        try:
            if self._telemetry_backend is not None:
                self._telemetry_backend.log_workflow(record)
        except (AttributeError, ValueError, TypeError):
            # Telemetry backend errors - log but don't crash workflow
            logger.debug("Failed to log workflow telemetry (backend error)")
        except OSError:
            # File system errors - log but don't crash workflow
            logger.debug("Failed to log workflow telemetry (file system error)")
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Telemetry is optional diagnostics - never crash workflow
            logger.debug("Unexpected error logging workflow telemetry")

    def _generate_run_id(self) -> str:
        """Generate a new run ID for telemetry correlation.

        Returns:
            A new UUID string for the run

        """
        self._run_id = str(uuid.uuid4())
        return self._run_id
