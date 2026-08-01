"""Behavioral coverage for HookExecutor branches not exercised elsewhere.

Complements test_hook_coverage.py (failure-branch tests) and
test_executor_webhook_security.py (SSRF prevention). This file targets the
remaining reachable-but-uncovered lines in src/attune/hooks/executor.py when
the test suite is scoped to tests/unit/hooks: async fire-and-forget mode,
timeout handling, hook-type dispatch (webhook + unknown type), COMMAND
success/KeyError branches, PYTHON format/prefix/import/getattr branches,
the async-handler path through _call_handler, the remaining WEBHOOK
sub-branches (aiohttp missing, non-2xx status, non-JSON body), and the
HookExecutorSync wrapper.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.hooks.config import HookDefinition, HookType
from attune.hooks.executor import HookExecutor, HookExecutorSync


def _make_hook(cmd: str, htype: HookType = HookType.COMMAND, **kwargs) -> HookDefinition:
    return HookDefinition(command=cmd, type=htype, **kwargs)


# ---------------------------------------------------------------------------
# execute() — async fire-and-forget mode, timeout, dispatch branches
# ---------------------------------------------------------------------------


class TestExecuteDispatchBranches:
    @pytest.mark.asyncio
    async def test_async_execution_schedules_and_returns_immediately(self):
        """async_execution=True fires the task and returns without waiting."""
        call_log: list[str] = []

        async def handler(**context):
            call_log.append("ran")

        executor = HookExecutor(python_handlers={"bg": handler})
        hook = _make_hook("bg", HookType.PYTHON, async_execution=True)

        result = await executor.execute(hook, {})

        assert result["success"] is True
        assert result["async"] is True
        assert result["duration_ms"] == 0
        # Fire-and-forget: handler has not necessarily run yet.
        assert call_log == []

        # Give the scheduled task a chance to complete.

        await asyncio.sleep(0.05)
        assert call_log == ["ran"]

    @pytest.mark.asyncio
    async def test_timeout_returns_error_dict(self):
        """A hook exceeding its timeout returns success=False, never raises.

        Deterministic by construction: patches asyncio.wait_for to raise
        TimeoutError directly rather than racing a real sleep against a
        real timeout, which is flaky under coverage instrumentation (the
        instrumentation slows execution enough that asyncio's internal
        cancel-and-wait cleanup can surface asyncio.CancelledError instead
        of the expected asyncio.TimeoutError, escaping the module's
        `except Exception` clause since CancelledError is a BaseException).
        """

        async def noop(**context):
            return None

        executor = HookExecutor(python_handlers={"noop": noop})
        hook = _make_hook("noop", HookType.PYTHON, timeout=1)

        with patch(
            "attune.hooks.executor.asyncio.wait_for",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            result = await executor.execute(hook, {})

        assert result["success"] is False
        assert "timed out" in result["error"].lower()
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_webhook_type_dispatches_to_execute_webhook(self):
        """HookType.WEBHOOK is routed through execute() to _execute_webhook."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})

        mock_session = MagicMock()
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_post_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        executor = HookExecutor()
        hook = _make_hook("https://hooks.example.com/notify", HookType.WEBHOOK)

        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch("aiohttp.ClientSession", return_value=mock_session_cm),
        ):
            result = await executor.execute(hook, {"event": "test"})

        assert result["success"] is True
        assert result["output"] == {"ok": True}

    @pytest.mark.asyncio
    async def test_unknown_hook_type_returns_error_dict(self):
        """A hook.type outside {COMMAND, PYTHON, WEBHOOK} is reported, not raised."""
        executor = HookExecutor()
        hook = _make_hook("irrelevant", HookType.COMMAND)
        # HookDefinition has no validate_assignment config, so this bypasses
        # enum validation to reach the executor's own defensive branch.
        hook.type = "bogus-type"

        result = await executor.execute(hook, {})

        assert result["success"] is False
        assert "Unknown hook type" in result["error"]


# ---------------------------------------------------------------------------
# _execute_command — success and KeyError branches
# ---------------------------------------------------------------------------


class TestExecuteCommandBranches:
    @pytest.mark.asyncio
    async def test_command_success_returns_stdout(self):
        executor = HookExecutor()
        hook = _make_hook("echo hello-command", HookType.COMMAND)

        result = await executor.execute(hook, context={})

        assert result["success"] is True
        assert "hello-command" in result["output"]

    @pytest.mark.asyncio
    async def test_command_missing_context_variable_returns_error_dict(self):
        executor = HookExecutor()
        hook = _make_hook("echo {missing_var}", HookType.COMMAND)

        result = await executor.execute(hook, context={})

        assert result["success"] is False
        assert "missing_var" in result["error"]


# ---------------------------------------------------------------------------
# _execute_python — format/prefix validation, real import, async handler
# ---------------------------------------------------------------------------


class TestExecutePythonBranches:
    @pytest.mark.asyncio
    async def test_missing_colon_returns_error_dict(self):
        executor = HookExecutor()
        hook = _make_hook("no_colon_here", HookType.PYTHON)

        result = await executor.execute(hook, context={})

        assert result["success"] is False
        assert "module.path:function" in result["error"]

    @pytest.mark.asyncio
    async def test_disallowed_module_prefix_returns_error_dict(self):
        """Only attune.* modules may be imported; others must go through handlers."""
        executor = HookExecutor()
        hook = _make_hook("os.path:exists", HookType.PYTHON)

        result = await executor.execute(hook, context={})

        assert result["success"] is False
        assert "not in allowed prefixes" in result["error"]

    @pytest.mark.asyncio
    async def test_real_attune_module_import_and_getattr_succeed(self):
        """An attune.*-prefixed module:function resolves via import + getattr."""
        executor = HookExecutor()
        # HookExecutor itself is a legitimate attune.* symbol; calling it with
        # no context kwargs succeeds (python_handlers defaults to None).
        hook = _make_hook("attune.hooks.executor:HookExecutor", HookType.PYTHON)

        result = await executor.execute(hook, context={})

        assert result["success"] is True
        assert isinstance(result["output"], HookExecutor)

    @pytest.mark.asyncio
    async def test_registered_async_handler_runs_via_call_handler(self):
        """A registered async handler is awaited directly (coroutine branch)."""

        async def async_handler(**context):
            return {"async": True, "input": context.get("input")}

        executor = HookExecutor(python_handlers={"async_id": async_handler})
        hook = _make_hook("async_id", HookType.PYTHON)

        result = await executor.execute(hook, {"input": 7})

        assert result["success"] is True
        assert result["output"] == {"async": True, "input": 7}


# ---------------------------------------------------------------------------
# _execute_webhook — remaining sub-branches
# ---------------------------------------------------------------------------


class TestExecuteWebhookBranches:
    @pytest.mark.asyncio
    async def test_missing_aiohttp_raises_import_error(self, monkeypatch):
        """If aiohttp cannot be imported, a clear ImportError is raised."""
        executor = HookExecutor()

        # Standard trick to force `import aiohttp` to raise ImportError even
        # though the real package is installed: a None entry in sys.modules
        # makes the import machinery fail immediately.
        monkeypatch.setitem(sys.modules, "aiohttp", None)

        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            pytest.raises(ImportError, match="aiohttp required for webhook hooks"),
        ):
            await executor._execute_webhook("https://hooks.example.com/notify", {})

    @pytest.mark.asyncio
    async def test_non_2xx_status_raises_runtime_error(self):
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        mock_session = MagicMock()
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_post_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        executor = HookExecutor()

        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch("aiohttp.ClientSession", return_value=mock_session_cm),
            pytest.raises(RuntimeError, match="Webhook failed with status 500"),
        ):
            await executor._execute_webhook("https://hooks.example.com/notify", {})

    @pytest.mark.asyncio
    async def test_non_json_response_falls_back_to_text(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=ValueError("not valid json"))
        mock_response.text = AsyncMock(return_value="plain text body")

        mock_session = MagicMock()
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_post_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        executor = HookExecutor()

        with (
            patch("attune.monitoring.validators._resolve_and_check_ip"),
            patch("aiohttp.ClientSession", return_value=mock_session_cm),
        ):
            result = await executor._execute_webhook(
                "https://hooks.example.com/notify",
                {},
            )

        assert result == {"status": 200, "text": "plain text body"}


# ---------------------------------------------------------------------------
# HookExecutorSync — constructor and sync execute()
# ---------------------------------------------------------------------------


class TestHookExecutorSyncWrapper:
    def test_sync_wrapper_constructs_and_executes(self):
        def handler(**context):
            return {"sync": True, "input": context.get("input")}

        executor = HookExecutorSync(python_handlers={"h": handler})
        hook = _make_hook("h", HookType.PYTHON)

        result = executor.execute(hook, {"input": 3})

        assert result["success"] is True
        assert result["output"] == {"sync": True, "input": 3}
