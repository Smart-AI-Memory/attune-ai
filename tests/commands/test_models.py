"""Tests for command data models.

Tests for CommandConfig, CommandMetadata, and CommandResult.
"""

from pathlib import Path

from attune_llm.commands.models import (
    CommandCategory,
    CommandConfig,
    CommandMetadata,
    CommandResult,
)


class TestCommandCategory:
    """Tests for CommandCategory enum."""

    def test_all_categories_exist(self):
        """Test all expected categories are defined."""
        expected = {
            "workflow",
            "git",
            "test",
            "docs",
            "security",
            "performance",
            "learning",
            "context",
            "utility",
        }
        actual = {c.value for c in CommandCategory}
        assert expected == actual

    def test_category_from_string(self):
        """Test creating category from string."""
        assert CommandCategory("git") == CommandCategory.GIT
        assert CommandCategory("learning") == CommandCategory.LEARNING


class TestCommandMetadata:
    """Tests for CommandMetadata dataclass."""

    def test_default_values(self):
        """Test metadata with default values."""
        meta = CommandMetadata(name="test")

        assert meta.name == "test"
        assert meta.description == ""
        assert meta.category == CommandCategory.UTILITY
        assert meta.aliases == []
        assert meta.hooks == {}
        assert meta.requires_user_id is False
        assert meta.version == "1.0"

    def test_full_metadata(self):
        """Test metadata with all fields set."""
        meta = CommandMetadata(
            name="compact",
            description="Context compaction",
            category=CommandCategory.CONTEXT,
            aliases=["comp", "save"],
            hooks={"pre": "PreCompact", "post": "PostCompact"},
            requires_user_id=True,
            requires_context=True,
            tags=["context", "state"],
            author="test",
            version="2.0",
        )

        assert meta.name == "compact"
        assert meta.category == CommandCategory.CONTEXT
        assert "comp" in meta.aliases
        assert meta.hooks["pre"] == "PreCompact"
        assert meta.requires_user_id is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        meta = CommandMetadata(
            name="test",
            category=CommandCategory.GIT,
            tags=["git", "commit"],
        )

        data = meta.to_dict()

        assert data["name"] == "test"
        assert data["category"] == "git"
        assert data["tags"] == ["git", "commit"]

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "name": "commit",
            "description": "Create git commit",
            "category": "git",
            "aliases": ["ci"],
            "tags": ["git"],
        }

        meta = CommandMetadata.from_dict(data)

        assert meta.name == "commit"
        assert meta.description == "Create git commit"
        assert meta.category == CommandCategory.GIT
        assert "ci" in meta.aliases

    def test_from_dict_invalid_category(self):
        """Test that invalid category falls back to utility."""
        data = {"name": "test", "category": "invalid"}
        meta = CommandMetadata.from_dict(data)
        assert meta.category == CommandCategory.UTILITY


class TestCommandConfig:
    """Tests for CommandConfig dataclass."""

    def test_basic_config(self):
        """Test basic command configuration."""
        meta = CommandMetadata(name="test")
        config = CommandConfig(
            name="test",
            description="Test command",
            body="## Instructions\nDo something.",
            metadata=meta,
        )

        assert config.name == "test"
        assert config.description == "Test command"
        assert "Instructions" in config.body

    def test_config_properties(self):
        """Test config property accessors."""
        meta = CommandMetadata(
            name="compact",
            aliases=["comp"],
            category=CommandCategory.CONTEXT,
            hooks={"pre": "PreCompact"},
        )
        config = CommandConfig(
            name="compact",
            description="Compact",
            body="Body",
            metadata=meta,
        )

        assert config.aliases == ["comp"]
        assert config.category == CommandCategory.CONTEXT
        assert config.hooks["pre"] == "PreCompact"

    def test_get_all_names(self):
        """Test getting name and all aliases."""
        meta = CommandMetadata(name="test", aliases=["t", "tst"])
        config = CommandConfig(name="test", description="", body="", metadata=meta)

        names = config.get_all_names()

        assert "test" in names
        assert "t" in names
        assert "tst" in names
        assert len(names) == 3

    def test_to_dict(self):
        """Test conversion to dictionary."""
        meta = CommandMetadata(name="test", tags=["tag1"])
        source = Path("/path/to/test.md")
        config = CommandConfig(
            name="test",
            description="Desc",
            body="Body",
            metadata=meta,
            source_file=source,
        )

        data = config.to_dict()

        assert data["name"] == "test"
        assert data["description"] == "Desc"
        assert data["body"] == "Body"
        assert data["metadata"]["tags"] == ["tag1"]
        assert data["source_file"] == str(source)

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "name": "test",
            "description": "Test",
            "body": "Body content",
            "metadata": {"name": "test", "category": "git"},
            "source_file": "/path/to/file.md",
            "loaded_at": "2025-01-23T10:00:00",
        }

        config = CommandConfig.from_dict(data)

        assert config.name == "test"
        assert config.body == "Body content"
        assert config.metadata.category == CommandCategory.GIT
        assert config.source_file == Path("/path/to/file.md")

    def test_format_for_display(self):
        """Test display formatting."""
        meta = CommandMetadata(
            name="commit",
            aliases=["ci"],
        )
        config = CommandConfig(
            name="commit",
            description="Create a git commit",
            body="",
            metadata=meta,
        )

        display = config.format_for_display()

        assert "/commit" in display
        assert "ci" in display
        assert "Create a git commit" in display

    def test_format_full_help(self):
        """Test full help formatting."""
        meta = CommandMetadata(
            name="test",
            aliases=["t"],
            tags=["testing"],
        )
        config = CommandConfig(
            name="test",
            description="Run tests",
            body="## Steps\n1. Run pytest",
            metadata=meta,
        )

        help_text = config.format_full_help()

        assert "# /test" in help_text
        assert "Run tests" in help_text
        assert "## Aliases" in help_text
        assert "## Tags" in help_text
        assert "## Instructions" in help_text
        assert "Run pytest" in help_text


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_successful_result(self):
        """Test successful command result."""
        result = CommandResult(
            command_name="test",
            success=True,
            output="Command completed",
            duration_ms=150.5,
            hooks_fired=["pre:PreCommand", "post:PostCommand"],
        )

        assert result.success is True
        assert result.error is None
        assert result.duration_ms == 150.5
        assert len(result.hooks_fired) == 2

    def test_failed_result(self):
        """Test failed command result."""
        result = CommandResult(
            command_name="test",
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = CommandResult(
            command_name="compact",
            success=True,
            output="State saved",
            context_saved=True,
            patterns_applied=["pattern1", "pattern2"],
        )

        data = result.to_dict()

        assert data["command_name"] == "compact"
        assert data["success"] is True
        assert data["context_saved"] is True
        assert len(data["patterns_applied"]) == 2
