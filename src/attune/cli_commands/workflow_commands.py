"""Workflow CLI commands.

Commands for listing, inspecting, and running workflows.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import re
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
    from attune.workflows import get_workflow

    name = args.name

    if getattr(args, "cheap", False):
        os.environ["ATTUNE_AGENT_MODEL_DEFAULT"] = "haiku"
        print(
            "💸 --cheap mode: ATTUNE_AGENT_MODEL_DEFAULT=haiku for this run "
            "(opus/sonnet-pinned subagents unaffected)"
        )

    # CLI-level errors (workflow not found, bad JSON, bad path, no auth,
    # spend-gate block) exit 3 — distinct from workflow-execution
    # outcomes (0/1/2). See the workflow-failure-exit-propagation spec.
    try:
        workflow_cls = get_workflow(name)
    except KeyError:
        print(f"❌ Workflow not found: {name}")
        return EXIT_CLI_ERROR

    input_data, input_error = _build_input_data(args)
    if input_error is not None:
        return input_error

    record_cost = False
    if not getattr(args, "no_llm", False):
        # Auth pre-flight (setup-friction F1/F4) — BEFORE the spend
        # gate, so a machine with no auth path at all gets one clean
        # sentence instead of (a) a spend warning about dollars it
        # cannot spend, then (b) an SDK traceback.
        preflight_error = _auth_preflight()
        if preflight_error:
            print(preflight_error)
            return EXIT_CLI_ERROR

        gate_exit, record_cost = _spend_gate_check(name, input_data.get("depth", "standard"))
        if gate_exit is not None:
            return gate_exit

    print(f"\n🚀 Running workflow: {name}\n")

    # Execution outcomes map to exit codes via the centralized
    # contract: success -> 0, WorkflowResult.success is False -> 1,
    # uncaught exception -> 2 (traceback to stderr).
    return run_workflow_with_exit_code(
        workflow_cls,
        input_data,
        name=name,
        json_mode=bool(getattr(args, "json", False)),
        print_result=lambda result: _print_workflow_result(
            result,
            workflow_name=name,
            verbose=bool(getattr(args, "verbose", False)),
        ),
        on_result=_record_envelope_cost if record_cost else None,
    )


def _build_input_data(args: Namespace) -> tuple[dict, int | None]:
    """Assemble the ``execute()`` kwargs from the CLI arguments.

    Returns ``(input_data, None)`` on success, or ``(input_data,
    exit_code)`` when a CLI-level input error (bad JSON, bad path) was
    already printed and the caller should return that code.
    """
    from attune.cli_commands._exit_codes import EXIT_CLI_ERROR
    from attune.security.path_validation import _validate_file_path

    input_data: dict = {}
    if args.input:
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON input: {e}")
            return input_data, EXIT_CLI_ERROR

    # Add common options with validation
    if args.path:
        try:
            # Validate path to prevent path traversal attacks
            validated_path = _validate_file_path(args.path)
            input_data["path"] = str(validated_path)
        except ValueError as e:
            print(f"❌ Invalid path: {e}")
            return input_data, EXIT_CLI_ERROR
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
        # printed by the exit-code layer (which produces awkward output
        # for nested dataclasses).
        input_data["output_format"] = "json"
    return input_data, None


def _spend_gate_check(name: str, depth: str) -> tuple[int | None, bool]:
    """Run the spend gate (collaboration-gates Phase 1) for one run.

    Guards the first billable run of the session. Free/local runs never
    reach it (R8): a ``--no-llm`` run makes no billable call. The
    gate's own off switch (``ATTUNE_SPEND_GATE=off`` /
    ``ATTUNE_MAX_BUDGET_USD=0``) short-circuits to proceed.

    Returns ``(exit_code, record_cost)``: a non-``None`` exit code means
    the caller returns it without running the workflow (block → 3 so a
    refused run is never green on exit-code consumers like the ops
    dashboard chips; interactive decline → 0, an explicit user choice).
    ``record_cost`` is True only when an enforced (non-disabled)
    envelope is in play, so the off path never touches the envelope
    store.
    """
    import sys

    from attune.cli_commands._exit_codes import EXIT_CLI_ERROR, EXIT_SUCCESS
    from attune.gates.spend_gate import (
        ACTION_BLOCK,
        ACTION_CONFIRM,
        evaluate_spend_gate,
    )

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    decision = evaluate_spend_gate(name, depth, interactive=interactive)

    if decision.action == ACTION_BLOCK:
        _print_spend_block(decision)
        return EXIT_CLI_ERROR, False
    if decision.action == ACTION_CONFIRM:
        if not _confirm_spend(decision):
            print("Skipped — no workflow run, no charge.")
            return EXIT_SUCCESS, False
        _authorize_envelope(decision)
    # Record actual cost into the envelope only when the gate is
    # enforced (a real dollar-capped window), never on the off path.
    return None, not decision.envelope.disabled


def _auth_preflight() -> str | None:
    """Return an actionable error when no LLM auth evidence exists.

    CLI *presence* can't be the test — ``claude-agent-sdk`` ships a
    bundled ``claude`` binary, so one always exists after
    ``pip install attune-ai``. What distinguishes a machine that can
    run workflows from a fresh one is evidence of *credentials*:

    - ``ANTHROPIC_API_KEY`` in the environment, or
    - ``CLAUDE_CODE_OAUTH_TOKEN`` in the environment, or
    - a ``~/.claude`` directory — Claude Code has been run (and
      possibly logged in) on this machine at least once. Existence
      only; the directory is never read (macOS keeps credentials in
      the Keychain, so requiring a credentials *file* would
      false-positive on logged-in Macs).

    Conservative by design: any evidence passes, and a stale/logged-
    out state still fails later with the SdkSubprocessError guidance.
    Only the nothing-at-all machine is blocked here, before the spend
    gate can warn it about dollars it cannot spend (setup-friction
    F1/F4).
    """
    import os
    from pathlib import Path

    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return None
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip():
        return None
    if (Path.home() / ".claude").exists():
        return None

    return (
        "\n🔑 No auth found — workflows make LLM calls and need one "
        "of these:\n"
        "   - Claude Code (subscription): install it "
        "(npm install -g @anthropic-ai/claude-code), run `claude` "
        "once to log in, then re-run this workflow.\n"
        "   - API key: export ANTHROPIC_API_KEY=... and re-run.\n"
        "   For guided configuration: attune auth setup\n"
        "   Setup fight you? https://github.com/Smart-AI-Memory/"
        "attune-ai/discussions/1325"
    )


def _confirm_spend(decision: object) -> bool:
    """Prompt the user to authorize the session spend window.

    Returns True on an explicit yes. An exhausted-window decision (the
    session has spent its authorized budget) is framed as "extend it."
    """
    breach = getattr(decision, "breach_usd", 0.0)
    framing = getattr(decision, "framing", "")
    if breach > 0:
        print(
            f"\n💰 Spend gate — this session's spend window is used up " f"(over by ${breach:.2f})."
        )
        print(f"   {framing}")
        prompt = "Extend the window and proceed? [y/N]: "
    else:
        print("\n💰 Spend gate — first paid run of this session.")
        print(f"   {framing}")
        print(
            "   Proceeding authorizes this session's spend window (~5h); "
            "later runs proceed silently until the budget is used up."
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


# Matches the renderer's exact <details> shape (report_renderer.render):
# <details><summary>{title}</summary>\n\n{body}\n\n</details>
_DETAILS_BLOCK_RE = re.compile(
    r"<details><summary>(?P<title>.*?)</summary>\n\n.*?\n\n</details>",
    re.DOTALL,
)


def _collapse_details_for_terminal(text: str) -> str:
    """Replace ``<details>`` blocks with a run-with-verbose hint.

    Terminals have no collapsibles, and ``rich.markdown`` renders
    straight through the HTML tags (the "collapsed" content would show
    anyway) — so summary mode swaps each block for a one-line pointer.
    MCP and the dashboard keep the raw ``<details>`` markdown.
    """
    return _DETAILS_BLOCK_RE.sub(
        lambda m: f'*(section "{m.group("title")}" collapsed — run with --verbose to expand)*',
        text,
    )


def _print_workflow_result(
    result: object,
    workflow_name: str = "unknown",
    verbose: bool = False,
) -> None:
    """Print a workflow result using the unified voice layer.

    Routes through attune.voice.format_output() for consistent
    personality, formatting, and contextual next-step suggestions.
    Results carrying a serialized ``WorkflowReport`` render as styled
    markdown on a TTY (``rich.markdown``); everything else keeps the
    plain text path unchanged.

    Args:
        result: Workflow execution result (WorkflowResult, dict, or other)
        workflow_name: Name of the workflow that produced this result
        verbose: Render the full report (detail sections inline) instead
            of the summary view

    """
    import sys

    from attune.voice import format_output
    from attune.voice.formatter import _is_report_result

    is_report = _is_report_result(result)
    text = format_output(
        workflow_name,
        result,
        disclosure="full" if verbose else "summary",
    )
    if is_report and not verbose:
        text = _collapse_details_for_terminal(text)

    printed = False
    if is_report and sys.stdout.isatty():
        try:
            from rich.console import Console
            from rich.markdown import Markdown

            Console().print(Markdown(text))
            printed = True
        except Exception:  # noqa: BLE001
            # INTENTIONAL: terminal styling is best-effort — fall back
            # to plain text rather than lose the report.
            logger.debug("rich markdown rendering failed", exc_info=True)
    if not printed:
        print(text)
    _emit_run_meta_for_daemon(result)


def _emit_run_meta_for_daemon(result: object) -> None:
    """Emit ``ATTUNE_RUN_META`` side-channel lines when the ops daemon
    has opted in via ``ATTUNE_RUN_META_EMIT=1``.

    Reads ``sdk_stderr`` / ``sdk_error_kind`` from
    ``result.metadata`` (set by ``BaseWorkflow._error_result()``
    during SDK subprocess failure) and writes them as base64-encoded
    + plain-text stdout lines that the runner parses. When
    ``result.final_output`` carries a serialized ``WorkflowReport``
    (the ``_type`` discriminator), it is also emitted as a
    ``report_b64`` line so the dashboard's run view can render a
    structured report panel (workflow-result-formatting T6). Silent
    no-op when the env var isn't set or when nothing is emittable.

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
    kind = metadata.get("sdk_error_kind") if isinstance(metadata, dict) else None
    stderr_text = metadata.get("sdk_stderr") if isinstance(metadata, dict) else None

    from attune.workflows.output import WorkflowReport

    final_output = getattr(result, "final_output", None)
    report_encoded = ""
    if WorkflowReport.is_report_dict(final_output):
        report_encoded = run_meta_stdout.encode_report(final_output)  # type: ignore[arg-type]

    if not kind and not stderr_text and not report_encoded:
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
    if report_encoded:
        run_meta_stdout.emit_field_line("report_b64", report_encoded)
