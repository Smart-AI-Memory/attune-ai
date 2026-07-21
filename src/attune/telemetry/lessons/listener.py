"""Trap Failure Listener for Attune AI.

Listens to hook execution logs, test outputs, and CLI non-zero exits to extract
structured failure telemetry.
"""

from typing import Any


class TrapFailureListener:
    """Captures execution failures from pre-commit hooks, tests, and CLI runs."""

    def capture_precommit_failure(
        self,
        hook_id: str,
        command: str,
        output: str,
        file_target: str | None = None,
    ) -> dict[str, Any]:
        """Captures telemetry from a failed pre-commit hook execution.

        Args:
            hook_id: Name/ID of the failing hook (e.g. 'eval-exec-guard').
            command: Command that was executed.
            output: Error output or stdout/stderr stream.
            file_target: Target file path if applicable.

        Returns:
            Structured failure telemetry dictionary.
        """
        return {
            "failure_type": "pre_commit_hook_rejection",
            "hook_id": hook_id,
            "command": command,
            "error_output": output,
            "file_target": file_target or "",
        }

    def capture_test_failure(
        self,
        test_name: str,
        error_message: str,
        file_path: str | None = None,
    ) -> dict[str, Any]:
        """Captures telemetry from a failed unit or integration test.

        Args:
            test_name: Identifier of the failing test.
            error_message: Stack trace or failure assertion.
            file_path: Path of the test file.

        Returns:
            Structured failure telemetry dictionary.
        """
        return {
            "failure_type": "unit_test_failure",
            "test_name": test_name,
            "error_message": error_message,
            "file_path": file_path or "",
        }
