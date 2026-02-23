"""Verification runner.

Executes a verification strategy as a subprocess and returns
a structured result. Uses shlex.split + shell=False for security.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from datetime import datetime
from typing import Any

from .config import VerificationConfig
from .strategies import VerificationStrategy

logger = logging.getLogger(__name__)

# Maximum output capture size (10KB)
_MAX_OUTPUT_BYTES = 10240


def run_verification(
    config: VerificationConfig,
    strategy: VerificationStrategy,
    workflow_name: str,
    workflow_result: Any,
    attempt: int = 1,
) -> dict[str, Any]:
    """Execute a single verification attempt.

    Runs the strategy's command as a subprocess and captures the
    result. Never raises exceptions -- all errors are captured in
    the returned dict.

    Args:
        config: Verification configuration.
        strategy: The strategy to execute.
        workflow_name: Name of the workflow being verified.
        workflow_result: The WorkflowResult from execution.
        attempt: Which attempt this is (1-based).

    Returns:
        Dict with keys matching VerificationResult fields.

    """
    from . import VerificationResult

    command = config.command or strategy.get_command(workflow_name, workflow_result)
    cmd_args = shlex.split(command)

    start = datetime.now()

    try:
        proc = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            cwd=config.working_directory,
        )
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        passed = strategy.parse_result(proc.returncode, proc.stdout, proc.stderr)

        return VerificationResult(
            passed=passed,
            strategy=strategy.name,
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout[:_MAX_OUTPUT_BYTES],
            stderr=proc.stderr[:_MAX_OUTPUT_BYTES],
            duration_ms=duration_ms,
            attempt=attempt,
            max_retries=config.max_retries,
        )

    except subprocess.TimeoutExpired:
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        logger.warning(
            "Verification timed out after %ds: %s",
            config.timeout_seconds,
            command,
        )
        return VerificationResult(
            passed=False,
            strategy=strategy.name,
            command=command,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_ms=duration_ms,
            attempt=attempt,
            max_retries=config.max_retries,
            error=f"Timed out after {config.timeout_seconds}s",
        )

    except FileNotFoundError as e:
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        logger.warning("Verification command not found: %s (%s)", command, e)
        return VerificationResult(
            passed=False,
            strategy=strategy.name,
            command=command,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_ms=duration_ms,
            attempt=attempt,
            max_retries=config.max_retries,
            error=f"Command not found: {cmd_args[0]}",
        )

    except OSError as e:
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        logger.warning("Verification OS error: %s (%s)", command, e)
        return VerificationResult(
            passed=False,
            strategy=strategy.name,
            command=command,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_ms=duration_ms,
            attempt=attempt,
            max_retries=config.max_retries,
            error=f"OS error: {e}",
        )


__all__ = ["run_verification"]
