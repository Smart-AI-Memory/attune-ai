"""First-class verification loops for attune-ai workflows.

Provides automatic post-workflow verification using real tools
(pytest, ruff, mypy, etc.) to close the feedback loop. Inspired
by Boris Cherny's #1 tip: "Give Claude a way to verify its work."

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationResult:
    """Result of a verification step.

    Attributes:
        passed: Whether verification passed.
        strategy: Strategy name (e.g. "run-tests", "lint-check").
        command: The actual shell command that was executed.
        exit_code: Process exit code (0 = success).
        stdout: Captured stdout, truncated to 10KB.
        stderr: Captured stderr, truncated to 10KB.
        duration_ms: How long verification took in milliseconds.
        attempt: Which attempt this was (1-based).
        max_retries: Total retries configured.
        error: Error message if verification itself failed to run.

    """

    passed: bool
    strategy: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    attempt: int
    max_retries: int
    error: str | None = None


__all__ = ["VerificationResult"]
