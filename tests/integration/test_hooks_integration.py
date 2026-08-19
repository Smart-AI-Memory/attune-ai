"""Integration tests for the hooks module.

Tests hook system integration with other framework components.
"""

import pytest

from attune.hooks.config import (
    HookConfig,
    HookDefinition,
    HookEvent,
    HookMatcher,
    HookType,
)
from attune.hooks.registry import HookRegistry


class TestHookRegistryIntegration:
    """Integration tests for HookRegistry."""

    def test_register_and_fire_python_hook(self):
        """Test registering and firing a Python function hook."""
        registry = HookRegistry()
        results = []

        # Note: Hook handlers receive keyword arguments, not positional context dict
        def my_handler(**kwargs):
            results.append(kwargs.get("value", "default"))
            return {"success": True, "output": "handled"}

        # Register
        handler_id = registry.register(
            event=HookEvent.SESSION_START,
            handler=my_handler,
            description="Test handler",
        )

        assert handler_id is not None

        # Fire
        execution_results = registry.fire_sync(
            HookEvent.SESSION_START,
            context={"value": "test123"},
        )

        assert len(execution_results) == 1
        assert execution_results[0]["success"] is True
        assert results == ["test123"]

    def test_hook_matching_with_tool_filter(self):
        """Test hook matching with tool-specific filters."""
        config = HookConfig()

        # Add hook for Edit tool only
        config.add_hook(
            event=HookEvent.PRE_TOOL_USE,
            hook=HookDefinition(
                type=HookType.PYTHON,
                command="test_handler",
                description="Edit hook",
            ),
            matcher=HookMatcher(tool="Edit"),
        )

        registry = HookRegistry(config=config)

        # Should match Edit
        matches = registry.get_matching_hooks(
            HookEvent.PRE_TOOL_USE,
            {"tool": "Edit", "file_path": "/test.py"},
        )
        assert len(matches) == 1

        # Should not match Bash
        matches = registry.get_matching_hooks(
            HookEvent.PRE_TOOL_USE,
            {"tool": "Bash", "command": "ls"},
        )
        assert len(matches) == 0

    def test_hook_matching_with_file_pattern(self):
        """Test hook matching with file pattern filters."""
        config = HookConfig()

        # Add hook for Python files only
        config.add_hook(
            event=HookEvent.POST_TOOL_USE,
            hook=HookDefinition(
                type=HookType.PYTHON,
                command="python_handler",
            ),
            matcher=HookMatcher(file_pattern=r"\.py$"),
        )

        registry = HookRegistry(config=config)

        # Should match .py files
        matches = registry.get_matching_hooks(
            HookEvent.POST_TOOL_USE,
            {"file_path": "/src/module.py"},
        )
        assert len(matches) == 1

        # Should not match .js files
        matches = registry.get_matching_hooks(
            HookEvent.POST_TOOL_USE,
            {"file_path": "/src/module.js"},
        )
        assert len(matches) == 0

    def test_multiple_hooks_priority_order(self):
        """Test that hooks fire in priority order."""
        config = HookConfig()

        # Add hooks with different priorities
        for priority, name in [(10, "high"), (0, "normal"), (5, "medium")]:
            config.add_hook(
                event=HookEvent.SESSION_START,
                hook=HookDefinition(
                    type=HookType.PYTHON,
                    command=f"handler_{name}",
                    description=f"{name} priority",
                ),
                priority=priority,
            )

        registry = HookRegistry(config=config)

        # Get hooks - should be sorted by priority (high first)
        hooks = registry.get_matching_hooks(HookEvent.SESSION_START, {})

        # Verify order: high (10), medium (5), normal (0)
        assert len(hooks) == 3
        priorities = [rule.priority for rule, _ in hooks]
        assert priorities == [10, 5, 0]

    def test_hook_unregister(self):
        """Test unregistering hooks."""
        registry = HookRegistry()

        def handler(ctx):
            return {"success": True}

        handler_id = registry.register(
            event=HookEvent.SESSION_END,
            handler=handler,
        )

        # Verify registered
        matches = registry.get_matching_hooks(HookEvent.SESSION_END, {})
        assert len(matches) == 1

        # Unregister
        result = registry.unregister(handler_id)
        assert result is True

        # Verify unregistered
        matches = registry.get_matching_hooks(HookEvent.SESSION_END, {})
        assert len(matches) == 0

    def test_execution_log_tracking(self):
        """Test that execution log tracks hook runs."""
        config = HookConfig(log_executions=True)
        registry = HookRegistry(config=config)

        # Hook handlers receive keyword arguments
        def handler(**kwargs):
            return {"success": True, "output": "logged"}

        registry.register(
            event=HookEvent.SESSION_START,
            handler=handler,
        )

        # Fire hook
        registry.fire_sync(HookEvent.SESSION_START, {})

        # Check log
        log = registry.get_execution_log()
        assert len(log) == 1
        assert log[0]["event"] == "SessionStart"
        assert log[0]["success"] is True

    def test_hook_stats(self):
        """Test hook registry statistics."""
        registry = HookRegistry()

        # Hook handlers receive keyword arguments
        registry.register(HookEvent.SESSION_START, lambda **kw: {"success": True})
        registry.register(HookEvent.SESSION_END, lambda **kw: {"success": True})

        # Fire one
        registry.fire_sync(HookEvent.SESSION_START, {})

        stats = registry.get_stats()

        assert stats["total_hooks"] == 2
        assert stats["python_handlers"] == 2
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1

    def test_disabled_config_skips_hooks(self):
        """Test that disabled config doesn't fire hooks."""
        config = HookConfig(enabled=False)
        registry = HookRegistry(config=config)

        executed = []
        registry.register(
            HookEvent.SESSION_START,
            lambda ctx: executed.append(True) or {"success": True},
        )

        # Fire - should be skipped
        results = registry.fire_sync(HookEvent.SESSION_START, {})

        assert results == []
        assert executed == []


class TestHookEventTypes:
    """Test all hook event types."""

    @pytest.mark.parametrize(
        "event",
        [
            HookEvent.PRE_TOOL_USE,
            HookEvent.POST_TOOL_USE,
            HookEvent.SESSION_START,
            HookEvent.SESSION_END,
            HookEvent.PRE_COMPACT,
            HookEvent.PRE_COMMAND,
            HookEvent.POST_COMMAND,
            HookEvent.STOP,
        ],
    )
    def test_all_event_types_work(self, event):
        """Test that all event types can be used."""
        registry = HookRegistry()
        executed = []

        # Use a closure to capture the event value correctly
        # Hook handlers receive keyword arguments
        def make_handler(evt):
            def handler(**kwargs):
                executed.append(evt.value)
                return {"success": True}

            return handler

        registry.register(
            event=event,
            handler=make_handler(event),
        )

        registry.fire_sync(event, {"test": True})

        assert executed == [event.value]


class TestHookConfigYaml:
    """Test YAML configuration loading."""

    def test_load_from_yaml(self, tmp_path):
        """Test loading config from YAML file."""
        yaml_content = """
hooks:
  SessionStart:
    - matcher:
        match_all: true
      hooks:
        - type: python
          command: test_handler
          description: Test hook
enabled: true
log_executions: true
"""
        yaml_file = tmp_path / "hooks.yaml"
        yaml_file.write_text(yaml_content)

        config = HookConfig.from_yaml(str(yaml_file))

        assert config.enabled is True
        assert config.log_executions is True
        assert "SessionStart" in config.hooks

    def test_save_to_yaml(self, tmp_path):
        """Test saving config to YAML file."""
        config = HookConfig(enabled=True, log_executions=False)
        config.add_hook(
            event=HookEvent.SESSION_START,
            hook=HookDefinition(
                type=HookType.PYTHON,
                command="handler",
            ),
        )

        yaml_file = tmp_path / "output.yaml"
        config.to_yaml(str(yaml_file))

        assert yaml_file.exists()
        content = yaml_file.read_text()
        assert "SessionStart" in content
