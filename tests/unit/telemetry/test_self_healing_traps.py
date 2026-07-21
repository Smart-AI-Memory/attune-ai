"""Unit tests for Self-Healing Traps & Lesson Synthesis."""

from attune.telemetry.lessons import (
    LessonSynthesizer,
    MemoryHydrator,
    TrapFailureListener,
)


class TestTrapFailureListener:
    """Tests for TrapFailureListener."""

    def test_capture_precommit_failure(self) -> None:
        listener = TrapFailureListener()
        telemetry = listener.capture_precommit_failure(
            hook_id="eval-exec-guard",
            command="git commit -m 'test'",
            output="Commit message contains eval(",
        )
        assert telemetry["failure_type"] == "pre_commit_hook_rejection"
        assert telemetry["hook_id"] == "eval-exec-guard"

    def test_capture_test_failure(self) -> None:
        listener = TrapFailureListener()
        telemetry = listener.capture_test_failure(
            test_name="test_login",
            error_message="AssertionError: 401 != 200",
        )
        assert telemetry["failure_type"] == "unit_test_failure"
        assert telemetry["test_name"] == "test_login"


class TestLessonSynthesizer:
    """Tests for LessonSynthesizer."""

    def test_synthesize_lesson_formatting(self) -> None:
        synthesizer = LessonSynthesizer()
        telemetry = {
            "failure_type": "pre_commit_hook_rejection",
            "hook_id": "eval-exec-guard",
            "command": "git commit",
            "error_output": "Commit message blocked by eval guard",
        }
        lesson = synthesizer.synthesize_lesson(telemetry)

        assert "### Gotcha: Pre-commit hook 'eval-exec-guard' rejection" in lesson
        assert "Commit message blocked by eval guard" in lesson


class TestMemoryHydrator:
    """Tests for MemoryHydrator."""

    def test_ephemeral_ghost_trajectory_withheld(self) -> None:
        hydrator = MemoryHydrator()
        res = hydrator.persist_lesson("### Lesson test", is_ephemeral=True)
        assert res is False
