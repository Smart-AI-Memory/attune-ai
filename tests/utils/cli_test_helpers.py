"""Test utilities for CLI command testing.

Provides mocking utilities and helpers for testing Typer CLI commands.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch


class MockTyperContext:
    """Mock Typer context for CLI tests.

    Simulates the Typer context object that's passed to commands.
    """

    def __init__(self, obj: dict | None = None):
        """Initialize mock context.

        Args:
            obj: Optional context object dictionary

        """
        self.obj = obj or {}
        self.parent = None
        self.invoked_subcommand = None
        self.command_path = "test"


def mock_cli_command(
    command_func: Callable,
    args: list[str] | None = None,
    mock_dependencies: dict[str, Any] | None = None,
) -> tuple[Any, MockTyperContext]:
    """Mock a Typer CLI command for testing.

    Args:
        command_func: The command function to test
        args: Command line arguments (not used currently, for future CLI runner)
        mock_dependencies: Dependencies to mock (file ops, API calls, etc.)

    Returns:
        Tuple of (result, context)

    Example:
        >>> def my_command():
        ...     return "result"
        >>> result, ctx = mock_cli_command(my_command)
        >>> assert result == "result"

    """
    ctx = MockTyperContext()

    # Apply mocks if provided
    active_mocks = []
    if mock_dependencies:
        for target, mock_value in mock_dependencies.items():
            mock_obj = patch(target, mock_value)
            active_mocks.append(mock_obj)
            mock_obj.start()

    try:
        result = command_func()
        return result, ctx
    finally:
        # Clean up all mocks
        for mock_obj in active_mocks:
            mock_obj.stop()


def mock_file_operations() -> dict[str, Any]:
    """Create mock file operations for CLI tests.

    Returns:
        Dictionary of mock targets and their mock objects

    Example:
        >>> mocks = mock_file_operations()
        >>> result, ctx = mock_cli_command(command, mock_dependencies=mocks)

    """
    mock_path = Mock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.is_file.return_value = True
    mock_path.read_text.return_value = "mock file content"
    mock_path.write_text.return_value = None
    mock_path.mkdir.return_value = None
    mock_path.__truediv__ = lambda self, other: mock_path  # For path / "subdir"
    mock_path.__str__ = lambda self: "/mock/path"

    return {
        "pathlib.Path": MagicMock(return_value=mock_path),
        "builtins.open": MagicMock(),
    }


def mock_workflow_execution() -> dict[str, Any]:
    """Create mock workflow execution for CLI tests.

    Returns:
        Dictionary of mock targets for workflow operations

    Example:
        >>> mocks = mock_workflow_execution()
        >>> result, ctx = mock_cli_command(workflow_command, mock_dependencies=mocks)

    """
    mock_result = {
        "status": "success",
        "result": "Mock workflow result",
        "cost": 0.001,
        "tokens": {"input": 100, "output": 50},
    }

    return {
        "attune.workflows.base.BaseWorkflow.execute": MagicMock(return_value=mock_result),
    }


def mock_memory_backend() -> dict[str, Any]:
    """Create mock memory backend for CLI tests.

    Returns:
        Dictionary of mock targets for memory operations

    Example:
        >>> mocks = mock_memory_backend()
        >>> result, ctx = mock_cli_command(memory_command, mock_dependencies=mocks)

    """
    mock_memory = Mock()
    mock_memory.stash.return_value = True
    mock_memory.retrieve.return_value = {"key": "value"}
    mock_memory.search_patterns.return_value = []

    return {
        "attune.memory.unified.UnifiedMemory": MagicMock(return_value=mock_memory),
    }


def mock_template_registry() -> dict[str, Any]:
    """Create mock template registry for CLI tests.

    Returns:
        Dictionary of mock targets for template operations

    Example:
        >>> mocks = mock_template_registry()
        >>> result, ctx = mock_cli_command(template_command, mock_dependencies=mocks)

    """
    mock_registry = {
        "test-template": {
            "name": "Test Template",
            "description": "A test template",
            "steps": ["step1", "step2"],
        },
        "another-template": {
            "name": "Another Template",
            "description": "Another test template",
            "steps": ["step1"],
        },
    }

    return {
        "attune.meta_workflows.template_registry.TEMPLATE_REGISTRY": mock_registry,
    }


def mock_analytics_backend() -> dict[str, Any]:
    """Create mock analytics backend for CLI tests.

    Returns:
        Dictionary of mock targets for analytics operations

    Example:
        >>> mocks = mock_analytics_backend()
        >>> result, ctx = mock_cli_command(analytics_command, mock_dependencies=mocks)

    """
    mock_runs = [
        {
            "run_id": "test-run-1",
            "workflow": "test-workflow",
            "status": "completed",
            "cost": 0.001,
        },
        {
            "run_id": "test-run-2",
            "workflow": "another-workflow",
            "status": "completed",
            "cost": 0.002,
        },
    ]

    return {
        "attune.meta_workflows.execution_tracker.get_recent_runs": MagicMock(
            return_value=mock_runs,
        ),
    }


def create_mock_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a mock configuration dictionary.

    Args:
        overrides: Optional configuration overrides

    Returns:
        Mock configuration dictionary

    Example:
        >>> config = create_mock_config({"tier_routing": False})
        >>> assert config["tier_routing"] is False

    """
    default_config = {
        "tier_routing": True,
        "max_tokens": 4000,
        "cache_enabled": True,
        "telemetry_enabled": False,
        "user_id": "test-user",
        "api_key": "test-api-key",
    }

    if overrides:
        default_config.update(overrides)

    return default_config
