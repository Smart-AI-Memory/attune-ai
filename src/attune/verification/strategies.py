"""Built-in verification strategies.

Each strategy maps to a shell command that verifies workflow output.
Strategies are subprocess-based (real tools, not LLM calls).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VerificationStrategy(ABC):
    """Abstract base class for verification strategies.

    Subclasses provide a shell command to run for verification
    and optionally custom result parsing logic.
    """

    name: str = ""

    @abstractmethod
    def get_command(self, workflow_name: str, workflow_result: Any) -> str:
        """Return the shell command to run for verification.

        Args:
            workflow_name: Name of the workflow being verified.
            workflow_result: The WorkflowResult from execution.

        Returns:
            Shell command string.

        """

    def parse_result(
        self,
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> bool:
        """Parse whether verification passed.

        Default: exit code 0 means pass.

        Args:
            returncode: Process exit code.
            stdout: Captured standard output.
            stderr: Captured standard error.

        Returns:
            True if verification passed.

        """
        return returncode == 0


class RunTestsStrategy(VerificationStrategy):
    """Run the project test suite via pytest."""

    name = "run-tests"

    def get_command(self, workflow_name: str, workflow_result: Any) -> str:
        """Return pytest command."""
        return "pytest tests/ -x --tb=short -q"


class LintCheckStrategy(VerificationStrategy):
    """Run the Ruff linter in check-only mode."""

    name = "lint-check"

    def get_command(self, workflow_name: str, workflow_result: Any) -> str:
        """Return ruff check command."""
        return "ruff check src/ --no-fix"


class TypeCheckStrategy(VerificationStrategy):
    """Run MyPy type checking."""

    name = "type-check"

    def get_command(self, workflow_name: str, workflow_result: Any) -> str:
        """Return mypy command."""
        return "mypy src/ --ignore-missing-imports"


class BuildStrategy(VerificationStrategy):
    """Run the Python build process."""

    name = "build"

    def get_command(self, workflow_name: str, workflow_result: Any) -> str:
        """Return build command."""
        return "python -m build --no-isolation"


class CustomCommandStrategy(VerificationStrategy):
    """Run a user-provided custom command."""

    name = "custom-command"

    def __init__(self, command: str) -> None:
        """Initialize with a custom command string.

        Args:
            command: The shell command to execute.

        """
        self._command = command

    def get_command(self, workflow_name: str, workflow_result: Any) -> str:
        """Return the custom command."""
        return self._command


# Registry of built-in strategies by name.
STRATEGY_REGISTRY: dict[str, type[VerificationStrategy]] = {
    "run-tests": RunTestsStrategy,
    "lint-check": LintCheckStrategy,
    "type-check": TypeCheckStrategy,
    "build": BuildStrategy,
}


def get_strategy(
    strategy_name: str,
    custom_command: str | None = None,
) -> VerificationStrategy | None:
    """Look up a verification strategy by name.

    Args:
        strategy_name: Strategy name (e.g. "run-tests").
        custom_command: Required when strategy_name is "custom-command".

    Returns:
        Strategy instance, or None if strategy_name is "none".

    Raises:
        ValueError: If strategy_name is unknown or custom-command
            is used without a command string.

    """
    if strategy_name == "none":
        return None

    if strategy_name == "custom-command":
        if not custom_command:
            raise ValueError("custom-command strategy requires a 'command' in config")
        return CustomCommandStrategy(custom_command)

    strategy_cls = STRATEGY_REGISTRY.get(strategy_name)
    if strategy_cls is None:
        raise ValueError(
            f"Unknown verification strategy: {strategy_name!r}. "
            f"Available: {', '.join(STRATEGY_REGISTRY)} or 'custom-command'",
        )

    return strategy_cls()


__all__ = [
    "STRATEGY_REGISTRY",
    "BuildStrategy",
    "CustomCommandStrategy",
    "LintCheckStrategy",
    "RunTestsStrategy",
    "TypeCheckStrategy",
    "VerificationStrategy",
    "get_strategy",
]
