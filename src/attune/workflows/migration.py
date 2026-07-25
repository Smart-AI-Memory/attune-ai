"""Workflow Migration System

Environment-aware workflow migration with config-driven preferences.
Helps users transition from deprecated workflows to consolidated versions.

Behavior:
- CI/Non-interactive: Silent aliasing with log message
- First interactive use: Show dialog with "remember" option
- Subsequent uses: Follow stored preference
- Config override: Users can set migration mode globally

Usage:
    from attune.workflows.migration import resolve_workflow_migration

    # Returns (canonical_name, kwargs, was_migrated)
    name, kwargs, migrated = resolve_workflow_migration("test-gen-behavioral")

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Migration mode options
MIGRATION_MODE_PROMPT = "prompt"  # Ask user on first use
MIGRATION_MODE_AUTO = "auto"  # Silently use new syntax
MIGRATION_MODE_LEGACY = "legacy"  # Keep using old syntax (deprecated)

# Workflow aliases: old_name -> (new_name, default_kwargs)
WORKFLOW_ALIASES: dict[str, tuple[str, dict[str, Any]]] = {
    # Code Review consolidation
    "pro-review": ("code-review", {"mode": "premium"}),
    "pr-review": ("code-review", {"mode": "security"}),
    # Test Generation consolidation
    "test-gen-behavioral": ("test-gen", {"style": "behavioral"}),
    "test-coverage-boost": ("test-gen", {"target": "coverage"}),
    "test-gen-parallel": ("test-gen", {"parallel": True}),
    "autonomous-test-gen": ("test-gen", {"autonomous": True}),
    "progressive-test-gen": ("test-gen", {"progressive": True}),
    # Release consolidation
    "secure-release": ("release-prep", {"mode": "secure"}),
    "orchestrated-release-prep": ("release-prep", {"mode": "full"}),
    # Deprecated (show warning, map to replacement)
    "release-prep-legacy": ("release-prep", {"mode": "standard", "_deprecated": True}),
    "document-manager": ("doc-gen", {"_deprecated": True}),
    # Removed (show error with migration path)
    "test5": (
        None,
        {"_removed": True, "_message": "test5 was a test artifact and has been removed"},
    ),
    "manage-docs": (
        None,
        {
            "_removed": True,
            "_message": "manage-docs was incomplete. Use doc-gen or doc-orchestrator",
        },
    ),
}

# Human-readable descriptions for the dialog
WORKFLOW_DESCRIPTIONS: dict[str, str] = {
    "code-review": "Comprehensive code analysis with optional premium mode",
    "test-gen": "Generate tests with style, target, parallel, and autonomous options",
    "release-prep": "Release readiness with modes: standard, secure, or full",
    "doc-gen": "Generate documentation for code",
}


@dataclass
class MigrationConfig:
    """Configuration for workflow migration behavior.

    Attributes:
        mode: How to handle migrations (prompt, auto, legacy)
        remembered_choices: User's choices for specific workflows
        show_tips: Whether to show migration tips after workflow runs
        last_prompted: Track when workflows were last prompted

    """

    mode: str = MIGRATION_MODE_PROMPT
    remembered_choices: dict[str, str] = field(default_factory=dict)
    show_tips: bool = True
    last_prompted: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "MigrationConfig":
        """Load migration config from .attune/migration.json.

        Returns:
            MigrationConfig with saved preferences, or defaults.

        """
        config_path = Path.cwd() / ".attune" / "migration.json"

        if config_path.exists():
            try:
                with config_path.open() as f:
                    data = json.load(f)
                return cls(
                    mode=data.get("mode", MIGRATION_MODE_PROMPT),
                    remembered_choices=data.get("remembered_choices", {}),
                    show_tips=data.get("show_tips", True),
                    last_prompted=data.get("last_prompted", {}),
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load migration config: {e}")

        return cls()

    def save(self) -> None:
        """Save migration config to .attune/migration.json."""
        config_dir = Path.cwd() / ".attune"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "migration.json"

        try:
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "mode": self.mode,
                        "remembered_choices": self.remembered_choices,
                        "show_tips": self.show_tips,
                        "last_prompted": self.last_prompted,
                    },
                    f,
                    indent=2,
                )
        except OSError as e:
            logger.warning(f"Failed to save migration config: {e}")

    def remember_choice(self, old_name: str, choice: str) -> None:
        """Remember user's migration choice for a workflow.

        Args:
            old_name: The deprecated workflow name
            choice: Either "new" or "legacy"

        """
        self.remembered_choices[old_name] = choice
        self.save()


def is_interactive() -> bool:
    """Check if we're running in an interactive terminal.

    Returns:
        False in CI environments or when stdin is not a TTY.

    """
    # Check common CI environment variables
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "CIRCLECI", "TRAVIS"]
    if any(os.getenv(var) for var in ci_vars):
        return False

    # Check for explicit non-interactive flag
    if os.getenv("ATTUNE_NO_INTERACTIVE"):
        return False

    # Check if stdin is a TTY
    return sys.stdin.isatty()


def show_migration_dialog(
    old_name: str,
    new_name: str,
    kwargs: dict[str, Any],
) -> tuple[str, dict[str, Any], bool]:
    """Show interactive migration dialog to user.

    Args:
        old_name: The deprecated workflow name
        new_name: The new canonical workflow name
        kwargs: Default kwargs for the new workflow

    Returns:
        Tuple of (chosen_name, chosen_kwargs, should_remember)

    """
    # Build the new command string
    flag_parts = []
    for key, value in kwargs.items():
        if key.startswith("_"):
            continue
        if isinstance(value, bool) and value:
            flag_parts.append(f"--{key.replace('_', '-')}")
        else:
            flag_parts.append(f"--{key.replace('_', '-')} {value}")

    new_command = f"attune workflow run {new_name}"
    if flag_parts:
        new_command += " " + " ".join(flag_parts)

    description = WORKFLOW_DESCRIPTIONS.get(new_name, "")

    # Print dialog
    print()
    print("┌" + "─" * 68 + "┐")
    print("│" + " Workflow Migration ".center(68) + "│")
    print("├" + "─" * 68 + "┤")
    print(f"│  '{old_name}' has been consolidated into '{new_name}'".ljust(69) + "│")
    if description:
        print(f"│  {description[:64]}".ljust(69) + "│")
    print("│" + " " * 68 + "│")
    print("│  New syntax:".ljust(69) + "│")
    print(f"│    {new_command[:62]}".ljust(69) + "│")
    print("│" + " " * 68 + "│")
    print("│  How would you like to proceed?".ljust(69) + "│")
    print("│" + " " * 68 + "│")
    print("│  1. Use new syntax (recommended)".ljust(69) + "│")
    print("│  2. Continue with legacy behavior (deprecated)".ljust(69) + "│")
    print("│  3. Always use new syntax (don't ask again)".ljust(69) + "│")
    print("│  4. Always use legacy (don't ask again)".ljust(69) + "│")
    print("└" + "─" * 68 + "┘")
    print()

    while True:
        try:
            choice = input("Enter choice [1-4]: ").strip()

            if choice == "1":
                return new_name, kwargs, False
            if choice == "2":
                return old_name, {}, False
            if choice == "3":
                return new_name, kwargs, True  # Remember: use new
            if choice == "4":
                return old_name, {}, True  # Remember: use legacy
            print("Please enter 1, 2, 3, or 4")
        except (EOFError, KeyboardInterrupt):
            # User cancelled - default to new syntax
            print("\nDefaulting to new syntax...")
            return new_name, kwargs, False


def show_removed_workflow_error(old_name: str, message: str) -> None:
    """Show error for removed workflows with migration guidance.

    Args:
        old_name: The removed workflow name
        message: Explanation of why it was removed and alternatives

    """
    print()
    print("┌" + "─" * 68 + "┐")
    print("│" + " Workflow Removed ".center(68) + "│")
    print("├" + "─" * 68 + "┤")
    print(f"│  '{old_name}' is no longer available.".ljust(69) + "│")
    print("│" + " " * 68 + "│")
    # Word wrap the message
    words = message.split()
    line = "│  "
    for word in words:
        if len(line) + len(word) + 1 > 67:
            print(line.ljust(69) + "│")
            line = "│  " + word + " "
        else:
            line += word + " "
    if line.strip() != "│":
        print(line.ljust(69) + "│")
    print("│" + " " * 68 + "│")
    print("│  Run 'attune workflow list' to see available workflows.".ljust(69) + "│")
    print("└" + "─" * 68 + "┘")
    print()


def show_deprecation_warning(old_name: str, new_name: str, kwargs: dict[str, Any]) -> None:
    """Show deprecation warning via logger (non-blocking).

    Args:
        old_name: The deprecated workflow name
        new_name: The canonical replacement name
        kwargs: Default kwargs for the new workflow

    """
    flag_parts = []
    for key, value in kwargs.items():
        if key.startswith("_"):
            continue
        if isinstance(value, bool) and value:
            flag_parts.append(f"--{key.replace('_', '-')}")
        else:
            flag_parts.append(f"--{key.replace('_', '-')} {value}")

    new_command = f"attune workflow run {new_name}"
    if flag_parts:
        new_command += " " + " ".join(flag_parts)

    logger.warning(
        f"'{old_name}' is deprecated. Use '{new_command}' instead. "
        f"Set ATTUNE_NO_INTERACTIVE=1 to suppress this warning in CI.",
    )


def resolve_workflow_migration(
    workflow_name: str,
    config: MigrationConfig | None = None,
) -> tuple[str, dict[str, Any], bool]:
    """Resolve a workflow name, handling migrations as needed.

    This is the main entry point for the migration system.

    Args:
        workflow_name: The workflow name from user input
        config: Optional migration config (loads from file if not provided)

    Returns:
        Tuple of:
            - resolved_name: The canonical workflow name to use
            - kwargs: Additional kwargs to pass to the workflow
            - was_migrated: True if the workflow was migrated

    Raises:
        SystemExit: If workflow has been removed

    """
    # Not an aliased workflow - return as-is
    if workflow_name not in WORKFLOW_ALIASES:
        return workflow_name, {}, False

    new_name, kwargs = WORKFLOW_ALIASES[workflow_name]

    # Handle removed workflows
    if kwargs.get("_removed"):
        message = kwargs.get("_message", "This workflow has been removed.")
        if is_interactive():
            show_removed_workflow_error(workflow_name, message)
        else:
            logger.error(f"Workflow '{workflow_name}' has been removed: {message}")
        raise SystemExit(1)

    # Load config if not provided
    if config is None:
        config = MigrationConfig.load()

    # Check if user has a remembered choice
    if workflow_name in config.remembered_choices:
        remembered = config.remembered_choices[workflow_name]
        if remembered == "new":
            logger.debug(f"Using remembered choice: {new_name}")
            return new_name, kwargs, True
        if remembered == "legacy":
            logger.debug(f"Using remembered choice: {workflow_name} (legacy)")
            return workflow_name, {}, True

    # Handle based on mode and environment
    is_deprecated = kwargs.get("_deprecated", False)

    if not is_interactive():
        # CI/non-interactive: silent aliasing with log
        if config.mode == MIGRATION_MODE_LEGACY:
            logger.info(f"Using legacy workflow '{workflow_name}' (migration mode: legacy)")
            return workflow_name, {}, False
        show_deprecation_warning(workflow_name, new_name, kwargs)
        return new_name, kwargs, True

    # Interactive mode
    if config.mode == MIGRATION_MODE_AUTO:
        # Auto-migrate without prompting
        show_deprecation_warning(workflow_name, new_name, kwargs)
        return new_name, kwargs, True

    if config.mode == MIGRATION_MODE_LEGACY:
        # Use legacy behavior
        if is_deprecated:
            show_deprecation_warning(workflow_name, new_name, kwargs)
        return workflow_name, {}, False

    # MIGRATION_MODE_PROMPT
    # Show interactive dialog
    chosen_name, chosen_kwargs, remember = show_migration_dialog(
        workflow_name,
        new_name,
        kwargs,
    )

    if remember:
        if chosen_name == new_name:
            config.remember_choice(workflow_name, "new")
        else:
            config.remember_choice(workflow_name, "legacy")

    was_migrated = chosen_name == new_name
    return chosen_name, chosen_kwargs, was_migrated


def show_migration_tip(old_name: str, new_name: str, kwargs: dict[str, Any]) -> None:
    """Show a migration tip after workflow completion.

    Prints a one-line tip to stdout in interactive terminals.
    Respects the ``show_tips`` config setting.

    Args:
        old_name: The deprecated workflow name used
        new_name: The canonical replacement name
        kwargs: Default kwargs for the new workflow

    """
    config = MigrationConfig.load()
    if not config.show_tips:
        return

    if not is_interactive():
        return

    # Build command
    flag_parts = []
    for key, value in kwargs.items():
        if key.startswith("_"):
            continue
        if isinstance(value, bool) and value:
            flag_parts.append(f"--{key.replace('_', '-')}")
        else:
            flag_parts.append(f"--{key.replace('_', '-')} {value}")

    new_command = f"attune workflow run {new_name}"
    if flag_parts:
        new_command += " " + " ".join(flag_parts)

    print()
    print(f"💡 Tip: '{old_name}' is now '{new_command}'")
    print("   Run 'attune config set workflow.migration.mode auto' to auto-migrate")
    print("   Run 'attune config set workflow.migration.show_tips false' to hide tips")
    print()


def get_canonical_workflow_name(workflow_name: str) -> str:
    """Get the canonical (new) name for a workflow.

    Args:
        workflow_name: Any workflow name (old or new)

    Returns:
        The canonical name, or the input unchanged if not aliased.

    """
    if workflow_name in WORKFLOW_ALIASES:
        new_name, _ = WORKFLOW_ALIASES[workflow_name]
        return new_name or workflow_name
    return workflow_name


def list_migrations() -> list[dict[str, Any]]:
    """List all workflow migrations for documentation.

    Returns:
        List of dicts with keys: old_name, new_name, status
        (consolidated/deprecated/removed), kwargs, and message.

    """
    migrations = []
    for old_name, (new_name, kwargs) in WORKFLOW_ALIASES.items():
        if new_name is None:
            status = "removed"
        elif kwargs.get("_deprecated"):
            status = "deprecated"
        else:
            status = "consolidated"

        migrations.append(
            {
                "old_name": old_name,
                "new_name": new_name,
                "status": status,
                "kwargs": {k: v for k, v in kwargs.items() if not k.startswith("_")},
                "message": kwargs.get("_message", ""),
            },
        )

    return migrations
