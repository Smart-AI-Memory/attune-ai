"""Tests for the redact→cache-or-Haiku orchestrator.

Covers the three branches of :func:`summarize_for_session` — cache
hit, cache miss with successful Haiku call, cache miss with LLM
error — plus the budget-tracker warn-once-on-breach semantics.
"""

from __future__ import annotations

import json
import logging

import pytest

from attune.ops import (
    session_summary,
    session_summary_cache,
    session_summary_llm,
)

# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------


def test_budget_tracker_accumulates_spend():
    b = session_summary.BudgetTracker(cap_usd=0.10)
    b.charge(0.02)
    b.charge(0.03)
    assert b.spend_usd == pytest.approx(0.05)


def test_budget_tracker_warns_once_on_breach(caplog):
    b = session_summary.BudgetTracker(cap_usd=0.05)
    with caplog.at_level(logging.WARNING, logger="attune.ops.session_summary"):
        b.charge(0.04)  # under cap, no warn
        b.charge(0.03)  # breaches cap, warn
        b.charge(0.01)  # still over, no second warn

    warn_messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    over_cap_warns = [m for m in warn_messages if "budget cap exceeded" in m]
    assert len(over_cap_warns) == 1


# ---------------------------------------------------------------------------
# summarize_for_session — three branches
# ---------------------------------------------------------------------------


@pytest.fixture
def attune_home(tmp_path):
    return tmp_path / "attune-home"


@pytest.fixture
def jsonl_path(tmp_path):
    """A small JSONL file with one prompt event."""
    path = tmp_path / "abc12345.jsonl"
    payload = {
        "type": "queue-operation",
        "operation": "enqueue",
        "timestamp": "2026-05-15T10:00:00Z",
        "content": "Help me fix the failing test on Windows.",
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _fake_summarize(text, *, api_key=None):
    """Stand-in for session_summary_llm.summarize. Captures input."""
    return session_summary_llm.SummaryResult(
        text=f"SUMMARY OF: {text[:30]}",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.001,
    )


def test_cache_miss_calls_llm_and_caches(attune_home, jsonl_path):
    """First call: cache miss → LLM call → write cache."""
    budget = session_summary.BudgetTracker()
    result = session_summary.summarize_for_session(
        jsonl_path,
        "raw text to summarize",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=_fake_summarize,
    )
    assert result is not None
    assert result.source == "haiku"
    assert result.text.startswith("SUMMARY OF:")
    assert result.cost_usd == pytest.approx(0.001)
    assert budget.spend_usd == pytest.approx(0.001)

    # Cache file written.
    cache_path = session_summary_cache.cache_path_for(attune_home, jsonl_path.stem)
    assert cache_path.is_file()


def test_cache_hit_skips_llm_and_does_not_charge_budget(attune_home, jsonl_path):
    """Second call on the same file: cache hit → no LLM, no charge."""
    budget = session_summary.BudgetTracker()
    # Prime the cache.
    session_summary.summarize_for_session(
        jsonl_path,
        "raw text",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=_fake_summarize,
    )
    assert budget.spend_usd == pytest.approx(0.001)

    # Second call should hit the cache.
    def must_not_call(*a, **k):
        raise AssertionError("LLM was called on cache hit")

    result = session_summary.summarize_for_session(
        jsonl_path,
        "raw text",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=must_not_call,
    )
    assert result is not None
    assert result.source == "cached"
    # Budget unchanged from the first call.
    assert budget.spend_usd == pytest.approx(0.001)


def test_cache_miss_on_content_change(attune_home, jsonl_path):
    """Same session id, different content → cache miss → fresh LLM call."""
    budget = session_summary.BudgetTracker()
    session_summary.summarize_for_session(
        jsonl_path,
        "v1",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=_fake_summarize,
    )
    # Modify file contents so the tail hash changes.
    jsonl_path.write_text(
        json.dumps({"timestamp": "2026-05-15T11:00:00Z", "content": "different"}) + "\n",
        encoding="utf-8",
    )

    second = session_summary.summarize_for_session(
        jsonl_path,
        "v2",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=_fake_summarize,
    )
    assert second is not None
    assert second.source == "haiku"  # fresh write, not cached
    # Spend doubled — second LLM call charged.
    assert budget.spend_usd == pytest.approx(0.002)


def test_llm_error_falls_back_to_none(attune_home, jsonl_path):
    """A runtime LLM error returns None (caller uses heuristic)."""
    budget = session_summary.BudgetTracker()

    def failing_summarize(text, *, api_key=None):
        raise RuntimeError("network blip")

    result = session_summary.summarize_for_session(
        jsonl_path,
        "text",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=failing_summarize,
    )
    assert result is None
    # Budget unchanged — no successful call.
    assert budget.spend_usd == 0.0
    # No cache file written.
    cache_path = session_summary_cache.cache_path_for(attune_home, jsonl_path.stem)
    assert not cache_path.exists()


def test_missing_api_key_propagates(attune_home, jsonl_path):
    """``MissingApiKeyError`` is re-raised, not swallowed."""
    budget = session_summary.BudgetTracker()

    def failing_summarize(text, *, api_key=None):
        raise session_summary_llm.MissingApiKeyError("no key")

    with pytest.raises(session_summary_llm.MissingApiKeyError):
        session_summary.summarize_for_session(
            jsonl_path,
            "text",
            attune_home=attune_home,
            budget=budget,
            summarize_fn=failing_summarize,
        )


def test_cache_key_io_failure_returns_none(attune_home, tmp_path):
    """Missing JSONL → ``compute_cache_key`` fails → caller falls back."""
    budget = session_summary.BudgetTracker()
    missing = tmp_path / "vanished.jsonl"
    result = session_summary.summarize_for_session(
        missing,
        "text",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=_fake_summarize,
    )
    assert result is None


def test_redaction_runs_before_llm(attune_home, jsonl_path):
    """Verifies redaction is applied to the text sent to the LLM,
    not to the original input the caller passed."""
    budget = session_summary.BudgetTracker()
    captured_inputs: list[str] = []

    def capturing_summarize(text, *, api_key=None):
        captured_inputs.append(text)
        return session_summary_llm.SummaryResult(
            text="ok", tokens_in=1, tokens_out=1, cost_usd=0.0001
        )

    secret_text = "the key is sk-ant-abcdef1234567890abcdef1234567890"
    result = session_summary.summarize_for_session(
        jsonl_path,
        secret_text,
        attune_home=attune_home,
        budget=budget,
        summarize_fn=capturing_summarize,
    )
    assert result is not None
    assert captured_inputs, "summarize was not called"
    sent_to_llm = captured_inputs[0]
    assert "sk-ant-" not in sent_to_llm, f"raw key leaked to LLM: {sent_to_llm!r}"
    assert "<redacted>" in sent_to_llm


def test_redaction_applied_to_cache(attune_home, jsonl_path):
    """Cached summary should be the post-redaction one (defense in depth)."""
    budget = session_summary.BudgetTracker()

    def echo_summarize(text, *, api_key=None):
        return session_summary_llm.SummaryResult(
            text=f"summary: {text[:60]}",
            tokens_in=10,
            tokens_out=10,
            cost_usd=0.0001,
        )

    session_summary.summarize_for_session(
        jsonl_path,
        "leaked sk-ant-abcdef1234567890abcdef1234567890",
        attune_home=attune_home,
        budget=budget,
        summarize_fn=echo_summarize,
    )
    cache_path = session_summary_cache.cache_path_for(attune_home, jsonl_path.stem)
    on_disk = cache_path.read_text(encoding="utf-8")
    assert "sk-ant-" not in on_disk


# ---------------------------------------------------------------------------
# extract_summarizable_text
# ---------------------------------------------------------------------------


def test_extract_summarizable_text_concatenates_content(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"timestamp": "t1", "content": "first prompt"}),
                json.dumps({"timestamp": "t2", "content": "second prompt"}),
                json.dumps({"timestamp": "t3"}),  # no content, skipped
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    text = session_summary.extract_summarizable_text(path)
    assert "first prompt" in text
    assert "second prompt" in text


def test_extract_summarizable_text_returns_empty_on_missing_file(tmp_path):
    assert session_summary.extract_summarizable_text(tmp_path / "missing.jsonl") == ""


def test_extract_summarizable_text_respects_cap(tmp_path):
    path = tmp_path / "big.jsonl"
    path.write_text(
        json.dumps({"content": "x" * 10_000}) + "\n",
        encoding="utf-8",
    )
    text = session_summary.extract_summarizable_text(path, max_chars=100)
    assert len(text) <= 100
