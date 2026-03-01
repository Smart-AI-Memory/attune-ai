"""Tests for hook registry."""

import pytest

from attune.hooks.config import HookConfig, HookDefinition, HookEvent, HookMatcher
from attune.hooks.registry import HookRegistry


class TestHookRegistry:
    """Tests for HookRegistry."""

    def test_create_empty_registry(self):
        """Test creating an empty registry."""
        registry = HookRegistry()

        assert registry.config.enabled is True
        assert len(registry._python_handlers) == 0

    def test_load_config(self):
        """Test loading configuration."""
        config = HookConfig(enabled=True, log_executions=False)
        registry = HookRegistry()

        registry.load_config(config)

        assert registry.config.log_executions is False

    def test_register_handler(self):
        """Test registering a Python handler."""
        registry = HookRegistry()

        def my_handler(**context):
            return "handled"

        handler_id = registry.register(
            event=HookEvent.SESSION_START,
            handler=my_handler,
            description="Test handler",
        )

        assert handler_id is not None
        assert my_handler.__name__ in handler_id
        assert registry._python_handlers[handler_id] == my_handler

    def test_unregister_handler(self):
        """Test unregistering a handler."""
        registry = HookRegistry()

        def my_handler(**context):
            pass

        handler_id = registry.register(
            event=HookEvent.SESSION_START,
            handler=my_handler,
        )

        assert registry.unregister(handler_id) is True
        assert handler_id not in registry._python_handlers

        # Unregistering again should return False
        assert registry.unregister(handler_id) is False

    def test_get_matching_hooks(self):
        """Test getting matching hooks."""
        registry = HookRegistry()

        # Add a hook that matches Edit on .py files
        registry.config.add_hook(
            event=HookEvent.POST_TOOL_USE,
            hook=HookDefinition(command="format:python"),
            matcher=HookMatcher(tool="Edit", file_pattern=r"\.py$"),
        )

        # Add a hook that matches all
        registry.config.add_hook(
            event=HookEvent.POST_TOOL_USE,
            hook=HookDefinition(command="log:all"),
            matcher=HookMatcher(match_all=True),
        )

        # Should match both
        matches = registry.get_matching_hooks(
            HookEvent.POST_TOOL_USE,
            {"tool": "Edit", "file_path": "test.py"},
        )
        assert len(matches) == 2

        # Should only match wildcard
        matches = registry.get_matching_hooks(
            HookEvent.POST_TOOL_USE,
            {"tool": "Read", "file_path": "test.js"},
        )
        assert len(matches) == 1
        assert matches[0][1].command == "log:all"

    def test_disabled_config_returns_no_hooks(self):
        """Test that disabled config returns no matching hooks."""
        config = HookConfig(enabled=False)
        config.add_hook(
            event=HookEvent.SESSION_START,
            hook=HookDefinition(command="test"),
        )

        registry = HookRegistry(config=config)

        matches = registry.get_matching_hooks(HookEvent.SESSION_START, {})
        assert len(matches) == 0

    def test_get_stats(self):
        """Test registry statistics."""
        registry = HookRegistry()

        def handler1(**ctx):
            pass

        def handler2(**ctx):
            pass

        registry.register(HookEvent.SESSION_START, handler1)
        registry.register(HookEvent.SESSION_END, handler2)

        stats = registry.get_stats()

        assert stats["enabled"] is True
        assert stats["total_hooks"] == 2
        assert stats["python_handlers"] == 2
        assert stats["total_executions"] == 0

    def test_execution_log(self):
        """Test execution logging."""
        registry = HookRegistry()

        # Manually add to execution log (simulating execution)
        registry._execution_log.append(
            {
                "event": "SessionStart",
                "hook": "test:main",
                "success": True,
            },
        )
        registry._execution_log.append(
            {
                "event": "SessionEnd",
                "hook": "test:end",
                "success": False,
            },
        )

        log = registry.get_execution_log()
        assert len(log) == 2

        # Filter by event
        log = registry.get_execution_log(event_filter=HookEvent.SESSION_START)
        assert len(log) == 1
        assert log[0]["event"] == "SessionStart"

        # Clear log
        registry.clear_execution_log()
        assert len(registry.get_execution_log()) == 0


@pytest.mark.asyncio
class TestHookRegistryAsync:
    """Async tests for HookRegistry."""

    async def test_fire_with_python_handler(self):
        """Test firing hooks with registered Python handlers."""
        registry = HookRegistry()
        call_count = {"value": 0}

        def increment_handler(**context):
            call_count["value"] += 1
            return {"handled": True}

        registry.register(
            event=HookEvent.SESSION_START,
            handler=increment_handler,
        )

        results = await registry.fire(HookEvent.SESSION_START, {"session_id": "test"})

        assert len(results) == 1
        assert results[0]["success"] is True
        assert call_count["value"] == 1

    async def test_fire_no_matching_hooks(self):
        """Test firing when no hooks match."""
        registry = HookRegistry()

        results = await registry.fire(HookEvent.STOP, {})

        assert results == []

    async def test_fire_with_context(self):
        """Test that context is passed to handlers."""
        registry = HookRegistry()
        received_context = {}

        def capture_context(**context):
            received_context.update(context)

        registry.register(
            event=HookEvent.PRE_TOOL_USE,
            handler=capture_context,
            matcher=HookMatcher(match_all=True),
        )

        await registry.fire(
            HookEvent.PRE_TOOL_USE,
            {"tool": "Bash", "command": "ls"},
        )

        assert received_context["tool"] == "Bash"
        assert received_context["command"] == "ls"

    async def test_fire_multiple_hooks(self):
        """Test firing multiple matching hooks."""
        registry = HookRegistry()
        results_order = []

        def handler_a(**ctx):
            results_order.append("a")

        def handler_b(**ctx):
            results_order.append("b")

        registry.register(
            event=HookEvent.SESSION_START,
            handler=handler_a,
            priority=1,
        )
        registry.register(
            event=HookEvent.SESSION_START,
            handler=handler_b,
            priority=10,  # Higher priority, should run first
        )

        await registry.fire(HookEvent.SESSION_START, {})

        assert results_order == ["b", "a"]
