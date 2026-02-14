"""Parser definitions for inspect commands.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from ..commands import inspect


def register_parsers(subparsers):
    """Register inspect command parsers.

    Args:
        subparsers: ArgumentParser subparsers object from main parser
    """
    # Run command - Interactive REPL
    parser_run = subparsers.add_parser("run", help="Interactive REPL mode")
    parser_run.add_argument("--config", "-c", help="Configuration file path")
    parser_run.add_argument("--user-id", help="User ID (default: cli_user)")
    parser_run.add_argument(
        "--level",
        type=int,
        default=4,
        help="Target level (1-5, default: 4)",
    )
    parser_run.set_defaults(func=inspect.cmd_run)

    # Inspect command - Unified inspection
    parser_inspect = subparsers.add_parser("inspect", help="Inspect patterns, metrics, or state")
    parser_inspect.add_argument(
        "type",
        choices=["patterns", "metrics", "state"],
        help="Type of inspection (patterns, metrics, or state)",
    )
    parser_inspect.add_argument("--user-id", help="User ID to filter by (optional)")
    parser_inspect.add_argument("--db", help="Database path (default: .attune/patterns.db)")
    parser_inspect.add_argument(
        "--state-dir",
        help="State directory path (default: .attune/state)",
    )
    parser_inspect.set_defaults(func=inspect.cmd_inspect)

    # Export command
    parser_export = subparsers.add_parser(
        "export",
        help="Export patterns to file for sharing/backup",
    )
    parser_export.add_argument("output", help="Output file path")
    parser_export.add_argument(
        "--user-id",
        help="User ID to export (optional, exports all if not specified)",
    )
    parser_export.add_argument("--db", help="Database path (default: .attune/patterns.db)")
    parser_export.add_argument(
        "--format",
        default="json",
        choices=["json"],
        help="Export format (default: json)",
    )
    parser_export.set_defaults(func=inspect.cmd_export)

    # Import command
    parser_import = subparsers.add_parser("import", help="Import patterns from file")
    parser_import.add_argument("input", help="Input file path")
    parser_import.add_argument("--db", help="Database path (default: .attune/patterns.db)")
    parser_import.set_defaults(func=inspect.cmd_import)
