"""Hook Configuration Models

Pydantic models for hook system configuration.
Based on everything-claude-code hooks.json pattern.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HookEvent(str, Enum):
    """Hook event types matching Claude Code lifecycle."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    PRE_COMPACT = "PreCompact"
    PRE_COMMAND = "PreCommand"
    POST_COMMAND = "PostCommand"
    STOP = "Stop"


class HookType(str, Enum):
    """Type of hook action."""

    COMMAND = "command"  # Run a command/script
    PYTHON = "python"  # Run a Python function
    WEBHOOK = "webhook"  # Call a webhook URL


class HookDefinition(BaseModel):
    """Definition of a single hook action.

    Example:
        hook = HookDefinition(
            type=HookType.PYTHON,
            command="attune.hooks.scripts.lessons_reminder:main",
            description="Check for lessons to record at session end"
        )

    """

    type: HookType = Field(
        default=HookType.PYTHON,
        description="Type of hook action",
    )
    command: str = Field(
        ...,
        description="Command to run, Python module:function path, or webhook URL",
    )
    description: str = Field(
        default="",
        description="Human-readable description of what this hook does",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout in seconds for hook execution",
    )
    async_execution: bool = Field(
        default=False,
        description="Run hook asynchronously (don't wait for completion)",
    )
    on_error: str = Field(
        default="log",
        description="Error handling: 'log', 'raise', or 'ignore'",
    )


class HookMatcher(BaseModel):
    """Matcher for determining when a hook should fire.

    Supports tool name matching, file path patterns, and custom conditions.

    Example:
        matcher = HookMatcher(
            tool="Edit",
            file_pattern=r"\\.(ts|tsx|js|jsx)$",
            description="Match TypeScript/JavaScript file edits"
        )

    """

    tool: str | None = Field(
        default=None,
        description="Tool name to match (e.g., 'Bash', 'Edit', 'Read')",
    )
    file_pattern: str | None = Field(
        default=None,
        description="Regex pattern to match file paths",
    )
    command_pattern: str | None = Field(
        default=None,
        description="Regex pattern to match command strings",
    )
    condition: str | None = Field(
        default=None,
        description="Custom condition expression",
    )
    match_all: bool = Field(
        default=False,
        description="If True, matches all events (wildcard)",
    )
    description: str = Field(
        default="",
        description="Human-readable description of match criteria",
    )

    def matches(self, context: dict[str, Any]) -> bool:
        """Check if this matcher matches the given context.

        Args:
            context: Event context with keys like 'tool', 'file_path', 'command'

        Returns:
            True if matcher matches the context

        """
        import re

        # Wildcard matches everything
        if self.match_all:
            return True

        # Tool name matching
        if self.tool and context.get("tool") != self.tool:
            return False

        # File path pattern matching
        if self.file_pattern:
            file_path = context.get("file_path", "")
            if not re.search(self.file_pattern, file_path):
                return False

        # Command pattern matching
        if self.command_pattern:
            command = context.get("command", "")
            if not re.search(self.command_pattern, command):
                return False

        return True


class HookRule(BaseModel):
    """A complete hook rule with matcher and actions.

    Example:
        rule = HookRule(
            matcher=HookMatcher(tool="Edit", file_pattern=r"\\.py$"),
            hooks=[HookDefinition(type=HookType.PYTHON, command="format_python")],
            description="Auto-format Python files after edits"
        )

    """

    matcher: HookMatcher = Field(
        default_factory=lambda: HookMatcher(match_all=True),
        description="Conditions for when this rule fires",
    )
    hooks: list[HookDefinition] = Field(
        default_factory=list,
        description="List of hooks to execute when matched",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this rule is active",
    )
    priority: int = Field(
        default=0,
        description="Execution priority (higher = earlier)",
    )
    description: str = Field(
        default="",
        description="Human-readable description",
    )


class HookConfig(BaseModel):
    """Complete hook configuration for an Empathy session.

    Example YAML configuration:
        hooks:
          Stop:
            - hooks:
                - type: python
                  command: attune.hooks.scripts.lessons_reminder:main
                  description: Check for lessons to record
          PostToolUse:
            - matcher:
                tool: Edit
                file_pattern: "\\.(py)$"
              hooks:
                - type: command
                  command: "ruff format {file_path}"
                  description: Auto-format Python files
    """

    hooks: dict[str, list[HookRule]] = Field(
        default_factory=lambda: {event.value: [] for event in HookEvent},
        description="Hooks organized by event type",
    )
    enabled: bool = Field(
        default=True,
        description="Global enable/disable for all hooks",
    )
    log_executions: bool = Field(
        default=True,
        description="Log hook executions for debugging",
    )
    default_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Default timeout for hooks without explicit timeout",
    )

    def get_hooks_for_event(self, event: HookEvent) -> list[HookRule]:
        """Get all hook rules for a specific event type.

        Args:
            event: The hook event type

        Returns:
            List of HookRule objects for this event, sorted by priority

        """
        rules = self.hooks.get(event.value, [])
        return sorted(
            [r for r in rules if r.enabled],
            key=lambda r: -r.priority,
        )

    def add_hook(
        self,
        event: HookEvent,
        hook: HookDefinition,
        matcher: HookMatcher | None = None,
        priority: int = 0,
    ) -> None:
        """Add a hook for an event.

        Args:
            event: Event type to hook
            hook: Hook definition to add
            matcher: Optional matcher (defaults to match_all)
            priority: Execution priority

        """
        if event.value not in self.hooks:
            self.hooks[event.value] = []

        rule = HookRule(
            matcher=matcher or HookMatcher(match_all=True),
            hooks=[hook],
            priority=priority,
        )
        self.hooks[event.value].append(rule)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "HookConfig":
        """Load hook configuration from a YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            HookConfig instance

        """
        from pathlib import Path

        import yaml

        config_file = Path(yaml_path)
        if not config_file.exists():
            return cls()

        with open(config_file) as f:
            data = yaml.safe_load(f) or {}

        hooks_data = data.get("hooks", {})
        return cls.model_validate({"hooks": hooks_data, **data})

    def to_yaml(self, yaml_path: str) -> None:
        """Save hook configuration to a YAML file.

        Args:
            yaml_path: Path to write YAML configuration

        """
        import yaml

        from attune.security.path_validation import _validate_file_path

        config_file = _validate_file_path(str(yaml_path))
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with config_file.open("w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)
