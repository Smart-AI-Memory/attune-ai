"""Telemetry tracking for Attune AI.

Privacy-first, local-only usage tracking to measure actual cost savings.

Includes:
- UsageTracker: Track LLM usage and costs
- HeartbeatCoordinator: Monitor agent liveness via TTL heartbeats
- CoordinationSignals: Inter-agent communication via TTL signals
- EventStreamer: Real-time event streaming via Redis Streams
- ApprovalGate: Human approval gates for workflow control
- FeedbackLoop: Agent-to-LLM quality feedback for adaptive routing

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys as _sys

import attune_forms.form_events as _form_events

from .agent_coordination import CoordinationSignal, CoordinationSignals
from .agent_tracking import AgentHeartbeat, HeartbeatCoordinator
from .approval_gates import ApprovalGate, ApprovalRequest, ApprovalResponse
from .event_streaming import EventStreamer, StreamEvent
from .features import FeatureInfo, FeatureStatus, TelemetryFeatures
from .feedback_loop import FeedbackEntry, FeedbackLoop, QualityStats, TierRecommendation
from .usage_tracker import UsageTracker

# ``attune.telemetry.form_events`` moved to the standalone attune-forms
# package; alias the legacy path to the SAME module object (os.path
# pattern) so imports and monkeypatching behave exactly as before. Any
# ``import attune.telemetry.form_events`` runs this package __init__ to
# completion first, so the alias is always in place by lookup time.
_sys.modules[__name__ + ".form_events"] = _form_events

__all__ = [
    "AgentHeartbeat",
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalResponse",
    "CoordinationSignal",
    "CoordinationSignals",
    "EventStreamer",
    "FeatureInfo",
    "FeatureStatus",
    "FeedbackEntry",
    "FeedbackLoop",
    "HeartbeatCoordinator",
    "QualityStats",
    "StreamEvent",
    "TelemetryFeatures",
    "TierRecommendation",
    "UsageTracker",
]
