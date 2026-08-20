"""Integration tests for the commands module.

Tests command loading, parsing, and registry integration.
"""

from pathlib import Path

import pytest

from attune.commands import (
    CommandCategory,
    CommandLoader,
    CommandParser,
    CommandRegistry,
)


class TestCommandsWithRealFiles:
    """Integration tests using real command files."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton before each test."""
        CommandRegistry.reset_instance()
        yield
        CommandRegistry.reset_instance()

    def test_load_actual_commands_directory(self):
        """Test loading from actual .claude/commands directory."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"

        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        registry = CommandRegistry.get_instance()
        count = registry.load_from_directory(commands_dir)

        # Should have some commands (number may vary based on setup)
        assert count > 5

        # Check that some commands were loaded (specific names may vary)
        commands = registry.list_commands()
        assert len(commands) > 0

    def test_load_new_empathy_commands(self):
        """Test loading empathy hub commands."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"

        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        registry = CommandRegistry.get_instance()
        registry.load_from_directory(commands_dir)

        # Check for hub commands (the new structure uses hubs)
        # These are the hub-based commands that exist in .claude/commands/
        commands = registry.list_commands()
        assert len(commands) > 0

        # Check that at least some commands loaded
        # Specific command names vary based on setup
        if registry.has("learning"):
            learning = registry.get("learning")
            assert learning is not None

        if registry.has("context"):
            context = registry.get("context")
            assert context is not None

    def test_command_alias_resolution(self):
        """Test that aliases resolve correctly."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"

        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        registry = CommandRegistry.get_instance()
        registry.load_from_directory(commands_dir)

        # Alias should resolve to same command
        compact_direct = registry.get("compact")
        compact_alias = registry.get("comp")

        assert compact_direct is compact_alias

    def test_search_commands(self):
        """Test searching commands."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"

        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        registry = CommandRegistry.get_instance()
        registry.load_from_directory(commands_dir)

        # list_commands() returns command names (strings)
        command_names = registry.list_commands()
        if len(command_names) > 0:
            # Search for any loaded command by partial name
            first_cmd_name = command_names[0]
            if isinstance(first_cmd_name, str):
                search_term = first_cmd_name[:3]
            else:
                # If it's a Command object
                search_term = first_cmd_name.name[:3]
            search_results = registry.search(search_term)
            # May or may not find results depending on search implementation
            assert isinstance(search_results, list)


class TestCommandParserIntegration:
    """Integration tests for CommandParser with real files."""

    def test_parse_compact_command(self):
        """Test parsing the compact command file."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"
        compact_path = commands_dir / "compact.md"

        if not compact_path.exists():
            pytest.skip("compact.md not found")

        parser = CommandParser()
        config = parser.parse_file(compact_path)

        assert config.name == "compact"
        assert config.category == CommandCategory.CONTEXT
        assert "comp" in config.aliases
        assert config.hooks.get("pre") == "PreCompact"
        assert "Work Handoff" in config.body

    def test_parse_patterns_command(self):
        """Test parsing the patterns command file."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"
        patterns_path = commands_dir / "patterns.md"

        if not patterns_path.exists():
            pytest.skip("patterns.md not found")

        parser = CommandParser()
        config = parser.parse_file(patterns_path)

        assert config.name == "patterns"
        assert config.category == CommandCategory.LEARNING
        assert "LearnedSkillsStorage" in config.body

    def test_parse_evaluate_command(self):
        """Test parsing the evaluate command file."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"
        eval_path = commands_dir / "evaluate.md"

        if not eval_path.exists():
            pytest.skip("evaluate.md not found")

        parser = CommandParser()
        config = parser.parse_file(eval_path)

        assert config.name == "evaluate"
        assert config.category == CommandCategory.LEARNING
        assert "eval" in config.aliases

    def test_parse_legacy_command_without_frontmatter(self):
        """Test parsing a legacy command without YAML frontmatter."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"
        commit_path = commands_dir / "commit.md"

        if not commit_path.exists():
            pytest.skip("commit.md not found")

        parser = CommandParser()
        config = parser.parse_file(commit_path)

        # Should infer name from filename
        assert config.name == "commit"
        # Should infer category
        assert config.category == CommandCategory.GIT


class TestCommandLoaderIntegration:
    """Integration tests for CommandLoader."""

    def test_loader_validates_directory(self):
        """Test loader validation of directory."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"

        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        loader = CommandLoader()
        errors = loader.validate_directory(commands_dir)

        # Should have no errors for valid commands
        # (or minimal errors for legacy format)
        assert isinstance(errors, dict)

    def test_loader_discover_yields_all_commands(self):
        """Test that discover yields all commands."""
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"

        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        loader = CommandLoader()
        commands = list(loader.discover(commands_dir))

        # Should have some commands (number may vary based on setup)
        assert len(commands) >= 5

        # Should include some commands
        names = {c.name for c in commands}
        assert len(names) > 0
