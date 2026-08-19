"""Command Configuration Models

Data models for command definitions loaded from markdown files.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class CommandCategory(str, Enum):
    """Categories for commands."""

    WORKFLOW = "workflow"  # Multi-step workflows
    GIT = "git"  # Git operations
    TEST = "test"  # Testing related
    DOCS = "docs"  # Documentation
    SECURITY = "security"  # Security analysis
    PERFORMANCE = "performance"  # Performance tools
    LEARNING = "learning"  # Pattern learning
    CONTEXT = "context"  # Context management
    UTILITY = "utility"  # General utilities


@dataclass
class CommandMetadata:
    """Metadata for a command extracted from YAML frontmatter.

    Example frontmatter:
        ---
        name: compact
        description: Strategic context compaction
        category: context
        aliases: [comp, save-state]
        hooks:
          pre: PreCommand
          post: PostCommand
        requires_user_id: true
        ---
    """

    name: str
    description: str = ""
    category: CommandCategory = CommandCategory.UTILITY
    aliases: list[str] = field(default_factory=list)
    hooks: dict[str, str] = field(default_factory=dict)
    requires_user_id: bool = False
    requires_context: bool = False
    tags: list[str] = field(default_factory=list)
    author: str = ""
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "aliases": self.aliases,
            "hooks": self.hooks,
            "requires_user_id": self.requires_user_id,
            "requires_context": self.requires_context,
            "tags": self.tags,
            "author": self.author,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandMetadata:
        """Create from dictionary."""
        category_str = data.get("category", "utility")
        try:
            category = CommandCategory(category_str)
        except ValueError:
            category = CommandCategory.UTILITY

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=category,
            aliases=data.get("aliases", []),
            hooks=data.get("hooks", {}),
            requires_user_id=data.get("requires_user_id", False),
            requires_context=data.get("requires_context", False),
            tags=data.get("tags", []),
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
        )


@dataclass
class CommandConfig:
    """Complete configuration for a command.

    Combines metadata from YAML frontmatter with the markdown body
    that contains the command instructions.
    """

    name: str
    description: str
    body: str  # Markdown content with instructions
    metadata: CommandMetadata
    source_file: Path | None = None
    loaded_at: datetime = field(default_factory=datetime.now)

    @property
    def aliases(self) -> list[str]:
        """Get command aliases."""
        return self.metadata.aliases

    @property
    def category(self) -> CommandCategory:
        """Get command category."""
        return self.metadata.category

    @property
    def hooks(self) -> dict[str, str]:
        """Get hook configuration."""
        return self.metadata.hooks

    def get_all_names(self) -> list[str]:
        """Get command name and all aliases."""
        return [self.name] + self.aliases

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "body": self.body,
            "metadata": self.metadata.to_dict(),
            "source_file": str(self.source_file) if self.source_file else None,
            "loaded_at": self.loaded_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandConfig:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            body=data.get("body", ""),
            metadata=CommandMetadata.from_dict(data.get("metadata", {})),
            source_file=Path(data["source_file"]) if data.get("source_file") else None,
            loaded_at=(
                datetime.fromisoformat(data["loaded_at"]) if "loaded_at" in data else datetime.now()
            ),
        )

    def format_for_display(self) -> str:
        """Format command for display in help."""
        aliases_str = ""
        if self.aliases:
            aliases_str = f" (aliases: {', '.join(self.aliases)})"

        return f"/{self.name}{aliases_str} - {self.description}"

    def format_full_help(self) -> str:
        """Format full help including body."""
        lines = [
            f"# /{self.name}",
            "",
            self.description,
            "",
        ]

        if self.aliases:
            lines.extend(
                [
                    "## Aliases",
                    ", ".join(f"/{a}" for a in self.aliases),
                    "",
                ],
            )

        if self.metadata.tags:
            lines.extend(
                [
                    "## Tags",
                    ", ".join(self.metadata.tags),
                    "",
                ],
            )

        lines.extend(
            [
                "## Instructions",
                "",
                self.body,
            ],
        )

        return "\n".join(lines)


@dataclass
class CommandResult:
    """Result from executing a command."""

    command_name: str
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    hooks_fired: list[str] = field(default_factory=list)
    context_saved: bool = False
    patterns_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "command_name": self.command_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "hooks_fired": self.hooks_fired,
            "context_saved": self.context_saved,
            "patterns_applied": self.patterns_applied,
        }
