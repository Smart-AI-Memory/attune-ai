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
    import sys

    from attune.cli_commands._exit_codes import (
        EXIT_CLI_ERROR,
        EXIT_SUCCESS,
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

    # Spend gate (collaboration-gates Phase 1) — guard the first
    # billable run of the session. Free/local runs never reach it
    # (R8): a ``--no-llm`` run makes no billable call. The gate's own
    # off switch (``ATTUNE_SPEND_GATE=off`` / ``ATTUNE_MAX_BUDGET_USD=0``)
    # short-circuits to proceed. ``record_cost`` stays False unless an
    # enforced (non-disabled) envelope is in play, so the off path and
    # ``--no-llm`` never touch the envelope store.
    record_cost = False
    if not getattr(args, "no_llm", False):
        from attune.gates.spend_gate import (
            ACTION_BLOCK,
            ACTION_CONFIRM,
            evaluate_spend_gate,
        )

        depth = input_data.get("depth", "standard")
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
        decision = evaluate_spend_gate(name, depth, interactive=interactive)

        if decision.action == ACTION_BLOCK:
            _print_spend_block(decision)
            return EXIT_SUCCESS
        if decision.action == ACTION_CONFIRM:
            if not _confirm_spend(decision):
                print("Skipped — no workflow run, no charge.")
                return EXIT_SUCCESS
            _authorize_envelope(decision)
        # Record actual cost into the envelope only when the gate is
        # enforced (a real dollar-capped window), never on the off path.
        record_cost = not decision.envelope.disabled

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
        on_result=_record_envelope_cost if record_cost else None,
    )


def _confirm_spend(decision: object) -> bool:
    """Prompt the user to authorize the session spend window.

    Returns True on an explicit yes. A breach decision (the run would
    exceed an already-authorized envelope) is framed as "proceed
    anyway."
    """
    breach = getattr(decision, "breach_usd", 0.0)
    framing = getattr(decision, "framing", "")
    if breach > 0:
        print(
            f"\n💰 Spend gate — this run would exceed your session spend "
            f"envelope (over by ${breach:.2f})."
        )
        print(f"   {framing}")
        prompt = "Proceed anyway? [y/N]: "
    else:
        print("\n💰 Spend gate — first paid run of this session.")
        print(f"   {framing}")
        print(
            "   Proceeding authorizes this session's spend window (~5h); "
            "later runs won't re-prompt."
        )
        prompt = "Proceed? [y/N]: "
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def _print_spend_block(decision: object) -> None:
    """Explain a non-interactive block and name the env override (D10)."""
    print("\n🚫 Spend gate — not spending silently in a non-interactive run.")
    print(f"   {getattr(decision, 'framing', '')}")
    print(
        "   To allow: set ATTUNE_SPEND_GATE_AUTHORIZED=1 (or "
        "ATTUNE_SPEND_GATE=off to disable the gate)."
    )


def _authorize_envelope(decision: object) -> None:
    """Mark the decision's envelope authorized and persist it.

    Establishes the session spend window after an explicit yes so
    subsequent runs within the window proceed silently (R3).
    """
    from attune.gates.envelope import save_envelope

    envelope = getattr(decision, "envelope", None)
    if envelope is None:
        return
    envelope.authorized = True
    save_envelope(envelope)


def _record_envelope_cost(result: object) -> None:
    """Record a completed run's actual cost into the session envelope (R4).

    Best-effort: reads ``result.cost_report.total_cost`` and adds it to
    the live envelope. Subscription-mode runs report ``$0`` and are a
    no-op. Never raises into the caller (the runner guards it too).
    """
    import time

    from attune.gates.envelope import load_envelope, save_envelope

    cost_report = getattr(result, "cost_report", None)
    cost = float(getattr(cost_report, "total_cost", 0.0) or 0.0)
    if cost <= 0:
        return
    envelope = load_envelope()
    if envelope is None or envelope.is_expired(time.time()):
        return
    envelope.record(cost)
    save_envelope(envelope)


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
