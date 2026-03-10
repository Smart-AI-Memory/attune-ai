"""Workflow CLI commands.

Commands for listing, inspecting, and running workflows.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

logger = logging.getLogger(__name__)


def cmd_workflow_list(args: Namespace) -> int:
    """List available workflows."""
    from attune.workflows import list_workflows

    show_all = getattr(args, "all", False)
    workflows = list_workflows(show_all=show_all)

    print("\n📋 Available Workflows\n")
    print("-" * 60)

    if not workflows:
        print("No workflows registered.")
        return 0

    for wf in sorted(workflows, key=lambda w: w["name"]):
        name = wf["name"]
        description = wf["description"]
        engine = wf.get("engine", "")
        tag = ""
        if engine == "sdk":
            tag = " [SDK]"
        elif engine == "api":
            tag = " [API]"
        print(f"  {name:25} {description}{tag}")

    print("-" * 60)
    print(f"\nTotal: {len(workflows)} workflows")
    print("\nRun a workflow: attune workflow run <name>")
    return 0


def cmd_workflow_info(args: Namespace) -> int:
    """Show workflow details."""
    from attune.workflows import get_workflow

    name = args.name
    try:
        workflow_cls = get_workflow(name)
    except KeyError:
        print(f"❌ Workflow not found: {name}")
        return 1
    print(f"\n📋 Workflow: {name}\n")
    print("-" * 60)

    # Show docstring
    if workflow_cls.__doc__:
        print(workflow_cls.__doc__)

    # Show input schema if available
    if hasattr(workflow_cls, "input_schema"):
        print("\nInput Schema:")
        print(json.dumps(workflow_cls.input_schema, indent=2))

    print("-" * 60)
    return 0


def cmd_workflow_run(args: Namespace) -> int:
    """Execute a workflow."""
    import asyncio

    from attune.security.path_validation import _validate_file_path
    from attune.workflows import get_workflow, is_using_api_fallback

    name = args.name

    try:
        workflow_cls = get_workflow(name)
    except KeyError:
        print(f"❌ Workflow not found: {name}")
        return 1

    # Warn if falling back to API version
    if is_using_api_fallback(name):
        print(
            f"⚠️  Using API version of '{name}'. "
            "Install claude-agent-sdk for the enhanced Agent SDK version:\n"
            "    pip install claude-agent-sdk\n"
        )

    # Parse input if provided
    input_data = {}
    if args.input:
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON input: {e}")
            return 1

    # Add common options with validation
    if args.path:
        try:
            # Validate path to prevent path traversal attacks
            validated_path = _validate_file_path(args.path)
            input_data["path"] = str(validated_path)
        except ValueError as e:
            print(f"❌ Invalid path: {e}")
            return 1
    if args.target:
        input_data["target"] = args.target

    print(f"\n🚀 Running workflow: {name}\n")

    try:
        workflow = workflow_cls()

        # Run the workflow
        if asyncio.iscoroutinefunction(workflow.execute):
            result = asyncio.run(workflow.execute(**input_data))
        else:
            result = workflow.execute(**input_data)

        # Output result
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            _print_workflow_result(result)

        return 0

    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception(f"Workflow failed: {e}")
        print(f"\n❌ Workflow failed: {e}")
        return 1


def _print_workflow_result(result: object) -> None:
    """Print a workflow result in a human-readable format.

    Handles WorkflowResult dataclass objects by extracting the formatted
    report and cost summary. Falls back to dict iteration or repr for
    other result types.

    Args:
        result: Workflow execution result (WorkflowResult, dict, or other)

    """
    from attune.workflows.data_classes import WorkflowResult

    if isinstance(result, WorkflowResult):
        # Print formatted report if available in final_output
        if isinstance(result.final_output, dict):
            report = result.final_output.get("formatted_report")
            if report:
                print(f"\n{report}")
            else:
                # No formatted report — show key fields from final_output
                print("\n✅ Workflow completed\n")
                for key, value in result.final_output.items():
                    if not isinstance(value, dict | list):
                        print(f"  {key}: {value}")
        elif result.final_output is not None:
            print("\n✅ Workflow completed\n")
            print(f"  {result.final_output}")
        else:
            print("\n✅ Workflow completed (no output)")

        # Print cost and duration summary
        cr = result.cost_report
        print(f"\n{'─' * 60}")
        print(f"  Cost: ${cr.total_cost:.4f}", end="")
        if cr.savings_percent > 0:
            print(f"  (saved {cr.savings_percent:.0f}% vs premium)")
        else:
            print()
        print(f"  Duration: {result.total_duration_ms / 1000:.1f}s")
        if not result.success:
            print(f"  Error: {result.error}")
        print()

    elif isinstance(result, dict):
        print("\n✅ Workflow completed\n")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print(f"\n✅ Result: {result}")
