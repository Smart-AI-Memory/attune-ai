"""Coverage tests for base_agent's LLM-init, Redis-signal, and _call_llm paths.

Targets branches not exercised by ``test_base_agent.py``:
- LLM client initialization (api-key present / absent)
- ``_register_heartbeat`` Redis-exception swallow
- ``_signal_completion`` (no-op, publish, exception swallow)
- ``_call_llm`` with a live client (success, empty content, no-text
  block, exception fallback)

Everything external is mocked — the ``anthropic`` SDK is patched and
no network call is made (keyless-safe).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


def _rule_based_agent(agent_id="cov", role="Role", **kwargs):
    """Build an agent with the LLM init path skipped (rule-based mode)."""
    with (
        patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
        patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
    ):
        from attune.agents.release.base_agent import ReleaseAgent

        return ReleaseAgent(agent_id=agent_id, role=role, **kwargs)


# ---------------------------------------------------------------------------
# __init__ — LLM client initialization (lines 111-117)
# ---------------------------------------------------------------------------


class TestInitLlmClient:
    """ANTHROPIC available + real mode drives the client-init branch."""

    def test_creates_client_with_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-test-key")  # pragma: allowlist secret
        mock_anthropic = MagicMock()
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", True),
            patch("attune.agents.release.base_agent.LLM_MODE", "real"),
            patch("attune.agents.release.base_agent.anthropic", mock_anthropic),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            agent = ReleaseAgent("init-key", "Role")

        assert agent.llm_client is mock_anthropic.Anthropic.return_value
        mock_anthropic.Anthropic.assert_called_once_with(
            api_key="fake-test-key"  # pragma: allowlist secret
        )

    def test_no_api_key_leaves_client_none(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", True),
            patch("attune.agents.release.base_agent.LLM_MODE", "real"),
            patch("attune.agents.release.base_agent.anthropic", MagicMock()),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            agent = ReleaseAgent("init-nokey", "Role")

        assert agent.llm_client is None


# ---------------------------------------------------------------------------
# _register_heartbeat — exception swallow (lines 137-139)
# ---------------------------------------------------------------------------


class TestHeartbeatException:
    def test_redis_error_swallowed(self):
        mock_redis = MagicMock()
        mock_redis.hset.side_effect = RuntimeError("redis down")
        agent = _rule_based_agent(redis_client=mock_redis)

        # Should not raise despite the backend error.
        agent._register_heartbeat(status="running", task="x")


# ---------------------------------------------------------------------------
# _signal_completion (lines 143-161)
# ---------------------------------------------------------------------------


class TestSignalCompletion:
    def test_no_op_without_redis(self):
        agent = _rule_based_agent()
        # No redis → returns silently, nothing to assert beyond no raise.
        agent._signal_completion({"score": 5.0})

    def test_publishes_scalar_only_summary(self):
        mock_redis = MagicMock()
        agent = _rule_based_agent(redis_client=mock_redis)

        agent._signal_completion(
            {"score": 7.5, "ok": True, "n": 3, "nested": {"a": 1}, "items": [1, 2]}
        )

        mock_redis.publish.assert_called_once()
        channel, raw = mock_redis.publish.call_args[0]
        assert channel.endswith(agent.agent_id)
        payload = json.loads(raw)
        summary = payload["result_summary"]
        # Scalars kept; dict/list values filtered out.
        assert summary["score"] == 7.5
        assert summary["ok"] is True
        assert summary["n"] == 3
        assert "nested" not in summary
        assert "items" not in summary

    def test_publish_exception_swallowed(self):
        mock_redis = MagicMock()
        mock_redis.publish.side_effect = RuntimeError("redis down")
        agent = _rule_based_agent(redis_client=mock_redis)

        # Should not raise.
        agent._signal_completion({"score": 1.0})


# ---------------------------------------------------------------------------
# _call_llm — live client paths (lines 178-216)
# ---------------------------------------------------------------------------


class TestCallLlmWithClient:
    def _agent_with_client(self, response=None, raises=None):
        from attune.agents.release.base_agent import ReleaseAgent  # noqa: F401

        agent = _rule_based_agent()
        client = MagicMock()
        # Fable (premium) calls route via client.beta.messages.create
        # (create_with_fable); wire both namespaces to the same behavior.
        if raises is not None:
            client.messages.create.side_effect = raises
            client.beta.messages.create.side_effect = raises
        else:
            client.messages.create.return_value = response
            client.beta.messages.create.return_value = response
        agent.llm_client = client
        return agent, client

    def _response(self, text="answer", content_blocks=None, in_tok=100, out_tok=50):
        resp = MagicMock()
        resp.usage.input_tokens = in_tok
        resp.usage.output_tokens = out_tok
        if content_blocks is None:
            block = MagicMock()
            block.text = text
            content_blocks = [block]
        resp.content = content_blocks
        return resp

    def test_success_parses_text_and_tracks_cost(self):
        from attune.agents.release.release_models import Tier

        agent, client = self._agent_with_client(response=self._response("llm answer"))
        text, meta = agent._call_llm("prompt", "system", Tier.CHEAP)

        assert text == "llm answer"
        assert meta["input_tokens"] == 100
        assert meta["output_tokens"] == 50
        assert meta["cost"] > 0
        assert agent.total_cost > 0
        assert agent.total_tokens == 150
        client.messages.create.assert_called_once()

    def test_empty_content_returns_empty_text(self):
        from attune.agents.release.release_models import Tier

        agent, _ = self._agent_with_client(response=self._response(content_blocks=[]))
        text, meta = agent._call_llm("p", "s", Tier.CAPABLE)

        assert text == ""
        # Still a successful call — model name recorded, not the fallback.
        assert meta["model"] != "fallback"
        assert meta["cost"] >= 0

    def test_block_without_text_attr_returns_empty(self):
        from attune.agents.release.release_models import Tier

        # A content block that lacks a ``.text`` attribute.
        agent, _ = self._agent_with_client(response=self._response(content_blocks=[42]))
        text, meta = agent._call_llm("p", "s", Tier.PREMIUM)

        assert text == ""
        assert meta["model"] != "fallback"

    def test_premium_routes_via_beta_namespace(self, monkeypatch):
        """Premium tier resolves to fable -> create_with_fable beta path.

        The beta-namespace route is reached BECAUSE premium resolves to
        fable, and that resolution happens at IMPORT time, so an exported
        ``ATTUNE_MODEL_PREMIUM`` genuinely changes production routing —
        the old failure here was a real behavior difference, not a bad
        assertion. Clear the override and reload so the test exercises
        the default routing deterministically, the same way
        test_release_models.py::test_model_config_uses_current_model_ids
        does for the literal ids.
        """
        import importlib

        import attune.agents.release.release_models as rm

        monkeypatch.delenv("ATTUNE_MODEL_PREMIUM", raising=False)
        importlib.reload(rm)
        MODEL_CONFIG, Tier = rm.MODEL_CONFIG, rm.Tier

        assert "fable" in MODEL_CONFIG["premium"]  # task 6 wiring
        resp = self._response("premium answer")
        resp.stop_reason = "end_turn"
        agent, client = self._agent_with_client(response=resp)
        text, meta = agent._call_llm("p", "s", Tier.PREMIUM)

        assert text == "premium answer"
        assert meta["model"] == MODEL_CONFIG["premium"]
        client.beta.messages.create.assert_called_once()
        client.messages.create.assert_not_called()

    def test_premium_refusal_returns_fallback_and_records_event(self):
        """A refusal keeps the graceful fallback AND records telemetry."""
        from unittest.mock import patch

        from attune.agents.release.release_models import Tier

        resp = self._response("never surfaced")
        resp.stop_reason = "refusal"
        agent, _ = self._agent_with_client(response=resp)
        with patch("attune.models.telemetry.log_fable_refusal") as mock_log:
            text, meta = agent._call_llm("p", "s", Tier.PREMIUM)

        assert text == ""
        assert meta["model"] == "fallback"
        assert "error" in meta
        mock_log.assert_called_once()

    def test_leading_thinking_block_skipped_for_first_text(self):
        """First TEXT block wins, not content[0] (fable_call gotcha)."""
        from types import SimpleNamespace

        from attune.agents.release.release_models import Tier

        thinking = SimpleNamespace(type="thinking", thinking="...")
        text_block = SimpleNamespace(type="text", text="real answer")
        resp = self._response(content_blocks=[thinking, text_block])
        agent, _ = self._agent_with_client(response=resp)
        text, _meta = agent._call_llm("p", "s", Tier.CHEAP)

        assert text == "real answer"

    def test_exception_returns_fallback_metadata(self):
        from attune.agents.release.release_models import Tier

        agent, _ = self._agent_with_client(raises=RuntimeError("api down"))
        text, meta = agent._call_llm("p", "s", Tier.CHEAP)

        assert text == ""
        assert meta["model"] == "fallback"
        assert meta["cost"] == 0.0
        assert "error" in meta


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
