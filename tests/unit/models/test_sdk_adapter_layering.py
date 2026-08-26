"""Layering receipts for #2239 — the models layer imports nothing upward.

Two properties, each of which fails loudly on regression:

1. ``attune.models`` never imports ``attune.workflows``: importing the
   adapter core, ``single_turn``, ``empathy_executor``, and the package
   root must load zero workflows modules. These are the two cycle edges
   the layering work removed (slice 1 = the SDK adapter, Edge 1 =
   ``empathy_executor``'s ``WorkflowConfig`` read, inverted to a
   constructor-injected ``dict[str, str]`` per spec R1) — a reintroduced
   upward import fails here in a clean subprocess, immune to import-order
   luck in the test session.
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
import attune.models
import attune.models.sdk_adapter
import attune.models.single_turn
import attune.models.empathy_executor
loaded = sorted(m for m in sys.modules if m.startswith("attune.workflows"))
if loaded:
    raise SystemExit(f"attune.workflows leaked into attune.models: {loaded}")
print("clean")
"""


@pytest.mark.unit
def test_models_sdk_adapter_imports_no_workflows_modules() -> None:
    """Importing the models layer loads no workflows module.

    Covers both former cycle edges: the SDK adapter core (slice 1) and
    ``empathy_executor`` (Edge 1). ``attune.models`` itself is imported
    too, so a new upward import anywhere the package root re-exports is
    caught, not just in the three named modules.
    """
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


@pytest.mark.unit
def test_no_models_module_imports_workflows_at_any_scope() -> None:
    """No module under ``attune/models/`` imports ``attune.workflows`` — at
    any scope, including function-local.

    The subprocess probe above only observes what a module import LOADS, so
    it is blind to a lazy function-local import: both #2239 cycle edges were
    exactly that shape, and both would pass it. Verified by mutation
    2026-08-26 — reinstating the original lazy ``_load_hybrid_config`` left
    the subprocess probe green. This static scan is the guard that actually
    fails on the regression the spec cares about; the subprocess probe stays
    because it additionally proves the eager import graph is clean.
    """
    import ast
    from pathlib import Path

    models_dir = Path(__file__).resolve().parents[3] / "src" / "attune" / "models"
    assert models_dir.is_dir(), models_dir

    offenders: list[str] = []
    for path in sorted(models_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "attune.workflows" or alias.name.startswith(
                        "attune.workflows."
                    ):
                        offenders.append(f"{path.name}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                # Absolute: from attune.workflows... import X
                if (
                    node.level == 0
                    and node.module
                    and (
                        node.module == "attune.workflows"
                        or node.module.startswith("attune.workflows.")
                    )
                ):
                    offenders.append(f"{path.name}:{node.lineno} from {node.module}")
                # Relative escaping models/ into a sibling workflows package:
                # from ..workflows import X  (level >= 2 from attune.models.*)
                elif node.level >= 2 and (node.module or "").startswith("workflows"):
                    dots = "." * node.level
                    offenders.append(f"{path.name}:{node.lineno} from {dots}{node.module}")

    assert not offenders, (
        "attune.models must not import attune.workflows (#2239 layering). "
        f"Offenders: {offenders}"
    )
