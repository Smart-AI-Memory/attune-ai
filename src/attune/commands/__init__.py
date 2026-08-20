"""Attune slash commands and command subsystem.

This package contains:
1. Markdown command files for Claude Code slash commands
2. Python command parsing, loading, and registry subsystem

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from pathlib import Path

from attune.commands.loader import (
    CommandLoader,
    get_default_commands_directory,
    load_commands_from_paths,
)
from attune.commands.models import (
    CommandCategory,
    CommandConfig,
    CommandMetadata,
    CommandResult,
)
from attune.commands.parser import CommandParser
from attune.commands.registry import CommandRegistry

# Path to the commands directory (markdown files)
COMMANDS_DIR = Path(__file__).parent


def get_command_files() -> list[Path]:
    """Get all command markdown files."""
    return list(COMMANDS_DIR.glob("*.md"))


__all__ = [
    "COMMANDS_DIR",
    "get_command_files",
    # Models
    "CommandCategory",
    "CommandConfig",
    "CommandMetadata",
    "CommandResult",
    # Parser
    "CommandParser",
    # Loader
    "CommandLoader",
    "get_default_commands_directory",
    "load_commands_from_paths",
    # Registry
    "CommandRegistry",
]
