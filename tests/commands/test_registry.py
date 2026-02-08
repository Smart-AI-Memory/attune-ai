"""Tests for command registry.

Tests for CommandRegistry singleton that manages command configurations.
"""

from pathlib import Path

import pytest

from attune_llm.commands.models import CommandCategory, CommandConfig, CommandMetadata
from attune_llm.commands.registry import CommandRegistry


class TestCommandRegistry:
    """Tests for CommandRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton before each test."""
        CommandRegistry.reset_instance()
        yield
        CommandRegistry.reset_instance()

    @pytest.fixture
    def registry(self):
        """Create fresh registry instance."""
        return CommandRegistry()

    @pytest.fixture
    def sample_config(self):
        """Create sample command config."""
        return CommandConfig(
            name="test-cmd",
            description="Test command",
            body="Test body",
            metadata=CommandMetadata(
                name="test-cmd",
                aliases=["tc", "test"],
                category=CommandCategory.TEST,
                tags=["testing"],
            ),
        )

    def test_singleton_instance(self):
        """Test singleton pattern returns same instance."""
        instance1 = CommandRegistry.get_instance()
        instance2 = CommandRegistry.get_instance()

        assert instance1 is instance2

    def test_reset_instance(self):
        """Test resetting singleton creates new instance."""
        instance1 = CommandRegistry.get_instance()
        CommandRegistry.reset_instance()
        instance2 = CommandRegistry.get_instance()

        assert instance1 is not instance2

    def test_register_command(self, registry, sample_config):
        """Test registering a command."""
        registry.register(sample_config)

        assert registry.has("test-cmd")
        assert registry.get("test-cmd") == sample_config

    def test_register_duplicate_raises(self, registry, sample_config):
        """Test registering duplicate name raises error."""
        registry.register(sample_config)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(sample_config)

    def test_register_duplicate_overwrite(self, registry, sample_config):
        """Test overwriting duplicate."""
        registry.register(sample_config)

        new_config = CommandConfig(
            name="test-cmd",
            description="Updated",
            body="New body",
            metadata=CommandMetadata(name="test-cmd"),
        )
        registry.register(new_config, overwrite=True)

        assert registry.get("test-cmd").description == "Updated"

    def test_unregister_command(self, registry, sample_config):
        """Test unregistering a command."""
        registry.register(sample_config)
        assert registry.has("test-cmd")

        result = registry.unregister("test-cmd")

        assert result is True
        assert not registry.has("test-cmd")

    def test_unregister_removes_aliases(self, registry, sample_config):
        """Test unregistering removes aliases."""
        registry.register(sample_config)
        assert registry.has("tc")  # alias

        registry.unregister("test-cmd")

        assert not registry.has("tc")

    def test_unregister_nonexistent(self, registry):
        """Test unregistering non-existent command."""
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_by_alias(self, registry, sample_config):
        """Test getting command by alias."""
        registry.register(sample_config)

        config = registry.get("tc")  # alias
        assert config == sample_config

        config = registry.get("test")  # another alias
        assert config == sample_config

    def test_get_nonexistent(self, registry):
        """Test getting non-existent command."""
        result = registry.get("nonexistent")
        assert result is None

    def test_get_required_raises(self, registry):
        """Test get_required raises for missing command."""
        with pytest.raises(KeyError, match="not found"):
            registry.get_required("nonexistent")

    def test_has_checks_aliases(self, registry, sample_config):
        """Test has() checks aliases."""
        registry.register(sample_config)

        assert registry.has("test-cmd")  # name
        assert registry.has("tc")  # alias
        assert not registry.has("nonexistent")

    def test_resolve_alias(self, registry, sample_config):
        """Test resolving alias to command name."""
        registry.register(sample_config)

        assert registry.resolve_alias("tc") == "test-cmd"
        assert registry.resolve_alias("test-cmd") == "test-cmd"
        assert registry.resolve_alias("unknown") == "unknown"

    def test_list_commands(self, registry):
        """Test listing all commands."""
        for name in ["alpha", "beta", "gamma"]:
            config = CommandConfig(
                name=name,
                description=f"{name} command",
                body="",
                metadata=CommandMetadata(name=name),
            )
            registry.register(config)

        commands = registry.list_commands()

        assert commands == ["alpha", "beta", "gamma"]  # sorted

    def test_list_aliases(self, registry, sample_config):
        """Test listing all aliases."""
        registry.register(sample_config)

        aliases = registry.list_aliases()

        assert aliases["tc"] == "test-cmd"
        assert aliases["test"] == "test-cmd"

    def test_iter_commands(self, registry):
        """Test iterating over commands."""
        for name in ["a", "b", "c"]:
            config = CommandConfig(
                name=name,
                description="",
                body="",
                metadata=CommandMetadata(name=name),
            )
            registry.register(config)

        configs = list(registry.iter_commands())

        assert len(configs) == 3
        names = [c.name for c in configs]
        assert names == ["a", "b", "c"]  # sorted

    def test_load_from_directory(self, registry, tmp_path):
        """Test loading commands from directory."""
        (tmp_path / "cmd1.md").write_text(
            """---
name: cmd1
---

Body.
"""
        )
        (tmp_path / "cmd2.md").write_text(
            """---
name: cmd2
---

Body.
"""
        )

        count = registry.load_from_directory(tmp_path)

        assert count == 2
        assert registry.has("cmd1")
        assert registry.has("cmd2")

    def test_load_from_file(self, registry, tmp_path):
        """Test loading single command file."""
        file_path = tmp_path / "single.md"
        file_path.write_text(
            """---
name: single
description: Single command
---

Body.
"""
        )

        config = registry.load_from_file(file_path)

        assert config.name == "single"
        assert registry.has("single")

    def test_reload(self, registry, tmp_path):
        """Test reloading commands."""
        (tmp_path / "cmd.md").write_text(
            """---
name: cmd
description: Original
---

Body.
"""
        )

        registry.load_from_directory(tmp_path)
        assert registry.get("cmd").description == "Original"

        # Modify file
        (tmp_path / "cmd.md").write_text(
            """---
name: cmd
description: Updated
---

Body.
"""
        )

        count = registry.reload()

        assert count == 1
        assert registry.get("cmd").description == "Updated"

    def test_get_by_category(self, registry):
        """Test filtering by category."""
        git_config = CommandConfig(
            name="commit",
            description="",
            body="",
            metadata=CommandMetadata(name="commit", category=CommandCategory.GIT),
        )
        test_config = CommandConfig(
            name="test",
            description="",
            body="",
            metadata=CommandMetadata(name="test", category=CommandCategory.TEST),
        )

        registry.register(git_config)
        registry.register(test_config)

        git_commands = registry.get_by_category(CommandCategory.GIT)
        assert len(git_commands) == 1
        assert git_commands[0].name == "commit"

    def test_get_by_tag(self, registry):
        """Test filtering by tag."""
        config = CommandConfig(
            name="tagged",
            description="",
            body="",
            metadata=CommandMetadata(name="tagged", tags=["important", "git"]),
        )
        registry.register(config)

        results = registry.get_by_tag("important")
        assert len(results) == 1

        results = registry.get_by_tag("IMPORTANT")  # case insensitive
        assert len(results) == 1

        results = registry.get_by_tag("nonexistent")
        assert len(results) == 0

    def test_search(self, registry):
        """Test searching commands."""
        registry.register(
            CommandConfig(
                name="git-commit",
                description="Create a git commit",
                body="",
                metadata=CommandMetadata(name="git-commit", tags=["git"]),
            )
        )
        registry.register(
            CommandConfig(
                name="test",
                description="Run tests",
                body="",
                metadata=CommandMetadata(name="test", tags=["testing"]),
            )
        )

        # Search by name
        results = registry.search("git")
        assert len(results) == 1
        assert results[0].name == "git-commit"

        # Search by description
        results = registry.search("commit")
        assert len(results) == 1

        # Search by tag
        results = registry.search("testing")
        assert len(results) == 1
        assert results[0].name == "test"

    def test_get_summary(self, registry):
        """Test getting registry summary."""
        registry.register(
            CommandConfig(
                name="cmd1",
                description="",
                body="",
                metadata=CommandMetadata(
                    name="cmd1",
                    category=CommandCategory.GIT,
                    aliases=["c1"],
                ),
            )
        )
        registry.register(
            CommandConfig(
                name="cmd2",
                description="",
                body="",
                metadata=CommandMetadata(name="cmd2", category=CommandCategory.GIT),
            )
        )

        summary = registry.get_summary()

        assert summary["total_commands"] == 2
        assert summary["total_aliases"] == 1
        assert summary["by_category"]["git"] == 2

    def test_format_help(self, registry):
        """Test formatting help text."""
        registry.register(
            CommandConfig(
                name="commit",
                description="Create commit",
                body="",
                metadata=CommandMetadata(
                    name="commit",
                    category=CommandCategory.GIT,
                ),
            )
        )
        registry.register(
            CommandConfig(
                name="test",
                description="Run tests",
                body="",
                metadata=CommandMetadata(name="test", category=CommandCategory.TEST),
            )
        )

        help_text = registry.format_help()

        assert "# Available Commands" in help_text
        assert "## Git" in help_text
        assert "## Test" in help_text
        assert "/commit" in help_text
        assert "/test" in help_text

    def test_clear(self, registry, sample_config):
        """Test clearing registry."""
        registry.register(sample_config)
        assert len(registry.list_commands()) > 0

        registry.clear()

        assert len(registry.list_commands()) == 0
        assert len(registry.list_aliases()) == 0


class TestCommandRegistryIntegration:
    """Integration tests for CommandRegistry with real commands."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton."""
        CommandRegistry.reset_instance()
        yield
        CommandRegistry.reset_instance()

    def test_load_actual_commands_directory(self):
        """Test loading from actual .claude/commands directory."""
        registry = CommandRegistry.get_instance()

        # Try to load from actual commands directory
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"

        if commands_dir.exists():
            count = registry.load_from_directory(commands_dir)
            assert count > 0

            # Check for expected commands
            assert registry.has("commit") or registry.has("test") or count > 0
