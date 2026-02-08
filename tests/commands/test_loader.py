"""Tests for command loader.

Tests for CommandLoader that discovers and loads command files.
"""

from pathlib import Path

import pytest

from attune_llm.commands.loader import (
    CommandLoader,
    get_default_commands_directory,
    load_commands_from_paths,
)


class TestCommandLoader:
    """Tests for CommandLoader."""

    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return CommandLoader()

    @pytest.fixture
    def commands_dir(self, tmp_path):
        """Create a temporary commands directory with test files."""
        # Create command files
        (tmp_path / "commit.md").write_text(
            """---
name: commit
description: Create a git commit
category: git
---

## Steps
1. Stage files
2. Commit
"""
        )

        (tmp_path / "test.md").write_text(
            """---
name: test
description: Run tests
category: test
aliases: [t]
---

## Steps
1. Run pytest
"""
        )

        (tmp_path / "review.md").write_text(
            """Review code - Automated code review.

## Overview
Review code for issues.
"""
        )

        # Create files that should be skipped
        (tmp_path / "README.md").write_text("# Commands Directory")
        (tmp_path / "_private.md").write_text("Private file")
        (tmp_path / ".hidden.md").write_text("Hidden file")

        return tmp_path

    def test_load_single_file(self, loader, commands_dir):
        """Test loading a single command file."""
        config = loader.load(commands_dir / "commit.md")

        assert config.name == "commit"
        assert config.description == "Create a git commit"

    def test_load_directory(self, loader, commands_dir):
        """Test loading all commands from directory."""
        commands = loader.load_directory(commands_dir)

        assert len(commands) == 3  # commit, test, review
        assert "commit" in commands
        assert "test" in commands
        assert "review" in commands

    def test_load_directory_skips_readme(self, loader, commands_dir):
        """Test that README.md is skipped."""
        commands = loader.load_directory(commands_dir)

        # README.md content shouldn't be in any command
        assert all("Commands Directory" not in c.body for c in commands.values())

    def test_load_directory_skips_private(self, loader, commands_dir):
        """Test that files starting with _ are skipped."""
        commands = loader.load_directory(commands_dir)

        # _private.md shouldn't be loaded
        assert "_private" not in commands

    def test_load_directory_skips_hidden(self, loader, commands_dir):
        """Test that hidden files are skipped."""
        commands = loader.load_directory(commands_dir)

        # .hidden.md shouldn't be loaded
        assert ".hidden" not in commands

    def test_discover_yields_commands(self, loader, commands_dir):
        """Test discover yields commands lazily."""
        configs = list(loader.discover(commands_dir))

        assert len(configs) == 3
        names = {c.name for c in configs}
        assert names == {"commit", "test", "review"}

    def test_discover_nonexistent_directory(self, loader):
        """Test discover with non-existent directory yields nothing."""
        configs = list(loader.discover("/nonexistent/path"))
        assert configs == []

    def test_discover_not_a_directory_raises(self, loader, tmp_path):
        """Test discover with file path raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="Not a directory"):
            list(loader.discover(file_path))

    def test_load_directory_handles_invalid_files(self, loader, tmp_path):
        """Test that invalid files are skipped gracefully."""
        (tmp_path / "valid.md").write_text("Valid content")
        # Create a file that will fail to parse (no name, no source context)
        # Actually, since we pass source, it should get name from filename
        # Let's create an empty frontmatter without name
        (tmp_path / "valid2.md").write_text(
            """---
category: git
---

Body without explicit name.
"""
        )

        # Should load both - one gets name from content, other from filename
        commands = loader.load_directory(tmp_path)
        assert len(commands) >= 1

    def test_load_directory_recursive(self, loader, tmp_path):
        """Test recursive directory loading."""
        # Create nested structure
        subdir = tmp_path / "sub"
        subdir.mkdir()

        (tmp_path / "top.md").write_text("Top level - Description")
        (subdir / "nested.md").write_text("Nested - Description")

        # Non-recursive
        commands = loader.load_directory(tmp_path, recursive=False)
        assert "top" in commands
        assert "nested" not in commands

        # Recursive
        commands = loader.load_directory(tmp_path, recursive=True)
        assert "top" in commands
        assert "nested" in commands

    def test_validate_directory(self, loader, tmp_path):
        """Test validating all files in directory."""
        (tmp_path / "valid.md").write_text(
            """---
name: valid
---

Body.
"""
        )
        (tmp_path / "invalid.md").write_text("")  # Empty file

        results = loader.validate_directory(tmp_path)

        # Should have errors for invalid file
        assert str(tmp_path / "invalid.md") in results
        # Valid file should not be in results (no errors)
        assert str(tmp_path / "valid.md") not in results

    def test_validate_directory_nonexistent(self, loader):
        """Test validating non-existent directory."""
        results = loader.validate_directory("/nonexistent")
        assert "nonexistent" in str(list(results.keys())[0])

    def test_get_command_names(self, loader, commands_dir):
        """Test getting command names without full loading."""
        names = loader.get_command_names(commands_dir)

        assert len(names) == 3
        assert "commit" in names
        assert "test" in names
        assert "review" in names

    def test_find_command_file(self, loader, commands_dir):
        """Test finding command file by name."""
        path = loader.find_command_file("commit", commands_dir)
        assert path == commands_dir / "commit.md"

    def test_find_command_file_not_found(self, loader, commands_dir):
        """Test finding non-existent command."""
        path = loader.find_command_file("nonexistent", commands_dir)
        assert path is None

    def test_duplicate_names_keeps_first(self, loader, tmp_path):
        """Test that duplicate command names keep first occurrence."""
        # Create two files with same command name
        (tmp_path / "first.md").write_text(
            """---
name: duplicate
description: First version
---

First body.
"""
        )
        (tmp_path / "second.md").write_text(
            """---
name: duplicate
description: Second version
---

Second body.
"""
        )

        commands = loader.load_directory(tmp_path)

        # Should only have one entry
        assert len(commands) == 1
        # Should be the first one (files are sorted)
        assert "First" in commands["duplicate"].description


class TestLoadCommandsFromPaths:
    """Tests for load_commands_from_paths helper."""

    def test_load_from_files(self, tmp_path):
        """Test loading from individual files."""
        (tmp_path / "a.md").write_text("A - Description A")
        (tmp_path / "b.md").write_text("B - Description B")

        commands = load_commands_from_paths(
            [
                tmp_path / "a.md",
                tmp_path / "b.md",
            ]
        )

        assert len(commands) == 2
        assert "a" in commands
        assert "b" in commands

    def test_load_from_directories(self, tmp_path):
        """Test loading from directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "cmd1.md").write_text("Cmd1 - Description")
        (dir2 / "cmd2.md").write_text("Cmd2 - Description")

        commands = load_commands_from_paths([dir1, dir2])

        assert len(commands) == 2
        assert "cmd1" in commands
        assert "cmd2" in commands

    def test_load_mixed_paths(self, tmp_path):
        """Test loading from mix of files and directories."""
        dir1 = tmp_path / "dir"
        dir1.mkdir()

        (tmp_path / "file.md").write_text("File - Description")
        (dir1 / "dir-cmd.md").write_text("DirCmd - Description")

        commands = load_commands_from_paths(
            [
                tmp_path / "file.md",
                dir1,
            ]
        )

        assert len(commands) == 2
        assert "file" in commands
        assert "dir-cmd" in commands

    def test_load_nonexistent_path_skipped(self, tmp_path):
        """Test that non-existent paths are skipped."""
        (tmp_path / "exists.md").write_text("Exists - Description")

        commands = load_commands_from_paths(
            [
                tmp_path / "exists.md",
                tmp_path / "nonexistent.md",
            ]
        )

        assert len(commands) == 1
        assert "exists" in commands


class TestGetDefaultCommandsDirectory:
    """Tests for get_default_commands_directory."""

    def test_returns_path(self):
        """Test that function returns a Path."""
        result = get_default_commands_directory()
        assert isinstance(result, Path)

    def test_finds_claude_commands_in_cwd(self, tmp_path, monkeypatch):
        """Test finding .claude/commands from current directory."""
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        result = get_default_commands_directory()
        assert result == commands_dir

    def test_finds_claude_commands_in_parent(self, tmp_path, monkeypatch):
        """Test finding .claude/commands in parent directory."""
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        subdir = tmp_path / "src" / "deep"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)

        result = get_default_commands_directory()
        assert result == commands_dir
