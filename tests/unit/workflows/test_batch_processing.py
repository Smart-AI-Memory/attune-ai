"""Tests for Batch Processing Workflow.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.batch_processing import (
    BatchProcessingWorkflow,
    BatchRequest,
    BatchResult,
)


class TestBatchRequest:
    """Test BatchRequest dataclass."""

    def test_create_batch_request(self):
        """Test creating a batch request."""
        req = BatchRequest(
            task_id="task_1",
            task_type="analyze_logs",
            input_data={"logs": "ERROR: Connection failed"},
            model_tier="capable",
        )

        assert req.task_id == "task_1"
        assert req.task_type == "analyze_logs"
        assert req.input_data["logs"] == "ERROR: Connection failed"
        assert req.model_tier == "capable"

    def test_batch_request_default_tier(self):
        """Test that model_tier defaults to 'capable'."""
        req = BatchRequest(task_id="task_1", task_type="analyze_logs", input_data={})

        assert req.model_tier == "capable"


class TestBatchResult:
    """Test BatchResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful result."""
        result = BatchResult(
            task_id="task_1",
            success=True,
            output={"content": "Analysis complete"},
        )

        assert result.task_id == "task_1"
        assert result.success is True
        assert result.output["content"] == "Analysis complete"
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed result."""
        result = BatchResult(
            task_id="task_1",
            success=False,
            error="Request timed out",
        )

        assert result.task_id == "task_1"
        assert result.success is False
        assert result.error == "Request timed out"
        assert result.output is None


class TestBatchProcessingWorkflow:
    """Test suite for BatchProcessingWorkflow."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance with mocked provider."""
        with patch("attune.workflows.batch_processing.AnthropicBatchProvider"):
            workflow = BatchProcessingWorkflow(api_key="test_key")
            workflow.batch_provider = MagicMock()
            return workflow

    @pytest.mark.asyncio
    async def test_execute_batch_success(self, workflow):
        """Test successful batch execution."""
        requests = [
            BatchRequest(
                task_id="task_1",
                task_type="analyze_logs",
                input_data={"logs": "ERROR: Test"},
                model_tier="capable",
            ),
            BatchRequest(
                task_id="task_2",
                task_type="generate_report",
                input_data={"data": "test data"},
                model_tier="cheap",
            ),
        ]

        # Mock batch provider responses
        workflow.batch_provider.create_batch.return_value = "msgbatch_test123"

        # Mock wait_for_batch to return successful results
        mock_raw_results = [
            {
                "custom_id": "task_1",
                "result": {
                    "type": "succeeded",
                    "message": {
                        "content": [{"type": "text", "text": "Analysis complete"}],
                        "usage": {"input_tokens": 100, "output_tokens": 50},
                        "model": "claude-sonnet-4-5-20250929",
                        "stop_reason": "end_turn",
                    },
                },
            },
            {
                "custom_id": "task_2",
                "result": {
                    "type": "succeeded",
                    "message": {
                        "content": [{"type": "text", "text": "Report generated"}],
                        "usage": {"input_tokens": 150, "output_tokens": 75},
                        "model": "claude-haiku-4-5-20251001",
                        "stop_reason": "end_turn",
                    },
                },
            },
        ]
        workflow.batch_provider.wait_for_batch = AsyncMock(return_value=mock_raw_results)

        # Execute batch
        results = await workflow.execute_batch(requests)

        # Verify
        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].task_id == "task_1"
        assert "Analysis complete" in results[0].output["content"]
        assert results[1].task_id == "task_2"
        assert "Report generated" in results[1].output["content"]

    @pytest.mark.asyncio
    async def test_execute_batch_with_errors(self, workflow):
        """Test batch execution with some errors."""
        requests = [
            BatchRequest(task_id="task_1", task_type="analyze_logs", input_data={}),
            BatchRequest(task_id="task_2", task_type="generate_report", input_data={}),
        ]

        workflow.batch_provider.create_batch.return_value = "msgbatch_test123"

        # Mock results with one success and one error
        mock_raw_results = [
            {
                "custom_id": "task_1",
                "result": {
                    "type": "succeeded",
                    "message": {
                        "content": [{"type": "text", "text": "Success"}],
                        "usage": {},
                        "model": "claude-sonnet-4-5-20250929",
                        "stop_reason": "end_turn",
                    },
                },
            },
            {
                "custom_id": "task_2",
                "result": {
                    "type": "errored",
                    "error": {"type": "invalid_request_error", "message": "Invalid input"},
                },
            },
        ]
        workflow.batch_provider.wait_for_batch = AsyncMock(return_value=mock_raw_results)

        # Execute batch
        results = await workflow.execute_batch(requests)

        # Verify
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "invalid_request_error" in results[1].error

    @pytest.mark.asyncio
    async def test_execute_batch_timeout(self, workflow):
        """Test batch execution timeout handling."""
        requests = [BatchRequest(task_id="task_1", task_type="analyze_logs", input_data={})]

        workflow.batch_provider.create_batch.return_value = "msgbatch_test123"
        workflow.batch_provider.wait_for_batch = AsyncMock(side_effect=TimeoutError("Timeout"))

        # Execute batch
        results = await workflow.execute_batch(requests, timeout=1)

        # Verify timeout handling
        assert len(results) == 1
        assert results[0].success is False
        assert "timed out" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_execute_batch_empty_raises_error(self, workflow):
        """Test that empty requests list raises ValueError."""
        with pytest.raises(ValueError, match="requests cannot be empty"):
            await workflow.execute_batch([])

    def test_format_messages_known_task_type(self, workflow):
        """Test message formatting for known task types."""
        request = BatchRequest(
            task_id="task_1",
            task_type="analyze_logs",
            input_data={"logs": "ERROR: Connection failed"},
        )

        messages = workflow._format_messages(request)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "ERROR: Connection failed" in messages[0]["content"]

    def test_format_messages_unknown_task_type(self, workflow):
        """Test message formatting for unknown task types uses default."""
        request = BatchRequest(
            task_id="task_1",
            task_type="custom_task",
            input_data={"custom_field": "value"},
        )

        messages = workflow._format_messages(request)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        # Should use default template with JSON input
        assert "value" in messages[0]["content"]

    def test_load_requests_from_file(self, workflow, tmp_path):
        """Test loading batch requests from JSON file."""
        # Create test JSON file
        input_file = tmp_path / "requests.json"
        test_data = [
            {
                "task_id": "task_1",
                "task_type": "analyze_logs",
                "input_data": {"logs": "ERROR: Test"},
                "model_tier": "capable",
            },
            {
                "task_id": "task_2",
                "task_type": "generate_report",
                "input_data": {"data": "test"},
            },
        ]
        input_file.write_text(json.dumps(test_data))

        # Load requests
        requests = workflow.load_requests_from_file(str(input_file))

        # Verify
        assert len(requests) == 2
        assert requests[0].task_id == "task_1"
        assert requests[0].task_type == "analyze_logs"
        assert requests[0].model_tier == "capable"
        assert requests[1].task_id == "task_2"
        assert requests[1].model_tier == "capable"  # Default

    def test_load_requests_file_not_found(self, workflow):
        """Test that loading from non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            workflow.load_requests_from_file("nonexistent.json")

    def test_load_requests_invalid_json(self, workflow, tmp_path):
        """Test that invalid JSON raises appropriate error."""
        input_file = tmp_path / "invalid.json"
        input_file.write_text("not valid json")

        with pytest.raises(json.JSONDecodeError):
            workflow.load_requests_from_file(str(input_file))

    def test_load_requests_invalid_format(self, workflow, tmp_path):
        """Test that invalid format raises ValueError."""
        input_file = tmp_path / "invalid_format.json"
        input_file.write_text('{"not": "an array"}')

        with pytest.raises(ValueError, match="must contain a JSON array"):
            workflow.load_requests_from_file(str(input_file))

    def test_save_results_to_file(self, workflow, tmp_path):
        """Test saving batch results to JSON file."""
        results = [
            BatchResult(
                task_id="task_1",
                success=True,
                output={"content": "Result 1"},
            ),
            BatchResult(
                task_id="task_2",
                success=False,
                error="Test error",
            ),
        ]

        output_file = tmp_path / "results.json"
        workflow.save_results_to_file(results, str(output_file))

        # Verify file was created
        assert output_file.exists()

        # Verify content
        with open(output_file) as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["task_id"] == "task_1"
        assert data[0]["success"] is True
        assert data[1]["task_id"] == "task_2"
        assert data[1]["success"] is False
        assert data[1]["error"] == "Test error"


class TestBatchProcessingCostSavings:
    """Test cost savings calculations and reporting."""

    @pytest.mark.asyncio
    async def test_batch_uses_correct_models(self):
        """Test that batch requests use correct model for each tier."""
        with patch("attune.workflows.batch_processing.AnthropicBatchProvider"):
            with patch("attune.workflows.batch_processing.get_model") as mock_get_model:
                # Mock model responses
                mock_cheap = MagicMock(id="claude-haiku-4-5-20251001")
                mock_capable = MagicMock(id="claude-sonnet-4-5-20250929")
                mock_premium = MagicMock(id="claude-opus-4-20250514")

                def get_model_side_effect(provider, tier):
                    if tier == "cheap":
                        return mock_cheap
                    elif tier == "capable":
                        return mock_capable
                    elif tier == "premium":
                        return mock_premium
                    return None

                mock_get_model.side_effect = get_model_side_effect

                workflow = BatchProcessingWorkflow(api_key="test_key")
                workflow.batch_provider = MagicMock()
                workflow.batch_provider.create_batch.return_value = "msgbatch_test"
                workflow.batch_provider.wait_for_batch = AsyncMock(return_value=[])

                # Create requests with different tiers
                requests = [
                    BatchRequest(task_id="t1", task_type="test", input_data={}, model_tier="cheap"),
                    BatchRequest(
                        task_id="t2", task_type="test", input_data={}, model_tier="capable"
                    ),
                    BatchRequest(
                        task_id="t3", task_type="test", input_data={}, model_tier="premium"
                    ),
                ]

                await workflow.execute_batch(requests)

                # Verify correct models were requested
                assert mock_get_model.call_count == 3
                mock_get_model.assert_any_call("anthropic", "cheap")
                mock_get_model.assert_any_call("anthropic", "capable")
                mock_get_model.assert_any_call("anthropic", "premium")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
