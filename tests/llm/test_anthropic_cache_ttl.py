"""Cache-TTL wire-shape tests for AnthropicProvider.

``ATTUNE_CACHE_TTL=1h`` extends the prompt-cache window from the
5-minute default to 1 hour by adding ``"ttl": "1h"`` to the
``cache_control`` marker. These tests lock the wire shape at all three
emit sites (``generate`` system prefix, ``analyze_large_codebase``
codebase block, ``generate_stream`` system prefix) for the default and
the 1h value, mocking the client — no live API.

Mirrors attune-rag's ``tests/unit/providers/test_claude_cache_ttl.py``;
see specs/extended-cache-ttl-siblings/ for the cross-package rollout.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.llm.providers import AnthropicProvider
from attune.llm.providers.anthropic import _cache_control

_EPHEMERAL = {"type": "ephemeral"}
_EPHEMERAL_1H = {"type": "ephemeral", "ttl": "1h"}


def _make_mock_anthropic(client: MagicMock) -> MagicMock:
    """Build a mock ``anthropic`` module exposing the async client."""
    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = client
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


# --- _cache_control() helper ------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, _EPHEMERAL),  # unset → default
        ("5m", _EPHEMERAL),  # explicit default
        ("1h", _EPHEMERAL_1H),  # extended
        (" 1H ", _EPHEMERAL_1H),  # case + whitespace insensitive
        ("30m", _EPHEMERAL),  # unsupported value → safe default
        ("", _EPHEMERAL),  # empty → default
    ],
)
def test_cache_control_resolves_from_env(monkeypatch: pytest.MonkeyPatch, value, expected) -> None:
    if value is None:
        monkeypatch.delenv("ATTUNE_CACHE_TTL", raising=False)
    else:
        monkeypatch.setenv("ATTUNE_CACHE_TTL", value)
    assert _cache_control() == expected


# --- generate() system prefix site ------------------------------------------


def _make_response(text: str = "ok") -> MagicMock:
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(input_tokens=1, output_tokens=1)
    response.stop_reason = "end_turn"
    return response


@pytest.mark.asyncio
async def test_generate_system_prefix_carries_1h_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With ATTUNE_CACHE_TTL=1h the cached system block carries the
    extended marker."""
    monkeypatch.setenv("ATTUNE_CACHE_TTL", "1h")
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=_make_response())
    mock_anthropic = _make_mock_anthropic(client)

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        provider = AnthropicProvider(api_key="test-key", use_prompt_caching=True)
        await provider.generate([{"role": "user", "content": "hi"}], system_prompt="be helpful")

    system = client.messages.create.await_args.kwargs["system"]
    assert system[0]["cache_control"] == _EPHEMERAL_1H


@pytest.mark.asyncio
async def test_generate_system_prefix_defaults_to_5m(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset env → the system marker is byte-identical to the prior default."""
    monkeypatch.delenv("ATTUNE_CACHE_TTL", raising=False)
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=_make_response())
    mock_anthropic = _make_mock_anthropic(client)

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        provider = AnthropicProvider(api_key="test-key", use_prompt_caching=True)
        await provider.generate([{"role": "user", "content": "hi"}], system_prompt="be helpful")

    system = client.messages.create.await_args.kwargs["system"]
    assert system[0]["cache_control"] == _EPHEMERAL


# --- analyze_large_codebase() codebase block site ---------------------------


@pytest.mark.asyncio
async def test_analyze_codebase_block_carries_1h_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With 1h set, the cached codebase block carries the extended marker."""
    monkeypatch.setenv("ATTUNE_CACHE_TTL", "1h")
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=_make_response())
    mock_anthropic = _make_mock_anthropic(client)

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        provider = AnthropicProvider(api_key="test-key")
        await provider.analyze_large_codebase(
            codebase_files=[{"path": "a.py", "content": "x = 1"}],
            analysis_prompt="summarize",
        )

    system = client.messages.create.await_args.kwargs["system"]
    assert system[1]["cache_control"] == _EPHEMERAL_1H


@pytest.mark.asyncio
async def test_analyze_codebase_block_defaults_to_5m(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset env → codebase-block marker is byte-identical to prior default."""
    monkeypatch.delenv("ATTUNE_CACHE_TTL", raising=False)
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=_make_response())
    mock_anthropic = _make_mock_anthropic(client)

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        provider = AnthropicProvider(api_key="test-key")
        await provider.analyze_large_codebase(
            codebase_files=[{"path": "a.py", "content": "x = 1"}],
            analysis_prompt="summarize",
        )

    system = client.messages.create.await_args.kwargs["system"]
    assert system[1]["cache_control"] == _EPHEMERAL


# --- generate_stream() system prefix site -----------------------------------


@pytest.mark.asyncio
async def test_stream_system_prefix_carries_1h_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With 1h set, the streamed system block carries the extended marker."""
    monkeypatch.setenv("ATTUNE_CACHE_TTL", "1h")
    client = MagicMock()
    client.messages.stream = MagicMock(return_value=_FakeStream(["x"]))
    mock_anthropic = _make_mock_anthropic(client)

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        provider = AnthropicProvider(api_key="test-key", use_prompt_caching=True)
        _ = [
            c
            async for c in provider.generate_stream(
                [{"role": "user", "content": "hi"}], system_prompt="be helpful"
            )
        ]

    system = client.messages.stream.call_args.kwargs["system"]
    assert system[0]["cache_control"] == _EPHEMERAL_1H


@pytest.mark.asyncio
async def test_stream_system_prefix_defaults_to_5m(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset env → streamed system marker is byte-identical to prior default."""
    monkeypatch.delenv("ATTUNE_CACHE_TTL", raising=False)
    client = MagicMock()
    client.messages.stream = MagicMock(return_value=_FakeStream(["x"]))
    mock_anthropic = _make_mock_anthropic(client)

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        provider = AnthropicProvider(api_key="test-key", use_prompt_caching=True)
        _ = [
            c
            async for c in provider.generate_stream(
                [{"role": "user", "content": "hi"}], system_prompt="be helpful"
            )
        ]

    system = client.messages.stream.call_args.kwargs["system"]
    assert system[0]["cache_control"] == _EPHEMERAL
