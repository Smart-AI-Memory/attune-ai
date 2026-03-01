"""Dashboard command implementations for telemetry CLI.

Provides interactive HTML dashboard generation for telemetry data.
Each dashboard command is implemented in its own module:

- dashboard_telemetry.py: Cost/tier telemetry dashboard
- dashboard_file_tests.py: File test status dashboard

This module re-exports for backward compatibility.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .dashboard_file_tests import cmd_file_test_dashboard
from .dashboard_telemetry import cmd_telemetry_dashboard

__all__ = ["cmd_file_test_dashboard", "cmd_telemetry_dashboard"]
