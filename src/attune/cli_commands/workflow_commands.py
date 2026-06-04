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

    workflows = list_workflows()

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
    import os

    from attune.cli_commands._exit_codes import (
        EXIT_CLI_ERROR,
        run_workflow_with_exit_code,
    )
    from attune.security.path_validation import _validate_file_path
    from attune.workflows import get_workflow

    name = args.name

    if getattr(args, "cheap", False):
        os.environ["ATTUNE_AGENT_MODEL_DEFAULT"] = "haiku"
        print(
            "💸 --cheap mode: ATTUNE_AGENT_MODEL_DEFAULT=haiku for this run "
            "(opus/sonnet-pinned subagents unaffected)"
        )

    # CLI-level errors (workflow not found, bad JSON, bad path) exit 3 —
    # distinct from workflow-execution outcomes (0/1/2). See the
    # workflow-failure-exit-propagation spec.
    try:
        workflow_cls = get_workflow(name)
    except KeyError:
        print(f"❌ Workflow not found: {name}")
        return EXIT_CLI_ERROR

    # Parse input if provided
    input_data = {}
    if args.input:
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON input: {e}")
            return EXIT_CLI_ERROR

    # Add common options with validation
    if args.path:
        try:
            # Validate path to prevent path traversal attacks
            validated_path = _validate_file_path(args.path)
            input_data["path"] = str(validated_path)
        except ValueError as e:
            print(f"❌ Invalid path: {e}")
            return EXIT_CLI_ERROR
    if args.target:
        input_data["target"] = args.target

    # Discovery-sweep flags (no-op for workflows that don't accept them
    # since execute() takes **kwargs — extra keys are dropped silently).
    if getattr(args, "verbose", False):
        input_data["verbose"] = True
    if getattr(args, "no_llm", False):
        input_data["no_llm"] = True
    if getattr(args, "source", None):
        input_data["source"] = args.source
    if getattr(args, "depth", None):
        input_data["depth"] = args.depth
    if getattr(args, "json", False):
        # Let workflows that honor it render their own JSON via
        # ``final_output`` rather than the generic ``json.dumps(result)``
        # at the bottom of this function (which produces awkward output
        # for nested dataclasses).
        input_data["output_format"] = "json"

    print(f"\n🚀 Running workflow: {name}\n")

    # Execution outcomes map to exit codes via the centralized
    # contract: success -> 0, WorkflowResult.success is False -> 1,
    # uncaught exception -> 2 (traceback to stderr).
    return run_workflow_with_exit_code(
        workflow_cls,
        input_data,
        name=name,
        json_mode=bool(getattr(args, "json", False)),
        print_result=lambda result: _print_workflow_result(result, workflow_name=name),
    )


def _print_workflow_result(
    result: object,
    workflow_name: str = "unknown",
) -> None:
    """Print a workflow result using the unified voice layer.

    Routes through attune.voice.format_output() for consistent
    personality, formatting, and contextual next-step suggestions.

    Args:
        result: Workflow execution result (WorkflowResult, dict, or other)
        workflow_name: Name of the workflow that produced this result

    """
    from attune.voice import format_output

    print(format_output(workflow_name, result))
    _emit_run_meta_for_daemon(result)


def _emit_run_meta_for_daemon(result: object) -> None:
    """Emit ``ATTUNE_RUN_META`` side-channel lines when the ops daemon
    has opted in via ``ATTUNE_RUN_META_EMIT=1``.

    Reads ``sdk_stderr`` / ``sdk_error_kind`` from
    ``result.metadata`` (set by ``BaseWorkflow._error_result()``
    during SDK subprocess failure) and writes them as base64-encoded
    + plain-text stdout lines that the runner parses. Silent no-op
    when the env var isn't set, when ``result`` doesn't carry
    metadata, or when neither field is populated.

    Part of the ``docs/specs/sdk-error-message-fidelity/`` Phase 3b
    flow. The side-channel design (rather than calling into runner
    APIs directly) keeps the CLI process decoupled from the daemon —
    the CLI just emits structured stdout, the daemon parses what it
    cares about.
    """
    from attune.ops import run_meta_stdout

    if not run_meta_stdout.is_emission_enabled():
        return
    metadata = getattr(result, "metadata", None)
    if not isinstance(metadata, dict):
        return
    kind = metadata.get("sdk_error_kind")
    stderr_text = metadata.get("sdk_stderr")
    if not kind and not stderr_text:
        return
    # Emit version line first so the parser knows what grammar it's
    # reading. Cheap; downstream consumer ignores it after the version
    # check.
    run_meta_stdout.emit_version_line()
    if kind:
        run_meta_stdout.emit_field_line("sdk_error_kind", str(kind))
    if stderr_text:
        encoded = run_meta_stdout.encode_stderr(str(stderr_text))
        if encoded:
            run_meta_stdout.emit_field_line("sdk_stderr_b64", encoded)
