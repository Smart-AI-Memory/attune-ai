"""Command Registry

Central registry for managing available commands.

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
from typing import Any

from attune.commands.loader import CommandLoader, get_default_commands_directory
from attune.commands.models import CommandCategory, CommandConfig

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Central registry for command configurations.

    Provides a single point of access for all available commands,
    supporting both programmatic registration and directory loading.
    Includes alias resolution for flexible command invocation.

    Example:
        # Create registry and load commands
        registry = CommandRegistry()
        registry.load_from_directory(".claude/commands/")

        # Get a command by name
        commit = registry.get("commit")

        # Get by alias
        compact = registry.get("comp")  # Resolves alias

        # Register a custom command
        registry.register(my_custom_config)

        # List all available commands
        for name in registry.list_commands():
            print(name)

    """

    _instance: CommandRegistry | None = None

    def __init__(self):
        """Initialize the registry."""
        self._commands: dict[str, CommandConfig] = {}
        self._aliases: dict[str, str] = {}  # alias -> command name
        self._loader: CommandLoader = CommandLoader()
        self._load_paths: list[Path] = []

    @classmethod
    def get_instance(cls) -> CommandRegistry:
        """Get the singleton registry instance.

        Returns:
            The global CommandRegistry instance

        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None

    def register(
        self,
        config: CommandConfig,
        overwrite: bool = False,
    ) -> None:
        """Register a command configuration.

        Args:
            config: Command configuration to register
            overwrite: If True, overwrite existing command with same name

        Raises:
            ValueError: If command name already exists and overwrite=False

        """
        if config.name in self._commands and not overwrite:
            raise ValueError(
                f"Command '{config.name}' already registered. Use overwrite=True to replace.",
            )

        self._commands[config.name] = config

        # Register aliases
        for alias in config.aliases:
            if alias in self._aliases and not overwrite:
                logger.warning(
                    "Alias '%s' already registered for '%s', skipping",
                    alias,
                    self._aliases[alias],
                )
                continue
            self._aliases[alias] = config.name

        logger.debug("Registered command: %s", config.name)

    def unregister(self, name: str) -> bool:
        """Unregister a command by name.

        Args:
            name: Command name to remove

        Returns:
            True if command was found and removed

        """
        if name in self._commands:
            config = self._commands[name]

            # Remove aliases
            for alias in config.aliases:
                if self._aliases.get(alias) == name:
                    del self._aliases[alias]

            del self._commands[name]
            logger.debug("Unregistered command: %s", name)
            return True
        return False

    def get(self, name: str) -> CommandConfig | None:
        """Get a command configuration by name or alias.

        Args:
            name: Command name or alias

        Returns:
            Command config or None if not found

        """
        # Direct lookup
        if name in self._commands:
            return self._commands[name]

        # Alias lookup
        if name in self._aliases:
            return self._commands.get(self._aliases[name])

        return None

    def get_required(self, name: str) -> CommandConfig:
        """Get a command configuration, raising if not found.

        Args:
            name: Command name or alias

        Returns:
            Command configuration

        Raises:
            KeyError: If command not found

        """
        config = self.get(name)
        if config is None:
            available = ", ".join(sorted(self._commands.keys()))
            raise KeyError(f"Command '{name}' not found. Available commands: {available}")
        return config

    def has(self, name: str) -> bool:
        """Check if a command is registered.

        Args:
            name: Command name or alias

        Returns:
            True if command exists

        """
        return name in self._commands or name in self._aliases

    def resolve_alias(self, name: str) -> str:
        """Resolve an alias to command name.

        Args:
            name: Name or alias

        Returns:
            Resolved command name

        """
        return self._aliases.get(name, name)

    def list_commands(self) -> list[str]:
        """Get list of all registered command names.

        Returns:
            Sorted list of command names

        """
        return sorted(self._commands.keys())

    def list_aliases(self) -> dict[str, str]:
        """Get all registered aliases.

        Returns:
            Dictionary mapping aliases to command names

        """
        return dict(self._aliases)

    def iter_commands(self) -> Iterator[CommandConfig]:
        """Iterate over all registered commands.

        Yields:
            Command configurations

        """
        for name in sorted(self._commands.keys()):
            yield self._commands[name]

    def load_from_directory(
        self,
        directory: str | Path,
        recursive: bool = False,
        overwrite: bool = False,
    ) -> int:
        """Load commands from a directory.

        Args:
            directory: Directory containing .md command files
            recursive: If True, scan subdirectories
            overwrite: If True, overwrite existing commands

        Returns:
            Number of commands loaded

        """
        directory = Path(directory)
        # Track loaded paths for reload (avoid duplicates)
        if directory not in self._load_paths:
            self._load_paths.append(directory)

        commands = self._loader.load_directory(directory, recursive=recursive)

        loaded = 0
        for _name, config in commands.items():
            try:
                self.register(config, overwrite=overwrite)
                loaded += 1
            except ValueError as e:
                logger.warning("Skipping command: %s", e)

        logger.info("Loaded %d command(s) from %s", loaded, directory)
        return loaded

    def load_from_file(
        self,
        file_path: str | Path,
        overwrite: bool = False,
    ) -> CommandConfig:
        """Load a single command from a file.

        Args:
            file_path: Path to command markdown file
            overwrite: If True, overwrite existing command

        Returns:
            Loaded command configuration

        """
        config = self._loader.load(file_path)
        self.register(config, overwrite=overwrite)
        return config

    def load_default_commands(self, overwrite: bool = False) -> int:
        """Load commands from default directory.

        Args:
            overwrite: If True, overwrite existing commands

        Returns:
            Number of commands loaded

        """
        default_dir = get_default_commands_directory()

        if not default_dir.exists():
            logger.info("Default commands directory not found: %s", default_dir)
            return 0

        return self.load_from_directory(default_dir, overwrite=overwrite)

    def reload(self) -> int:
        """Reload all commands from previously loaded directories.

        Returns:
            Total number of commands after reload

        """
        self._commands.clear()
        self._aliases.clear()

        # Copy _load_paths and clear it to avoid duplicates when load_from_directory appends
        paths_to_reload = list(self._load_paths)
        self._load_paths.clear()

        for directory in paths_to_reload:
            if directory.exists():
                self.load_from_directory(directory, overwrite=True)

        return len(self._commands)

    def get_by_category(self, category: CommandCategory) -> list[CommandConfig]:
        """Get all commands with a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of matching command configs

        """
        return [config for config in self._commands.values() if config.category == category]

    def get_by_tag(self, tag: str) -> list[CommandConfig]:
        """Get all commands with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of matching command configs

        """
        tag = tag.lower()
        return [
            config
            for config in self._commands.values()
            if tag in [t.lower() for t in config.metadata.tags]
        ]

    def search(self, query: str) -> list[CommandConfig]:
        """Search commands by name, description, or tags.

        Args:
            query: Search query

        Returns:
            List of matching commands

        """
        query = query.lower()
        results: list[CommandConfig] = []

        for config in self._commands.values():
            if (
                query in config.name.lower()
                or query in config.description.lower()
                or any(query in tag.lower() for tag in config.metadata.tags)
            ):
                results.append(config)

        return results

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of registered commands.

        Returns:
            Summary dictionary

        """
        by_category: dict[str, int] = {}

        for config in self._commands.values():
            cat = config.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total_commands": len(self._commands),
            "total_aliases": len(self._aliases),
            "command_names": self.list_commands(),
            "by_category": by_category,
            "load_paths": [str(p) for p in self._load_paths],
        }

    def format_help(self) -> str:
        """Format help text listing all commands.

        Returns:
            Formatted help string

        """
        lines = ["# Available Commands", ""]

        # Group by category
        by_category: dict[CommandCategory, list[CommandConfig]] = {}
        for config in self._commands.values():
            cat = config.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(config)

        for category in CommandCategory:
            commands = by_category.get(category, [])
            if not commands:
                continue

            lines.append(f"## {category.value.title()}")
            lines.append("")

            for config in sorted(commands, key=lambda c: c.name):
                lines.append(config.format_for_display())

            lines.append("")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all registered commands."""
        self._commands.clear()
        self._aliases.clear()
        self._load_paths.clear()
        logger.debug("Cleared command registry")
