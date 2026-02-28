"""Anthropic Agent SDK integration.

Provides ``SDKAgent`` and ``SDKAgentTeam`` that wrap the optional
``claude-agent-sdk`` package while preserving attune's tier escalation,
heartbeats, and persistent state patterns.

Install the SDK extra to enable::

    pip install attune-ai[agent-sdk]

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from .adapters import SDKToolsMixin
from .sdk_agent import SDKAgent
from .sdk_models import SDK_AVAILABLE, SDKAgentResult, SDKExecutionMode
from .sdk_team import QualityGate, SDKAgentTeam, SDKTeamResult

__all__ = [
    "SDK_AVAILABLE",
    "QualityGate",
    "SDKAgent",
    "SDKAgentResult",
    "SDKAgentTeam",
    "SDKExecutionMode",
    "SDKTeamResult",
    "SDKToolsMixin",
]
