"""CLI for test generator.

Usage:
    python -m test_generator.cli generate soap_note --patterns linear_flow,approval,structured_fields
    python -m test_generator.cli analyze soap_note --patterns linear_flow,approval

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import argparse
import heapq
import json
import logging
import sys
from pathlib import Path

from attune.security.path_validation import _validate_file_path

from .generator import TestGenerator
from .risk_analyzer import RiskAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_generate(args):
    """Generate tests for a workflow.

    Args:
        args: Command line arguments

    """
    workflow_id = args.workflow_id
    pattern_ids = args.patterns.split(",") if args.patterns else []

    logger.info(f"Generating tests for workflow: {workflow_id}")
    logger.info(f"Patterns: {', '.join(pattern_ids)}")

    # Generate tests
    generator = TestGenerator()
    tests = generator.generate_tests(
        workflow_id=workflow_id,
        pattern_ids=pattern_ids,
        workflow_module=args.module,
        workflow_class=args.workflow_class,
    )

    # Determine output directory
    output_dir = Path(args.output) if args.output else Path("tests/unit/workflows")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write unit tests (utf-8 explicit for Windows cp1252 default)
    unit_test_file = output_dir / f"test_{workflow_id}_workflow.py"
    validated_unit_test = _validate_file_path(str(unit_test_file))
    with open(validated_unit_test, "w", encoding="utf-8") as f:
        f.write(tests["unit"])
    logger.info(f"✓ Unit tests written to: {validated_unit_test}")

    # Write integration tests (if generated)
    if tests["integration"]:
        integration_test_file = (
            output_dir.parent.parent / "integration" / f"test_{workflow_id}_integration.py"
        )
        integration_test_file.parent.mkdir(parents=True, exist_ok=True)
        validated_integration = _validate_file_path(str(integration_test_file))
        with open(validated_integration, "w", encoding="utf-8") as f:
            f.write(tests["integration"])
        logger.info(f"✓ Integration tests written to: {validated_integration}")

    # Write fixtures
    fixtures_file = output_dir / f"fixtures_{workflow_id}.py"
    validated_fixtures = _validate_file_path(str(fixtures_file))
    with open(validated_fixtures, "w", encoding="utf-8") as f:
        f.write(tests["fixtures"])
    logger.info(f"✓ Fixtures written to: {validated_fixtures}")

    print("\n🎉 Test generation complete!")
    print("\nGenerated files:")
    print(f"  - {unit_test_file}")
    if tests["integration"]:
        print(f"  - {integration_test_file}")
    print(f"  - {fixtures_file}")

    print("\nNext steps:")
    print("  1. Review generated tests")
    print(f"  2. Run tests: pytest {unit_test_file}")
    print("  3. Add custom test cases as needed")


def cmd_analyze(args):
    """Analyze workflow risk and show recommendations.

    Args:
        args: Command line arguments

    """
    workflow_id = args.workflow_id
    pattern_ids = args.patterns.split(",") if args.patterns else []

    logger.info(f"Analyzing workflow: {workflow_id}")

    # Perform risk analysis
    analyzer = RiskAnalyzer()
    analysis = analyzer.analyze(workflow_id, pattern_ids)

    # Display results
    print(f"\n{'=' * 60}")
    print(f"Risk Analysis: {workflow_id}")
    print(f"{'=' * 60}\n")

    print(f"Patterns Used: {len(analysis.pattern_ids)}")
    for pid in analysis.pattern_ids:
        print(f"  - {pid}")

    print(f"\nCritical Paths: {len(analysis.critical_paths)}")
    for path in analysis.critical_paths:
        print(f"  - {path}")

    print(f"\nHigh-Risk Inputs: {len(analysis.high_risk_inputs)}")
    for input_risk in analysis.high_risk_inputs[:5]:  # Top 5
        print(f"  - {input_risk}")

    print(f"\nValidation Points: {len(analysis.validation_points)}")
    for validation in analysis.validation_points[:5]:  # Top 5
        print(f"  - {validation}")

    print(f"\n{'=' * 60}")
    print(f"Recommended Test Coverage: {analysis.recommended_coverage}%")
    print(f"{'=' * 60}\n")

    print("Test Priorities:")
    for test_name, priority in heapq.nsmallest(
        10,
        analysis.test_priorities.items(),
        key=lambda x: x[1],
    ):
        priority_label = {
            1: "CRITICAL",
            2: "HIGH",
            3: "MEDIUM",
            4: "LOW",
            5: "OPTIONAL",
        }.get(priority, "UNKNOWN")
        print(f"  [{priority_label:8}] {test_name}")

    # JSON output if requested
    if args.json:
        json_output = analysis.to_dict()
        json_file = Path(f"{workflow_id}_risk_analysis.json")
        validated_json = _validate_file_path(str(json_file))
        with open(validated_json, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2)
        print(f"\n✓ JSON output written to: {validated_json}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test Generator for Attune Workflow Factory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate tests for SOAP Note workflow
  %(prog)s generate soap_note --patterns linear_flow,approval,structured_fields

  # Analyze risk for debugging workflow
  %(prog)s analyze debugging --patterns code_analysis_input,risk_assessment

  # Generate with custom module/class
  %(prog)s generate my_workflow --patterns linear_flow --module workflows.my_workflow --class MyWorkflow

  # Output to custom directory
  %(prog)s generate soap_note --patterns linear_flow --output tests/custom/
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate tests for a workflow")
    gen_parser.add_argument("workflow_id", help="Workflow identifier (e.g., soap_note)")
    gen_parser.add_argument(
        "--patterns",
        required=True,
        help="Comma-separated pattern IDs (e.g., linear_flow,approval)",
    )
    gen_parser.add_argument(
        "--module",
        help="Python module path (e.g., workflows.soap_note)",
    )
    gen_parser.add_argument(
        "--class",
        dest="workflow_class",
        help="Workflow class name (e.g., SOAPNoteWorkflow)",
    )
    gen_parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: tests/unit/workflows/)",
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze workflow risk")
    analyze_parser.add_argument("workflow_id", help="Workflow identifier")
    analyze_parser.add_argument(
        "--patterns",
        required=True,
        help="Comma-separated pattern IDs",
    )
    analyze_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON file with analysis results",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
