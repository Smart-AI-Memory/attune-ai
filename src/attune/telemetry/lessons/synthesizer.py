"""Lesson Synthesizer for Attune AI.

Synthesizes raw failure telemetry into formatted Gotcha and Lesson markdown entries.
"""

from typing import Any


class LessonSynthesizer:
    """Synthesizes failure telemetry into structured lesson entries."""

    def synthesize_lesson(self, telemetry: dict[str, Any]) -> str:
        """Converts raw telemetry into formatted lesson markdown string.

        Args:
            telemetry: Dictionary emitted by TrapFailureListener.

        Returns:
            Formatted lesson markdown entry.
        """
        failure_type = telemetry.get("failure_type", "unknown_failure")

        if failure_type == "pre_commit_hook_rejection":
            hook_id = telemetry.get("hook_id", "guard")
            cmd = telemetry.get("command", "")
            err = telemetry.get("error_output", "").strip()

            return (
                f"### Gotcha: Pre-commit hook '{hook_id}' rejection\n"
                f"- **Pattern:** Failed pre-commit execution when running `{cmd}`.\n"
                f"- **Root Cause:** {err[:150]}...\n"
                f"- **Prevention:** Inspect file parameters and pre-flight hook before committing.\n"
            )

        elif failure_type == "unit_test_failure":
            test_name = telemetry.get("test_name", "test")
            err_msg = telemetry.get("error_message", "").strip()

            return (
                f"### Lesson: Test failure in '{test_name}'\n"
                f"- **Pattern:** Test assertion failure during verification.\n"
                f"- **Root Cause:** {err_msg[:150]}...\n"
                f"- **Prevention:** Verify boundary conditions and mock setups before re-running test.\n"
            )

        return f"### Lesson: Generic failure observed in {failure_type}\n"
