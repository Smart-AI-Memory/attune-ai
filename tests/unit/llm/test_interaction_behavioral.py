"""Behavioral tests for the LLM InteractionMixin.

The mixin provides the five empathy-level handlers and background pattern
detection for EmpathyLLM. Each handler awaits ``self.provider.generate``
and shapes a response dict; a minimal _Host supplies a fake async provider
that records the kwargs it receives so prompt building, history wiring,
model-override pass-through, and pattern-driven branching can all be
exercised without a real LLM. The level methods are driven via
``asyncio.run``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from attune.llm.interaction import InteractionMixin
from attune.llm.state import CollaborationState, PatternType, UserPattern


class _FakeResponse:
    def __init__(self):
        self.content = "generated reply"
        self.tokens_used = 42
        self.model = "claude-test"


class _FakeProvider:
    """Records generate() kwargs and returns a canned response."""

    def __init__(self):
        self.calls: list[dict] = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse()


class _Host(InteractionMixin):
    """Minimal host satisfying the mixin's expected attributes."""

    def __init__(self, *, pattern_library=None, cached_memory=None):
        self.provider = _FakeProvider()
        self.pattern_library = {} if pattern_library is None else pattern_library
        self._cached_memory = cached_memory


def _state(user_id="dev_1", trust=0.5):
    return CollaborationState(user_id=user_id, trust_level=trust)


def _high_confidence_pattern(trigger="deploy"):
    return UserPattern(
        pattern_type=PatternType.SEQUENTIAL,
        trigger=trigger,
        action="run the smoke tests",
        confidence=0.9,
        occurrences=3,
        last_seen=datetime.now(),
    )


# ---------------------------------------------------------------------------
# _build_system_prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    def test_returns_level_prompt_without_cached_memory(self):
        host = _Host()
        prompt = host._build_system_prompt(1)
        assert isinstance(prompt, str) and prompt
        assert "Attune AI Instructions" not in prompt

    def test_prepends_cached_memory_when_present(self):
        host = _Host(cached_memory="REMEMBER: user prefers brevity")
        prompt = host._build_system_prompt(2)
        assert prompt.startswith("REMEMBER: user prefers brevity")
        assert "Attune AI Instructions" in prompt


# ---------------------------------------------------------------------------
# Level handlers — shared shape + model override
# ---------------------------------------------------------------------------


class TestLevelHandlers:
    def test_level_1_reactive_basic_response(self):
        host = _Host()
        result = asyncio.run(host._level_1_reactive("hi", _state(), {}))

        assert result["content"] == "generated reply"
        assert result["proactive"] is False
        assert result["metadata"]["tokens_used"] == 42
        sent = host.provider.calls[0]
        assert sent["messages"] == [{"role": "user", "content": "hi"}]
        assert "system_prompt" in sent and "temperature" in sent

    def test_level_1_passes_model_override(self):
        host = _Host()
        asyncio.run(host._level_1_reactive("hi", _state(), {}, model_override="opus-x"))
        assert host.provider.calls[0]["model"] == "opus-x"

    def test_level_2_guided_includes_history(self):
        host = _Host()
        state = _state()
        state.add_interaction("user", "earlier question", 2)
        result = asyncio.run(host._level_2_guided("follow up", state, {}))

        assert result["metadata"]["history_turns"] >= 1
        # last message is the new user input
        assert host.provider.calls[0]["messages"][-1]["content"] == "follow up"

    def test_level_2_passes_model_override(self):
        host = _Host()
        asyncio.run(host._level_2_guided("q", _state(), {}, model_override="m2"))
        assert host.provider.calls[0]["model"] == "m2"

    def test_level_3_acts_on_matching_pattern(self):
        host = _Host()
        state = _state(trust=0.9)
        state.detected_patterns.append(_high_confidence_pattern("deploy"))
        result = asyncio.run(host._level_3_proactive("time to deploy", state, {}))

        assert result["proactive"] is True
        assert result["metadata"]["pattern"]["trigger"] == "deploy"

    def test_level_3_no_match_runs_standard_path(self):
        host = _Host()
        result = asyncio.run(host._level_3_proactive("hello", _state(), {}))

        assert result["proactive"] is False
        assert result["metadata"]["pattern"] is None

    def test_level_3_passes_model_override(self):
        host = _Host()
        state = _state(trust=0.9)
        state.detected_patterns.append(_high_confidence_pattern("deploy"))
        asyncio.run(host._level_3_proactive("deploy now", state, {}, model_override="m3"))
        assert host.provider.calls[0]["model"] == "m3"

    def test_level_4_anticipatory_is_proactive(self):
        host = _Host()
        state = _state(trust=0.8)
        result = asyncio.run(host._level_4_anticipatory("plan ahead", state, {}))

        assert result["proactive"] is True
        assert result["metadata"]["trajectory_analyzed"] is True
        assert result["metadata"]["trust_level"] == 0.8

    def test_level_4_passes_model_override(self):
        host = _Host()
        asyncio.run(host._level_4_anticipatory("q", _state(), {}, model_override="m4"))
        assert host.provider.calls[0]["model"] == "m4"

    def test_level_5_systems_includes_pattern_library(self):
        host = _Host(pattern_library={"p1": "x", "p2": "y"})
        result = asyncio.run(host._level_5_systems("generalize", _state(), {}))

        assert result["proactive"] is True
        assert result["metadata"]["pattern_library_size"] == 2
        assert result["metadata"]["systems_level"] is True
        # pattern library text injected into the prompt
        assert "SHARED PATTERN LIBRARY" in host.provider.calls[0]["messages"][-1]["content"]

    def test_level_5_empty_library_omits_context(self):
        host = _Host(pattern_library={})
        result = asyncio.run(host._level_5_systems("q", _state(), {}))

        assert result["metadata"]["pattern_library_size"] == 0
        assert "SHARED PATTERN LIBRARY" not in host.provider.calls[0]["messages"][-1]["content"]

    def test_level_5_passes_model_override(self):
        host = _Host(pattern_library={"p": 1})
        asyncio.run(host._level_5_systems("q", _state(), {}, model_override="m5"))
        assert host.provider.calls[0]["model"] == "m5"


# ---------------------------------------------------------------------------
# _detect_patterns_async
# ---------------------------------------------------------------------------


def _populate(state, messages):
    for role, content in messages:
        state.add_interaction(role, content, 3)


class TestDetectPatternsAsync:
    def test_returns_early_with_few_interactions(self):
        host = _Host()
        state = _state()
        _populate(state, [("user", "hello"), ("user", "again")])

        asyncio.run(host._detect_patterns_async(state, "now"))
        assert state.detected_patterns == []

    def test_detects_sequential_pattern(self):
        host = _Host()
        state = _state()
        _populate(
            state,
            [
                ("user", "please review this code"),
                ("user", "now fix the bug"),
                ("user", "thanks"),
            ],
        )

        asyncio.run(host._detect_patterns_async(state, "next"))
        types = {p.pattern_type for p in state.detected_patterns}
        assert PatternType.SEQUENTIAL in types

    def test_detects_preference_pattern(self):
        host = _Host()
        state = _state()
        _populate(
            state,
            [
                ("user", "keep it concise"),
                ("user", "concise please"),
                ("user", "still concise"),
            ],
        )

        asyncio.run(host._detect_patterns_async(state, "next"))
        prefs = [p for p in state.detected_patterns if p.pattern_type == PatternType.PREFERENCE]
        assert prefs and prefs[0].trigger == "concise"

    def test_detects_conditional_pattern(self):
        host = _Host()
        state = _state()
        _populate(
            state,
            [
                ("user", "I hit an error"),
                ("user", "help me debug it"),
                ("user", "ok"),
            ],
        )

        asyncio.run(host._detect_patterns_async(state, "next"))
        conds = [p for p in state.detected_patterns if p.pattern_type == PatternType.CONDITIONAL]
        assert conds and conds[0].trigger == "error"

    def test_returns_when_too_few_user_messages(self):
        host = _Host()
        state = _state()
        # 3 interactions but only one is from the user
        _populate(
            state,
            [("assistant", "a"), ("assistant", "b"), ("user", "only one")],
        )

        asyncio.run(host._detect_patterns_async(state, "next"))
        assert state.detected_patterns == []

    def test_exception_is_swallowed(self):
        host = _Host()
        # interactions has length >= 3 but items lack .role -> AttributeError
        broken_state = CollaborationState(user_id="x")
        broken_state.interactions = [object(), object(), object()]

        # should not raise — the handler logs and returns
        asyncio.run(host._detect_patterns_async(broken_state, "input"))
