"""Exit-code contract for ``attune workflow run``.

Centralizes the mapping from a workflow's execution outcome to the
process exit code, so every CLI entry point that runs a workflow
agrees on what each code means. See
``docs/specs/workflow-failure-exit-propagation/``.

The contract (decisions.md):

- ``0`` — workflow ran AND ``WorkflowResult.success is True``
- ``1`` — workflow ran AND ``WorkflowResult.success is False``
  (planned failure)
- ``2`` — workflow ran AND raised an uncaught exception
  (unplanned failure); the traceback is printed to stderr
- ``3`` — CLI-level error (workflow not found, bad path, bad JSON)

CLI-level errors (exit ``3``) are detected by the caller *before*
``execute()`` is reached, so this module only owns the ``0``/``1``/``2``
boundary plus the ``EXIT_CLI_ERROR`` constant the caller returns.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from collections.abc import Callable
from typing import Any

from attune.workflows.validation import WorkflowValidationError

logger = logging.getLogger(__name__)

# Exit-code contract — see module docstring / decisions.md.
EXIT_SUCCESS = 0
EXIT_PLANNED_FAILURE = 1
EXIT_UNPLANNED_FAILURE = 2
EXIT_CLI_ERROR = 3


def _is_planned_failure(result: Any) -> bool:
    """Return True only when the result carries an explicit
    ``success is False``.

    Legacy workflows return plain ``dict`` / ``str`` / ``None`` with no
    ``success`` attribute — those are treated as success (exit ``0``),
    preserving backwards compatibility. Only a real ``WorkflowResult``
    (or any object exposing ``success``) can trip the planned-failure
    branch.
    """
    return getattr(result, "success", None) is False


def _sdk_error_kind(result: Any) -> str | None:
    """Extract the classified SDK failure kind from result metadata.

    Populated by ``BaseWorkflow._error_result()`` on SDK subprocess
    failures (see the sdk-error-message-fidelity spec). Returns None
    when absent.
    """
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict):
        kind = metadata.get("sdk_error_kind")
        if kind:
            return str(kind)
    return None


def _coerce_json_dict(result: Any) -> dict[str, Any] | None:
    """Return a mutable dict to print in ``--json`` mode, or None.

    Prefers the workflow's own JSON object rendered in
    ``final_output`` (when it honored ``output_format="json"``);
    falls back to the result itself when it is already a dict. Returns
    None when the result isn't dict-shaped, signalling the caller to
    wrap it in an envelope instead.
    """
    final_output = getattr(result, "final_output", None)
    if isinstance(final_output, str) and final_output.lstrip().startswith("{"):
        try:
            obj = json.loads(final_output)
        except (json.JSONDecodeError, ValueError):
            obj = None
        if isinstance(obj, dict):
            return obj
    if isinstance(result, dict):
        # Copy so we never mutate the caller's object when injecting
        # the contract fields below.
        return dict(result)
    return None


def _emit_json_result(result: Any, *, exit_code: int) -> None:
    """Print the workflow's JSON output, threading ``exit_code`` and
    ``sdk_error_kind`` so CI consumers parsing stdout JSON don't also
    have to branch on ``$?``.

    ``$?`` remains authoritative — these fields are a convenience
    mirror. The output always contains a single ``{...}`` object so
    last-brace extractors (e.g. ``.github/workflows/security-scan.yml``)
    keep working.
    """
    sdk_error_kind = _sdk_error_kind(result)
    payload = _coerce_json_dict(result)
    if payload is not None:
        payload.setdefault("exit_code", exit_code)
        payload.setdefault("sdk_error_kind", sdk_error_kind)
        print(json.dumps(payload, indent=2, default=str))
        return
    # Non-dict result (string / dataclass / list) — wrap in an
    # envelope that always carries the contract fields.
    print(
        json.dumps(
            {
                "exit_code": exit_code,
                "success": not _is_planned_failure(result),
                "sdk_error_kind": sdk_error_kind,
                "result": result,
            },
            indent=2,
            default=str,
        )
    )


def run_workflow_with_exit_code(
    workflow_cls: type,
    input_data: dict[str, Any],
    *,
    name: str,
    json_mode: bool,
    print_result: Callable[[Any], None],
    on_result: Callable[[Any], None] | None = None,
) -> int:
    """Instantiate + execute a workflow and return the contract exit code.

    Centralizes the ``0``/``1``/``2`` classification:

    - any uncaught exception (including from the constructor or
      ``execute()``) → ``EXIT_UNPLANNED_FAILURE`` (2), traceback to
      stderr;
    - ``WorkflowResult.success is False`` → ``EXIT_PLANNED_FAILURE`` (1);
    - otherwise → ``EXIT_SUCCESS`` (0).

    Args:
        workflow_cls: The workflow class (instantiated here so
            constructor failures are classified as exit 2).
        input_data: kwargs forwarded to ``execute()``.
        name: Workflow name, for log/voice messages.
        json_mode: When True, emit JSON to stdout (threading the
            exit code + sdk_error_kind); otherwise call
            ``print_result``.
        print_result: Callback rendering the human-readable
            voice-layer output (injected to avoid an import cycle and
            to preserve the ops daemon side-channel emission).
        on_result: Optional side-effect callback invoked with the
            result after a (non-exception) run, in both json and
            human modes — used by the spend gate to record the run's
            actual cost into the session envelope (R4). Wrapped in a
            best-effort guard so it can never alter the exit code.

    Returns:
        The process exit code (0, 1, or 2).
    """
    try:
        workflow = workflow_cls()
        if asyncio.iscoroutinefunction(workflow.execute):
            result = asyncio.run(workflow.execute(**input_data))
        else:
            result = workflow.execute(**input_data)
    except WorkflowValidationError as exc:
        # Malformed INPUT is a CLI-level error, not a workflow crash:
        # name every failing field cleanly, no traceback (Task 1 of
        # docs/specs/workflow-intake-forms/ — schemas now validate).
        logger.info("Workflow %r rejected its input: %s", name, exc)
        print(f"❌ Invalid input for workflow '{name}':")
        for err in getattr(exc, "errors", None) or [str(exc)]:
            print(f"  - {err}")
        return EXIT_CLI_ERROR
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: any uncaught error from the workflow is the
        # exit-2 "unplanned failure" branch. Traceback to stderr so
        # operators/scripts see the real cause; voiced summary to
        # stdout for humans.
        logger.exception("Workflow %r raised an uncaught exception", name)
        traceback.print_exc()
        from attune.voice import format_error

        print(format_error(str(exc), workflow_name=name))
        return EXIT_UNPLANNED_FAILURE

    exit_code = EXIT_PLANNED_FAILURE if _is_planned_failure(result) else EXIT_SUCCESS

    if json_mode:
        _emit_json_result(result, exit_code=exit_code)
    else:
        print_result(result)

    if on_result is not None:
        try:
            on_result(result)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: the post-run hook (spend-gate cost record)
            # is best-effort; a failure here must never change the
            # exit-code contract.
            logger.exception("on_result hook failed for workflow %r", name)

    return exit_code
