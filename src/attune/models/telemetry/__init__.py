"""Telemetry tracking and analytics.

Modular telemetry system for tracking LLM calls, workflows, tests, and agent performance.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import uuid
from datetime import datetime, timezone

# Data models
# Analytics
from .analytics import TelemetryAnalytics

# Backend interface
from .backend import TelemetryBackend
from .data_models import (
    AgentAssignmentRecord,
    CoverageRecord,
    DiagnosisRecord,
    FileTestRecord,
    LLMCallRecord,
    TaskRoutingRecord,
    TestExecutionRecord,
    WorkflowRunRecord,
    WorkflowStageRecord,
)

# Storage implementation
from .storage import TelemetryStore

logger = logging.getLogger(__name__)

# Singleton store instance
_store_instance: TelemetryStore | None = None


def get_telemetry_store() -> TelemetryStore:
    """Get singleton telemetry store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = TelemetryStore()
    return _store_instance


def log_llm_call(record: LLMCallRecord):
    """Log an LLM API call."""
    get_telemetry_store().log_call(record)


def log_workflow_run(record: WorkflowRunRecord):
    """Log a workflow run."""
    get_telemetry_store().log_workflow(record)


def log_fable_refusal(
    error: Exception,
    *,
    workflow: str | None = None,
    model: str | None = None,
) -> None:
    """Record a ``fable_refusal`` telemetry event (best-effort, never raises).

    Emitted where a :class:`attune.model_tiers.ModelRefusalError` stops
    propagating (workflow error handling, agent fallbacks). Reaching a
    refusal means the whole fable -> opus server-side fallback chain
    refused, so the item errors — never a silent skip. The refusal
    ``category``/``explanation`` from ``stop_details`` ride in
    ``metadata`` and feed the batch Option B revisit
    (docs/specs/fable-premium-tier design §5).

    Args:
        error: The ``ModelRefusalError`` (attribute access is defensive,
            so any exception is accepted).
        workflow: Workflow/agent name for attribution, when known.
        model: Model ID that refused, when known.
    """
    try:
        record = LLMCallRecord(
            call_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            workflow_name=workflow,
            task_type="fable_refusal",
            tier="premium",
            model_id=model or "",
            success=False,
            error_type="fable_refusal",
            error_message=str(error),
            metadata={
                "category": getattr(error, "category", None),
                "explanation": getattr(error, "explanation", None),
            },
        )
        log_llm_call(record)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry is best-effort; never mask the refusal.
        logger.debug("fable_refusal telemetry write failed", exc_info=True)


__all__ = [
    # Data models
    "LLMCallRecord",
    "WorkflowStageRecord",
    "WorkflowRunRecord",
    "TaskRoutingRecord",
    "TestExecutionRecord",
    "CoverageRecord",
    "DiagnosisRecord",
    "AgentAssignmentRecord",
    "FileTestRecord",
    # Backend
    "TelemetryBackend",
    # Storage
    "TelemetryStore",
    # Analytics
    "TelemetryAnalytics",
    # Utilities
    "get_telemetry_store",
    "log_fable_refusal",
    "log_llm_call",
    "log_workflow_run",
]
