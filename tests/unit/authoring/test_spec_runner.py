"""Tests for the bounded Fable spec-drafting runner (workflow todo item 2)."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import pytest

from attune.authoring.spec_runner import (
    PER_DOCUMENT,
    WHOLE_SPEC,
    Budgets,
    DocRequest,
    SpecDraftRunner,
    build_prompt,
    parse_documents,
)

REQ = DocRequest("docs/specs/x/requirements.md", "user stories")
DES = DocRequest("docs/specs/x/design.md", "architecture")

FAST = Budgets(
    first_event_s=0.2,
    inter_event_s=0.2,
    total_single_s=5.0,
    total_multi_s=5.0,
    max_chars_per_doc=200,
)


def _text_event(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text=text))


def _stop_event(reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(type="message_delta", delta=SimpleNamespace(stop_reason=reason))


def _doc_block(path: str, body: str = "content") -> str:
    return f"=== FILE: {path} ===\n{body}\n"


class FakeClient:
    """anthropic-shaped client whose scripted streams are plain generators.

    ``scripts`` is consumed one entry per create() call; each entry is a
    list of events, a float (sleep before yielding nothing — silence),
    or an Exception to raise mid-stream.
    """

    def __init__(self, scripts: list[Any]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._scripts = list(scripts)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any):
        self.calls.append(kwargs)
        script = self._scripts.pop(0)

        def _gen():
            if isinstance(script, float):
                time.sleep(script)
                return
            for item in script:
                if isinstance(item, Exception):
                    raise item
                if isinstance(item, float):
                    time.sleep(item)
                    continue
                yield item

        return _gen()

    def prompt(self, call_index: int) -> str:
        return self.calls[call_index]["messages"][0]["content"]


def test_parse_documents_splits_on_markers():
    text = _doc_block("a.md", "alpha") + _doc_block("b.md", "beta")
    assert parse_documents(text) == {"a.md": "alpha", "b.md": "beta"}


def test_build_prompt_lists_every_doc_and_marker_rule():
    prompt = build_prompt("brief", [REQ, DES])
    assert REQ.path in prompt and DES.path in prompt
    assert "=== FILE: <path> ===" in prompt


def test_whole_spec_happy_path_one_attempt():
    client = FakeClient(
        [[_text_event(_doc_block(REQ.path)), _text_event(_doc_block(DES.path)), _stop_event()]]
    )
    result = SpecDraftRunner(client, budgets=FAST).draft("brief", [REQ, DES])
    assert result.ok
    assert set(result.documents) == {REQ.path, DES.path}
    assert [a.strategy for a in result.attempts] == [WHOLE_SPEC]
    assert result.attempts[0].failure is None
    assert result.attempts[0].stop_reason == "end_turn"


def test_first_event_timeout_switches_to_per_document_once():
    client = FakeClient(
        [
            1.0,  # whole-spec: silent past first_event_s
            [_text_event(_doc_block(REQ.path)), _stop_event()],
            [_text_event(_doc_block(DES.path)), _stop_event()],
        ]
    )
    result = SpecDraftRunner(client, budgets=FAST).draft("brief", [REQ, DES])
    assert result.ok
    strategies = [a.strategy for a in result.attempts]
    assert strategies == [WHOLE_SPEC, PER_DOCUMENT, PER_DOCUMENT]
    assert result.attempts[0].failure == "first_event_timeout"
    assert strategies.count(WHOLE_SPEC) == 1  # never retried
    assert len(client.calls) == 3


def test_missing_marker_re_requests_only_missing_doc():
    client = FakeClient(
        [
            [_text_event(_doc_block(REQ.path)), _stop_event()],  # DES missing
            [_text_event(_doc_block(DES.path)), _stop_event()],
        ]
    )
    result = SpecDraftRunner(client, budgets=FAST).draft("brief", [REQ, DES])
    assert result.ok
    assert [a.strategy for a in result.attempts] == [WHOLE_SPEC, PER_DOCUMENT]
    assert result.attempts[1].doc_paths == [DES.path]
    assert DES.path in client.prompt(1)
    assert REQ.path not in client.prompt(1)


def test_oversize_document_is_a_recorded_failure():
    big = "x" * (FAST.max_chars_per_doc + 1)
    client = FakeClient(
        [
            [_text_event(_doc_block(REQ.path, big)), _stop_event()],
            [_text_event(_doc_block(REQ.path, big)), _stop_event()],
        ]
    )
    result = SpecDraftRunner(client, budgets=FAST).draft("brief", [REQ])
    assert not result.ok
    assert "size limit" in result.failures[REQ.path]


def test_provider_error_is_captured_and_secret_redacted():
    exc = RuntimeError("auth failed for sk-ant-api03-SECRETSECRET")
    client = FakeClient([[exc], [exc]])
    result = SpecDraftRunner(client, budgets=FAST).draft("brief", [REQ])
    assert not result.ok
    for attempt in result.attempts:
        assert "SECRETSECRET" not in (attempt.failure or "")
        assert "sk-ant-***" in (attempt.failure or "")
    assert "RuntimeError" in result.failures[REQ.path]


def test_refusal_stop_reason_is_a_failure():
    script = [_text_event("nope"), _stop_event("refusal")]
    client = FakeClient([list(script), list(script)])
    result = SpecDraftRunner(client, budgets=FAST).draft("brief", [REQ])
    assert not result.ok
    assert result.attempts[0].failure == "refusal"


def test_total_timeout_trips_wall_clock_bound():
    budgets = Budgets(
        first_event_s=0.5,
        inter_event_s=0.5,
        total_single_s=0.05,
        total_multi_s=0.05,
        max_chars_per_doc=200,
    )
    slow = [_text_event("a"), 0.1, _text_event("b"), 0.1, _text_event("c"), _stop_event()]
    client = FakeClient([list(slow), list(slow)])
    result = SpecDraftRunner(client, budgets=budgets).draft("brief", [REQ])
    assert not result.ok
    assert result.attempts[0].failure == "total_timeout"


def test_progress_callback_ticks_first_event_and_done():
    stages: list[str] = []
    client = FakeClient([[_text_event(_doc_block(REQ.path)), _stop_event()]])
    runner = SpecDraftRunner(
        client, budgets=FAST, on_progress=lambda stage, elapsed: stages.append(stage)
    )
    assert runner.draft("brief", [REQ]).ok
    assert any("first event" in s for s in stages)
    assert any("done (ok)" in s for s in stages)


def test_budgets_total_for_selects_by_doc_count():
    budgets = Budgets()
    assert budgets.total_for(1) == budgets.total_single_s
    assert budgets.total_for(5) == budgets.total_multi_s


@pytest.mark.parametrize("doc_count,expected_key", [(1, 32_000), (2, 64_000)])
def test_max_tokens_scales_with_packet_size(doc_count, expected_key):
    docs = [REQ, DES][:doc_count]
    events = [_text_event(_doc_block(d.path)) for d in docs] + [_stop_event()]
    client = FakeClient([events])
    SpecDraftRunner(client, budgets=FAST).draft("brief", docs)
    assert client.calls[0]["max_tokens"] == expected_key
