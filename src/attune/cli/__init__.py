"""Attune AI CLI - Refactored modular structure.

Entry point for the attune command-line interface.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import argparse
import sys

from attune.discovery import show_tip_if_available
from attune.logging_config import get_logger
from attune.platform_utils import setup_asyncio_policy

logger = get_logger(__name__)


def get_version() -> str:
    """Get package version.

    Returns:
        Version string or "dev" if not installed
    """
    try:
        from importlib.metadata import version

        return version("attune-ai")
    except Exception:  # noqa: BLE001
        return "dev"


def main() -> int:
    """Main CLI entry point.

    This is the refactored CLI entry point that uses modular command
    and parser organization instead of a monolithic 3,957-line file.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Windows async compatibility
    setup_asyncio_policy()

    # Create main parser
    parser = argparse.ArgumentParser(
        prog="attune", description="Attune AI - Context-aware development automation"
    )

    # Add global flags
    parser.add_argument("--version", action="version", version=f"attune {get_version()}")

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="command", title="commands", description="Available commands"
    )

    # Register all command parsers (modular!)
    from .parsers import register_all_parsers

    register_all_parsers(subparsers)

    # NOTE: CLI refactoring is COMPLETE (v2.1.5)
    # All 30 commands have been extracted from the monolithic cli_legacy.py
    # to the new modular structure in cli/commands/ and cli/parsers/.

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    if hasattr(args, "func"):
        try:
            result = args.func(args)

            # Show discovery tips (except for dashboard/run)
            if args.command and args.command not in ("dashboard", "run"):
                try:
                    show_tip_if_available(args.command)
                except Exception:  # noqa: BLE001
                    logger.debug("Discovery tip not available")

            return result if result is not None else 0

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            return 130

        except Exception as e:  # noqa: BLE001
            logger.exception(f"Unexpected error in command {args.command}")
            print(f"\n❌ Error: {e}")
            return 1

    # No command specified
    parser.print_help()
    return 0


# Preserve backward compatibility
if __name__ == "__main__":
    sys.exit(main())
