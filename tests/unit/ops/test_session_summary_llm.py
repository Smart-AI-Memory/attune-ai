"""Tests for the Haiku-summarizer module.

Covers prompt assembly, input truncation, token + cost accounting,
empty-response fallback, and missing-API-key signaling. Uses a
fake client factory throughout so no real network calls are made.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from attune.ops import session_summary_llm as llm

# ---------------------------------------------------------------------------
# Fake Anthropic client — shape-compatible with the real SDK's
# ``messages.create`` return value (content list of blocks with
# ``.text`` plus ``usage`` with ``input_tokens`` / ``output_tokens``).
# ---------------------------------------------------------------------------


@dataclass
class _FakeBlock:
    text: str


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeResponse:
    content: list
    usage: _FakeUsage


class _FakeMessages:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self.messages = _FakeMessages(response)


def _client_factory(response: _FakeResponse):
    """Build a ``client_factory`` callable that returns the same fake every call."""

    def factory(*, api_key: str):
        return _FakeClient(response)

    return factory


# ---------------------------------------------------------------------------
# summarize() — happy path + token + cost accounting
# ---------------------------------------------------------------------------


def test_summarize_returns_text_and_accounting():
    response = _FakeResponse(
        content=[_FakeBlock(text="**What was being worked on.** Foo.")],
        usage=_FakeUsage(input_tokens=120, output_tokens=40),
    )
    result = llm.summarize(
        "Help me with the foo bar baz.",
        api_key="fake-key",  # pragma: allowlist secret
        client_factory=_client_factory(response),
    )
    assert result.text.startswith("**What was being worked on.**")
    assert result.tokens_in == 120
    assert result.tokens_out == 40
    # Cost: 120 * $1/M + 40 * $5/M = 0.00012 + 0.0002 = 0.00032
    assert result.cost_usd == pytest.approx(0.00032, rel=1e-6)


def test_summarize_uses_haiku_4_5_model():
    response = _FakeResponse(
        content=[_FakeBlock(text="ok")],
        usage=_FakeUsage(input_tokens=10, output_tokens=10),
    )
    factory = _client_factory(response)
    captured: list = []

    def wrapping_factory(*, api_key: str):
        client = factory(api_key=api_key)
        captured.append(client)
        return client

    llm.summarize(
        "text",
        api_key="fake-key",  # pragma: allowlist secret
        client_factory=wrapping_factory,
    )
    assert captured, "client factory was not invoked"
    call_kwargs = captured[0].messages.calls[0]
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


def test_summarize_includes_system_prompt():
    response = _FakeResponse(
        content=[_FakeBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    client_holder: list = []

    def wrapping_factory(*, api_key: str):
        c = _FakeClient(response)
        client_holder.append(c)
        return c

    llm.summarize(
        "text", api_key="fake-key", client_factory=wrapping_factory
    )  # pragma: allowlist secret
    call_kwargs = client_holder[0].messages.calls[0]
    system = call_kwargs["system"]
    # Spec Decision 2 — three-section output shape.
    assert "What was being worked on" in system
    assert "Open threads" in system
    assert "Resume prompt" in system


def test_summarize_caps_input_text():
    """An oversized input string is truncated before being sent."""
    response = _FakeResponse(
        content=[_FakeBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    client_holder: list = []

    def wrapping_factory(*, api_key: str):
        c = _FakeClient(response)
        client_holder.append(c)
        return c

    huge = "x" * 50_000
    llm.summarize(
        huge, api_key="fake-key", client_factory=wrapping_factory
    )  # pragma: allowlist secret
    sent = client_holder[0].messages.calls[0]["messages"][0]["content"]
    assert len(sent) < len(huge)
    assert sent.endswith("[...session truncated for summarization...]")


def test_summarize_handles_empty_response_content():
    """An empty content list yields a sentinel string, not a crash."""
    response = _FakeResponse(
        content=[],
        usage=_FakeUsage(input_tokens=5, output_tokens=0),
    )
    result = llm.summarize(
        "text",
        api_key="fake-key",
        client_factory=_client_factory(response),  # pragma: allowlist secret
    )
    assert result.text == "(no summary returned)"


def test_summarize_missing_api_key_raises_typed_error(monkeypatch):
    """Missing API key is a config error, distinct from runtime LLM failures."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.MissingApiKeyError):
        llm.summarize("text")


def test_summarize_reads_api_key_from_env(monkeypatch):
    """Env var is consulted when no explicit ``api_key`` is passed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")  # pragma: allowlist secret
    response = _FakeResponse(
        content=[_FakeBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    captured_keys: list[str] = []

    def factory(*, api_key: str):
        captured_keys.append(api_key)
        return _FakeClient(response)

    llm.summarize("text", client_factory=factory)
    assert captured_keys == ["env-key"]


# ---------------------------------------------------------------------------
# Cost calc — straight math sanity
# ---------------------------------------------------------------------------


def test_estimate_cost_uses_haiku_pricing():
    # 1M input + 1M output = $1.00 + $5.00 = $6.00
    assert llm._estimate_cost(1_000_000, 1_000_000) == pytest.approx(6.00)
    # 1000 input, 250 output = 0.001 + 0.00125 = 0.00225
    assert llm._estimate_cost(1000, 250) == pytest.approx(0.00225)


# ---------------------------------------------------------------------------
# Input truncation — boundary heuristics
# ---------------------------------------------------------------------------


def test_truncate_input_passes_short_text_through():
    text = "short text"
    assert llm._truncate_input(text, cap=100) == text


def test_truncate_input_respects_paragraph_boundary():
    """Truncation prefers the last paragraph break inside the soft floor."""
    text = ("a" * 4500) + "\n\n" + ("b" * 4500)
    result = llm._truncate_input(text, cap=5000)
    assert result.endswith("[...session truncated for summarization...]")
    # The b-block must be excluded — boundary cut at the \n\n.
    assert "b" not in result, "b-block leaked past the paragraph boundary"
