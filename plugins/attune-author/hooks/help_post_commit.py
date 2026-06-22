#!/usr/bin/env python3
"""PostToolUse hook: surface stale-template suggestions after commits.

Triggered after every Bash tool call. Filters for `git commit`
commands, then calls attune_author.maintenance.run_hook() to
detect features touched by the commit and report stale templates.

Always exits 0 (non-blocking). Suggestions go to stderr so
Claude Code surfaces them; stdout is silently discarded by the
hook protocol.
"""

from __future__ import annotations

import json
import sys


def _read_payload() -> dict:
    """Read the JSON payload from stdin.

    Returns:
        Parsed payload dict, or empty dict on parse failure.
    """
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        return {}


def _is_git_commit(tool_input: dict) -> bool:
    """Return True if the bash command is a git commit."""
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        return False
    return "git commit" in command


def main() -> int:
    """Hook entry point. Always returns 0 (non-blocking)."""
    payload = _read_payload()

    tool_name = payload.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    tool_input = payload.get("tool_input") or {}
    if not _is_git_commit(tool_input):
        return 0

    # Lazy import — keeps the hook fast for non-commit calls
    try:
        from attune_author.maintenance import run_hook
    except ImportError:
        # attune-author not installed in this environment
        return 0

    try:
        from pathlib import Path

        cwd = Path.cwd()
        help_dir = cwd / ".help"
        if not (help_dir / "features.yaml").exists():
            return 0

        result = run_hook(help_dir=help_dir, project_root=cwd)
        if result is None or result.stale_count == 0:
            return 0

        print(
            f"\n[attune-author] {result.stale_count} feature(s) "
            f"may have stale documentation after this commit:",
            file=sys.stderr,
        )
        for name in result.staleness.stale_features[:5]:
            print(f"  - {name}", file=sys.stderr)
        print(
            "  Run /author maintain to refresh templates.",
            file=sys.stderr,
        )
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: hook is non-blocking — never raise
        print(
            f"[attune-author] hook error (non-fatal): {e}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
