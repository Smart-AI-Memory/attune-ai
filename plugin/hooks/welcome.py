#!/usr/bin/env python3
"""SessionStart welcome message for attune-ai plugin.

Prints a brief orientation message when a Claude Code session
begins so users know the plugin is loaded and how to start.

Exit code 0 — informational only, never blocks.
"""

from __future__ import annotations

import sys


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
    main()
