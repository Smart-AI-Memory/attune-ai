"""CLI commands for telemetry tracking.

Provides commands to view, analyze, and manage local usage telemetry data.

IMPORTANT: This module re-exports all command functions from submodules for
backward compatibility. All symbols remain importable from attune.telemetry.cli.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from attune.security.path_validation import (
    _validate_file_path,  # noqa: F401 - re-exported for backward compat
)

# Analysis commands (model fallback analysis, per-file test status)
from .cli_analysis import (  # noqa: F401
    cmd_file_test_status,
    cmd_sonnet_opus_analysis,
)

# Tier 1 automation monitoring commands
from .cli_automation import (  # noqa: F401
    cmd_agent_performance,
    cmd_task_routing_report,
    cmd_test_status,
    cmd_tier1_status,
)

# Core telemetry commands (show, savings, cache stats, compare, reset, export)
from .cli_core import (  # noqa: F401
    cmd_telemetry_cache_stats,
    cmd_telemetry_compare,
    cmd_telemetry_export,
    cmd_telemetry_reset,
    cmd_telemetry_savings,
    cmd_telemetry_show,
)
