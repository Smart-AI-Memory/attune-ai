"""Verification configuration.

Defines the VerificationConfig dataclass and loading logic for
per-workflow verification settings.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VerificationConfig:
    """Configuration for a workflow's verification step.

    Attributes:
        enabled: Whether verification is enabled.
        strategy: Strategy name or "auto" for default lookup.
        command: Custom command (used with "custom-command" strategy).
        max_retries: Max retry attempts after initial failure.
        timeout_seconds: Per-verification timeout.
        fail_open: If True, failed verification does not fail the workflow.
        working_directory: Override cwd for the verification command.
        correction_enabled: If True, feed verification errors back to
            the LLM for self-correction before retrying.
        max_corrections: Max LLM correction attempts per verification loop.

    """

    enabled: bool = True
    strategy: str = "auto"
    command: str | None = None
    max_retries: int = 2
    timeout_seconds: int = 300
    fail_open: bool = False
    working_directory: str | None = None
    correction_enabled: bool = False
    max_corrections: int = 2

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationConfig:
        """Create config from a dictionary.

        Args:
            data: Dictionary with verification settings.

        Returns:
            VerificationConfig instance.

        """
        return cls(
            enabled=data.get("enabled", True),
            strategy=data.get("strategy", "auto"),
            command=data.get("command"),
            max_retries=data.get("max_retries", 2),
            timeout_seconds=data.get("timeout_seconds", 300),
            fail_open=data.get("fail_open", False),
            working_directory=data.get("working_directory"),
            correction_enabled=data.get("correction_enabled", False),
            max_corrections=data.get("max_corrections", 2),
        )

    @classmethod
    def load_for_workflow(
        cls,
        workflow_name: str,
        verification_data: dict[str, Any] | None,
    ) -> VerificationConfig | None:
        """Load verification config for a specific workflow.

        Merges global verification settings with per-workflow overrides.

        Args:
            workflow_name: The workflow name (e.g. "code-review").
            verification_data: The raw "verification" section from config.

        Returns:
            VerificationConfig or None if verification is disabled.

        """
        if verification_data is None:
            return None

        if not verification_data.get("enabled", True):
            return None

        # Start with global defaults
        global_config: dict[str, Any] = {
            k: v for k, v in verification_data.items() if k != "workflows"
        }

        # Merge per-workflow overrides
        per_workflow = verification_data.get("workflows", {})
        if workflow_name in per_workflow:
            workflow_overrides = per_workflow[workflow_name]
            if isinstance(workflow_overrides, dict):
                global_config.update(workflow_overrides)

        return cls.from_dict(global_config)


__all__ = ["VerificationConfig"]
