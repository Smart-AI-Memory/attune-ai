"""CLI for workflow scaffolding.

Usage:
    python -m scaffolding create my_workflow --domain healthcare
    python -m scaffolding create my_workflow --interactive

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_create(args):
    """Create a new workflow using specified methodology.

    Args:
        args: Command line arguments

    """
    workflow_name = args.name
    domain = args.domain or "general"
    workflow_type = args.type or "domain"
    methodology = args.methodology or "pattern"

    print(f"\n{'=' * 60}")
    print(f"Creating Workflow: {workflow_name}")
    print(f"{'=' * 60}\n")
    print(f"Domain: {domain}")
    print(f"Type: {workflow_type}")
    print(f"Methodology: {methodology}")
    print()

    # Lazy imports — patterns package is a dev-time dependency at the project root
    from patterns import get_pattern_registry

    from .methodologies.pattern_compose import PatternCompose

    # Get pattern recommendations
    registry = get_pattern_registry()
    recommended = registry.recommend_for_workflow(
        workflow_type=workflow_type,
        domain=domain,
    )

    print(f"Recommended Patterns ({len(recommended)}):")
    for i, pattern in enumerate(recommended, 1):
        print(f"  {i}. {pattern.name} - {pattern.description[:60]}...")

    # Pattern selection
    if args.patterns:
        # User provided patterns
        selected_patterns = args.patterns.split(",")
    elif args.interactive:
        # Interactive selection
        print("\nSelect patterns (comma-separated numbers, or 'all' for all):")
        selection = input("> ").strip()

        if selection.lower() == "all":
            selected_patterns = [p.id for p in recommended]
        else:
            try:
                indices = [int(i.strip()) - 1 for i in selection.split(",")]
                selected_patterns = [recommended[i].id for i in indices]
            except (ValueError, IndexError):
                print("Invalid selection. Using all patterns.")
                selected_patterns = [p.id for p in recommended]
    else:
        # Use all recommended
        selected_patterns = [p.id for p in recommended]

    print(f"\nUsing {len(selected_patterns)} patterns:")
    for pid in selected_patterns:
        print(f"  - {pid}")

    # Create workflow using selected methodology
    print(f"\nCreating workflow with {methodology} methodology...")

    if methodology == "pattern":
        method = PatternCompose()
        result = method.create_workflow(
            name=workflow_name,
            domain=domain,
            workflow_type=workflow_type,
            selected_patterns=selected_patterns,
        )
    else:
        print(f"Unknown methodology: {methodology}")
        sys.exit(1)

    # Display results
    print(f"\n{'=' * 60}")
    print("✅ Workflow Created Successfully!")
    print(f"{'=' * 60}\n")

    print("Generated Files:")
    for file_path in result["files"]:
        print(f"  - {file_path}")

    print("\nPatterns Used:")
    for pattern_name in result.get("patterns", selected_patterns):
        print(f"  - {pattern_name}")

    print("\nNext Steps:")
    for step in result["next_steps"]:
        print(f"  {step}")

    print()


def cmd_list_patterns(args):
    """List available patterns.

    Args:
        args: Command line arguments

    """
    from patterns import get_pattern_registry
    from patterns.core import PatternCategory

    registry = get_pattern_registry()

    print(f"\n{'=' * 60}")
    print("Available Patterns")
    print(f"{'=' * 60}\n")

    for category in PatternCategory:
        patterns = registry.list_by_category(category)
        if not patterns:
            continue

        print(f"{category.value.upper()} ({len(patterns)} patterns):")
        for pattern in patterns:
            print(
                f"  - {pattern.id:25} | {pattern.name:20} | Reusability: {pattern.reusability_score:.2f}"
            )
        print()

    stats = registry.get_statistics()
    print(f"Total: {stats['total_patterns']} patterns")
    print(f"Average Reusability: {stats['average_reusability']:.2f}")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Workflow Scaffolding for Attune AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create healthcare workflow (recommended approach)
  %(prog)s create patient_intake --domain healthcare

  # Interactive pattern selection
  %(prog)s create my_workflow --interactive --domain legal

  # Specify patterns manually
  %(prog)s create my_workflow --patterns linear_flow,approval,structured_fields

  # List available patterns
  %(prog)s list-patterns
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new workflow")
    create_parser.add_argument("name", help="Workflow name (e.g., patient_intake)")
    create_parser.add_argument(
        "--domain",
        "-d",
        help="Domain (e.g., healthcare, finance, legal)",
    )
    create_parser.add_argument(
        "--type",
        "-t",
        choices=["domain", "coach", "ai"],
        help="Workflow type (default: domain)",
    )
    create_parser.add_argument(
        "--methodology",
        "-m",
        choices=["pattern"],
        help="Methodology (default: pattern)",
    )
    create_parser.add_argument(
        "--patterns",
        "-p",
        help="Comma-separated pattern IDs",
    )
    create_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive pattern selection",
    )

    # List patterns command
    subparsers.add_parser("list-patterns", help="List available patterns")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "create":
        cmd_create(args)
    elif args.command == "list-patterns":
        cmd_list_patterns(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
