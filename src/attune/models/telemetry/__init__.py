"""Telemetry tracking and analytics.

Modular telemetry system for tracking LLM calls, workflows, tests, and agent performance.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

# Data models
# Analytics
from .analytics import TelemetryAnalytics

# Backend interface
from .backend import TelemetryBackend
from .data_models import (
    AgentAssignmentRecord,
    CoverageRecord,
    FileTestRecord,
    LLMCallRecord,
    TaskRoutingRecord,
    TestExecutionRecord,
    WorkflowRunRecord,
    WorkflowStageRecord,
)

# Storage implementation
from .storage import TelemetryStore

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


__all__ = [
    # Data models
    "LLMCallRecord",
    "WorkflowStageRecord",
    "WorkflowRunRecord",
    "TaskRoutingRecord",
    "TestExecutionRecord",
    "CoverageRecord",
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
    "log_llm_call",
    "log_workflow_run",
]
