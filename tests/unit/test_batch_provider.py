"""Tests for AnthropicBatchProvider.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock, patch

import pytest


class TestAnthropicBatchProvider:
    """Test suite for Anthropic Batch API provider."""

    @pytest.fixture
    def provider(self):
        """Create a batch provider instance."""
        # Mock the anthropic module during import
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            from attune.llm.providers.anthropic_batch import AnthropicBatchProvider

            provider = AnthropicBatchProvider(api_key="test_key")
            provider.client = mock_client
            return provider

    def test_create_batch_with_new_format(self, provider):
        """Test creating batch with correct Message Batches API format."""
        requests = [
            {
                "custom_id": "task_1",
                "params": {
                    "model": "claude-sonnet-5",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 1024,
                },
            },
        ]

        # Mock the API response
        mock_batch = MagicMock()
        mock_batch.id = "msgbatch_abc123"
        provider.client.messages.batches.create = MagicMock(return_value=mock_batch)

        # Create batch
        batch_id = provider.create_batch(requests)

        # Verify
        assert batch_id == "msgbatch_abc123"
        provider.client.messages.batches.create.assert_called_once()
        call_args = provider.client.messages.batches.create.call_args
        assert call_args[1]["requests"] == requests

    def test_create_batch_with_old_format_converts(self, provider):
        """Test that old format is automatically converted to new format."""
        requests = [
            {
                "custom_id": "task_1",
                "model": "claude-sonnet-5",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 1024,
            },
        ]

        # Mock the API response
        mock_batch = MagicMock()
        mock_batch.id = "msgbatch_abc123"
        provider.client.messages.batches.create = MagicMock(return_value=mock_batch)

        # Create batch
        batch_id = provider.create_batch(requests)

        # Verify format was converted
        assert batch_id == "msgbatch_abc123"
        call_args = provider.client.messages.batches.create.call_args
        converted_requests = call_args[1]["requests"]

        # Check that params wrapper was added
        assert "params" in converted_requests[0]
        assert converted_requests[0]["params"]["model"] == "claude-sonnet-5"

    def test_create_batch_empty_raises_error(self, provider):
        """Test that empty requests list raises ValueError."""
        with pytest.raises(ValueError, match="requests cannot be empty"):
            provider.create_batch([])

    def test_get_batch_status(self, provider):
        """Test getting batch status."""
        # Mock the API response
        mock_status = MagicMock()
        mock_status.id = "msgbatch_abc123"
        mock_status.processing_status = "in_progress"
        mock_status.request_counts = MagicMock(
            processing=10,
            succeeded=0,
            errored=0,
            canceled=0,
            expired=0,
        )
        provider.client.messages.batches.retrieve = MagicMock(return_value=mock_status)

        # Get status
        status = provider.get_batch_status("msgbatch_abc123")

        # Verify
        assert status.id == "msgbatch_abc123"
        assert status.processing_status == "in_progress"
        assert status.request_counts.processing == 10
        provider.client.messages.batches.retrieve.assert_called_once_with("msgbatch_abc123")

    def test_get_batch_results_not_ended_raises_error(self, provider):
        """Test that getting results before batch ends raises ValueError."""
        # Mock status as in_progress
        mock_status = MagicMock()
        mock_status.processing_status = "in_progress"
        provider.client.messages.batches.retrieve = MagicMock(return_value=mock_status)

        # Try to get results
        with pytest.raises(ValueError, match="has not ended processing"):
            provider.get_batch_results("msgbatch_abc123")

    def test_get_batch_results_success(self, provider):
        """Test retrieving results from completed batch."""
        # Mock status as ended
        mock_status = MagicMock()
        mock_status.processing_status = "ended"
        provider.client.messages.batches.retrieve = MagicMock(return_value=mock_status)

        # Mock results
        mock_results = [
            {
                "custom_id": "task_1",
                "result": {
                    "type": "succeeded",
                    "message": {
                        "content": [{"type": "text", "text": "Hello, world!"}],
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                        "model": "claude-sonnet-5",
                        "stop_reason": "end_turn",
                    },
                },
            },
        ]
        provider.client.messages.batches.results = MagicMock(return_value=iter(mock_results))

        # Get results
        results = provider.get_batch_results("msgbatch_abc123")

        # Verify
        assert len(results) == 1
        assert results[0]["custom_id"] == "task_1"
        assert results[0]["result"]["type"] == "succeeded"

    @pytest.mark.asyncio
    async def test_wait_for_batch_success(self, provider):
        """Test waiting for batch to complete."""
        # Mock status that changes from in_progress to ended
        status_in_progress = MagicMock(
            processing_status="in_progress",
            request_counts=MagicMock(processing=10, succeeded=0, errored=0, canceled=0, expired=0),
        )
        status_ended = MagicMock(
            processing_status="ended",
            request_counts=MagicMock(processing=0, succeeded=10, errored=0, canceled=0, expired=0),
        )

        # First call returns in_progress, subsequent calls return ended
        call_count = 0

        def get_status_side_effect(batch_id):
            nonlocal call_count
            call_count += 1
            return status_in_progress if call_count == 1 else status_ended

        provider.client.messages.batches.retrieve = MagicMock(side_effect=get_status_side_effect)

        # Mock results
        mock_results = [
            {"custom_id": f"task_{i}", "result": {"type": "succeeded"}} for i in range(10)
        ]
        provider.client.messages.batches.results = MagicMock(return_value=iter(mock_results))

        # Wait for batch (short poll interval for testing)
        results = await provider.wait_for_batch("msgbatch_abc123", poll_interval=0.1, timeout=10)

        # Verify
        assert len(results) == 10
        assert call_count >= 2  # At least 2 status checks

    @pytest.mark.asyncio
    async def test_wait_for_batch_timeout(self, provider):
        """Test that wait raises TimeoutError if batch doesn't complete."""
        # Mock status always in_progress
        mock_status = MagicMock(
            processing_status="in_progress",
            request_counts=MagicMock(processing=10, succeeded=0, errored=0, canceled=0, expired=0),
        )
        provider.client.messages.batches.retrieve = MagicMock(return_value=mock_status)

        # Wait for batch with short timeout
        with pytest.raises(TimeoutError, match="did not complete within"):
            await provider.wait_for_batch("msgbatch_abc123", poll_interval=0.1, timeout=0.5)


class TestBatchRequestFormatConversion:
    """Test request format conversion logic."""

    def test_conversion_preserves_custom_id(self):
        """Test that custom_id is preserved during conversion."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            from attune.llm.providers.anthropic_batch import AnthropicBatchProvider

            provider = AnthropicBatchProvider(api_key="test_key")
            provider.client = mock_client

            old_format = {
                "custom_id": "my_unique_id",
                "model": "claude-sonnet-5",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 2048,
            }

            mock_batch = MagicMock(id="msgbatch_test")
            provider.client.messages.batches.create = MagicMock(return_value=mock_batch)

            provider.create_batch([old_format])

            call_args = provider.client.messages.batches.create.call_args
            converted = call_args[1]["requests"][0]

            assert converted["custom_id"] == "my_unique_id"
            assert converted["params"]["model"] == "claude-sonnet-5"
            assert converted["params"]["max_tokens"] == 2048

    def test_conversion_handles_optional_params(self):
        """Test that optional parameters are preserved."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            from attune.llm.providers.anthropic_batch import AnthropicBatchProvider

            provider = AnthropicBatchProvider(api_key="test_key")
            provider.client = mock_client

            old_format = {
                "custom_id": "test_id",
                "model": "claude-sonnet-5",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 1024,
                "temperature": 0.8,
                "system": "You are a helpful assistant",
            }

            mock_batch = MagicMock(id="msgbatch_test")
            provider.client.messages.batches.create = MagicMock(return_value=mock_batch)

            provider.create_batch([old_format])

            call_args = provider.client.messages.batches.create.call_args
            converted = call_args[1]["requests"][0]

            assert converted["params"]["temperature"] == 0.8
            assert converted["params"]["system"] == "You are a helpful assistant"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
