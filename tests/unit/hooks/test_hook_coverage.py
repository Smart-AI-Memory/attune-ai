"""Tests for uncovered branches in hooks/executor.py, config.py, registry.py."""

from __future__ import annotations

import pytest
import yaml

from attune.hooks.config import (
    HookConfig,
    HookDefinition,
    HookEvent,
    HookType,
)
from attune.hooks.executor import HookExecutor
from attune.hooks.registry import HookRegistry


def _make_hook(cmd: str, htype: HookType = HookType.COMMAND) -> HookDefinition:
    return HookDefinition(command=cmd, type=htype)


# ---------------------------------------------------------------------------
# HookConfig.from_yaml / to_yaml
# ---------------------------------------------------------------------------


class TestHookConfigYaml:
    def test_from_yaml_missing_file_returns_empty_config(self, tmp_path):
        cfg = HookConfig.from_yaml(str(tmp_path / "nonexistent.yaml"))
        assert isinstance(cfg, HookConfig)
        # Default HookConfig has all event keys with empty lists
        assert all(isinstance(v, list) for v in cfg.hooks.values())

    def test_from_yaml_loads_hooks(self, tmp_path):
        data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": {"match_all": True},
                        "hooks": [{"command": "echo hi", "type": "command"}],
                        "priority": 0,
                    }
                ]
            }
        }
        f = tmp_path / "hooks.yaml"
        f.write_text(yaml.safe_dump(data))
        cfg = HookConfig.from_yaml(str(f))
        assert "PreToolUse" in cfg.hooks

    def test_to_yaml_writes_readable_file(self, tmp_path):
        cfg = HookConfig()
        out = tmp_path / "out.yaml"
        cfg.to_yaml(str(out))
        loaded = yaml.safe_load(out.read_text())
        assert isinstance(loaded, dict)

    def test_to_yaml_blocks_system_path(self):
        cfg = HookConfig()
        with pytest.raises(ValueError):
            cfg.to_yaml("/etc/attune-hooks.yaml")


# ---------------------------------------------------------------------------
# HookExecutor — failure branches
# ---------------------------------------------------------------------------


class TestHookExecutorFailureBranches:
    @pytest.mark.asyncio
    async def test_command_non_zero_exit_returns_error_dict(self):
        """A shell command that exits non-zero returns success=False (never raises)."""
        executor = HookExecutor()
        hook = _make_hook("sh -c 'exit 1'", HookType.COMMAND)

        result = await executor.execute(hook, context={})
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_python_handler_import_error_returns_error_dict(self):
        """A PYTHON hook with bad module path returns success=False (never raises)."""
        executor = HookExecutor()
        hook = _make_hook("attune.nonexistent_submodule:fn", HookType.PYTHON)

        result = await executor.execute(hook, context={})
        assert result["success"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# HookRegistry — fire_sync and exception handling
# ---------------------------------------------------------------------------


class TestHookRegistryFireSync:
    def test_fire_sync_runs_python_handler(self):
        """fire_sync (no running event loop) executes a Python callable hook."""
        registry = HookRegistry()

        def my_handler(**context) -> dict:
            return {"success": True, "output": "ok"}

        registry.register(HookEvent.PRE_TOOL_USE, my_handler)
        results = registry.fire_sync(HookEvent.PRE_TOOL_USE, context={})
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["success"] is True

    @pytest.mark.asyncio
    async def test_fire_command_hook_failure_captured(self):
        """A failing COMMAND hook records the error without raising (on_error=log)."""
        registry = HookRegistry()
        # Add a command hook directly through config to use on_error="log"
        from attune.hooks.config import HookMatcher, HookRule

        hook_def = HookDefinition(
            command="sh -c 'exit 42'",
            type=HookType.COMMAND,
            on_error="log",
        )
        rule = HookRule(
            matcher=HookMatcher(match_all=True),
            hooks=[hook_def],
        )
        registry.config.hooks[HookEvent.PRE_TOOL_USE.value].append(rule)

        results = await registry.fire(HookEvent.PRE_TOOL_USE, context={})
        # Error captured — result has success=False and error field
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "error" in results[0]

    @pytest.mark.asyncio
    async def test_fire_propagates_exception_when_on_error_raise(self):
        """on_error='raise' re-raises when the executor itself raises (not a dict)."""
        from unittest.mock import AsyncMock, patch

        registry = HookRegistry()
        from attune.hooks.config import HookMatcher, HookRule

        hook_def = HookDefinition(
            command="sh -c 'exit 1'",
            type=HookType.COMMAND,
            on_error="raise",
        )
        rule = HookRule(
            matcher=HookMatcher(match_all=True),
            hooks=[hook_def],
        )
        registry.config.hooks[HookEvent.PRE_TOOL_USE.value].append(rule)

        # Force the executor to raise (bypassing its internal catch) to exercise
        # the registry's on_error="raise" re-raise path (registry.py:222-223)
        with patch(
            "attune.hooks.executor.HookExecutor.execute",
            new=AsyncMock(side_effect=RuntimeError("forced failure")),
        ):
            with pytest.raises(RuntimeError, match="forced failure"):
                await registry.fire(HookEvent.PRE_TOOL_USE, context={})
