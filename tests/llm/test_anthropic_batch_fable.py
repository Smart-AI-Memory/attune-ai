"""Batch-provider fable policy tests (fable-premium-tier task 5).

The Batch API rejects the beta ``fallbacks`` param, so fable models
never run in batches (design §4b, Option A):

- ``_batch_premium_model()`` resolves the premium tier and swaps a
  fable result for ``claude-opus-4-8``.
- ``create_batch`` downgrades any fable-model request at request-build
  time, then normalizes under the downgraded model's rules (sampling
  params stripped per Opus 4.7+).

All mock-only — no live Anthropic calls.
"""

from unittest.mock import MagicMock

from attune.llm.providers.anthropic_batch import (
    AnthropicBatchProvider,
    _batch_premium_model,
)


class TestBatchPremiumModel:
    def test_fable_premium_downgrades_to_opus(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_MODEL_PREMIUM", "claude-fable-5")
        assert _batch_premium_model() == "claude-opus-4-8"

    def test_default_premium_is_fable_so_batch_gets_opus(self, monkeypatch):
        monkeypatch.delenv("ATTUNE_MODEL_PREMIUM", raising=False)
        # Contract default: premium resolves to claude-fable-5 (task 1),
        # so the batch helper must return the fallback.
        assert _batch_premium_model() == "claude-opus-4-8"

    def test_non_fable_pin_passes_through(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_MODEL_PREMIUM", "claude-opus-4-8")
        assert _batch_premium_model() == "claude-opus-4-8"


class TestCreateBatchDowngrade:
    def _provider_with_client(self):
        provider = AnthropicBatchProvider.__new__(AnthropicBatchProvider)
        provider.client = MagicMock()
        provider.client.messages.batches.create.return_value = MagicMock(id="msgbatch_test")
        provider._batch_jobs = {}
        return provider

    def test_fable_request_downgraded_at_build(self):
        provider = self._provider_with_client()
        provider.create_batch(
            [
                {
                    "custom_id": "t1",
                    "params": {
                        "model": "claude-fable-5",
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 64,
                        "temperature": 0.7,
                    },
                }
            ]
        )
        sent = provider.client.messages.batches.create.call_args.kwargs["requests"]
        params = sent[0]["params"]
        assert params["model"] == "claude-opus-4-8"
        # Normalized under the DOWNGRADED model's rules: opus-4-8
        # rejects sampling params, so temperature must be gone.
        assert "temperature" not in params

    def test_non_fable_request_untouched(self):
        provider = self._provider_with_client()
        provider.create_batch(
            [
                {
                    "custom_id": "t2",
                    "params": {
                        # pre-Claude-5: outside the sampling-strip list
                        "model": "claude-sonnet-4-5",
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 64,
                        "temperature": 0.3,
                    },
                }
            ]
        )
        sent = provider.client.messages.batches.create.call_args.kwargs["requests"]
        params = sent[0]["params"]
        assert params["model"] == "claude-sonnet-4-5"
        assert params["temperature"] == 0.3
