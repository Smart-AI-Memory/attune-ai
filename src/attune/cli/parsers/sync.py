"""Parser definitions for sync commands.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from ..commands import sync


def register_parsers(subparsers):
    """Register sync command parsers.

    Args:
        subparsers: ArgumentParser subparsers object from main parser
    """
    # Sync-claude command
    parser_sync_claude = subparsers.add_parser(
        "sync-claude",
        help="Sync learned patterns to Claude Code rules",
    )
    parser_sync_claude.add_argument(
        "--patterns-dir",
        default="patterns",
        help="Source patterns directory (default: patterns)",
    )
    parser_sync_claude.add_argument(
        "--output-dir",
        default=".claude/rules/attune",
        help="Target Claude Code rules directory (default: .claude/rules/attune)",
    )
    parser_sync_claude.set_defaults(func=sync.cmd_sync_claude)
