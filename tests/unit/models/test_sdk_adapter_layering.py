"""Layering receipts for #2239 slice 1 — the SDK adapter's models-layer home.

Two properties, each of which fails loudly on regression:

1. ``attune.models`` never imports ``attune.workflows``: importing the
   adapter core (and ``single_turn``, its models-layer consumer) must
   load zero workflows modules. This is the cycle edge the slice
   removed — a reintroduced upward import fails here in a clean
   subprocess, immune to import-order luck in the test session.
2. The back-compat surfaces (``attune.workflows.agent_sdk_adapter``
   facade, ``attune.workflows.sdk_errors`` shim) re-export the SAME
   objects as the defining modules. A facade that drifts to a copy or
   a stub silently vacates monkeypatches (#2162) — identity is the
   guard.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import subprocess
import sys

import pytest

_PROBE = """
import sys
import attune.models.sdk_adapter
import attune.models.single_turn
loaded = sorted(m for m in sys.modules if m.startswith("attune.workflows"))
if loaded:
    raise SystemExit(f"attune.workflows leaked into attune.models: {loaded}")
print("clean")
"""


@pytest.mark.unit
def test_models_sdk_adapter_imports_no_workflows_modules() -> None:
    """Importing the adapter core + single_turn loads no workflows module."""
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "clean" in result.stdout


@pytest.mark.unit
def test_workflows_facade_re_exports_defining_objects() -> None:
    """Every facade binding IS the defining module's object (not a copy)."""
    import attune.models.sdk_adapter as core
    import attune.models.sdk_errors as errors
    import attune.workflows.agent_sdk_adapter as facade
    import attune.workflows.sdk_errors as errors_shim
    import attune.workflows.sdk_output_parser as parser

    for name in (
        "SDK_SUBPROCESS_ENV_VAR",
        "AgentRunResult",
        "build_result_text",
        "collect_agent_output",
        "collect_subagent_transcripts",
        "format_subagent_transcripts_markdown",
        "get_max_budget_usd",
        "get_subagent_model",
        "get_task_budget",
        "get_thinking_config",
        "iter_agent_messages",
        "make_edit_scope_guard",
        "resolve_cwd_for_path",
        "sdk_isolation_kwargs",
    ):
        assert getattr(facade, name) is getattr(core, name), name

    for name in (
        "SdkErrorKind",
        "SdkSubprocessError",
        "capture_subprocess_failure",
        "classify_subprocess_failure",
        "sdk_error_from_exception",
        "sdk_error_message",
    ):
        assert getattr(facade, name) is getattr(errors, name), name
        assert getattr(errors_shim, name) is getattr(errors, name), name

    assert facade.AgentSDKResultAdapter is parser.AgentSDKResultAdapter


@pytest.mark.unit
def test_facade_does_not_re_export_the_mutable_probe_cache() -> None:
    """``_CLI_SUPPORTS_TASK_BUDGET`` is a mutable cache — a re-exported
    snapshot would silently go stale, so the facade must not carry it."""
    import attune.workflows.agent_sdk_adapter as facade

    assert not hasattr(facade, "_CLI_SUPPORTS_TASK_BUDGET")
