"""Anthropic Agent SDK integration.

Provides ``SDKAgent`` and ``SDKAgentTeam`` that wrap
``claude-agent-sdk`` while preserving attune's tier escalation,
heartbeats, and persistent state patterns.

The SDK is a core dependency as of v4.2.0.

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
