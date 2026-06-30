"""Tests for attune.agent_factory.adapters.langchain_adapter._get_llm.

Focus: Opus 4.7+ sampling-param normalization. Opus 4.7 and later reject
temperature/top_p/top_k with HTTP 400, so the Anthropic branch must omit
them for those models while keeping them for older models and OpenAI.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import attune.agent_factory.adapters.langchain_adapter as mod
from attune.agent_factory.adapters.langchain_adapter import LangChainAdapter
from attune.agent_factory.base import AgentConfig, AgentRole


def _config(model_id: str) -> AgentConfig:
    return AgentConfig(name="t", role=AgentRole.COORDINATOR, model_override=model_id)


@pytest.mark.unit
class TestLangChainAdapterGetLLMNormalization:
    def setup_method(self):
        mod._langchain_available = True  # force is_available() True

    def teardown_method(self):
        mod._langchain_available = None

    def test_anthropic_omits_temperature_for_opus_4_8(self):
        """Opus 4.7+ reject temperature/top_p/top_k → not passed to ChatAnthropic."""
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
            adapter = LangChainAdapter(provider="anthropic", api_key="sk-test")
            adapter._get_llm(_config("claude-opus-4-8"))
        kwargs = mock_chat.call_args.kwargs
        assert "temperature" not in kwargs
        assert "top_p" not in kwargs
        assert "top_k" not in kwargs
        assert kwargs["model"] == "claude-opus-4-8"

    def test_anthropic_keeps_temperature_for_sonnet(self):
        """Sonnet still accepts temperature → passed through."""
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
            adapter = LangChainAdapter(provider="anthropic", api_key="sk-test")
            adapter._get_llm(_config("claude-sonnet-5"))
        assert "temperature" in mock_chat.call_args.kwargs

    def test_anthropic_keeps_temperature_for_opus_4_6(self):
        """Opus 4.6 still accepts temperature → passed through."""
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
            adapter = LangChainAdapter(provider="anthropic", api_key="sk-test")
            adapter._get_llm(_config("claude-opus-4-6"))
        assert "temperature" in mock_chat.call_args.kwargs
