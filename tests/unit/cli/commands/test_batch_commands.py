"""Comprehensive tests for CLI batch commands.

Tests all four batch command functions: submit, status, results, and wait.
Mocks BatchProcessingWorkflow and _validate_file_path to isolate CLI logic.

Module under test: src/attune/cli/commands/batch.py
"""

import json
import types
from unittest.mock import MagicMock, Mock, patch

import pytest


# The batch module imports BatchProcessingWorkflow at the top level,
# so we must patch it before importing the commands.
@pytest.fixture(autouse=True)
def _mock_batch_workflow():
    """Patch BatchProcessingWorkflow for all tests in this module.

    The batch.py module does a top-level import of BatchProcessingWorkflow,
    so we patch it on the target module after it has been imported.
    """
    with patch(
        "attune.cli.commands.batch.BatchProcessingWorkflow"
    ) as mock_cls:
        mock_cls.return_value = MagicMock()
        yield mock_cls


from attune.cli.commands.batch import (  # noqa: E402
    cmd_batch_results,
    cmd_batch_status,
    cmd_batch_submit,
    cmd_batch_wait,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_args(**kwargs) -> types.SimpleNamespace:
    """Create a SimpleNamespace to simulate argparse args."""
    return types.SimpleNamespace(**kwargs)


def _make_status(
    batch_id: str = "batch_abc123",
    processing_status: str = "in_progress",
    created_at: str = "2026-02-08T10:00:00Z",
    ended_at: str | None = None,
    processing: int = 5,
    succeeded: int = 0,
    errored: int = 0,
    canceled: int = 0,
    expired: int = 0,
) -> types.SimpleNamespace:
    """Create a batch status object with request_counts.

    Uses SimpleNamespace instead of Mock to avoid __dict__ conflicts
    that cause AttributeError: _mock_methods on Python 3.10.
    """
    counts = types.SimpleNamespace(
        processing=processing,
        succeeded=succeeded,
        errored=errored,
        canceled=canceled,
        expired=expired,
    )
    return types.SimpleNamespace(
        id=batch_id,
        processing_status=processing_status,
        created_at=created_at,
        ended_at=ended_at,
        request_counts=counts,
    )


# ============================================================================
# cmd_batch_submit Tests
# ============================================================================


@pytest.mark.unit
class TestCmdBatchSubmit:
    """Tests for the cmd_batch_submit function."""

    def test_submit_missing_input_file_returns_1(self, capsys: pytest.CaptureFixture) -> None:
        """Test that submit returns 1 when the input file does not exist."""
        args = _make_args(input_file="/nonexistent/path/to/batch.json")

        result = cmd_batch_submit(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Input file not found" in captured.out

    def test_submit_missing_api_key_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that submit returns 1 when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        input_file = tmp_path / "requests.json"
        input_file.write_text(json.dumps([{"task_id": "t1"}]))
        args = _make_args(input_file=str(input_file))

        result = cmd_batch_submit(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out

    def test_submit_successful_returns_0(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test successful batch submission returns 0."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        # Create a valid input file
        requests_data = [
            {
                "task_id": "task_1",
                "task_type": "analyze_logs",
                "input_data": {"logs": "ERROR: test"},
                "model_tier": "capable",
            }
        ]
        input_file = tmp_path / "requests.json"
        input_file.write_text(json.dumps(requests_data))

        # Configure mock workflow
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_request = Mock()
        mock_request.task_id = "task_1"
        mock_workflow_instance.load_requests_from_file.return_value = [mock_request]
        mock_workflow_instance.batch_provider.create_batch.return_value = "batch_xyz789"
        mock_workflow_instance._format_messages.return_value = [
            {"role": "user", "content": "test"}
        ]

        args = _make_args(input_file=str(input_file))

        result = cmd_batch_submit(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Batch submitted successfully" in captured.out
        assert "batch_xyz789" in captured.out
        mock_workflow_instance.load_requests_from_file.assert_called_once_with(str(input_file))

    def test_submit_workflow_exception_returns_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that submit returns 1 when workflow raises an exception."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        input_file = tmp_path / "requests.json"
        input_file.write_text(json.dumps([]))
        args = _make_args(input_file=str(input_file))

        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.load_requests_from_file.side_effect = ValueError(
            "Invalid request format"
        )

        result = cmd_batch_submit(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_submit_shows_request_count(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that submit prints the number of requests found."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        input_file = tmp_path / "requests.json"
        input_file.write_text(json.dumps([]))
        args = _make_args(input_file=str(input_file))

        mock_req_1 = Mock(task_id="t1")
        mock_req_2 = Mock(task_id="t2")
        mock_req_3 = Mock(task_id="t3")
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.load_requests_from_file.return_value = [
            mock_req_1,
            mock_req_2,
            mock_req_3,
        ]
        mock_workflow_instance.batch_provider.create_batch.return_value = "batch_001"
        mock_workflow_instance._format_messages.return_value = []

        result = cmd_batch_submit(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Found 3 requests" in captured.out


# ============================================================================
# cmd_batch_status Tests
# ============================================================================


@pytest.mark.unit
class TestCmdBatchStatus:
    """Tests for the cmd_batch_status function."""

    def test_status_missing_api_key_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that status returns 1 when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        args = _make_args(batch_id="batch_123", json=False)

        result = cmd_batch_status(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out

    def test_status_in_progress_returns_0(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that status returns 0 and shows in-progress information."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        status = _make_status(
            batch_id="batch_456",
            processing_status="in_progress",
            processing=3,
            succeeded=2,
            errored=0,
            canceled=0,
            expired=0,
        )
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status

        args = _make_args(batch_id="batch_456", json=False)

        result = cmd_batch_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "batch_456" in captured.out
        assert "in_progress" in captured.out
        assert "Processing: 3" in captured.out
        assert "Succeeded: 2" in captured.out
        assert "still processing" in captured.out

    def test_status_ended_shows_completion_message(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that status shows completion message when batch has ended."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        status = _make_status(
            batch_id="batch_789",
            processing_status="ended",
            ended_at="2026-02-08T12:00:00Z",
            processing=0,
            succeeded=5,
            errored=0,
        )
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status

        args = _make_args(batch_id="batch_789", json=False)

        result = cmd_batch_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Batch processing completed" in captured.out
        assert "Ended:" in captured.out

    def test_status_json_output(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that status outputs JSON when args.json is True."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        status = _make_status(
            batch_id="batch_json",
            processing_status="in_progress",
        )
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status

        args = _make_args(batch_id="batch_json", json=True)

        result = cmd_batch_status(args)

        assert result == 0
        captured = capsys.readouterr()
        # Verify JSON output is present in stdout
        assert '"processing_status": "in_progress"' in captured.out

    def test_status_shows_request_counts(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that status displays all request count fields."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        status = _make_status(
            processing=1,
            succeeded=10,
            errored=2,
            canceled=3,
            expired=4,
        )
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status

        args = _make_args(batch_id="batch_counts", json=False)

        result = cmd_batch_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Processing: 1" in captured.out
        assert "Succeeded: 10" in captured.out
        assert "Errored: 2" in captured.out
        assert "Canceled: 3" in captured.out
        assert "Expired: 4" in captured.out

    def test_status_exception_returns_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that status returns 1 when API call raises an exception."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.side_effect = (
            ConnectionError("API unreachable")
        )

        args = _make_args(batch_id="batch_err", json=False)

        result = cmd_batch_status(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ============================================================================
# cmd_batch_results Tests
# ============================================================================


@pytest.mark.unit
class TestCmdBatchResults:
    """Tests for the cmd_batch_results function."""

    def test_results_missing_api_key_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that results returns 1 when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        args = _make_args(batch_id="batch_123", output_file="/tmp/output.json")

        result = cmd_batch_results(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out

    def test_results_batch_not_ended_returns_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that results returns 1 when batch has not finished processing."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        status = _make_status(processing_status="in_progress")
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status

        args = _make_args(batch_id="batch_running", output_file="output.json")

        result = cmd_batch_results(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "has not ended processing" in captured.out
        assert "in_progress" in captured.out

    @patch("attune.cli.commands.batch._validate_file_path")
    def test_results_ended_saves_output_returns_0(
        self,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that results saves JSON output when batch has ended."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        output_path = tmp_path / "output.json"
        mock_validate.return_value = output_path

        status = _make_status(processing_status="ended")
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status

        # Simulate results as list of dict-like objects
        result_1 = {"custom_id": "t1", "result": {"type": "succeeded", "message": {"content": "ok"}}}
        result_2 = {"custom_id": "t2", "result": {"type": "errored", "error": "timeout"}}
        mock_workflow_instance.batch_provider.get_batch_results.return_value = [
            result_1,
            result_2,
        ]

        args = _make_args(batch_id="batch_done", output_file="output.json")

        result = cmd_batch_results(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Results saved to" in captured.out
        assert "Total: 2 results" in captured.out
        assert "Succeeded: 1" in captured.out
        assert "Errored: 1" in captured.out

        # Verify file was written
        assert output_path.exists()
        saved_data = json.loads(output_path.read_text())
        assert len(saved_data) == 2

    @patch("attune.cli.commands.batch._validate_file_path")
    def test_results_validates_output_path(
        self,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        _mock_batch_workflow,
    ) -> None:
        """Test that results validates the output file path."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        mock_validate.side_effect = ValueError("Cannot write to system directory: /etc")

        status = _make_status(processing_status="ended")
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status
        mock_workflow_instance.batch_provider.get_batch_results.return_value = []

        args = _make_args(batch_id="batch_path", output_file="/etc/evil.json")

        result = cmd_batch_results(args)

        assert result == 1
        mock_validate.assert_called_once_with("/etc/evil.json")

    def test_results_exception_returns_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that results returns 1 when an unexpected exception occurs."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.side_effect = RuntimeError(
            "Connection lost"
        )

        args = _make_args(batch_id="batch_fail", output_file="output.json")

        result = cmd_batch_results(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    @patch("attune.cli.commands.batch._validate_file_path")
    def test_results_all_succeeded(
        self,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test results summary when all requests succeeded."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        output_path = tmp_path / "results.json"
        mock_validate.return_value = output_path

        status = _make_status(processing_status="ended")
        mock_workflow_instance = _mock_batch_workflow.return_value
        mock_workflow_instance.batch_provider.get_batch_status.return_value = status

        results_data = [
            {"custom_id": f"t{i}", "result": {"type": "succeeded"}} for i in range(5)
        ]
        mock_workflow_instance.batch_provider.get_batch_results.return_value = results_data

        args = _make_args(batch_id="batch_all_ok", output_file="results.json")

        result = cmd_batch_results(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Succeeded: 5" in captured.out
        assert "Errored: 0" in captured.out


# ============================================================================
# cmd_batch_wait Tests
# ============================================================================


@pytest.mark.unit
class TestCmdBatchWait:
    """Tests for the cmd_batch_wait function."""

    def test_wait_missing_api_key_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that wait returns 1 when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        args = _make_args(
            batch_id="batch_123",
            output_file="/tmp/output.json",
            poll_interval=300,
            timeout=3600,
        )

        result = cmd_batch_wait(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out

    @patch("attune.cli.commands.batch._validate_file_path")
    @patch("attune.cli.commands.batch.asyncio")
    def test_wait_success_saves_results_returns_0(
        self,
        mock_asyncio: Mock,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that wait saves results and returns 0 on successful completion."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        output_path = tmp_path / "output.json"
        mock_validate.return_value = output_path

        results_data = [
            {"custom_id": "t1", "result": {"type": "succeeded"}},
            {"custom_id": "t2", "result": {"type": "succeeded"}},
            {"custom_id": "t3", "result": {"type": "errored", "error": "rate_limit"}},
        ]
        mock_asyncio.run.return_value = results_data

        args = _make_args(
            batch_id="batch_wait_ok",
            output_file="output.json",
            poll_interval=60,
            timeout=1800,
        )

        result = cmd_batch_wait(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Batch completed" in captured.out
        assert "Total: 3 results" in captured.out
        assert "Succeeded: 2" in captured.out
        assert "Errored: 1" in captured.out

        # Verify file was written
        assert output_path.exists()
        saved_data = json.loads(output_path.read_text())
        assert len(saved_data) == 3

    @patch("attune.cli.commands.batch.asyncio")
    def test_wait_timeout_returns_1(
        self,
        mock_asyncio: Mock,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that wait returns 1 when batch times out."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        mock_asyncio.run.side_effect = TimeoutError("Exceeded timeout")

        args = _make_args(
            batch_id="batch_timeout",
            output_file="output.json",
            poll_interval=10,
            timeout=60,
        )

        result = cmd_batch_wait(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Timeout" in captured.out
        assert "60" in captured.out

    @patch("attune.cli.commands.batch.asyncio")
    def test_wait_general_exception_returns_1(
        self,
        mock_asyncio: Mock,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that wait returns 1 when an unexpected exception occurs."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        mock_asyncio.run.side_effect = RuntimeError("Network failure")

        args = _make_args(
            batch_id="batch_err",
            output_file="output.json",
            poll_interval=60,
            timeout=3600,
        )

        result = cmd_batch_wait(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    @patch("attune.cli.commands.batch._validate_file_path")
    @patch("attune.cli.commands.batch.asyncio")
    def test_wait_shows_poll_and_timeout_info(
        self,
        mock_asyncio: Mock,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that wait displays poll interval and timeout in output."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        output_path = tmp_path / "output.json"
        mock_validate.return_value = output_path
        mock_asyncio.run.return_value = []

        args = _make_args(
            batch_id="batch_info",
            output_file="output.json",
            poll_interval=120,
            timeout=7200,
        )

        result = cmd_batch_wait(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "120s" in captured.out
        assert "7200s" in captured.out

    @patch("attune.cli.commands.batch._validate_file_path")
    @patch("attune.cli.commands.batch.asyncio")
    def test_wait_passes_correct_params_to_provider(
        self,
        mock_asyncio: Mock,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        _mock_batch_workflow,
    ) -> None:
        """Test that wait passes poll_interval and timeout to the batch provider."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        output_path = tmp_path / "output.json"
        mock_validate.return_value = output_path
        mock_asyncio.run.return_value = []

        mock_workflow_instance = _mock_batch_workflow.return_value

        args = _make_args(
            batch_id="batch_params",
            output_file="output.json",
            poll_interval=180,
            timeout=5400,
        )

        cmd_batch_wait(args)

        # Verify asyncio.run was called; the coroutine passed to it should
        # have been created with the correct parameters.
        mock_asyncio.run.assert_called_once()
        mock_workflow_instance.batch_provider.wait_for_batch.assert_called_once_with(
            "batch_params", poll_interval=180, timeout=5400
        )

    @patch("attune.cli.commands.batch._validate_file_path")
    @patch("attune.cli.commands.batch.asyncio")
    def test_wait_validates_output_path(
        self,
        mock_asyncio: Mock,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        _mock_batch_workflow,
    ) -> None:
        """Test that wait validates the output file path before writing."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        mock_asyncio.run.return_value = []
        mock_validate.side_effect = ValueError("Cannot write to system directory: /sys")

        args = _make_args(
            batch_id="batch_validate",
            output_file="/sys/output.json",
            poll_interval=60,
            timeout=3600,
        )

        result = cmd_batch_wait(args)

        assert result == 1
        mock_validate.assert_called_once_with("/sys/output.json")

    @patch("attune.cli.commands.batch._validate_file_path")
    @patch("attune.cli.commands.batch.asyncio")
    def test_wait_empty_results_returns_0(
        self,
        mock_asyncio: Mock,
        mock_validate: Mock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        capsys: pytest.CaptureFixture,
        _mock_batch_workflow,
    ) -> None:
        """Test that wait returns 0 even when batch returns empty results."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")

        output_path = tmp_path / "output.json"
        mock_validate.return_value = output_path
        mock_asyncio.run.return_value = []

        args = _make_args(
            batch_id="batch_empty",
            output_file="output.json",
            poll_interval=60,
            timeout=3600,
        )

        result = cmd_batch_wait(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Total: 0 results" in captured.out
        assert output_path.exists()
        saved_data = json.loads(output_path.read_text())
        assert saved_data == []
