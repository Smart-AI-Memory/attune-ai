"""PostToolUse hook: auto-format Python files after Write/Edit.

Runs black + ruff --fix on any .py file that Claude writes or edits.
Prevents CI failures from minor formatting issues.

Inspired by Boris Cherny's PostToolUse formatting hook pattern.

Reads tool result from stdin (JSON with tool_name and tool_input).
Exits 0 always (formatting is best-effort, never blocks).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_file_path(data: dict) -> str | None:
    """Extract the file path from tool input.

    Args:
        data: Parsed JSON from stdin with tool_name and tool_input.

    Returns:
        File path string if found, None otherwise.

    """
    tool_input = data.get("tool_input", {})
    return tool_input.get("file_path") or tool_input.get("path")


def _is_python_file(path: str) -> bool:
    """Check if the path points to a Python file.

    Args:
        path: File path to check.

    Returns:
        True if the file has a .py extension.

    """
    return Path(path).suffix == ".py"


def _run_formatter(cmd: list[str], path: str) -> None:
    """Run a formatting command silently.

    Args:
        cmd: Command and arguments to run.
        path: File path to format.

    """
    try:
        subprocess.run(
            [*cmd, path],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


def main() -> None:
    """Read tool result from stdin, format Python files."""
    try:
        _buf = getattr(sys.stdin, "buffer", None)  # None when tests patch stdin
        raw = _buf.read().decode("utf-8", errors="replace") if _buf else sys.stdin.read()
        if not raw.strip():
            return

        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return

    file_path = _get_file_path(data)
    if not file_path or not _is_python_file(file_path):
        return

    try:
        from attune.security.path_validation import _validate_file_path

        validated = _validate_file_path(file_path)
    except (ValueError, ImportError):
        return

    if not validated.exists():
        return

    _run_formatter(["black", "--quiet", "--line-length=100"], str(validated))
    _run_formatter(["ruff", "check", "--fix", "--quiet"], str(validated))


if __name__ == "__main__":
    try:
        from _bootstrap import ensure_utf8_stdio
    except ImportError:
        # Vendored copies (sibling .claude/hooks/) may not ship
        # _bootstrap.py — degrade to the pre-bootstrap behavior
        # rather than crashing the hook.
        pass
    else:
        ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    main()
