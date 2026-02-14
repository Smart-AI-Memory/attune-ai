"""Parser definitions for workflow commands.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from ..commands import workflow


def register_parsers(subparsers):
    """Register workflow command parsers.

    Args:
        subparsers: ArgumentParser subparsers object from main parser
    """
    # Main workflow command - multi-model workflow management
    parser_workflow = subparsers.add_parser(
        "workflow",
        help="Multi-model workflows for cost-optimized task pipelines",
    )
    parser_workflow.add_argument(
        "action",
        choices=["list", "describe", "run", "config"],
        help="Action: list, describe, run, or config",
    )
    parser_workflow.add_argument(
        "name",
        nargs="?",
        help="Workflow name (for describe/run)",
    )
    parser_workflow.add_argument(
        "--input",
        "-i",
        help="JSON input data for workflow execution",
    )
    parser_workflow.add_argument(
        "--provider",
        "-p",
        choices=["anthropic", "openai", "google", "ollama", "hybrid"],
        default=None,  # None means use config
        help="Model provider: anthropic, openai, google, ollama, or hybrid (mix of best models)",
    )
    parser_workflow.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing config file",
    )
    parser_workflow.add_argument("--json", action="store_true", help="Output as JSON")
    parser_workflow.add_argument(
        "--use-recommended-tier",
        action="store_true",
        help="Enable intelligent tier fallback: start with CHEAP tier and automatically upgrade if quality gates fail",
    )
    parser_workflow.add_argument(
        "--write-tests",
        action="store_true",
        help="(test-gen workflow) Write generated tests to disk",
    )
    parser_workflow.add_argument(
        "--output-dir",
        default="tests/generated",
        help="(test-gen workflow) Output directory for generated tests",
    )
    parser_workflow.add_argument(
        "--health-score-threshold",
        type=int,
        default=95,
        help="(health-check workflow) Minimum health score required (0-100, default: 95 for very strict quality)",
    )
    parser_workflow.set_defaults(func=workflow.cmd_workflow)

    # Legacy workflow-setup command (DEPRECATED)
    parser_workflow_setup = subparsers.add_parser(
        "workflow-setup",
        help="[DEPRECATED] Interactive setup wizard (use 'attune init' instead)",
    )
    parser_workflow_setup.set_defaults(func=workflow.cmd_workflow_legacy)
