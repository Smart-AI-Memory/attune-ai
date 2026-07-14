"""PostToolUse hook: auto-maintain .help/ after git commits.

When the user runs a successful `git commit`, checks if
any committed files match features in .help/features.yaml.
If stale features are found, reports them via stderr.

Only fires on Bash tool calls that contain `git commit`.
Exits 0 always (informational, never blocks).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Force utf-8 on stdout and stderr. On Windows the default cp1252
# encoding can't emit emoji/em-dash and would crash this hook (caught
# by the outer try/except → silent breakage). errors='replace'
# substitutes '?' for any stray non-encodable byte.
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    """Check for stale help after git commit."""
    try:
        _buf = getattr(sys.stdin, "buffer", None)  # None when tests patch stdin
        raw = (
            _buf.read(10_000).decode("utf-8", errors="replace") if _buf else sys.stdin.read(10_000)
        )
        if not raw.strip():
            return
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        return

    # Only trigger on git commit commands
    tool_input = data.get("tool_input", {})
    command = ""
    if isinstance(tool_input, dict):
        command = tool_input.get("command", "")
    elif isinstance(tool_input, str):
        command = tool_input

    if "git commit" not in command:
        return

    # Check if the commit succeeded (exit code 0)
    result = data.get("tool_result", "")
    if isinstance(result, dict):
        stdout = result.get("stdout", "")
        if "nothing to commit" in stdout:
            return
    elif isinstance(result, str):
        if "nothing to commit" in result:
            return

    # Find .help/features.yaml relative to the repo
    # Walk up from cwd to find it
    cwd = Path.cwd()
    help_dir = None
    for parent in [cwd, *cwd.parents]:
        candidate = parent / ".help" / "features.yaml"
        if candidate.exists():
            help_dir = parent / ".help"
            break

    if help_dir is None:
        return

    # Lazy import — only runs when we know there's
    # a manifest to check
    try:
        sys.path.insert(0, str(help_dir.parent / "src"))
        from attune.help.maintenance import run_hook

        hook_result = run_hook(
            help_dir=str(help_dir),
            project_root=str(help_dir.parent),
        )
    except Exception:  # noqa: BLE001
        # INTENTIONAL: hook must never crash the commit flow
        return

    if hook_result is None:
        return

    if hook_result.stale_count > 0:
        regen = hook_result.regenerated_count
        if regen > 0:
            print(
                f"attune: auto-updated {regen} help "
                f"template(s) in .help/. Stage and commit "
                f"the changes with your next commit.",
                file=sys.stderr,
            )
        else:
            stale = hook_result.staleness.stale_features
            names = ", ".join(stale[:5])
            print(
                f"attune: {hook_result.stale_count} help feature(s) "
                f"are stale ({names}). Run /coach maintain "
                f"to update.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    main()
