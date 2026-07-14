#!/usr/bin/env python
"""SessionStart welcome message for attune-ai plugin.

Prints a brief orientation message when a Claude Code session
begins so users know the plugin is loaded and how to start.

Exit code 0 — informational only, never blocks.
"""

from __future__ import annotations

import sys

# Force utf-8 on stdout and stderr. On Windows the default cp1252
# encoding can't emit emoji/em-dash and would crash this hook (caught
# by the outer try/except → silent breakage). errors='replace'
# substitutes '?' for any stray non-encodable byte.
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    """Print welcome message to stderr (Claude Code surfaces stderr)."""
    msg = (
        "\n"
        "attune-ai loaded — 18 workflows, 31 MCP tools\n"
        "\n"
        "  /attune           Guided menu\n"
        "  /attune security  Security audit\n"
        "  /attune review    Code review\n"
        '  "generate tests"  Auto-triggers smart-test\n'
        "\n"
        "Type /attune for the full list.\n"
    )
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    main()
