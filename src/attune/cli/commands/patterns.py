"""Pattern management commands for the CLI.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys

from attune.config import _validate_file_path
from attune.logging_config import get_logger
from attune.persistence import PatternPersistence

logger = get_logger(__name__)


def cmd_patterns_list(args):
    """List patterns in a pattern library.

    Args:
        args: Namespace object from argparse with attributes:
            - library (str): Path to pattern library file.
            - format (str): Library format ('json' or 'sqlite').

    Returns:
        None: Prints pattern list to stdout. Exits with code 1 on failure.
    """
    filepath = args.library
    format_type = args.format
    logger.info(f"Listing patterns from library: {filepath} (format: {format_type})")

    try:
        if format_type == "json":
            library = PatternPersistence.load_from_json(filepath)
        elif format_type == "sqlite":
            library = PatternPersistence.load_from_sqlite(filepath)
        else:
            logger.error(f"Unknown pattern library format: {format_type}")
            logger.error(f"✗ Unknown format: {format_type}")
            sys.exit(1)

        logger.info(f"Loaded {len(library.patterns)} patterns from {filepath}")
        logger.info(f"=== Pattern Library: {filepath} ===\n")
        logger.info(f"Total patterns: {len(library.patterns)}")
        logger.info(f"Total agents: {len(library.agent_contributions)}")

        if library.patterns:
            logger.info("\nPatterns:")
            for pattern_id, pattern in library.patterns.items():
                logger.info(f"\n  [{pattern_id}] {pattern.name}")
                logger.info(f"    Agent: {pattern.agent_id}")
                logger.info(f"    Type: {pattern.pattern_type}")
                logger.info(f"    Confidence: {pattern.confidence:.2f}")
                logger.info(f"    Usage: {pattern.usage_count}")
                logger.info(f"    Success Rate: {pattern.success_rate:.2f}")
    except FileNotFoundError:
        logger.error(f"Pattern library not found: {filepath}")
        logger.error(f"✗ Pattern library not found: {filepath}")
        sys.exit(1)


def cmd_patterns_export(args):
    """Export patterns from one format to another.

    Args:
        args: Namespace object from argparse with attributes:
            - input (str): Input file path.
            - output (str): Output file path.
            - input_format (str): Input format ('json' or 'sqlite').
            - output_format (str): Output format ('json' or 'sqlite').

    Returns:
        None: Exports patterns to output file. Exits with code 1 on failure.

    Raises:
        ValueError: If output path is invalid or unsafe.
    """
    input_file = args.input
    input_format = args.input_format
    output_file = args.output
    output_format = args.output_format

    logger.info(f"Exporting patterns from {input_format} to {output_format}")

    # Load from input format
    try:
        if input_format == "json":
            library = PatternPersistence.load_from_json(input_file)
        elif input_format == "sqlite":
            library = PatternPersistence.load_from_sqlite(input_file)
        else:
            logger.error(f"Unknown input format: {input_format}")
            logger.error(f"✗ Unknown input format: {input_format}")
            sys.exit(1)

        logger.info(f"Loaded {len(library.patterns)} patterns from {input_file}")
        logger.info(f"✓ Loaded {len(library.patterns)} patterns from {input_file}")
    except (OSError, FileNotFoundError) as e:
        # Input file not found or cannot be read
        logger.error(f"Pattern file error: {e}")
        logger.error(f"✗ Cannot read pattern file: {e}")
        sys.exit(1)
    except (ValueError, KeyError) as e:
        # Invalid pattern data format
        logger.error(f"Pattern data error: {e}")
        logger.error(f"✗ Invalid pattern data: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected errors loading patterns
        logger.exception(f"Unexpected error loading patterns: {e}")
        logger.error(f"✗ Failed to load patterns: {e}")
        sys.exit(1)

    # Validate output path
    validated_output = _validate_file_path(output_file)

    # Save to output format
    try:
        if output_format == "json":
            PatternPersistence.save_to_json(library, str(validated_output))
        elif output_format == "sqlite":
            PatternPersistence.save_to_sqlite(library, str(validated_output))

        logger.info(f"Saved {len(library.patterns)} patterns to {output_file}")
        logger.info(f"✓ Saved {len(library.patterns)} patterns to {output_file}")
    except (OSError, FileNotFoundError, PermissionError) as e:
        # Cannot write output file
        logger.error(f"Pattern file write error: {e}")
        logger.error(f"✗ Cannot write pattern file: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected errors saving patterns
        logger.exception(f"Unexpected error saving patterns: {e}")
        logger.error(f"✗ Failed to save patterns: {e}")
        sys.exit(1)


def cmd_patterns_resolve(args):
    """Resolve investigating bug patterns with root cause and fix.

    Updates pattern status and adds resolution information.

    Args:
        args: Namespace object from argparse with attributes:
            - pattern_id (str | None): Pattern ID to resolve.
            - root_cause (str | None): Root cause description.
            - fix (str | None): Fix description.
            - fix_code (str | None): Code snippet of the fix.
            - time (int | None): Resolution time in minutes.
            - status (str): New status ('resolved', 'wont_fix', etc.).
            - patterns_dir (str): Patterns directory path.
            - commit (str | None): Related commit hash.

    Returns:
        None: Updates pattern and prints result. Exits with code 1 on failure.
    """
    from attune.patterns.resolver import PatternResolver

    resolver = PatternResolver(args.patterns_dir)

    # If no bug_id, list investigating bugs
    if not args.bug_id:
        investigating = resolver.list_investigating()
        if not investigating:
            print("No bugs with 'investigating' status found.")
            return

        print(f"\nBugs needing resolution ({len(investigating)}):\n")
        for bug in investigating:
            print(f"  {bug.get('bug_id', 'unknown')}")
            print(f"    Type: {bug.get('error_type', 'unknown')}")
            print(f"    File: {bug.get('file_path', 'unknown')}")
            msg = bug.get("error_message", "N/A")
            print(f"    Message: {msg[:60]}..." if len(msg) > 60 else f"    Message: {msg}")
            print()
        return

    # Validate required args
    if not args.root_cause or not args.fix:
        print("✗ --root-cause and --fix are required when resolving a bug")
        print(
            "  Example: attune patterns resolve bug_123 --root-cause 'Null check' --fix 'Added ?.'",
        )
        sys.exit(1)

    # Resolve the specified bug
    success = resolver.resolve_bug(
        bug_id=args.bug_id,
        root_cause=args.root_cause,
        fix_applied=args.fix,
        fix_code=args.fix_code,
        resolution_time_minutes=args.time or 0,
        resolved_by=args.resolved_by or "@developer",
    )

    if success:
        print(f"✓ Resolved: {args.bug_id}")

        # Regenerate summary if requested
        if not args.no_regenerate:
            if resolver.regenerate_summary():
                print("✓ Regenerated patterns_summary.md")
            else:
                print("⚠ Failed to regenerate summary")
    else:
        print(f"✗ Failed to resolve: {args.bug_id}")
        print("  Use 'attune patterns resolve' (no args) to list investigating bugs")
        sys.exit(1)
