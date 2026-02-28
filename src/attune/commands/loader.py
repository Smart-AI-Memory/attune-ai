"""Command Loader

Loads commands from directory structures.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from attune.commands.models import CommandConfig
from attune.commands.parser import CommandParser

logger = logging.getLogger(__name__)

# Default commands directory relative to project root
DEFAULT_COMMANDS_DIR = ".claude/commands"

# Files to skip when scanning
SKIP_FILES = frozenset(
    {
        "README.md",
        "readme.md",
        "CHANGELOG.md",
        "changelog.md",
        "INDEX.md",
        "index.md",
    },
)


class CommandLoader:
    """Loader for discovering and loading command markdown files.

    Scans directories for .md files with command definitions and loads
    them into CommandConfig instances.

    Example:
        loader = CommandLoader()

        # Load a single command
        config = loader.load(".claude/commands/commit.md")

        # Load all commands from a directory
        commands = loader.load_directory(".claude/commands/")

        # Discover and iterate commands lazily
        for config in loader.discover(".claude/commands/"):
            print(config.name)

    """

    def __init__(self, parser: CommandParser | None = None):
        """Initialize the loader.

        Args:
            parser: Optional custom parser instance

        """
        self.parser = parser or CommandParser()

    def load(self, file_path: str | Path) -> CommandConfig:
        """Load a single command file.

        Args:
            file_path: Path to the command markdown file

        Returns:
            CommandConfig instance

        """
        return self.parser.parse_file(file_path)

    def load_directory(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> dict[str, CommandConfig]:
        """Load all commands from a directory.

        Args:
            directory: Directory to scan for .md files
            recursive: If True, scan subdirectories

        Returns:
            Dictionary mapping command names to configs

        """
        commands: dict[str, CommandConfig] = {}

        for config in self.discover(directory, recursive=recursive):
            if config.name in commands:
                logger.warning(
                    "Duplicate command name '%s' - keeping first occurrence",
                    config.name,
                )
                continue
            commands[config.name] = config

        logger.info("Loaded %d command(s) from %s", len(commands), directory)
        return commands

    def discover(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> Iterator[CommandConfig]:
        """Discover and yield commands from a directory.

        Args:
            directory: Directory to scan
            recursive: If True, scan subdirectories

        Yields:
            CommandConfig instances

        """
        directory = Path(directory)

        if not directory.exists():
            logger.warning("Commands directory not found: %s", directory)
            return

        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Get pattern for globbing
        pattern = "**/*.md" if recursive else "*.md"

        for file_path in sorted(directory.glob(pattern)):
            if not file_path.is_file():
                continue

            # Skip non-command files
            if file_path.name in SKIP_FILES:
                continue
            if file_path.name.startswith("_"):
                continue
            if file_path.name.startswith("."):
                continue

            try:
                config = self.parser.parse_file(file_path)
                yield config
            except ValueError as e:
                logger.warning("Skipping invalid command file %s: %s", file_path, e)
            except FileNotFoundError as e:
                logger.warning("Command file not found %s: %s", file_path, e)
            except OSError as e:
                logger.error("Error loading command file %s: %s", file_path, e)

    def validate_directory(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> dict[str, list[str]]:
        """Validate all command files in a directory.

        Args:
            directory: Directory to validate
            recursive: If True, scan subdirectories

        Returns:
            Dictionary mapping file paths to lists of errors

        """
        directory = Path(directory)
        results: dict[str, list[str]] = {}

        if not directory.exists():
            return {str(directory): ["Directory not found"]}

        pattern = "**/*.md" if recursive else "*.md"

        for file_path in sorted(directory.glob(pattern)):
            if not file_path.is_file():
                continue
            if file_path.name in SKIP_FILES:
                continue
            if file_path.name.startswith("_"):
                continue

            errors = self.parser.validate_file(file_path)
            if errors:
                results[str(file_path)] = errors

        return results

    def get_command_names(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> list[str]:
        """Get list of command names in a directory without fully loading.

        Args:
            directory: Directory to scan
            recursive: If True, scan subdirectories

        Returns:
            List of command names

        """
        names: list[str] = []
        for config in self.discover(directory, recursive=recursive):
            names.append(config.name)
        return names

    def find_command_file(
        self,
        name: str,
        directory: str | Path,
    ) -> Path | None:
        """Find a command file by name.

        Args:
            name: Command name to find
            directory: Directory to search

        Returns:
            Path to command file or None

        """
        directory = Path(directory)

        # Try exact match first
        exact_path = directory / f"{name}.md"
        if exact_path.exists():
            return exact_path

        # Search through files
        for file_path in directory.glob("*.md"):
            if file_path.stem == name:
                return file_path

        return None


def load_commands_from_paths(
    paths: list[str | Path],
    parser: CommandParser | None = None,
) -> dict[str, CommandConfig]:
    """Load commands from multiple paths (files or directories).

    Args:
        paths: List of file or directory paths
        parser: Optional custom parser

    Returns:
        Dictionary mapping command names to configs

    """
    loader = CommandLoader(parser=parser)
    commands: dict[str, CommandConfig] = {}

    for path in paths:
        path = Path(path)

        if path.is_file():
            config = loader.load(path)
            commands[config.name] = config
        elif path.is_dir():
            dir_commands = loader.load_directory(path)
            commands.update(dir_commands)
        else:
            logger.warning("Path not found: %s", path)

    return commands


def get_default_commands_directory() -> Path:
    """Get the default commands directory.

    Searches for .claude/commands/ starting from current directory
    and walking up to find project root.

    Returns:
        Path to commands directory

    """
    current = Path.cwd()

    # Walk up looking for .claude/commands/
    for parent in [current, *current.parents]:
        commands_dir = parent / DEFAULT_COMMANDS_DIR
        if commands_dir.exists():
            return commands_dir

        # Also check for .claude directory as project root indicator
        if (parent / ".claude").exists():
            return commands_dir

    # Fall back to current directory
    return current / DEFAULT_COMMANDS_DIR
