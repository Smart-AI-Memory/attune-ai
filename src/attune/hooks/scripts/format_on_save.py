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
import time
from pathlib import Path

logger = logging.getLogger(__name__)

#: Total wall-clock budget SHARED across both formatters (black + ruff),
#: seconds. The registered PostToolUse timeout is 10s (10 in both
#: ``plugin/hooks/hooks.json`` and ``.claude/settings.json`` — the
#: ``timeout`` field is SECONDS on both surfaces); this
#: sits below it so the two formatters COMBINED — plus interpreter
#: start-up and the src-path import — finish before the harness SIGKILLs
#: the hook. Each formatter previously carried its own 10s ceiling, so a
#: hung black + hung ruff could run ~20s (> the 10s timeout) and be
#: killed mid-format. Kept under the registered timeout by
#: ``tests/unit/hooks/test_hook_scripts.py``.
WALL_BUDGET = 8

#: Monotonic instant by which both formatters must finish, set once in
#: ``main()`` around the formatter pair and shared between them. ``None``
#: (the default) means unbounded — a standalone ``_run_formatter`` call
#: uses ``WALL_BUDGET`` as its per-call ceiling.
_DEADLINE: float | None = None


def _remaining(ceiling: float) -> float:
    """Clamp ``ceiling`` to the time left before the shared ``_DEADLINE``.

    Returns ``ceiling`` when no deadline is set, ``0.0`` once it has
    passed (caller skips the formatter), or the seconds remaining.
    """
    if _DEADLINE is None:
        return ceiling
    return max(0.0, min(ceiling, _DEADLINE - time.monotonic()))


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
    timeout = _remaining(WALL_BUDGET)
    if timeout <= 0:
        return  # shared budget already spent — skip, don't start a run
    try:
        subprocess.run(
            [*cmd, path],
            capture_output=True,
            timeout=timeout,
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
    except (json.JSONDecodeError, ValueError, RecursionError):
        return

    # A non-dict payload (list/int/str/null) has no tool fields; the
    # contract is exit-0-always, so degrade instead of crashing (L3).
    if not isinstance(data, dict):
        return

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return

    file_path = _get_file_path(data)
    if not file_path or not _is_python_file(file_path):
        return

    try:
        # Make repo src/ importable without POSIX-only PYTHONPATH=src
        # env-prefix syntax in the hook registration (Windows-safe).
        from _bootstrap import ensure_repo_src_on_path

        ensure_repo_src_on_path()
        from attune.security.path_validation import _validate_file_path

        validated = _validate_file_path(file_path)
    except (ValueError, ImportError):
        return

    if not validated.exists():
        return

    # One budget shared by both formatters, so a hung black + hung ruff
    # can't sum past the registered PostToolUse timeout. Reset in the
    # finally so nothing leaks between invocations (or test runs); real
    # runs are one-shot processes either way.
    global _DEADLINE
    _DEADLINE = time.monotonic() + WALL_BUDGET
    try:
        _run_formatter(["black", "--quiet", "--line-length=100"], str(validated))
        # `--ignore F401,F811`: never strip "unused" imports on save. An agent
        # editing in two steps (import first, usage next) loses the import to
        # this hook in the gap — hit 4x in one session (2026-08-09) despite a
        # same-edit discipline rule. Genuinely dead imports are still caught
        # at commit time by pre-commit ruff, where the file is complete.
        _run_formatter(
            ["ruff", "check", "--fix", "--quiet", "--ignore", "F401,F811"], str(validated)
        )
    finally:
        _DEADLINE = None


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    try:
        main()
    except Exception:  # noqa: BLE001
        # PostToolUse best-effort: wrong-typed nested fields (e.g.
        # tool_input=[...] or file_path=5) must not crash the
        # exit-0-always contract (library-review L3).
        pass
