"""Tests for the VerificationMixin."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

from attune.verification import VerificationResult
from attune.verification.config import VerificationConfig
from attune.verification.mixin import VerificationMixin


@dataclass
class FakeWorkflowResult:
    """Minimal WorkflowResult stand-in for testing."""

    success: bool = True
    error: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FakeWorkflow(VerificationMixin):
    """Minimal workflow-like object for mixin testing."""

    def __init__(
        self,
        name: str = "test-workflow",
        config: Any = None,
    ) -> None:
        self.name = name
        self._config = config
        self._verification_config: VerificationConfig | None = None


class TestVerificationMixinInit:
    """Test _init_verification behavior."""

    def test_no_config_sets_none(self) -> None:
        """Test mixin with no config results in None."""
        wf = FakeWorkflow(config=None)
        wf._init_verification()
        assert wf._verification_config is None

    def test_config_without_verification_sets_none(self) -> None:
        """Test config without verification key results in None."""
        config = MagicMock()
        config.verification = None
        wf = FakeWorkflow(config=config)
        wf._init_verification()
        assert wf._verification_config is None

    def test_config_with_verification_loads(self) -> None:
        """Test config with verification data creates config."""
        config = MagicMock()
        config.verification = {
            "enabled": True,
            "strategy": "run-tests",
            "max_retries": 1,
        }
        wf = FakeWorkflow(name="test-gen", config=config)
        wf._init_verification()
        assert wf._verification_config is not None
        assert wf._verification_config.strategy == "run-tests"
        assert wf._verification_config.max_retries == 1

    def test_config_disabled_returns_none(self) -> None:
        """Test disabled verification returns None."""
        config = MagicMock()
        config.verification = {"enabled": False}
        wf = FakeWorkflow(config=config)
        wf._init_verification()
        assert wf._verification_config is None


class TestVerificationMixinLoop:
    """Test _run_verification_loop behavior."""

    def test_noop_when_config_is_none(self) -> None:
        """Test loop no-ops when config is None."""
        wf = FakeWorkflow()
        wf._verification_config = None
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert updated is result
        assert vr is None
        assert "verification" not in result.metadata

    def test_noop_when_disabled(self) -> None:
        """Test loop no-ops when config is disabled."""
        wf = FakeWorkflow()
        wf._verification_config = VerificationConfig(enabled=False)
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert updated is result
        assert vr is None

    def test_noop_when_strategy_is_none(self) -> None:
        """Test loop no-ops when resolved strategy is 'none'."""
        wf = FakeWorkflow(name="doc-gen")  # defaults to "none"
        wf._verification_config = VerificationConfig(enabled=True, strategy="auto")
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert updated is result
        assert vr is None

    @patch("attune.verification.mixin.run_verification")
    def test_passing_verification_attaches_metadata(self, mock_run) -> None:
        """Test passing verification populates metadata."""
        mock_run.return_value = VerificationResult(
            passed=True,
            strategy="run-tests",
            command="pytest tests/ -x --tb=short -q",
            exit_code=0,
            stdout="2 passed",
            stderr="",
            duration_ms=500,
            attempt=1,
            max_retries=2,
        )
        wf = FakeWorkflow()
        wf._verification_config = VerificationConfig(enabled=True, strategy="run-tests")
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert vr is not None
        assert vr.passed is True
        assert updated.success is True
        assert updated.metadata["verification"]["passed"] is True
        assert updated.metadata["verification"]["strategy"] == "run-tests"

    @patch("attune.verification.mixin.run_verification")
    def test_failing_verification_marks_workflow_failed(self, mock_run) -> None:
        """Test failed verification sets success=False."""
        mock_run.return_value = VerificationResult(
            passed=False,
            strategy="run-tests",
            command="pytest",
            exit_code=1,
            stdout="",
            stderr="FAILED",
            duration_ms=1000,
            attempt=1,
            max_retries=0,
        )
        wf = FakeWorkflow()
        wf._verification_config = VerificationConfig(
            enabled=True, strategy="run-tests", max_retries=0
        )
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert updated.success is False
        assert "Verification failed" in (updated.error or "")
        assert updated.error_type == "verification"

    @patch("attune.verification.mixin.run_verification")
    def test_fail_open_does_not_mark_failed(self, mock_run) -> None:
        """Test fail_open=True keeps workflow success."""
        mock_run.return_value = VerificationResult(
            passed=False,
            strategy="lint-check",
            command="ruff check src/",
            exit_code=1,
            stdout="",
            stderr="lint errors",
            duration_ms=200,
            attempt=1,
            max_retries=0,
        )
        wf = FakeWorkflow()
        wf._verification_config = VerificationConfig(
            enabled=True,
            strategy="lint-check",
            max_retries=0,
            fail_open=True,
        )
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert updated.success is True
        assert updated.error is None
        assert updated.metadata["verification"]["passed"] is False

    @patch("attune.verification.mixin.run_verification")
    def test_retry_loop_runs_correct_attempts(self, mock_run) -> None:
        """Test retry loop runs max_retries + 1 times on failure."""
        mock_run.return_value = VerificationResult(
            passed=False,
            strategy="run-tests",
            command="pytest",
            exit_code=1,
            stdout="",
            stderr="",
            duration_ms=100,
            attempt=1,
            max_retries=2,
        )
        wf = FakeWorkflow()
        wf._verification_config = VerificationConfig(
            enabled=True, strategy="run-tests", max_retries=2
        )
        result = FakeWorkflowResult()

        wf._run_verification_loop(result, {})

        # Should be called 3 times (initial + 2 retries)
        assert mock_run.call_count == 3

    @patch("attune.verification.mixin.run_verification")
    def test_retry_stops_on_success(self, mock_run) -> None:
        """Test retry loop stops early when verification passes."""
        fail_result = VerificationResult(
            passed=False,
            strategy="run-tests",
            command="pytest",
            exit_code=1,
            stdout="",
            stderr="",
            duration_ms=100,
            attempt=1,
            max_retries=2,
        )
        pass_result = VerificationResult(
            passed=True,
            strategy="run-tests",
            command="pytest",
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_ms=100,
            attempt=2,
            max_retries=2,
        )
        mock_run.side_effect = [fail_result, pass_result]

        wf = FakeWorkflow()
        wf._verification_config = VerificationConfig(
            enabled=True, strategy="run-tests", max_retries=2
        )
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert mock_run.call_count == 2
        assert updated.success is True
        assert vr is not None
        assert vr.passed is True

    @patch("attune.verification.mixin.run_verification")
    def test_exception_in_loop_returns_gracefully(self, mock_run) -> None:
        """Test that exceptions in verification don't crash."""
        mock_run.side_effect = RuntimeError("unexpected")
        wf = FakeWorkflow()
        wf._verification_config = VerificationConfig(enabled=True, strategy="run-tests")
        result = FakeWorkflowResult()

        updated, vr = wf._run_verification_loop(result, {})

        assert updated is result
        assert vr is None
        assert updated.success is True  # Not modified
