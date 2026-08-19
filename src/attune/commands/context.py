"""Command Context

Provides execution context for commands with access to hooks, context management,
and learning modules.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from attune.commands.models import CommandConfig, CommandResult

if TYPE_CHECKING:
    from attune.hooks.config import HookEvent
    from attune.hooks.registry import HookRegistry
    from attune.learning.storage import LearnedSkillsStorage
    from attune.llm.state import CollaborationState

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Execution context for commands.

    Provides access to framework components that commands may need:
    - Hook registry for firing events
    - Learning storage for pattern access
    - Collaboration state for user context

    Example:
        # Create context with all components
        ctx = CommandContext(
            user_id="user123",
            hook_registry=hooks,
            learning_storage=storage,
            collaboration_state=state,
        )

        # Commands can access components
        patterns = ctx.get_patterns_for_context()
        ctx.fire_hook("PreCommand", {"command": "compact"})

    """

    user_id: str
    hook_registry: HookRegistry | None = None
    learning_storage: LearnedSkillsStorage | None = None
    collaboration_state: CollaborationState | None = None
    project_root: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def fire_hook(
        self,
        event: str | HookEvent,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fire a hook event.

        Args:
            event: Event type (string or HookEvent enum)
            context: Additional context for the hook

        Returns:
            List of hook execution results

        """
        if self.hook_registry is None:
            logger.debug("No hook registry available, skipping hook")
            return []

        from attune.hooks.config import HookEvent

        # Convert string to enum if needed
        if isinstance(event, str):
            try:
                event = HookEvent(event)
            except ValueError:
                logger.warning("Unknown hook event: %s", event)
                return []

        hook_context = context or {}
        hook_context["user_id"] = self.user_id

        return self.hook_registry.fire_sync(event, hook_context)

    def get_patterns_for_context(
        self,
        max_patterns: int = 5,
    ) -> str:
        """Get learned patterns formatted for context injection.

        Args:
            max_patterns: Maximum patterns to include

        Returns:
            Formatted markdown string

        """
        if self.learning_storage is None:
            return ""

        return self.learning_storage.format_patterns_for_context(
            self.user_id,
            max_patterns=max_patterns,
        )

    def search_patterns(self, query: str) -> list[Any]:
        """Search learned patterns.

        Args:
            query: Search query

        Returns:
            List of matching patterns

        """
        if self.learning_storage is None:
            return []

        return self.learning_storage.search_patterns(self.user_id, query)

    def get_learning_summary(self) -> dict[str, Any]:
        """Get learning summary for user.

        Returns:
            Summary dictionary

        """
        if self.learning_storage is None:
            return {}

        return self.learning_storage.get_summary(self.user_id)


class CommandExecutor:
    """Executes commands with proper hook integration.

    Handles the lifecycle of command execution:
    1. Fire PreCommand hook
    2. Execute command logic
    3. Fire PostCommand hook
    4. Return result

    Example:
        executor = CommandExecutor(context)

        # Execute a command
        result = await executor.execute(compact_command)

        # Check result
        if result.success:
            print(f"Output: {result.output}")

    """

    def __init__(self, context: CommandContext):
        """Initialize the executor.

        Args:
            context: Command execution context

        """
        self.context = context

    def execute(
        self,
        command: CommandConfig,
        args: dict[str, Any] | None = None,
    ) -> CommandResult:
        """Execute a command.

        Args:
            command: Command configuration to execute
            args: Additional arguments

        Returns:
            CommandResult with execution details

        """
        args = args or {}
        start_time = time.time()
        hooks_fired: list[str] = []
        patterns_applied: list[str] = []

        # Fire pre-command hook if configured
        pre_hook = command.hooks.get("pre")
        if pre_hook:
            try:
                self.context.fire_hook(
                    pre_hook,
                    {
                        "command": command.name,
                        "args": args,
                    },
                )
                hooks_fired.append(f"pre:{pre_hook}")
                logger.debug("Pre-command hook fired: %s", pre_hook)
            except Exception as e:  # noqa: BLE001
                logger.error("Pre-command hook failed: %s", e)

        # Get relevant patterns
        if self.context.learning_storage:
            patterns = self.context.search_patterns(command.name)
            patterns_applied = [p.pattern_id for p in patterns[:3]]

        # The actual command execution happens in Claude
        # This executor prepares the context and returns the command body
        output = command.body

        # Fire post-command hook if configured
        post_hook = command.hooks.get("post")
        if post_hook:
            try:
                self.context.fire_hook(
                    post_hook,
                    {
                        "command": command.name,
                        "args": args,
                        "success": True,
                    },
                )
                hooks_fired.append(f"post:{post_hook}")
                logger.debug("Post-command hook fired: %s", post_hook)
            except Exception as e:  # noqa: BLE001
                logger.error("Post-command hook failed: %s", e)

        duration_ms = (time.time() - start_time) * 1000

        return CommandResult(
            command_name=command.name,
            success=True,
            output=output,
            duration_ms=duration_ms,
            hooks_fired=hooks_fired,
            patterns_applied=patterns_applied,
        )

    def prepare_command(
        self,
        command: CommandConfig,
        args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prepare command for execution without running hooks.

        Useful for getting command context before actual execution.

        Args:
            command: Command configuration
            args: Additional arguments

        Returns:
            Dictionary with prepared command context

        """
        args = args or {}

        # Get relevant patterns
        patterns_context = ""
        if self.context.learning_storage:
            patterns_context = self.context.get_patterns_for_context(max_patterns=3)

        return {
            "command": command.name,
            "description": command.description,
            "body": command.body,
            "args": args,
            "patterns_context": patterns_context,
            "user_id": self.context.user_id,
            "has_hooks": bool(command.hooks),
        }


def create_command_context(
    user_id: str,
    project_root: str | Path | None = None,
    enable_hooks: bool = True,
    enable_learning: bool = True,
) -> CommandContext:
    """Create a CommandContext with available components.

    Factory function that creates a context with the requested
    components, handling import errors gracefully.

    Args:
        user_id: User identifier
        project_root: Project root directory
        enable_hooks: Enable hook integration
        enable_learning: Enable learning integration

    Returns:
        Configured CommandContext

    """
    hook_registry = None
    learning_storage = None

    if enable_hooks:
        try:
            from attune.hooks.registry import HookRegistry

            hook_registry = HookRegistry()
        except ImportError:
            logger.debug("Hooks module not available")

    if enable_learning:
        try:
            from attune.learning.storage import LearnedSkillsStorage

            learning_storage = LearnedSkillsStorage()
        except ImportError:
            logger.debug("Learning module not available")

    return CommandContext(
        user_id=user_id,
        hook_registry=hook_registry,
        learning_storage=learning_storage,
        project_root=Path(project_root) if project_root else None,
    )
