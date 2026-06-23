"""Non-mocked guard for the MCP-handler → workflow ``execute`` contract.

The handler unit tests mock ``execute`` (AsyncMock), which means they
verify *which kwargs the handler passes* but never that the workflow's
real ``execute`` actually *reads* those kwargs. That gap let a whole
class of bug ship: the v4.2.0 SDK migration changed several workflow
``execute`` signatures to ``(path, depth)``, but the MCP handlers kept
passing the pre-migration kwargs (``module_path``, ``source_code`` /
``doc_type`` / ``audience``, ``project_root``). The stale kwargs were
silently dropped, ``path`` was empty, and every call failed with
"path argument is required" — yet the mocked tests stayed green.

These tests call the REAL ``execute`` (no mocking) with the legacy
kwargs and assert it still fails fast on the missing ``path``. That
proves ``path`` is the required scope kwarg, so a handler that passes
anything else is broken. The path gate returns before any Agent SDK /
LLM call, so these tests are cheap and make no network calls.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.doc_audit import DocAuditWorkflow
from attune.workflows.document_gen import DocumentGenerationWorkflow
from attune.workflows.test_gen import TestGenerationWorkflow


@pytest.mark.parametrize(
    "workflow_cls",
    [TestGenerationWorkflow, DocumentGenerationWorkflow, DocAuditWorkflow],
)
@pytest.mark.asyncio
async def test_execute_reads_path_not_legacy_kwargs(workflow_cls):
    """Real ``execute`` requires ``path`` and ignores the legacy kwargs.

    Passing every pre-migration kwarg the broken handlers used to send
    must STILL fail with "path argument is required" — that is exactly
    the failure users hit, and the receipt that those kwargs are dead.
    """
    result = await workflow_cls().execute(
        module_path="/x",
        source_code="def f(): pass",
        doc_type="api_reference",
        audience="developers",
        project_root="/x",
    )

    assert result.success is False
    assert "path argument is required" in (result.error or "")


@pytest.mark.parametrize(
    "workflow_cls",
    [TestGenerationWorkflow, DocumentGenerationWorkflow, DocAuditWorkflow],
)
@pytest.mark.asyncio
async def test_execute_path_gate_passes_with_path(workflow_cls):
    """A non-empty ``path`` clears the gate (no 'path argument is required').

    We do not run the workflow to completion (that needs the Agent SDK);
    we only assert that *with* ``path`` the early required-arg gate no
    longer fires — i.e. the kwarg the handlers now pass is the right one.
    The SDK call is stubbed so no network/LLM work happens.
    """
    workflow = workflow_cls()

    async def _stub(*_args, **_kwargs):
        # Minimal AgentRunResult-shaped stub so execute can build a result.
        from attune.workflows.agent_sdk_adapter import AgentRunResult

        return AgentRunResult(result_text="stub")

    # Each workflow's SDK call lives in a private _run_agent_* method that
    # runs AFTER the path gate. Stub whichever this workflow has.
    for attr in ("_run_agent_gen", "_run_agent_audit"):
        if hasattr(workflow, attr):
            setattr(workflow, attr, _stub)

    result = await workflow.execute(path="src/")

    # The point is only that the required-arg gate did not fire.
    assert "path argument is required" not in (result.error or "")
