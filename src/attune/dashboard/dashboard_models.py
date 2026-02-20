"""Pydantic models for the Agent Coordination Dashboard API.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from pydantic import BaseModel


class AgentStatus(BaseModel):
    """Agent status summary."""

    agent_id: str
    status: str
    last_seen: str
    progress: float
    current_task: str


class SignalSummary(BaseModel):
    """Coordination signal summary."""

    signal_type: str
    source_agent: str
    target_agent: str
    timestamp: str
    payload: dict[str, Any]


class ApprovalRequestSummary(BaseModel):
    """Approval request summary."""

    request_id: str
    approval_type: str
    agent_id: str
    context: dict[str, Any]
    timestamp: str
    timeout_seconds: float


class QualityMetrics(BaseModel):
    """Quality feedback metrics."""

    workflow_name: str
    stage_name: str
    tier: str
    avg_quality: float
    sample_count: int
    trend: float
