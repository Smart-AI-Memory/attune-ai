"""Unified voice layer for Attune AI.

All user-facing output passes through this module to ensure
a consistent personality, formatting, and contextual next-step
guidance across every surface (workflows, MCP, CLI, errors).

Public API::

    from attune.voice import format_output, format_error

    # Workflow result -> voiced output string
    text = format_output(workflow_name, result)

    # Error -> voiced error string
    text = format_error(message, context="workflow")

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from .formatter import format_error, format_output

__all__ = ["format_error", "format_output"]
