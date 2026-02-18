"""Tests for batch CLI commands (submit, status, results, wait).

Tests for src/attune/cli_commands/batch_commands.py which provides
cmd_batch_submit, cmd_batch_status, cmd_batch_results, and cmd_batch_wait.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import types
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_submit_args(**kwargs) -> types.SimpleNamespace:
    """Create args for cmd_batch_submit."""
    defaults = {"input_file": "batch_requests.json"}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_status_args(**kwargs) -> types.SimpleNamespace:
    """Create args for cmd_batch_status."""
    defaults = {"batch_id": "msgbatch_test123", "json": False}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_results_args(**kwargs) -> types.SimpleNamespace:
    """Create args for cmd_batch_results."""
    defaults = {"batch_id": "msgbatch_test123", "output_file": "results.json"}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_wait_args(**kwargs) -> types.SimpleNamespace:
    """Create args for cmd_batch_wait."""
    defaults = {
        "batch_id": "msgbatch_test123",
        "output_file": "results.json",
        "poll_interval": 300,
        "timeout": 86400,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _mock_batch_status(processing_status: str = "in_progress", **count_overrides):
    """Create a mock batch status object."""
    counts = MagicMock()
    counts.processing = count_overrides.get("processing", 0)
    counts.succeeded = count_overrides.get("succeeded", 0)
    counts.errored = count_overrides.get("errored", 0)
    counts.canceled = count_overrides.get("canceled", 0)
    counts.expired = count_overrides.get("expired", 0)

    status = MagicMock()
    status.processing_status = processing_status
    status.request_counts = counts
    return status


# ===========================================================================
# cmd_batch_submit
# ===========================================================================


class TestCmdBatchSubmitApiKey:
    """Tests for API key validation in cmd_batch_submit."""

    @patch.dict("os.environ", {}, clear=True)
    def test_submit_missing_api_key_returns_one(self, capsys):
        """Test that missing API key returns error."""
        from attune.cli_commands.batch_commands import cmd_batch_submit

        result = cmd_batch_submit(_make_submit_args())

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False)
    def test_submit_empty_api_key_returns_one(self, capsys):
        """Test that empty API key returns error."""
        from attune.cli_commands.batch_commands import cmd_batch_submit

        result = cmd_batch_submit(_make_submit_args())

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out


class TestCmdBatchSubmitFileValidation:
    """Tests for file validation in cmd_batch_submit."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"}, clear=False)
    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    def test_submit_file_not_found_returns_one(self, mock_key, capsys, tmp_path):
        """Test that non-existent input file returns error."""
        from attune.cli_commands.batch_commands import cmd_batch_submit

        nonexistent = str(tmp_path / "nonexistent.json")
        result = cmd_batch_submit(_make_submit_args(input_file=nonexistent))

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "File not found" in captured.out

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    def test_submit_invalid_json_returns_one(self, mock_key, capsys, tmp_path):
        """Test that invalid JSON file returns error."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json")

        from attune.cli_commands.batch_commands import cmd_batch_submit

        result = cmd_batch_submit(_make_submit_args(input_file=str(bad_file)))

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.out or "JSON" in captured.out

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    def test_submit_wrong_format_returns_one(self, mock_key, capsys, tmp_path):
        """Test that wrong JSON format (not array) returns error."""
        wrong_file = tmp_path / "wrong.json"
        wrong_file.write_text('{"not": "an array"}')

        from attune.cli_commands.batch_commands import cmd_batch_submit

        result = cmd_batch_submit(_make_submit_args(input_file=str(wrong_file)))

        assert result == 1

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.config._validate_file_path")
    def test_submit_path_traversal_blocked(self, mock_validate, mock_key, capsys):
        """Test that path traversal in input_file is blocked."""
        mock_validate.side_effect = ValueError("Cannot write to system directory: /etc")

        from attune.cli_commands.batch_commands import cmd_batch_submit

        result = cmd_batch_submit(_make_submit_args(input_file="/etc/passwd"))

        assert result == 1
        captured = capsys.readouterr()
        assert "Validation error" in captured.out or "system directory" in captured.out


class TestCmdBatchSubmitSuccess:
    """Tests for successful batch submission."""

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    def test_submit_success(self, mock_key, capsys, tmp_path):
        """Test successful batch submission."""
        input_file = tmp_path / "requests.json"
        input_file.write_text(
            json.dumps(
                [
                    {
                        "task_id": "task_1",
                        "task_type": "analyze_logs",
                        "input_data": {"logs": "ERROR: test"},
                        "model_tier": "capable",
                    }
                ]
            )
        )

        mock_provider = MagicMock()
        mock_provider.create_batch.return_value = "msgbatch_abc123"

        with patch(
            "attune.workflows.batch_processing.AnthropicBatchProvider",
            return_value=mock_provider,
        ):
            from attune.cli_commands.batch_commands import cmd_batch_submit

            result = cmd_batch_submit(_make_submit_args(input_file=str(input_file)))

        assert result == 0
        captured = capsys.readouterr()
        assert "msgbatch_abc123" in captured.out
        assert "submitted successfully" in captured.out.lower() or "Batch submitted" in captured.out
        mock_provider.create_batch.assert_called_once()

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    def test_submit_prints_follow_up_commands(self, mock_key, capsys, tmp_path):
        """Test that follow-up commands are printed after submission."""
        input_file = tmp_path / "requests.json"
        input_file.write_text(
            json.dumps(
                [
                    {
                        "task_id": "t1",
                        "task_type": "analyze_logs",
                        "input_data": {"logs": "test"},
                    }
                ]
            )
        )

        mock_provider = MagicMock()
        mock_provider.create_batch.return_value = "msgbatch_xyz"

        with patch(
            "attune.workflows.batch_processing.AnthropicBatchProvider",
            return_value=mock_provider,
        ):
            from attune.cli_commands.batch_commands import cmd_batch_submit

            cmd_batch_submit(_make_submit_args(input_file=str(input_file)))

        captured = capsys.readouterr()
        assert "attune batch status msgbatch_xyz" in captured.out
        assert "attune batch results msgbatch_xyz" in captured.out
        assert "attune batch wait msgbatch_xyz" in captured.out


# ===========================================================================
# cmd_batch_status
# ===========================================================================


class TestCmdBatchStatusApiKey:
    """Tests for API key validation in cmd_batch_status."""

    @patch.dict("os.environ", {}, clear=True)
    def test_status_missing_api_key_returns_one(self, capsys):
        """Test that missing API key returns error."""
        from attune.cli_commands.batch_commands import cmd_batch_status

        result = cmd_batch_status(_make_status_args())

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out


class TestCmdBatchStatusDisplay:
    """Tests for batch status display."""

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_status_in_progress(self, mock_provider_cls, mock_key, capsys):
        """Test status display for in-progress batch."""
        mock_provider = MagicMock()
        mock_provider.get_batch_status.return_value = _mock_batch_status(
            "in_progress", processing=5
        )
        mock_provider_cls.return_value = mock_provider

        from attune.cli_commands.batch_commands import cmd_batch_status

        result = cmd_batch_status(_make_status_args())

        assert result == 0
        captured = capsys.readouterr()
        assert "in_progress" in captured.out
        assert "still processing" in captured.out.lower()

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_status_ended_shows_retrieval_hint(self, mock_provider_cls, mock_key, capsys):
        """Test status display for completed batch."""
        mock_provider = MagicMock()
        mock_provider.get_batch_status.return_value = _mock_batch_status(
            "ended", succeeded=3, errored=1
        )
        mock_provider_cls.return_value = mock_provider

        from attune.cli_commands.batch_commands import cmd_batch_status

        result = cmd_batch_status(_make_status_args())

        assert result == 0
        captured = capsys.readouterr()
        assert "ended" in captured.out
        assert "attune batch results" in captured.out

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_status_json_output(self, mock_provider_cls, mock_key, capsys):
        """Test --json flag outputs valid JSON."""
        mock_provider = MagicMock()
        mock_provider.get_batch_status.return_value = _mock_batch_status(
            "in_progress", processing=2
        )
        mock_provider_cls.return_value = mock_provider

        from attune.cli_commands.batch_commands import cmd_batch_status

        args = _make_status_args(json=True)
        result = cmd_batch_status(args)

        assert result == 0
        captured = capsys.readouterr()
        # Extract JSON from output (skip the "Checking status" line)
        lines = captured.out.strip().split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("{"):
                in_json = True
            if in_json:
                json_lines.append(line)
        json_text = "\n".join(json_lines)
        parsed = json.loads(json_text)
        assert parsed["processing_status"] == "in_progress"
        assert parsed["request_counts"]["processing"] == 2

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_status_api_error_returns_one(self, mock_provider_cls, mock_key, capsys):
        """Test handling of API errors."""
        mock_provider = MagicMock()
        mock_provider.get_batch_status.side_effect = RuntimeError("API error")
        mock_provider_cls.return_value = mock_provider

        from attune.cli_commands.batch_commands import cmd_batch_status

        result = cmd_batch_status(_make_status_args())

        assert result == 1
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_status_shows_request_counts(self, mock_provider_cls, mock_key, capsys):
        """Test that request counts are displayed."""
        mock_provider = MagicMock()
        mock_provider.get_batch_status.return_value = _mock_batch_status(
            "in_progress", processing=3, succeeded=2, errored=1
        )
        mock_provider_cls.return_value = mock_provider

        from attune.cli_commands.batch_commands import cmd_batch_status

        result = cmd_batch_status(_make_status_args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Processing: 3" in captured.out
        assert "Succeeded: 2" in captured.out
        assert "Errored: 1" in captured.out


# ===========================================================================
# cmd_batch_results
# ===========================================================================


class TestCmdBatchResultsApiKey:
    """Tests for API key validation in cmd_batch_results."""

    @patch.dict("os.environ", {}, clear=True)
    def test_results_missing_api_key_returns_one(self, capsys):
        """Test that missing API key returns error."""
        from attune.cli_commands.batch_commands import cmd_batch_results

        result = cmd_batch_results(_make_results_args())

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out


class TestCmdBatchResultsDownload:
    """Tests for batch results download."""

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_results_success(self, mock_provider_cls, mock_key, capsys, tmp_path):
        """Test successful results download."""
        mock_results = [
            {
                "custom_id": "task_1",
                "result": {"type": "succeeded", "message": {"content": []}},
            },
            {
                "custom_id": "task_2",
                "result": {"type": "errored", "error": {"message": "bad input"}},
            },
        ]
        mock_provider = MagicMock()
        mock_provider.get_batch_results.return_value = mock_results
        mock_provider_cls.return_value = mock_provider

        output_file = tmp_path / "output.json"

        from attune.cli_commands.batch_commands import cmd_batch_results

        result = cmd_batch_results(_make_results_args(output_file=str(output_file)))

        assert result == 0
        assert output_file.exists()

        saved = json.loads(output_file.read_text())
        assert len(saved) == 2

        captured = capsys.readouterr()
        assert "Succeeded: 1" in captured.out
        assert "Errored: 1" in captured.out

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_results_batch_not_ended_returns_one(
        self, mock_provider_cls, mock_key, capsys, tmp_path
    ):
        """Test error when batch is not complete."""
        mock_provider = MagicMock()
        mock_provider.get_batch_results.side_effect = ValueError("Batch has not ended processing")
        mock_provider_cls.return_value = mock_provider

        output_file = tmp_path / "output.json"

        from attune.cli_commands.batch_commands import cmd_batch_results

        result = cmd_batch_results(_make_results_args(output_file=str(output_file)))

        assert result == 1

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.config._validate_file_path")
    def test_results_output_path_traversal_blocked(self, mock_validate, mock_key, capsys):
        """Test output path validation blocks system paths."""
        mock_validate.side_effect = ValueError("Cannot write to system directory: /etc")

        from attune.cli_commands.batch_commands import cmd_batch_results

        result = cmd_batch_results(_make_results_args(output_file="/etc/test.json"))

        assert result == 1


# ===========================================================================
# cmd_batch_wait
# ===========================================================================


class TestCmdBatchWaitApiKey:
    """Tests for API key validation in cmd_batch_wait."""

    @patch.dict("os.environ", {}, clear=True)
    def test_wait_missing_api_key_returns_one(self, capsys):
        """Test that missing API key returns error."""
        from attune.cli_commands.batch_commands import cmd_batch_wait

        result = cmd_batch_wait(_make_wait_args())

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out


class TestCmdBatchWaitExecution:
    """Tests for batch wait execution."""

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_wait_success(self, mock_provider_cls, mock_key, capsys, tmp_path):
        """Test successful wait and download."""
        mock_results = [
            {
                "custom_id": "task_1",
                "result": {"type": "succeeded", "message": {"content": []}},
            }
        ]
        mock_provider = MagicMock()
        mock_provider.wait_for_batch = AsyncMock(return_value=mock_results)
        mock_provider_cls.return_value = mock_provider

        output_file = tmp_path / "output.json"

        from attune.cli_commands.batch_commands import cmd_batch_wait

        result = cmd_batch_wait(_make_wait_args(output_file=str(output_file)))

        assert result == 0
        assert output_file.exists()

        saved = json.loads(output_file.read_text())
        assert len(saved) == 1

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()
        assert "Succeeded: 1" in captured.out

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_wait_timeout_returns_one(self, mock_provider_cls, mock_key, capsys, tmp_path):
        """Test timeout handling."""
        mock_provider = MagicMock()
        mock_provider.wait_for_batch = AsyncMock(
            side_effect=TimeoutError("Batch did not complete within 86400s")
        )
        mock_provider_cls.return_value = mock_provider

        output_file = tmp_path / "output.json"

        from attune.cli_commands.batch_commands import cmd_batch_wait

        result = cmd_batch_wait(_make_wait_args(output_file=str(output_file)))

        assert result == 1
        captured = capsys.readouterr()
        assert "timed out" in captured.out.lower()

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_wait_custom_poll_interval_passed(self, mock_provider_cls, mock_key, capsys, tmp_path):
        """Test that custom poll_interval is passed to provider."""
        mock_provider = MagicMock()
        mock_provider.wait_for_batch = AsyncMock(return_value=[])
        mock_provider_cls.return_value = mock_provider

        output_file = tmp_path / "output.json"

        from attune.cli_commands.batch_commands import cmd_batch_wait

        cmd_batch_wait(_make_wait_args(output_file=str(output_file), poll_interval=600))

        mock_provider.wait_for_batch.assert_called_once_with(
            "msgbatch_test123", poll_interval=600, timeout=86400
        )

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.llm.providers.AnthropicBatchProvider")
    def test_wait_custom_timeout_passed(self, mock_provider_cls, mock_key, capsys, tmp_path):
        """Test that custom timeout is passed to provider."""
        mock_provider = MagicMock()
        mock_provider.wait_for_batch = AsyncMock(return_value=[])
        mock_provider_cls.return_value = mock_provider

        output_file = tmp_path / "output.json"

        from attune.cli_commands.batch_commands import cmd_batch_wait

        cmd_batch_wait(_make_wait_args(output_file=str(output_file), timeout=43200))

        mock_provider.wait_for_batch.assert_called_once_with(
            "msgbatch_test123", poll_interval=300, timeout=43200
        )

    @patch("attune.cli_commands.batch_commands._get_api_key", return_value="sk-test-key")
    @patch("attune.config._validate_file_path")
    def test_wait_output_path_traversal_blocked(self, mock_validate, mock_key, capsys):
        """Test output path validation blocks system paths."""
        mock_validate.side_effect = ValueError("Cannot write to system directory: /etc")

        from attune.cli_commands.batch_commands import cmd_batch_wait

        result = cmd_batch_wait(_make_wait_args(output_file="/etc/test.json"))

        assert result == 1


# ===========================================================================
# Parser integration tests
# ===========================================================================


class TestBatchParserIntegration:
    """Test that batch commands are properly wired in CLI parser."""

    def test_batch_submit_parser(self):
        """Test argparse recognizes 'batch submit'."""
        from attune.cli_minimal import create_parser

        parser = create_parser()
        args = parser.parse_args(["batch", "submit", "input.json"])
        assert args.command == "batch"
        assert args.batch_command == "submit"
        assert args.input_file == "input.json"

    def test_batch_status_parser(self):
        """Test argparse recognizes 'batch status'."""
        from attune.cli_minimal import create_parser

        parser = create_parser()
        args = parser.parse_args(["batch", "status", "msgbatch_abc123"])
        assert args.command == "batch"
        assert args.batch_command == "status"
        assert args.batch_id == "msgbatch_abc123"

    def test_batch_status_json_flag(self):
        """Test --json flag is parsed."""
        from attune.cli_minimal import create_parser

        parser = create_parser()
        args = parser.parse_args(["batch", "status", "msgbatch_abc123", "--json"])
        assert args.json is True

    def test_batch_results_parser(self):
        """Test argparse recognizes 'batch results'."""
        from attune.cli_minimal import create_parser

        parser = create_parser()
        args = parser.parse_args(["batch", "results", "msgbatch_abc123", "out.json"])
        assert args.command == "batch"
        assert args.batch_command == "results"
        assert args.batch_id == "msgbatch_abc123"
        assert args.output_file == "out.json"

    def test_batch_wait_parser_defaults(self):
        """Test argparse defaults for batch wait."""
        from attune.cli_minimal import create_parser

        parser = create_parser()
        args = parser.parse_args(["batch", "wait", "msgbatch_abc123", "out.json"])
        assert args.poll_interval == 300
        assert args.timeout == 86400

    def test_batch_wait_parser_custom(self):
        """Test custom poll_interval and timeout."""
        from attune.cli_minimal import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "batch",
                "wait",
                "msgbatch_abc123",
                "out.json",
                "--poll-interval",
                "600",
                "--timeout",
                "43200",
            ]
        )
        assert args.poll_interval == 600
        assert args.timeout == 43200
