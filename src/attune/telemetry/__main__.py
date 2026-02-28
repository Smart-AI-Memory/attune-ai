"""Enable running telemetry as a module.

Usage:
    python -m attune.telemetry show
    python -m attune.telemetry savings
    python -m attune.telemetry export -o telemetry.json

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import argparse
import sys

from attune._deprecation import _emit_cli_deprecation


def main() -> int:
    """Telemetry CLI entry point."""
    _emit_cli_deprecation("attune.telemetry", "attune telemetry <command>")
    parser = argparse.ArgumentParser(
        description="Attune AI Telemetry - Usage and cost tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m attune.telemetry show
    python -m attune.telemetry show --days 7
    python -m attune.telemetry savings
    python -m attune.telemetry export -o telemetry.json

Note: The canonical CLI is 'attune telemetry <command>'.
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Telemetry command")

    # show
    show_parser = subparsers.add_parser("show", help="Display usage summary")
    show_parser.add_argument("--days", "-d", type=int, default=30, help="Number of days")
    show_parser.add_argument("--limit", "-l", type=int, default=20, help="Max entries")

    # savings
    savings_parser = subparsers.add_parser("savings", help="Show cost savings")
    savings_parser.add_argument("--days", "-d", type=int, default=30, help="Number of days")

    # export
    export_parser = subparsers.add_parser("export", help="Export telemetry data")
    export_parser.add_argument("--output", "-o", required=True, help="Output file path")
    export_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "csv"],
        default="json",
        help="Output format",
    )
    export_parser.add_argument("--days", "-d", type=int, default=30, help="Number of days")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    from .cli_core import cmd_telemetry_export, cmd_telemetry_savings, cmd_telemetry_show

    commands = {
        "show": cmd_telemetry_show,
        "savings": cmd_telemetry_savings,
        "export": cmd_telemetry_export,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
