"""Inspect commands for patterns, metrics, and interactive REPL.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import heapq
import sys
import time

from attune.config import EmpathyConfig, _validate_file_path, load_config
from attune.core import EmpathyOS
from attune.logging_config import get_logger
from attune.metrics.collector import MetricsCollector
from attune.pattern_library import PatternLibrary
from attune.persistence import PatternPersistence, StateManager

logger = get_logger(__name__)


def cmd_run(args):
    """Interactive REPL for testing Attune AI interactions.

    Starts an interactive session for testing interaction levels and features.

    Args:
        args: Namespace object from argparse with attributes:
            - config (str | None): Path to configuration file.
            - user_id (str | None): User ID (default: cli_user).
            - level (int): Target level (1-5).

    Returns:
        None: Runs interactive REPL until user exits.
    """
    config_file = args.config
    user_id = args.user_id or "cli_user"
    level = args.level

    print("🧠 Attune AI - Interactive Mode")
    print("=" * 50)

    # Load configuration
    if config_file:
        config = load_config(filepath=config_file)
        print(f"✓ Loaded config from: {config_file}")
    else:
        config = EmpathyConfig(user_id=user_id, target_level=level)
        print("✓ Using default configuration")

    print(f"\nUser ID: {config.user_id}")
    print(f"Target Level: {config.target_level}")
    print(f"Confidence Threshold: {config.confidence_threshold:.0%}")

    # Create Attune OS instance
    try:
        attune_os = EmpathyOS(
            user_id=config.user_id,
            target_level=config.target_level,
            confidence_threshold=config.confidence_threshold,
            persistence_enabled=config.persistence_enabled,
        )
        print("✓ Attune OS initialized")
    except ValueError as e:
        # Invalid configuration parameters
        print(f"✗ Configuration error: {e}")
        sys.exit(1)
    except (OSError, FileNotFoundError, PermissionError) as e:
        # Cannot access required files/directories
        print(f"✗ File system error: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected initialization failure
        logger.exception(f"Unexpected error initializing Attune OS: {e}")
        print(f"✗ Failed to initialize Attune OS: {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("Type your input (or 'exit'/'quit' to stop)")
    print("Type 'help' for available commands")
    print("=" * 50 + "\n")

    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n👋 Goodbye!")
                break

            if user_input.lower() == "help":
                print("\nAvailable commands:")
                print("  exit, quit, q - Exit the program")
                print("  help - Show this help message")
                print("  trust - Show current trust level")
                print("  stats - Show session statistics")
                print("  level - Show current level")
                print()
                continue

            if user_input.lower() == "trust":
                trust = attune_os.collaboration_state.trust_level
                print(f"\n  Current trust level: {trust:.0%}\n")
                continue

            if user_input.lower() == "level":
                current_level = attune_os.collaboration_state.current_level
                print(f"\n  Current level: {current_level}\n")
                continue

            if user_input.lower() == "stats":
                print("\n  Session Statistics:")
                print(f"    Trust: {attune_os.collaboration_state.trust_level:.0%}")
                print(f"    Current Level: {attune_os.collaboration_state.current_level}")
                print(f"    Target Level: {config.target_level}")
                print()
                continue

            # Process interaction
            start_time = time.time()
            response = attune_os.interact(user_id=config.user_id, user_input=user_input, context={})
            duration = (time.time() - start_time) * 1000

            # Display response with level indicator
            level_indicators = ["❌", "🔵", "🟢", "🟡", "🔮"]
            level_indicator = level_indicators[response.level]

            print(f"\nBot {level_indicator} [L{response.level}]: {response.response}")

            # Show predictions if Level 4
            if response.predictions:
                print("\n🔮 Predictions:")
                for pred in response.predictions:
                    print(f"   • {pred}")

            conf = f"{response.confidence:.0%}"
            print(f"\n  Level: {response.level} | Confidence: {conf} | Time: {duration:.0f}ms")
            print()

            # Ask for feedback
            feedback = input("Was this helpful? (y/n/skip): ").strip().lower()
            if feedback == "y":
                attune_os.record_success(success=True)
                trust = attune_os.collaboration_state.trust_level
                print(f"  ✓ Trust increased to {trust:.0%}\n")
            elif feedback == "n":
                attune_os.record_success(success=False)
                trust = attune_os.collaboration_state.trust_level
                print(f"  ✗ Trust decreased to {trust:.0%}\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except (ValueError, KeyError) as e:
            # Invalid input or response structure
            print(f"\n✗ Input error: {e}\n")
        except Exception as e:
            # Unexpected errors in interactive loop - log and continue
            logger.exception(f"Unexpected error in interactive loop: {e}")
            print(f"\n✗ Error: {e}\n")


def cmd_inspect(args):
    """Unified inspection command for patterns, metrics, and state.

    Inspect various framework data including patterns, user metrics, and states.

    Args:
        args: Namespace object from argparse with attributes:
            - type (str): What to inspect ('patterns', 'metrics', or 'state').
            - user_id (str | None): Filter by user ID.
            - db (str | None): Database path (default: .attune/patterns.db).
            - state_dir (str | None): State directory for state inspection.

    Returns:
        None: Prints inspection results. Exits with code 1 on failure.
    """
    inspect_type = args.type
    user_id = args.user_id
    db_path = args.db or ".attune/patterns.db"

    print(f"🔍 Inspecting: {inspect_type}")
    print("=" * 50)

    if inspect_type == "patterns":
        try:
            # Determine file format from extension
            if db_path.endswith(".json"):
                library = PatternPersistence.load_from_json(db_path)
            else:
                library = PatternPersistence.load_from_sqlite(db_path)

            patterns = list(library.patterns.values())

            # Filter by user_id if specified
            if user_id:
                patterns = [p for p in patterns if p.agent_id == user_id]

            print(f"\nPatterns for {'user ' + user_id if user_id else 'all users'}:")
            print(f"  Total patterns: {len(patterns)}")

            if patterns:
                print("\n  Top patterns:")
                # Sort by confidence
                top_patterns = heapq.nlargest(10, patterns, key=lambda p: p.confidence)
                for i, pattern in enumerate(top_patterns, 1):
                    print(f"\n  {i}. {pattern.name}")
                    print(f"     Confidence: {pattern.confidence:.0%}")
                    print(f"     Used: {pattern.usage_count} times")
                    print(f"     Success rate: {pattern.success_rate:.0%}")
        except FileNotFoundError:
            print(f"✗ Pattern library not found: {db_path}")
            print("  Tip: Use 'attune workflow' to set up your first project")
            sys.exit(1)
        except (ValueError, KeyError) as e:
            # Invalid pattern data format
            print(f"✗ Invalid pattern data: {e}")
            sys.exit(1)
        except Exception as e:
            # Unexpected errors loading patterns
            logger.exception(f"Unexpected error loading patterns: {e}")
            print(f"✗ Failed to load patterns: {e}")
            sys.exit(1)

    elif inspect_type == "metrics":
        if not user_id:
            print("✗ User ID required for metrics inspection")
            print("  Usage: attune inspect metrics --user-id USER_ID")
            sys.exit(1)

        try:
            collector = MetricsCollector(db_path=db_path)
            stats = collector.get_user_stats(user_id)

            print(f"\nMetrics for user: {user_id}")
            print(f"  Total operations: {stats.get('total_operations', 0)}")
            print(f"  Success rate: {stats.get('success_rate', 0):.0%}")
            print(f"  Average response time: {stats.get('avg_response_time_ms', 0):.0f}ms")
            print("\n  Level usage:")
            for level in range(1, 6):
                count = stats.get(f"level_{level}_count", 0)
                print(f"    Level {level}: {count} times")
        except (OSError, FileNotFoundError) as e:
            # Database file not found
            print(f"✗ Metrics database not found: {e}")
            sys.exit(1)
        except KeyError as e:
            # User not found
            print(f"✗ User {user_id} not found: {e}")
            sys.exit(1)
        except Exception as e:
            # Unexpected errors loading metrics
            logger.exception(f"Unexpected error loading metrics: {e}")
            print(f"✗ Failed to load metrics: {e}")
            sys.exit(1)

    elif inspect_type == "state":
        state_dir = args.state_dir or ".attune/state"
        try:
            manager = StateManager(state_dir)
            users = manager.list_users()

            print("\nSaved states:")
            print(f"  Total users: {len(users)}")

            if users:
                print("\n  Users:")
                for uid in users:
                    print(f"    • {uid}")
        except (OSError, FileNotFoundError) as e:
            # State directory not found
            print(f"✗ State directory not found: {e}")
            sys.exit(1)
        except Exception as e:
            # Unexpected errors loading state
            logger.exception(f"Unexpected error loading state: {e}")
            print(f"✗ Failed to load state: {e}")
            sys.exit(1)

    print()


def cmd_export(args):
    """Export patterns to file for sharing/backup.

    Args:
        args: Namespace object from argparse with attributes:
            - output (str): Output file path.
            - user_id (str | None): Filter patterns by user ID.
            - db (str | None): Source database path.
            - format (str): Output format ('json').

    Returns:
        None: Exports patterns to file. Exits with code 1 on failure.

    Raises:
        ValueError: If output path is invalid or unsafe.
    """
    output_file = args.output
    user_id = args.user_id
    db_path = args.db or ".attune/patterns.db"
    format_type = args.format

    print(f"📦 Exporting patterns to: {output_file}")
    print("=" * 50)

    try:
        # Load pattern library from source file
        if db_path.endswith(".json"):
            library = PatternPersistence.load_from_json(db_path)
        else:
            library = PatternPersistence.load_from_sqlite(db_path)

        patterns = list(library.patterns.values())

        # Filter by user_id if specified
        if user_id:
            patterns = [p for p in patterns if p.agent_id == user_id]

        print(f"  Found {len(patterns)} patterns")

        # Validate output path
        validated_output = _validate_file_path(output_file)

        if format_type == "json":
            # Create filtered library if user_id specified
            if user_id:
                filtered_library = PatternLibrary()
                for pattern in patterns:
                    filtered_library.contribute_pattern(pattern.agent_id, pattern)
            else:
                filtered_library = library

            # Export as JSON
            PatternPersistence.save_to_json(filtered_library, str(validated_output))
            print(f"  ✓ Exported {len(patterns)} patterns to {output_file}")
        else:
            print(f"✗ Unsupported format: {format_type}")
            sys.exit(1)

    except FileNotFoundError:
        print(f"✗ Source file not found: {db_path}")
        print("  Tip: Patterns are saved automatically when using the framework")
        sys.exit(1)
    except (OSError, PermissionError) as e:
        # Cannot write output file
        print(f"✗ Cannot write to file: {e}")
        sys.exit(1)
    except (ValueError, KeyError) as e:
        # Invalid pattern data
        print(f"✗ Invalid pattern data: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected errors during export
        logger.exception(f"Unexpected error exporting patterns: {e}")
        print(f"✗ Export failed: {e}")
        sys.exit(1)

    print()


def cmd_import(args):
    """Import patterns from file (local dev only - SQLite/JSON).

    Merges imported patterns into existing pattern library.

    Args:
        args: Namespace object from argparse with attributes:
            - input (str): Input file path.
            - db (str | None): Target database path (default: .attune/patterns.db).

    Returns:
        None: Imports and merges patterns. Exits with code 1 on failure.
    """
    input_file = args.input
    db_path = args.db or ".attune/patterns.db"

    print(f"📥 Importing patterns from: {input_file}")
    print("=" * 50)

    try:
        # Load patterns from input file
        if input_file.endswith(".json"):
            imported_library = PatternPersistence.load_from_json(input_file)
        else:
            imported_library = PatternPersistence.load_from_sqlite(input_file)

        pattern_count = len(imported_library.patterns)
        print(f"  Found {pattern_count} patterns in file")

        # Load existing library if it exists, otherwise create new one
        try:
            if db_path.endswith(".json"):
                existing_library = PatternPersistence.load_from_json(db_path)
            else:
                existing_library = PatternPersistence.load_from_sqlite(db_path)

            print(f"  Existing library has {len(existing_library.patterns)} patterns")
        except FileNotFoundError:
            existing_library = PatternLibrary()
            print("  Creating new pattern library")

        # Merge imported patterns into existing library
        for pattern in imported_library.patterns.values():
            existing_library.contribute_pattern(pattern.agent_id, pattern)

        # Save merged library (SQLite for local dev)
        if db_path.endswith(".json"):
            PatternPersistence.save_to_json(existing_library, db_path)
        else:
            PatternPersistence.save_to_sqlite(existing_library, db_path)

        print(f"  ✓ Imported {pattern_count} patterns")
        print(f"  ✓ Total patterns in library: {len(existing_library.patterns)}")

    except FileNotFoundError:
        print(f"✗ Input file not found: {input_file}")
        sys.exit(1)
    except (ValueError, KeyError) as e:
        # Invalid pattern data format
        print(f"✗ Invalid pattern data: {e}")
        sys.exit(1)
    except (OSError, PermissionError) as e:
        # Cannot read input or write to database
        print(f"✗ File access error: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected errors during import
        logger.exception(f"Unexpected error importing patterns: {e}")
        print(f"✗ Import failed: {e}")
        sys.exit(1)

    print()
