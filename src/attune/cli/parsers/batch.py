"""Argument parser for batch processing commands.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


def register_parsers(subparsers):
    """Register batch command parsers.

    Args:
        subparsers: Subparser object from main argument parser

    Returns:
        None: Adds batch subparser with submit, status, results, wait subcommands
    """
    from ..commands.batch import (
        cmd_batch_results,
        cmd_batch_status,
        cmd_batch_submit,
        cmd_batch_wait,
    )

    # Main batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Batch processing via Anthropic Batch API (50%% cost savings)",
        description="Submit and manage batch processing jobs for non-urgent tasks",
    )

    # Batch subcommands
    batch_subparsers = batch_parser.add_subparsers(dest="batch_command", required=True)

    # batch submit command
    submit_parser = batch_subparsers.add_parser(
        "submit",
        help="Submit a batch processing job from JSON file",
        description="Submit batch requests for asynchronous processing (50% cost savings)",
    )

    submit_parser.add_argument(
        "input_file",
        help='JSON file with batch requests. Format: [{"task_id": "...", "task_type": "...", "input_data": {...}}]',
    )

    submit_parser.set_defaults(func=cmd_batch_submit)

    # batch status command
    status_parser = batch_subparsers.add_parser(
        "status",
        help="Check status of a batch processing job",
        description="Display current status and request counts for a batch",
    )

    status_parser.add_argument(
        "batch_id",
        help="Batch ID (e.g., msgbatch_abc123)",
    )

    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON status",
    )

    status_parser.set_defaults(func=cmd_batch_status)

    # batch results command
    results_parser = batch_subparsers.add_parser(
        "results",
        help="Retrieve results from completed batch",
        description="Download and save batch results to JSON file",
    )

    results_parser.add_argument(
        "batch_id",
        help="Batch ID (e.g., msgbatch_abc123)",
    )

    results_parser.add_argument(
        "output_file",
        help="Path to output JSON file",
    )

    results_parser.set_defaults(func=cmd_batch_results)

    # batch wait command
    wait_parser = batch_subparsers.add_parser(
        "wait",
        help="Wait for batch to complete and retrieve results",
        description="Poll batch status until completion, then download results",
    )

    wait_parser.add_argument(
        "batch_id",
        help="Batch ID (e.g., msgbatch_abc123)",
    )

    wait_parser.add_argument(
        "output_file",
        help="Path to output JSON file",
    )

    wait_parser.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        help="Seconds between status checks (default: 300 = 5 minutes)",
    )

    wait_parser.add_argument(
        "--timeout",
        type=int,
        default=86400,
        help="Maximum wait time in seconds (default: 86400 = 24 hours)",
    )

    wait_parser.set_defaults(func=cmd_batch_wait)
