"""Agent Coordination Dashboard — DEPRECATED.

.. deprecated:: 3.6.3
    ``attune.dashboard`` is deprecated and will be removed in a future
    major version. The React frontend has been removed. Use the telemetry
    classes (``FeedbackLoop``, ``UsageTracker``) directly instead.

Usage (Standalone - Direct Redis Access):
    >>> from attune.dashboard import run_standalone_dashboard
    >>> run_standalone_dashboard(host="0.0.0.0", port=8080)

Usage (Simple Server - Uses Telemetry API):
    >>> from attune.dashboard import run_simple_dashboard
    >>> run_simple_dashboard(host="0.0.0.0", port=8080)

Usage (FastAPI - Requires fastapi and uvicorn):
    >>> from attune.dashboard import run_dashboard
    >>> run_dashboard(host="0.0.0.0", port=8080)

Features:
- Real-time agent status monitoring (Pattern 1)
- Coordination signal viewer (Pattern 2)
- Event stream monitor (Pattern 4)
- Approval request manager (Pattern 5)
- Quality feedback analytics (Pattern 6)
- Auto-refresh every 5 seconds

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune.dashboard is deprecated as of v3.6.3 and will be removed in a "
    "future major version. Use telemetry classes (FeedbackLoop, UsageTracker) "
    "directly instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Standalone server - reads directly from Redis
# Simple server - uses telemetry API classes
from .simple_server import run_simple_dashboard  # noqa: E402
from .standalone_server import run_standalone_dashboard  # noqa: E402

# Optional FastAPI version (requires dependencies)
try:
    from .app import app, run_dashboard  # noqa: E402

    __all__ = ["app", "run_dashboard", "run_simple_dashboard", "run_standalone_dashboard"]
except ImportError:
    # FastAPI not installed
    __all__ = ["run_simple_dashboard", "run_standalone_dashboard"]
