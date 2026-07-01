"""Coverage tests for AnthropicProvider error, streaming, and fallback paths.

Targets the previously-uncovered regions of
``src/attune/llm/providers/anthropic.py``:

- ``generate()`` typed error handlers (RateLimitError, APIConnectionError,
  APITimeoutError, AuthenticationError, APIStatusError) — they log and
  re-raise.
- ``generate_stream()`` success path (plus the caching / no-caching system
  prompt branches) and its RateLimitError / APIConnectionError handlers.
- ``estimate_tokens()`` ImportError fallback to the base-class heuristic.

All paths are exercised with mocks — no live Anthropic API call. The mocked
``anthropic`` module exposes *real* ``Exception`` subclasses for its error
classes so the SUT's ``except anthropic.XError`` clauses can actually catch
them.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.llm.providers import AnthropicProvider

# --- Fake anthropic error classes (real exceptions so `except` works) -------


class _FakeRateLimitError(Exception):
    """Stand-in for ``anthropic.RateLimitError``."""


class _FakeAPIConnectionError(Exception):
    """Stand-in for ``anthropic.APIConnectionError``."""


class _FakeAPITimeoutError(Exception):
    """Stand-in for ``anthropic.APITimeoutError``."""


class _FakeAuthenticationError(Exception):
    """Stand-in for ``anthropic.AuthenticationError``."""


class _FakeAPIStatusError(Exception):
    """Stand-in for ``anthropic.APIStatusError`` (has status_code/response)."""

    def __init__(self, message: str = "boom", status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code
        self.response = MagicMock()
        self.response.text = message


def _make_mock_anthropic(client: MagicMock) -> MagicMock:
    """Build a mock ``anthropic`` module with real exception classes."""
    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = client
    mock_anthropic.RateLimitError = _FakeRateLimitError
    mock_anthropic.APIConnectionError = _FakeAPIConnectionError
    mock_anthropic.APITimeoutError = _FakeAPITimeoutError
    mock_anthropic.AuthenticationError = _FakeAuthenticationError
    mock_anthropic.APIStatusError = _FakeAPIStatusError
    return mock_anthropic


class _FakeStream:
    """Async context manager mimicking ``client.messages.stream(...)``."""

    def __init__(self, texts):
        self._texts = texts

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        texts = self._texts

        async def _gen():
            for text in texts:
                yield text

        return _gen()


# --- generate() error handlers ----------------------------------------------


class TestAnthropicGenerateErrorHandlers:
    """Each typed Anthropic error is logged and re-raised by ``generate()``."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [
            _FakeRateLimitError("rate limited"),
            _FakeAPIConnectionError("connection failed"),
            _FakeAPITimeoutError("timed out"),
            _FakeAuthenticationError("bad key"),
            _FakeAPIStatusError("server error", status_code=503),
        ],
    )
    async def test_generate_reraises_typed_errors(self, error):
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=error)
        mock_anthropic = _make_mock_anthropic(client)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")
            with pytest.raises(type(error)):
                await provider.generate([{"role": "user", "content": "hi"}])


# --- generate_stream() ------------------------------------------------------


class TestAnthropicGenerateStream:
    """Streaming success branches and error handlers."""

    @pytest.mark.asyncio
    async def test_stream_yields_text_chunks(self):
        client = MagicMock()
        client.messages.stream = MagicMock(return_value=_FakeStream(["Hello", " world"]))
        mock_anthropic = _make_mock_anthropic(client)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")
            chunks = [
                chunk
                async for chunk in provider.generate_stream([{"role": "user", "content": "hi"}])
            ]

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_with_caching_system_prompt(self):
        client = MagicMock()
        client.messages.stream = MagicMock(return_value=_FakeStream(["x"]))
        mock_anthropic = _make_mock_anthropic(client)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", use_prompt_caching=True)
            _ = [
                c
                async for c in provider.generate_stream(
                    [{"role": "user", "content": "hi"}],
                    system_prompt="be helpful",
                )
            ]

        system = client.messages.stream.call_args.kwargs["system"]
        assert isinstance(system, list)
        assert system[0]["cache_control"] == {"type": "ephemeral"}

    @pytest.mark.asyncio
    async def test_stream_with_plain_system_prompt(self):
        client = MagicMock()
        client.messages.stream = MagicMock(return_value=_FakeStream(["x"]))
        mock_anthropic = _make_mock_anthropic(client)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")
            _ = [
                c
                async for c in provider.generate_stream(
                    [{"role": "user", "content": "hi"}],
                    system_prompt="be helpful",
                )
            ]

        assert client.messages.stream.call_args.kwargs["system"] == "be helpful"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [
            _FakeRateLimitError("rate limited"),
            _FakeAPIConnectionError("connection failed"),
        ],
    )
    async def test_stream_reraises_typed_errors(self, error):
        client = MagicMock()
        client.messages.stream = MagicMock(side_effect=error)
        mock_anthropic = _make_mock_anthropic(client)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")
            with pytest.raises(type(error)):
                async for _ in provider.generate_stream([{"role": "user", "content": "hi"}]):
                    pass


# --- estimate_tokens() fallback ---------------------------------------------


class TestAnthropicEstimateTokensFallback:
    """When ``attune.utils.tokens`` is unavailable, fall back to base heuristic."""

    @pytest.mark.asyncio
    async def test_estimate_tokens_falls_back_on_importerror(self):
        with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(MagicMock())}):
            provider = AnthropicProvider(api_key="test-key")

        # Force `from attune.utils.tokens import count_tokens` to raise.
        with patch.dict("sys.modules", {"attune.utils.tokens": None}):
            # Base heuristic is len(text) // 4.
            assert provider.estimate_tokens("x" * 40) == 10

    @pytest.mark.asyncio
    async def test_estimate_tokens_uses_counter_when_available(self):
        with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(MagicMock())}):
            provider = AnthropicProvider(api_key="test-key")

        # Real attune.utils.tokens.count_tokens is importable here.
        tokens = provider.estimate_tokens("hello world from attune")
        assert isinstance(tokens, int)
        assert tokens > 0


# --- calculate_actual_cost() ------------------------------------------------


class TestAnthropicCalculateActualCost:
    """Cost breakdown arithmetic including cache write/read adjustments."""

    @pytest.mark.asyncio
    async def test_cost_breakdown_with_caching(self):
        with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(MagicMock())}):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-5")

        cost = provider.calculate_actual_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_creation_tokens=1_000_000,
            cache_read_tokens=1_000_000,
        )

        # Sonnet: $3/M input, $15/M output.
        assert cost["base_cost"] == 18.0
        assert cost["cache_write_cost"] == 3.75  # 3 * 1.25
        assert cost["cache_read_cost"] == 0.3  # 3 * 0.1
        assert cost["total_cost"] == round(18.0 + 3.75 + 0.3, 6)
        assert cost["savings"] == round(3.0 - 0.3, 6)
        assert cost["currency"] == "USD"
