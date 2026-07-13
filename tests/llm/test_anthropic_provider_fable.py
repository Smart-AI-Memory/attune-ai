"""Fable-tier wiring tests for AnthropicProvider.generate() (task 4).

Covers the central-provider fable handling added in
docs/specs/fable-premium-tier design §4a:

- fable models route via ``client.beta.messages.create`` with the beta
  flags + ``extra_body`` fallbacks (from ``attune.model_tiers.fable_extras``)
- non-fable models keep the exact pre-tier path (plain
  ``client.messages.create``)
- ``stop_reason == "refusal"`` surfaces as ``ModelRefusalError``
- a fable 400 is re-raised with the retention hint appended
- ``_normalize_api_kwargs_for_model`` strips sampling params AND any
  explicit thinking config for ``claude-fable*`` with logged warnings,
  while the opus-4.7+ behavior is unchanged

All paths are exercised with mocks — no live Anthropic API call.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from attune.llm.providers import AnthropicProvider
from attune.model_tiers import ModelRefusalError


class _FakeAPIStatusError(Exception):
    """Stand-in for ``anthropic.APIStatusError`` (has status_code/response)."""

    def __init__(self, message: str = "boom", status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code
        self.response = MagicMock()
        self.response.text = message


def _make_mock_anthropic(client: MagicMock) -> MagicMock:
    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = client
    mock_anthropic.RateLimitError = type("RateLimitError", (Exception,), {})
    mock_anthropic.APIConnectionError = type("APIConnectionError", (Exception,), {})
    mock_anthropic.APITimeoutError = type("APITimeoutError", (Exception,), {})
    mock_anthropic.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_anthropic.APIStatusError = _FakeAPIStatusError
    return mock_anthropic


def _response(model: str = "claude-fable-5", stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="ok")],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        stop_reason=stop_reason,
        model=model,
    )


def _make_client(fable_response=None, plain_response=None) -> MagicMock:
    client = MagicMock()
    client.beta.messages.create = AsyncMock(return_value=fable_response or _response())
    client.messages.create = AsyncMock(
        return_value=plain_response or _response(model="claude-sonnet-5")
    )
    return client


class TestFableRouting:
    """Fable models take the beta path; everything else is untouched."""

    @pytest.mark.asyncio
    async def test_fable_routes_via_beta_namespace(self, fake_module):
        client = _make_client()
        fake_module("anthropic", _make_mock_anthropic(client))
        provider = AnthropicProvider(api_key="test-key", model="claude-fable-5")
        result = await provider.generate([{"role": "user", "content": "hi"}])

        client.beta.messages.create.assert_awaited_once()
        client.messages.create.assert_not_called()
        kwargs = client.beta.messages.create.await_args.kwargs
        assert kwargs["model"] == "claude-fable-5"
        assert "betas" in kwargs
        assert "fallbacks" in kwargs["extra_body"]
        assert result.content == "ok"

    @pytest.mark.asyncio
    async def test_non_fable_path_unchanged(self, fake_module):
        client = _make_client()
        fake_module("anthropic", _make_mock_anthropic(client))
        provider = AnthropicProvider(api_key="test-key")  # claude-sonnet-5
        await provider.generate([{"role": "user", "content": "hi"}])

        client.messages.create.assert_awaited_once()
        client.beta.messages.create.assert_not_called()
        kwargs = client.messages.create.await_args.kwargs
        # Sonnet still accepts sampling params — the provider default survives.
        assert kwargs["temperature"] == 0.7
        assert "betas" not in kwargs

    @pytest.mark.asyncio
    async def test_fable_refusal_raises_model_refusal_error(self, fake_module):
        client = _make_client(fable_response=_response(stop_reason="refusal"))
        fake_module("anthropic", _make_mock_anthropic(client))
        provider = AnthropicProvider(api_key="test-key", model="claude-fable-5")
        with pytest.raises(ModelRefusalError):
            await provider.generate([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_fable_400_carries_retention_hint(self, fake_module):
        client = MagicMock()
        client.beta.messages.create = AsyncMock(
            side_effect=_FakeAPIStatusError("bad request", status_code=400)
        )
        fake_module("anthropic", _make_mock_anthropic(client))
        provider = AnthropicProvider(api_key="test-key", model="claude-fable-5")
        with pytest.raises(_FakeAPIStatusError) as excinfo:
            await provider.generate([{"role": "user", "content": "hi"}])

        assert "retention" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, _FakeAPIStatusError)


class TestFableParamStripping:
    """claude-fable* strips sampling AND thinking, each with a warning."""

    @pytest.mark.asyncio
    async def test_fable_strips_sampling_and_thinking(self, caplog, fake_module):
        client = _make_client()
        fake_module("anthropic", _make_mock_anthropic(client))
        provider = AnthropicProvider(api_key="test-key", model="claude-fable-5", use_thinking=True)
        with caplog.at_level(logging.WARNING, logger="attune.llm.providers.anthropic"):
            await provider.generate([{"role": "user", "content": "hi"}], top_p=0.9, top_k=40)

        kwargs = client.beta.messages.create.await_args.kwargs
        for param in ("temperature", "top_p", "top_k", "thinking"):
            assert param not in kwargs
        warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        stripped = "\n".join(str(m) for m in warnings)
        assert "temperature" in stripped
        assert "thinking" in stripped

    @pytest.mark.asyncio
    async def test_opus_strip_behavior_unchanged(self, fake_module):
        client = _make_client(plain_response=_response(model="claude-opus-4-8"))
        fake_module("anthropic", _make_mock_anthropic(client))
        provider = AnthropicProvider(api_key="test-key", model="claude-opus-4-8", use_thinking=True)
        await provider.generate([{"role": "user", "content": "hi"}])

        # Opus is NOT fable: plain namespace, sampling stripped silently,
        # enabled thinking converted to adaptive (not removed).
        kwargs = client.messages.create.await_args.kwargs
        assert "temperature" not in kwargs
        assert kwargs["thinking"] == {"type": "adaptive"}
        assert "betas" not in kwargs
