"""Tests for the curator orchestrator (``run_curator``).

Deterministic — no real network or LLM. The Anthropic client is a
hand-built fake whose ``messages.create`` returns a forced-tool-use
response, and the cache root is redirected to ``tmp_path``.

Covers the happy path, per-source failure isolation, the
fabricated-source validation drop, cache hit / force-refresh, the
offline degradation path, and the advisory-budget warning.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import patch

import pytest

from attune.curator import core
from attune.curator.result import SourceItem, SourceSummary


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------
class _Block:
    """Minimal stand-in for an Anthropic content block."""

    def __init__(self, type: str, **kw) -> None:
        self.type = type
        for k, v in kw.items():
            setattr(self, k, v)


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Response:
    def __init__(self, content: list, usage: _Usage | None) -> None:
        self.content = content
        self.usage = usage


class _FakeMessages:
    def __init__(self, response=None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        return self._response


class _FakeBeta:
    def __init__(self, messages: _FakeMessages) -> None:
        self.messages = messages


class _FakeClient:
    def __init__(self, response=None, exc: Exception | None = None) -> None:
        self.messages = _FakeMessages(response=response, exc=exc)
        # Fable models route via the beta namespace (fable_call); share
        # the recorder so ``client.messages.calls`` sees every call.
        self.beta = _FakeBeta(self.messages)


def _tool_response(summary: str, items: list, *, in_tok: int = 1000, out_tok: int = 200):
    block = _Block("tool_use", input={"summary": summary, "items": items})
    return _Response([block], _Usage(in_tok, out_tok))


def _fake_summaries() -> list[SourceSummary]:
    """Two sources with three known item_ids each."""
    return [
        SourceSummary(
            source_id="bulletin",
            state_hash="bh1",
            items=[
                SourceItem(item_id="bulletin:r1", title="run a", detail="d", link="/runs/a"),
                SourceItem(item_id="bulletin:r2", title="run b", detail="d", link="/runs/b"),
                SourceItem(item_id="bulletin:r3", title="run c", detail="d", link="/runs/c"),
            ],
        ),
        SourceSummary(
            source_id="specs",
            state_hash="sh1",
            items=[
                SourceItem(item_id="spec:alpha", title="alpha", detail="d", link="/specs/alpha"),
                SourceItem(item_id="spec:beta", title="beta", detail="d", link="/specs/beta"),
                SourceItem(item_id="spec:gamma", title="gamma", detail="d", link="/specs/gamma"),
            ],
        ),
    ]


def _item(item_id: str, sources: list[str], *, severity: str = "nudge") -> dict:
    return {
        "id": item_id,
        "title": f"item {item_id}",
        "severity": severity,
        "rationale": f"because [{sources[0]}]",
        "sources": sources,
    }


@pytest.fixture
def isolate(tmp_path, monkeypatch):
    """Redirect the cache root and stub source reads with fixtures."""
    monkeypatch.setattr("attune.curator.cache.attune_home", lambda: tmp_path)

    async def _fake_read_all(project_root):
        return _fake_summaries()

    monkeypatch.setattr(core, "_read_all_sources", _fake_read_all)
    return tmp_path


# --------------------------------------------------------------------------
# Source reading isolation
# --------------------------------------------------------------------------
def test_safe_read_swallows_reader_exception(tmp_path, monkeypatch):
    """A reader that raises yields an empty summary, not a crash."""

    def _boom(*, project_root, since=None):
        raise RuntimeError("reader exploded")

    monkeypatch.setattr(core.bulletin, "read", _boom)
    summary = core._safe_read(core.bulletin, tmp_path)
    assert summary.source_id == "bulletin"
    assert summary.items == []


def test_read_all_sources_isolates_one_failure(tmp_path, monkeypatch):
    """One failing reader doesn't abort the others."""

    def _boom(*, project_root, since=None):
        raise RuntimeError("nope")

    monkeypatch.setattr(core.bulletin, "read", _boom)
    summaries = asyncio.run(core._read_all_sources(tmp_path))
    assert len(summaries) == len(core._SOURCE_MODULES)
    by_id = {s.source_id: s for s in summaries}
    assert by_id["bulletin"].items == []


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------
def test_happy_path_returns_validated_items(isolate):
    client = _FakeClient(
        _tool_response(
            "Two things need attention [bulletin:r1].",
            [
                _item("i1", ["bulletin:r1"]),
                _item("i2", ["spec:alpha", "bulletin:r2"]),
            ],
        )
    )
    result = asyncio.run(core.run_curator(project_root=isolate, client=client))
    assert result.summary.startswith("Two things")
    assert [i.id for i in result.items] == ["i1", "i2"]
    assert result.model == core._curator_model()
    assert set(result.sources_consulted) == {"bulletin", "specs"}
    assert result.cost_usd > 0
    assert client.messages.calls  # SDK was invoked


def test_forced_tool_use_options_passed(isolate):
    client = _FakeClient(_tool_response("ok", []))
    asyncio.run(core.run_curator(project_root=isolate, client=client, max_items=7))
    call = client.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": "emit_curation"}
    assert call["tools"][0]["name"] == "emit_curation"
    # max_items flows into the schema cap
    assert call["tools"][0]["input_schema"]["properties"]["items"]["maxItems"] == 7


def test_fabricated_source_item_dropped(isolate, caplog):
    client = _FakeClient(
        _tool_response(
            "summary [bulletin:r1]",
            [
                _item("real", ["bulletin:r1"]),
                _item("fake", ["spec:nonexistent"]),
            ],
        )
    )
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(core.run_curator(project_root=isolate, client=client))
    assert [i.id for i in result.items] == ["real"]
    assert "unknown sources" in caplog.text


def test_cache_hit_skips_second_sdk_call(isolate):
    client = _FakeClient(_tool_response("cached summary", [_item("i1", ["bulletin:r1"])]))
    first = asyncio.run(core.run_curator(project_root=isolate, client=client))
    second = asyncio.run(core.run_curator(project_root=isolate, client=client))
    assert len(client.messages.calls) == 1  # second call served from cache
    assert first.summary == second.summary == "cached summary"


def test_force_refresh_bypasses_cache(isolate):
    client = _FakeClient(_tool_response("fresh", [_item("i1", ["bulletin:r1"])]))
    asyncio.run(core.run_curator(project_root=isolate, client=client))
    asyncio.run(core.run_curator(project_root=isolate, client=client, force_refresh=True))
    assert len(client.messages.calls) == 2  # cache bypassed both times


def test_zero_ttl_always_misses(isolate):
    client = _FakeClient(_tool_response("no cache", [_item("i1", ["bulletin:r1"])]))
    asyncio.run(core.run_curator(project_root=isolate, client=client, cache_ttl_seconds=0))
    asyncio.run(core.run_curator(project_root=isolate, client=client, cache_ttl_seconds=0))
    assert len(client.messages.calls) == 2


class _StatusError(Exception):
    """Stand-in for an anthropic SDK status error (carries ``status_code``)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_offline_on_sdk_failure(isolate):
    client = _FakeClient(exc=RuntimeError("api down"))
    result = asyncio.run(core.run_curator(project_root=isolate, client=client))
    assert result.items == []
    assert result.summary.startswith("The curator is offline")
    # The raw exception text must NOT leak into the dashboard-facing summary.
    assert "api down" not in result.summary
    assert set(result.sources_consulted) == {"bulletin", "specs"}


def test_offline_auth_error_gives_key_guidance(isolate):
    exc = _StatusError("Error code: 401 - invalid x-api-key", status_code=401)
    result = asyncio.run(core.run_curator(project_root=isolate, client=_FakeClient(exc=exc)))
    assert "ANTHROPIC_API_KEY" in result.summary
    # No raw error / request_id leakage.
    assert "401" not in result.summary
    assert "x-api-key" not in result.summary


def test_offline_no_credits_gives_billing_guidance(isolate):
    exc = _StatusError(
        "Error code: 400 - Your credit balance is too low to access the "
        "Anthropic API. request_id: req_abc123",
        status_code=400,
    )
    result = asyncio.run(core.run_curator(project_root=isolate, client=_FakeClient(exc=exc)))
    assert "credit" in result.summary.lower()
    assert "subscription does not include raw API access" in result.summary
    # The request_id must never reach the UI.
    assert "req_abc123" not in result.summary


def test_offline_rate_limit_message(isolate):
    exc = _StatusError("Error code: 429 - rate limit exceeded", status_code=429)
    result = asyncio.run(core.run_curator(project_root=isolate, client=_FakeClient(exc=exc)))
    assert "rate limit" in result.summary.lower()
    assert "429" not in result.summary


def test_refusal_records_event_and_degrades(isolate):
    """A fable refusal degrades to an errored briefing + telemetry event.

    The default curator model is the premium tier (fable), so the call
    rides the beta path where ``stop_reason == "refusal"`` surfaces as
    ``ModelRefusalError``; ``run_curator`` records the ``fable_refusal``
    event and keeps its never-raises contract.
    """
    refusal = _Response([], _Usage(10, 1))
    refusal.stop_reason = "refusal"
    client = _FakeClient(refusal)
    with patch("attune.models.telemetry.log_fable_refusal") as mock_log:
        result = asyncio.run(core.run_curator(project_root=isolate, client=client))

    assert result.items == []
    assert "refused" in result.summary
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["workflow"] == "curator"
    assert mock_log.call_args.kwargs["model"] == core._curator_model()


def test_budget_overage_logs_warning(isolate, caplog):
    # Huge output tokens drive cost above the advisory cap.
    client = _FakeClient(_tool_response("spendy", [_item("i1", ["bulletin:r1"])], out_tok=100_000))
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(
            core.run_curator(project_root=isolate, client=client, max_budget_usd=0.10)
        )
    assert result.cost_usd > 0.10
    assert "advisory budget" in caplog.text


def test_default_client_constructed_when_none(isolate, monkeypatch):
    """client=None lazily builds an AsyncAnthropic (covered via a fake)."""
    import anthropic

    built = _FakeClient(_tool_response("default-client", [_item("i1", ["bulletin:r1"])]))
    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda *a, **k: built)
    result = asyncio.run(core.run_curator(project_root=isolate))
    assert result.summary == "default-client"
    assert built.messages.calls


# --------------------------------------------------------------------------
# Helper units (edge paths)
# --------------------------------------------------------------------------
def test_compute_cost_none_usage_is_zero():
    assert core._compute_cost(core._curator_model(), None) == 0.0


def test_compute_cost_unknown_model_no_pricing(monkeypatch):
    monkeypatch.setattr("attune.cost_tracker.MODEL_PRICING", {})
    assert core._compute_cost("nonexistent-model", _Usage(100, 100)) == 0.0


def test_compute_cost_swallows_pricing_error():
    class _Boom:
        @property
        def input_tokens(self):
            raise RuntimeError("usage broke")

    assert core._compute_cost(core._curator_model(), _Boom()) == 0.0


def test_extract_payload_text_fallback():
    block = _Block("text", text='{"summary": "from text", "items": []}')
    payload = core._extract_curation_payload(_Response([block], None))
    assert payload["summary"] == "from text"


def test_extract_payload_unparseable_text_raises():
    block = _Block("text", text="not json at all")
    with pytest.raises(RuntimeError, match="unparseable"):
        core._extract_curation_payload(_Response([block], None))


def test_extract_payload_no_blocks_raises():
    with pytest.raises(RuntimeError, match="no tool_use"):
        core._extract_curation_payload(_Response([], None))


def test_parse_action_variants():
    assert core._parse_action(None) is None
    assert core._parse_action({"label": "x"}) is None  # missing kind
    assert core._parse_action({"kind": "bogus"}) is None  # invalid kind
    action = core._parse_action({"kind": "ask", "question": "go?", "choices": ["y", "n"]})
    assert action is not None
    assert action.kind == "ask"
    assert action.choices == ["y", "n"]


def test_payload_to_items_skips_malformed():
    payload = {
        "items": [
            "not a dict",
            {"title": "no id"},
            {"id": "ok", "title": "t", "severity": "warn", "sources": ["bulletin:r1"]},
        ]
    }
    items = core._payload_to_items(payload)
    assert [i.id for i in items] == ["ok"]
    assert items[0].severity == "warn"
