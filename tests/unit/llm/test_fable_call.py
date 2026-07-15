"""Unit tests for attune.llm.fable_call (mock-only, no live calls).

Mirrors attune-author's proven coverage (test_anthropic_fable.py):
beta-namespace routing with fallback kwargs for fable models, exact
pre-tier payload for non-fable, refusal -> ModelRefusalError, and the
retention hint on a fable 400 — plus the async twin.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from attune.llm.fable_call import (
    _ADAPTIVE_THINKING_HEADROOM,
    _RETENTION_HINT,
    acreate_with_fable,
    create_with_fable,
)
from attune.model_tiers import ModelRefusalError

FABLE = "claude-fable-5"
OPUS = "claude-opus-4-8"


def _response(text: str = "out", stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        stop_reason=stop_reason,
    )


class _Fake400(Exception):
    status_code = 400


class _Fake400NeedsKwargs(Exception):
    """Mimics anthropic.BadRequestError: not rebuildable from a message."""

    status_code = 400

    def __init__(self, message: str, *, response: object, body: object) -> None:
        super().__init__(message)


class TestSync:
    def test_fable_routes_to_beta_namespace_with_extras(self):
        client = MagicMock()
        client.beta.messages.create.return_value = _response("hi")
        resp = create_with_fable(client, model=FABLE, max_tokens=64)
        assert resp.content[0].text == "hi"
        client.messages.create.assert_not_called()
        kwargs = client.beta.messages.create.call_args.kwargs
        assert kwargs["model"] == FABLE
        assert kwargs["betas"]
        assert "fallbacks" in kwargs["extra_body"]

    def test_non_fable_keeps_plain_namespace_and_payload(self):
        client = MagicMock()
        client.messages.create.return_value = _response()
        create_with_fable(client, model=OPUS, max_tokens=64)
        client.beta.messages.create.assert_not_called()
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs == {"model": OPUS, "max_tokens": 64}

    def test_fable_refusal_raises_typed_error_once(self):
        client = MagicMock()
        refusal = _response("", stop_reason="refusal")
        refusal.stop_details = SimpleNamespace(category="harmful", explanation="no")
        client.beta.messages.create.return_value = refusal
        with pytest.raises(ModelRefusalError) as excinfo:
            create_with_fable(client, model=FABLE, max_tokens=64)
        assert excinfo.value.category == "harmful"
        assert excinfo.value.explanation == "no"
        # a refusal is a verdict, not transport noise — exactly one attempt
        assert client.beta.messages.create.call_count == 1

    def test_refusal_details_from_dict(self):
        client = MagicMock()
        refusal = _response("", stop_reason="refusal")
        refusal.stop_details = {"category": "c", "explanation": "e"}
        client.beta.messages.create.return_value = refusal
        with pytest.raises(ModelRefusalError) as excinfo:
            create_with_fable(client, model=FABLE, max_tokens=64)
        assert excinfo.value.category == "c"

    def test_non_fable_refusal_also_raises(self):
        client = MagicMock()
        refusal = _response("t", stop_reason="refusal")
        refusal.stop_details = SimpleNamespace(category="harmful", explanation="no")
        client.messages.create.return_value = refusal
        with pytest.raises(ModelRefusalError) as excinfo:
            create_with_fable(client, model=OPUS, max_tokens=64)
        assert excinfo.value.category == "harmful"
        client.beta.messages.create.assert_not_called()

    def test_fable_400_carries_retention_hint_same_type(self):
        client = MagicMock()
        client.beta.messages.create.side_effect = _Fake400("bad request")
        with pytest.raises(_Fake400) as excinfo:
            create_with_fable(client, model=FABLE, max_tokens=64)
        assert _RETENTION_HINT in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, _Fake400)

    def test_fable_400_unrebuildable_type_falls_back_to_runtimeerror(self):
        client = MagicMock()
        client.beta.messages.create.side_effect = _Fake400NeedsKwargs(
            "nope", response=None, body=None
        )
        with pytest.raises(RuntimeError) as excinfo:
            create_with_fable(client, model=FABLE, max_tokens=64)
        assert _RETENTION_HINT in str(excinfo.value)

    def test_fable_non_400_reraises_unchanged(self):
        client = MagicMock()
        client.beta.messages.create.side_effect = ValueError("boom")
        with pytest.raises(ValueError, match="^boom$"):
            create_with_fable(client, model=FABLE, max_tokens=64)

    def test_non_fable_400_has_no_retention_hint(self):
        client = MagicMock()
        client.messages.create.side_effect = _Fake400("plain 400")
        with pytest.raises(_Fake400) as excinfo:
            create_with_fable(client, model=OPUS, max_tokens=64)
        assert _RETENTION_HINT not in str(excinfo.value)

    def test_fable_low_max_tokens_grows_for_adaptive_thinking(self):
        client = MagicMock()
        client.beta.messages.create.return_value = _response()
        create_with_fable(client, model=FABLE, max_tokens=1024)
        sent = client.beta.messages.create.call_args.kwargs["max_tokens"]
        assert sent == _ADAPTIVE_THINKING_HEADROOM + 1024

    def test_fable_large_max_tokens_untouched(self):
        client = MagicMock()
        client.beta.messages.create.return_value = _response()
        create_with_fable(client, model=FABLE, max_tokens=_ADAPTIVE_THINKING_HEADROOM + 1)
        sent = client.beta.messages.create.call_args.kwargs["max_tokens"]
        assert sent == _ADAPTIVE_THINKING_HEADROOM + 1

    def test_non_fable_max_tokens_never_grows(self):
        client = MagicMock()
        client.messages.create.return_value = _response()
        create_with_fable(client, model=OPUS, max_tokens=64)
        assert client.messages.create.call_args.kwargs["max_tokens"] == 64


class TestAsync:
    @pytest.mark.asyncio
    async def test_fable_routes_to_beta_namespace(self):
        client = MagicMock()
        client.beta.messages.create = AsyncMock(return_value=_response("hi"))
        resp = await acreate_with_fable(client, model=FABLE, max_tokens=64)
        assert resp.content[0].text == "hi"
        assert "fallbacks" in client.beta.messages.create.call_args.kwargs["extra_body"]

    @pytest.mark.asyncio
    async def test_non_fable_plain_namespace(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=_response())
        await acreate_with_fable(client, model=OPUS, max_tokens=64)
        assert client.messages.create.call_args.kwargs == {
            "model": OPUS,
            "max_tokens": 64,
        }

    @pytest.mark.asyncio
    async def test_fable_refusal_raises(self):
        client = MagicMock()
        refusal = _response("", stop_reason="refusal")
        refusal.stop_details = None
        client.beta.messages.create = AsyncMock(return_value=refusal)
        with pytest.raises(ModelRefusalError) as excinfo:
            await acreate_with_fable(client, model=FABLE, max_tokens=64)
        assert excinfo.value.category is None

    @pytest.mark.asyncio
    async def test_non_fable_refusal_also_raises(self):
        client = MagicMock()
        refusal = _response("t", stop_reason="refusal")
        refusal.stop_details = None
        client.messages.create = AsyncMock(return_value=refusal)
        with pytest.raises(ModelRefusalError):
            await acreate_with_fable(client, model=OPUS, max_tokens=64)
        client.beta.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_fable_400_carries_retention_hint(self):
        client = MagicMock()
        client.beta.messages.create = AsyncMock(side_effect=_Fake400("bad"))
        with pytest.raises(_Fake400) as excinfo:
            await acreate_with_fable(client, model=FABLE, max_tokens=64)
        assert _RETENTION_HINT in str(excinfo.value)
