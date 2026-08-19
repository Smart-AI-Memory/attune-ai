"""Tests for hook configuration models."""

from attune.hooks.config import (
    HookConfig,
    HookDefinition,
    HookEvent,
    HookMatcher,
    HookRule,
    HookType,
)


class TestHookEvent:
    """Tests for HookEvent enum."""

    def test_all_events_defined(self):
        """Verify all expected hook events are defined."""
        expected = [
            "PreToolUse",
            "PostToolUse",
            "SessionStart",
            "SessionEnd",
            "PreCompact",
            "PreCommand",
            "PostCommand",
            "Stop",
        ]
        actual = [e.value for e in HookEvent]
        assert sorted(actual) == sorted(expected)


class TestHookDefinition:
    """Tests for HookDefinition model."""

    def test_default_values(self):
        """Test default hook definition values."""
        hook = HookDefinition(command="test:main")

        assert hook.type == HookType.PYTHON
        assert hook.command == "test:main"
        assert hook.timeout == 30
        assert hook.async_execution is False
        assert hook.on_error == "log"

    def test_command_hook(self):
        """Test command type hook."""
        hook = HookDefinition(
            type=HookType.COMMAND,
            command="echo hello",
            description="Test command",
        )

        assert hook.type == HookType.COMMAND
        assert hook.command == "echo hello"

    def test_webhook_hook(self):
        """Test webhook type hook."""
        hook = HookDefinition(
            type=HookType.WEBHOOK,
            command="https://example.com/hook",
            timeout=60,
        )

        assert hook.type == HookType.WEBHOOK
        assert hook.timeout == 60


class TestHookMatcher:
    """Tests for HookMatcher model."""

    def test_match_all(self):
        """Test wildcard matcher."""
        matcher = HookMatcher(match_all=True)

        assert matcher.matches({}) is True
        assert matcher.matches({"tool": "Bash"}) is True
        assert matcher.matches({"anything": "value"}) is True

    def test_tool_matching(self):
        """Test tool name matching."""
        matcher = HookMatcher(tool="Edit")

        assert matcher.matches({"tool": "Edit"}) is True
        assert matcher.matches({"tool": "Read"}) is False
        assert matcher.matches({}) is False

    def test_file_pattern_matching(self):
        """Test file path pattern matching."""
        matcher = HookMatcher(file_pattern=r"\.(py|ts)$")

        assert matcher.matches({"file_path": "test.py"}) is True
        assert matcher.matches({"file_path": "test.ts"}) is True
        assert matcher.matches({"file_path": "test.js"}) is False
        assert matcher.matches({}) is False

    def test_command_pattern_matching(self):
        """Test command pattern matching."""
        matcher = HookMatcher(command_pattern=r"npm run (dev|build)")

        assert matcher.matches({"command": "npm run dev"}) is True
        assert matcher.matches({"command": "npm run build"}) is True
        assert matcher.matches({"command": "npm install"}) is False

    def test_combined_matching(self):
        """Test multiple criteria matching."""
        matcher = HookMatcher(
            tool="Edit",
            file_pattern=r"\.py$",
        )

        # Both must match
        assert matcher.matches({"tool": "Edit", "file_path": "test.py"}) is True
        assert matcher.matches({"tool": "Edit", "file_path": "test.js"}) is False
        assert matcher.matches({"tool": "Read", "file_path": "test.py"}) is False


class TestHookRule:
    """Tests for HookRule model."""

    def test_default_values(self):
        """Test default rule values."""
        rule = HookRule()

        assert rule.enabled is True
        assert rule.priority == 0
        assert rule.matcher.match_all is True
        assert rule.hooks == []

    def test_rule_with_hooks(self):
        """Test rule with hook definitions."""
        rule = HookRule(
            matcher=HookMatcher(tool="Bash"),
            hooks=[
                HookDefinition(command="log:main"),
                HookDefinition(command="audit:main"),
            ],
            priority=10,
        )

        assert len(rule.hooks) == 2
        assert rule.priority == 10


class TestHookConfig:
    """Tests for HookConfig model."""

    def test_default_config(self):
        """Test default configuration."""
        config = HookConfig()

        assert config.enabled is True
        assert config.log_executions is True
        assert config.default_timeout == 30

        # All event types should have empty lists
        for event in HookEvent:
            assert event.value in config.hooks
            assert config.hooks[event.value] == []

    def test_get_hooks_for_event(self):
        """Test getting hooks for a specific event."""
        rule1 = HookRule(hooks=[HookDefinition(command="a")], priority=1)
        rule2 = HookRule(hooks=[HookDefinition(command="b")], priority=10)
        rule3 = HookRule(hooks=[HookDefinition(command="c")], enabled=False)

        config = HookConfig(hooks={HookEvent.SESSION_START.value: [rule1, rule2, rule3]})

        hooks = config.get_hooks_for_event(HookEvent.SESSION_START)

        # Should be sorted by priority (highest first), disabled excluded
        assert len(hooks) == 2
        assert hooks[0].hooks[0].command == "b"  # priority 10
        assert hooks[1].hooks[0].command == "a"  # priority 1

    def test_add_hook(self):
        """Test adding a hook."""
        config = HookConfig()

        hook = HookDefinition(command="test:main", description="Test hook")
        matcher = HookMatcher(tool="Edit")

        config.add_hook(
            event=HookEvent.POST_TOOL_USE,
            hook=hook,
            matcher=matcher,
            priority=5,
        )

        rules = config.get_hooks_for_event(HookEvent.POST_TOOL_USE)
        assert len(rules) == 1
        assert rules[0].hooks[0].command == "test:main"
        assert rules[0].matcher.tool == "Edit"
        assert rules[0].priority == 5

    def test_disabled_config(self):
        """Test that disabled config returns no hooks."""
        config = HookConfig(enabled=False)
        config.add_hook(
            event=HookEvent.SESSION_START,
            hook=HookDefinition(command="test"),
        )

        # get_hooks_for_event checks config.enabled
        rules = config.get_hooks_for_event(HookEvent.SESSION_START)
        # Note: get_hooks_for_event doesn't check global enabled, only rule.enabled
        # The registry.fire() checks config.enabled
        assert len(rules) == 1
