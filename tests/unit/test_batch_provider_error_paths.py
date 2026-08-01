"""Error-path and edge-case coverage for AnthropicBatchProvider.

Coverage lane: raises src/attune/llm/providers/anthropic_batch.py from
83.3% to >=85% by exercising branches the existing test_batch_provider.py
and test_anthropic_batch_fable.py suites don't reach:

- __init__ ImportError when the ``anthropic`` package is unavailable
- create_batch / get_batch_status / get_batch_results wrapping an
  underlying SDK exception into a RuntimeError
- wait_for_batch's AttributeError fallback when request_counts lacks
  a ``processing`` field (older/partial SDK response shapes)

All mock-only — no live Anthropic calls, no real client construction.
ANTHROPIC_API_KEY is never read; every provider is built with an
explicit api_key= string.
"""

import sys
from unittest.mock import MagicMock

import pytest


class TestInitImportError:
    """__init__ raises ImportError when the anthropic package is absent."""

    def test_missing_anthropic_package_raises_importerror(self, monkeypatch):
        # Force `import anthropic` to raise ImportError regardless of
        # whether the real package is installed in this environment:
        # a `None` entry in sys.modules makes the import system raise
        # ImportError for that name.
        monkeypatch.setitem(sys.modules, "anthropic", None)

        from attune.llm.providers.anthropic_batch import AnthropicBatchProvider

        with pytest.raises(ImportError, match="anthropic package required"):
            AnthropicBatchProvider(api_key="test_key")


class TestSDKExceptionWrapping:
    """SDK-level exceptions are wrapped into RuntimeError with context."""

    @pytest.fixture
    def provider(self, monkeypatch):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        # monkeypatch.setitem restores only this key on teardown — no
        # patch.dict sys.modules clear+rebuild race under xdist.
        monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)
        from attune.llm.providers.anthropic_batch import AnthropicBatchProvider

        provider = AnthropicBatchProvider(api_key="test_key")
        provider.client = mock_client
        return provider

    def test_create_batch_sdk_failure_raises_runtimeerror(self, provider):
        provider.client.messages.batches.create = MagicMock(
            side_effect=Exception("rate limited"),
        )

        with pytest.raises(RuntimeError, match="Batch creation failed"):
            provider.create_batch(
                [
                    {
                        "custom_id": "t1",
                        "params": {
                            "model": "claude-sonnet-5",
                            "messages": [{"role": "user", "content": "hi"}],
                            "max_tokens": 10,
                        },
                    }
                ]
            )

    def test_get_batch_status_sdk_failure_raises_runtimeerror(self, provider):
        provider.client.messages.batches.retrieve = MagicMock(
            side_effect=Exception("not found"),
        )

        with pytest.raises(RuntimeError, match="Failed to get batch status"):
            provider.get_batch_status("msgbatch_missing")

    def test_get_batch_results_sdk_failure_raises_runtimeerror(self, provider):
        mock_status = MagicMock()
        mock_status.processing_status = "ended"
        provider.client.messages.batches.retrieve = MagicMock(return_value=mock_status)
        provider.client.messages.batches.results = MagicMock(
            side_effect=Exception("results expired"),
        )

        with pytest.raises(RuntimeError, match="Failed to get batch results"):
            provider.get_batch_results("msgbatch_abc123")


class TestWaitForBatchProgressLogging:
    """wait_for_batch tolerates a request_counts shape missing 'processing'."""

    @pytest.fixture
    def provider(self, monkeypatch):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)
        from attune.llm.providers.anthropic_batch import AnthropicBatchProvider

        provider = AnthropicBatchProvider(api_key="test_key")
        provider.client = mock_client
        return provider

    @pytest.mark.asyncio
    async def test_wait_for_batch_falls_back_when_processing_count_missing(
        self,
        provider,
    ):
        class CountsWithoutProcessing:
            """Mimics a request_counts payload lacking 'processing'."""

            succeeded = 0
            errored = 0
            canceled = 0
            expired = 0

        status_in_progress = MagicMock(
            processing_status="in_progress",
            request_counts=CountsWithoutProcessing(),
        )
        status_ended = MagicMock(
            processing_status="ended",
            request_counts=MagicMock(succeeded=1, errored=0, canceled=0, expired=0),
        )

        call_count = 0

        def get_status_side_effect(batch_id):
            nonlocal call_count
            call_count += 1
            return status_in_progress if call_count == 1 else status_ended

        provider.client.messages.batches.retrieve = MagicMock(
            side_effect=get_status_side_effect,
        )
        provider.client.messages.batches.results = MagicMock(return_value=iter([]))

        results = await provider.wait_for_batch(
            "msgbatch_abc123",
            poll_interval=0.01,
            timeout=5,
        )

        assert results == []
        assert call_count >= 2
