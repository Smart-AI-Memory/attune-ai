"""Tests for verification runner."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from attune.verification import VerificationResult
from attune.verification.config import VerificationConfig
from attune.verification.runner import run_verification
from attune.verification.strategies import RunTestsStrategy


class TestRunVerification:
    """Test the run_verification function."""

    def _make_config(self, **kwargs) -> VerificationConfig:
        """Helper to create config with defaults."""
        defaults = {
            "enabled": True,
            "strategy": "run-tests",
            "max_retries": 2,
            "timeout_seconds": 300,
        }
        defaults.update(kwargs)
        return VerificationConfig(**defaults)

    @patch("attune.verification.runner.subprocess.run")
    def test_passing_verification(self, mock_run) -> None:
        """Test verification that passes (exit code 0)."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout="2 passed",
            stderr="",
        )
        config = self._make_config()
        strategy = RunTestsStrategy()

        result = run_verification(config, strategy, "test-gen", None)

        assert isinstance(result, VerificationResult)
        assert result.passed is True
        assert result.exit_code == 0
        assert result.stdout == "2 passed"
        assert result.strategy == "run-tests"
        assert result.attempt == 1

    @patch("attune.verification.runner.subprocess.run")
    def test_failing_verification(self, mock_run) -> None:
        """Test verification that fails (exit code 1)."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=1,
            stdout="",
            stderr="FAILED",
        )
        config = self._make_config()
        strategy = RunTestsStrategy()

        result = run_verification(config, strategy, "test-gen", None)

        assert result.passed is False
        assert result.exit_code == 1

    @patch("attune.verification.runner.subprocess.run")
    def test_timeout_handling(self, mock_run) -> None:
        """Test timeout is handled gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=300)
        config = self._make_config(timeout_seconds=300)
        strategy = RunTestsStrategy()

        result = run_verification(config, strategy, "test-gen", None)

        assert result.passed is False
        assert result.exit_code == -1
        assert "Timed out" in (result.error or "")

    @patch("attune.verification.runner.subprocess.run")
    def test_command_not_found(self, mock_run) -> None:
        """Test missing command handled gracefully."""
        mock_run.side_effect = FileNotFoundError("pytest not found")
        config = self._make_config()
        strategy = RunTestsStrategy()

        result = run_verification(config, strategy, "test-gen", None)

        assert result.passed is False
        assert result.exit_code == -1
        assert "Command not found" in (result.error or "")

    @patch("attune.verification.runner.subprocess.run")
    def test_os_error_handled(self, mock_run) -> None:
        """Test OS error handled gracefully."""
        mock_run.side_effect = OSError("Permission denied")
        config = self._make_config()
        strategy = RunTestsStrategy()

        result = run_verification(config, strategy, "test-gen", None)

        assert result.passed is False
        assert result.exit_code == -1
        assert "OS error" in (result.error or "")

    @patch("attune.verification.runner.subprocess.run")
    def test_stdout_truncation(self, mock_run) -> None:
        """Test that stdout is truncated to 10KB."""
        long_output = "x" * 20000
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout=long_output,
            stderr="",
        )
        config = self._make_config()
        strategy = RunTestsStrategy()

        result = run_verification(config, strategy, "test-gen", None)

        assert len(result.stdout) == 10240

    @patch("attune.verification.runner.subprocess.run")
    def test_custom_command_override(self, mock_run) -> None:
        """Test that config.command overrides strategy command."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo"],
            returncode=0,
            stdout="hello",
            stderr="",
        )
        config = self._make_config(command="echo hello")
        strategy = RunTestsStrategy()

        run_verification(config, strategy, "test-gen", None)

        # Should have called "echo hello", not "pytest ..."
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["echo", "hello"]

    @patch("attune.verification.runner.subprocess.run")
    def test_working_directory_passed(self, mock_run) -> None:
        """Test working_directory is passed to subprocess."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout="ok",
            stderr="",
        )
        config = self._make_config(working_directory="/tmp/project")
        strategy = RunTestsStrategy()

        run_verification(config, strategy, "test-gen", None)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == "/tmp/project"

    @patch("attune.verification.runner.subprocess.run")
    def test_no_shell_true(self, mock_run) -> None:
        """Test that shell=True is never used (security)."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout="ok",
            stderr="",
        )
        config = self._make_config()
        strategy = RunTestsStrategy()

        run_verification(config, strategy, "test-gen", None)

        # Verify shell=False is used (or not passed, default is False)
        call_kwargs = mock_run.call_args[1]
        # shell should not be True
        assert call_kwargs.get("shell", False) is False

    @patch("attune.verification.runner.subprocess.run")
    def test_attempt_number_passed_through(self, mock_run) -> None:
        """Test that attempt number is set correctly."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout="",
            stderr="",
        )
        config = self._make_config()
        strategy = RunTestsStrategy()

        result = run_verification(config, strategy, "test-gen", None, attempt=3)

        assert result.attempt == 3
