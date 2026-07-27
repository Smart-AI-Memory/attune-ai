"""Tests for subscription-first auth routing (attune.models.single_turn).

Phase 1 of the sibling-subscription-auth spec. Covers the four
credential states (subscription / API key / both / neither), the
explicit-override precedence, and the failure modes (subscription
dies mid-run, forced modes, no credentials at all).

Mocking happens at the adapter boundary (``_call_subscription``)
and at the Anthropic-SDK source module — never at the wire.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.models import single_turn as auth
from attune.models.single_turn import (
    AUTH_MODE_ENV,
    AnthropicCallError,
    auth_status,
    auth_telemetry,
    call_llm,
    reset_auth_telemetry,
    resolve_auth_mode,
    subscription_available,
)

_CALL_KWARGS = {
    "system": "sys prompt",
    "user_message": "polish this",
    "model": "claude-sonnet-4-6",
    "max_tokens": 64,
}


@pytest.fixture(autouse=True)
def _clean_auth_env(monkeypatch: pytest.MonkeyPatch):
    """Neutral auth environment per test.

    The suite-wide conftest pins ``ATTUNE_AUTH_MODE=api``
    (so un-mocked polish calls can't hit a real subscription);
    these tests exercise the routing itself, so start from a
    clean slate instead.
    """
    monkeypatch.delenv(AUTH_MODE_ENV, raising=False)
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reset_auth_telemetry()
    yield
    reset_auth_telemetry()


def _enable_subscription(monkeypatch: pytest.MonkeyPatch, importable: bool = True) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setattr(auth, "_sdk_importable", lambda: importable)


class TestSubscriptionDetection:
    def test_unavailable_without_claudecode(self, monkeypatch):
        monkeypatch.setattr(auth, "_sdk_importable", lambda: True)
        assert subscription_available() is False

    def test_unavailable_without_sdk(self, monkeypatch):
        _enable_subscription(monkeypatch, importable=False)
        assert subscription_available() is False

    def test_available_with_both_signals(self, monkeypatch):
        _enable_subscription(monkeypatch)
        assert subscription_available() is True


class TestResolveAuthMode:
    def test_auto_prefers_subscription(self, monkeypatch):
        _enable_subscription(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        assert resolve_auth_mode() == "sub"

    def test_auto_falls_back_to_api(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        assert resolve_auth_mode() == "api"

    def test_explicit_api_beats_available_subscription(self, monkeypatch):
        _enable_subscription(monkeypatch)
        assert resolve_auth_mode("api") == "api"

    def test_explicit_param_beats_env_var(self, monkeypatch):
        _enable_subscription(monkeypatch)
        monkeypatch.setenv(AUTH_MODE_ENV, "api")
        assert resolve_auth_mode("sub") == "sub"

    def test_env_var_consulted_when_no_explicit(self, monkeypatch):
        _enable_subscription(monkeypatch)
        monkeypatch.setenv(AUTH_MODE_ENV, "api")
        assert resolve_auth_mode() == "api"

    def test_forced_sub_without_subscription_raises(self):
        with pytest.raises(AnthropicCallError, match="forced but no subscription"):
            resolve_auth_mode("sub")

    def test_invalid_mode_raises(self):
        with pytest.raises(AnthropicCallError, match="Invalid auth mode"):
            resolve_auth_mode("subscription")


class TestCallLlmRouting:
    def test_subscription_route(self, monkeypatch):
        _enable_subscription(monkeypatch)
        with patch.object(auth, "_call_subscription", return_value="polished!") as sub:
            result = call_llm(**_CALL_KWARGS)
        assert result == "polished!"
        sub.assert_called_once_with(
            system="sys prompt",
            user_message="polish this",
            model="claude-sonnet-4-6",
        )
        assert auth_telemetry() == {"sub_calls": 1.0, "api_calls": 0.0}

    def test_api_route(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("attune.models.single_turn.get_client") as gc:
            gc.return_value = object()
            with patch(
                "attune.models.single_turn.call_api",
                return_value="api polished",
            ) as ca:
                result = call_llm(**_CALL_KWARGS, cache_system=True)
        assert result == "api polished"
        kwargs = ca.call_args.kwargs
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["max_tokens"] == 64
        assert kwargs["cache_system"] is True
        assert auth_telemetry() == {"sub_calls": 0.0, "api_calls": 1.0}

    def test_no_credentials_raises_with_both_paths_named(self):
        with pytest.raises(AnthropicCallError, match="Claude Code") as exc_info:
            call_llm(**_CALL_KWARGS)
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)


class TestSubscriptionFailureModes:
    def test_auto_falls_back_to_api_on_sub_failure(self, monkeypatch, caplog):
        _enable_subscription(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch.object(auth, "_call_subscription", side_effect=RuntimeError("session expired")):
            with patch("attune.models.single_turn.get_client") as gc:
                gc.return_value = object()
                with patch(
                    "attune.models.single_turn.call_api",
                    return_value="api polished",
                ):
                    with caplog.at_level("WARNING"):
                        result = call_llm(**_CALL_KWARGS)
        assert result == "api polished"
        assert any("falling back" in r.message for r in caplog.records)
        assert auth_telemetry() == {"sub_calls": 0.0, "api_calls": 1.0}

    def test_auto_sub_failure_without_key_raises(self, monkeypatch):
        _enable_subscription(monkeypatch)
        with patch.object(auth, "_call_subscription", side_effect=RuntimeError("session expired")):
            with pytest.raises(AnthropicCallError, match="session expired"):
                call_llm(**_CALL_KWARGS)

    def test_forced_sub_failure_does_not_fall_back(self, monkeypatch):
        """Explicit --auth-mode=sub means its failures too — no
        silent billing of the API key behind the user's back."""
        _enable_subscription(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch.object(auth, "_call_subscription", side_effect=RuntimeError("boom")):
            with patch("attune.models.single_turn.call_api") as ca:
                with pytest.raises(AnthropicCallError, match="boom"):
                    call_llm(**_CALL_KWARGS, auth_mode="sub")
        ca.assert_not_called()

    def test_sub_failure_message_is_redacted(self, monkeypatch):
        """Credential-looking material in subscription errors gets the
        same redaction contract as call_api."""
        _enable_subscription(monkeypatch)
        secret = "sk-ant-" + "abc123def456ghi789"
        with patch.object(auth, "_call_subscription", side_effect=RuntimeError(f"bad {secret}")):
            with pytest.raises(AnthropicCallError) as exc_info:
                call_llm(**_CALL_KWARGS)
        assert secret not in str(exc_info.value)
        assert "sk-ant-[REDACTED]" in str(exc_info.value)


class TestAuthStatus:
    def test_subscription_state(self, monkeypatch):
        _enable_subscription(monkeypatch)
        status = auth_status()
        assert status["claudecode"] is True
        assert status["subscription_available"] is True
        assert status["resolved_mode"] == "sub"
        assert status["error"] is None

    def test_no_credentials_state(self, monkeypatch):
        monkeypatch.setattr(auth, "_sdk_importable", lambda: False)
        status = auth_status()
        assert status["subscription_available"] is False
        assert status["api_key_available"] is False
        assert status["resolved_mode"] == "api"

    def test_forced_sub_error_reported_not_raised(self, monkeypatch):
        monkeypatch.setenv(AUTH_MODE_ENV, "sub")
        monkeypatch.setattr(auth, "_sdk_importable", lambda: False)
        status = auth_status()
        assert status["resolved_mode"] is None
        assert "forced but no subscription" in str(status["error"])


class TestPolishWiring:
    def test_call_llm_is_the_polish_chokepoint(self, monkeypatch):
        """polish._call_llm routes through auth.call_llm (task 1.3)."""
        from attune.authoring import polish

        with patch.object(auth, "call_llm", return_value="routed") as cl:
            result = polish._call_llm(
                content="# T\n\nbody\n",
                feature_name="feat",
                source_summary="def f(): pass",
                template_type="concept",
            )
        assert result == "routed"
        kwargs = cl.call_args.kwargs
        assert kwargs["model"] == polish._polish_model()
        assert kwargs["max_tokens"] == polish.POLISH_MAX_TOKENS


def _install_fake_sdk(monkeypatch: pytest.MonkeyPatch, *, result_text: str | None):
    """Install a duck-shaped ``claude_agent_sdk`` into ``sys.modules``.

    ``_query_subscription`` imports the SDK inside the function, so a
    ``sys.modules`` entry intercepts it without the real package (or
    its subprocess) being involved. Returns the capture dict the fake
    ``query`` fills in.
    """
    import sys
    import types

    fake = types.ModuleType("claude_agent_sdk")

    class TextBlock:
        def __init__(self, text: str) -> None:
            self.text = text

    class AssistantMessage:
        def __init__(self, content: list) -> None:
            self.content = content

    class ResultMessage:
        def __init__(self, result: str | None) -> None:
            self.result = result

    class ClaudeAgentOptions:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    captured: dict[str, object] = {}

    async def query(*, prompt: str, options: object):
        captured["prompt"] = prompt
        captured["options"] = options
        yield AssistantMessage([TextBlock("part one "), TextBlock("part two")])
        yield ResultMessage(result_text)

    fake.TextBlock = TextBlock
    fake.AssistantMessage = AssistantMessage
    fake.ResultMessage = ResultMessage
    fake.ClaudeAgentOptions = ClaudeAgentOptions
    fake.query = query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake)
    return captured


class TestSubscriptionAdapter:
    """Adapter internals, with the SDK faked at the module boundary."""

    async def test_query_prefers_result_message(self, monkeypatch):
        _install_fake_sdk(monkeypatch, result_text="final result")
        text = await auth._query_subscription(system="sys", user_message="msg", model="m-1")
        assert text == "final result"

    async def test_query_falls_back_to_assistant_text(self, monkeypatch):
        """ResultMessage.result can be None on some runs — the
        collected AssistantMessage text is the fallback."""
        _install_fake_sdk(monkeypatch, result_text=None)
        text = await auth._query_subscription(system="sys", user_message="msg", model="m-1")
        assert text == "part one part two"

    async def test_query_options_keep_isolation_invariant(self, monkeypatch):
        """Drift-guard: the subscription subprocess must run with
        setting_sources=[] (no user/project hooks or CLAUDE.md — they
        pollute the stream-json channel), no tools, and one turn."""
        captured = _install_fake_sdk(monkeypatch, result_text="ok")
        await auth._query_subscription(
            system="the system prompt", user_message="the user msg", model="m-1"
        )
        kwargs = captured["options"].kwargs
        assert kwargs["setting_sources"] == []
        assert kwargs["allowed_tools"] == []
        assert kwargs["max_turns"] == 1
        assert kwargs["system_prompt"] == "the system prompt"
        assert kwargs["model"] == "m-1"
        assert captured["prompt"] == "the user msg"

    def test_call_subscription_without_running_loop(self, monkeypatch):
        async def fake_query(**kwargs: object) -> str:
            return "from-coro"

        monkeypatch.setattr(auth, "_query_subscription", fake_query)
        result = auth._call_subscription(system="s", user_message="u", model="m")
        assert result == "from-coro"

    async def test_call_subscription_inside_running_loop(self, monkeypatch):
        """A caller already inside an event loop gets the worker-thread
        dispatch instead of a nested asyncio.run crash."""

        async def fake_query(**kwargs: object) -> str:
            return "threaded"

        monkeypatch.setattr(auth, "_query_subscription", fake_query)
        result = auth._call_subscription(system="s", user_message="u", model="m")
        assert result == "threaded"


class TestDetectionEdgeCases:
    def test_sdk_importable_swallows_find_spec_errors(self, monkeypatch):
        import importlib.util

        def boom(name: str):
            raise ValueError("broken finder")

        monkeypatch.setattr(importlib.util, "find_spec", boom)
        assert auth._sdk_importable() is False

    def test_telemetry_lazy_init(self, monkeypatch):
        monkeypatch.delattr(auth.auth_telemetry, "_state", raising=False)
        assert auth_telemetry() == {"sub_calls": 0.0, "api_calls": 0.0}
