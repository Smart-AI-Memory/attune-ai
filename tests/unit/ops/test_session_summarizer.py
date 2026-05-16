"""Tests for the Haiku summarizer wire-up (S3b of ops-sessions-page).

All Anthropic SDK calls are mocked — no real API hits in CI. The
tests cover:

- Env gates: LLM disabled, no API key, explicit ``ATTUNE_OPS_SESSIONS_LLM=0``
- Cache lifecycle: miss -> Haiku -> save -> hit returns ``source=cached``
- Redaction is called BEFORE the LLM (decisions.md Decision 3)
- Budget enforcement: breach skips fresh calls but allows cache reads
- Failure paths: missing SDK, SDK exception, empty response → ``None``
- Cost computation matches the registry rates
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.ops import session_summarizer, session_summary_cache

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, events: list[dict]) -> Path:
    """Write a JSONL file with the given events; create parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )
    return path


def _fake_haiku_response(text: str, *, tokens_in: int = 100, tokens_out: int = 50):
    """Build a mock ``anthropic`` response object with the expected shape."""
    content_block = types.SimpleNamespace(text=text, type="text")
    usage = types.SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out)
    return types.SimpleNamespace(content=[content_block], usage=usage)


def _install_fake_anthropic(monkeypatch, *, response=None, exception=None):
    """Install a fake ``anthropic`` module on sys.modules.

    The fake exposes ``Anthropic(api_key=...)`` returning a client
    whose ``messages.create(...)`` returns ``response`` or raises
    ``exception``. Captures the call args on the messages mock so
    tests can assert that the redacted text was the one sent.
    """
    messages_create = MagicMock()
    if exception is not None:
        messages_create.side_effect = exception
    else:
        messages_create.return_value = response or _fake_haiku_response("(default)")

    client = types.SimpleNamespace(messages=types.SimpleNamespace(create=messages_create))

    class _FakeAnthropic:
        def __init__(self, *, api_key):
            assert api_key  # sanity — the summarizer must pass the key

        def __new__(cls, *, api_key):
            return client

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return messages_create


# ---------------------------------------------------------------------------
# Env gates
# ---------------------------------------------------------------------------


def test_llm_enabled_false_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ATTUNE_OPS_SESSIONS_LLM", raising=False)
    assert session_summarizer.llm_enabled() is False


def test_llm_enabled_true_with_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    monkeypatch.delenv("ATTUNE_OPS_SESSIONS_LLM", raising=False)
    assert session_summarizer.llm_enabled() is True


def test_llm_enabled_false_when_explicitly_disabled(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    monkeypatch.setenv("ATTUNE_OPS_SESSIONS_LLM", "0")
    assert session_summarizer.llm_enabled() is False


def test_summarize_returns_none_when_llm_disabled(tmp_path, monkeypatch):
    """No LLM available + no cache → None (caller falls back to heuristic)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    jsonl = _write_jsonl(
        tmp_path / "session.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Test prompt content."}],
    )
    result = session_summarizer.summarize_session(jsonl, attune_home=tmp_path / "attune-home")
    assert result is None


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def test_new_budget_uses_default():
    monkeypatch_clean = pytest.MonkeyPatch()
    try:
        monkeypatch_clean.delenv("ATTUNE_OPS_SESSIONS_BUDGET_USD", raising=False)
        b = session_summarizer.new_budget()
        assert b.cap_usd == session_summarizer.DEFAULT_BUDGET_USD
        assert b.spent_usd == 0.0
        assert b.breached is False
    finally:
        monkeypatch_clean.undo()


def test_new_budget_reads_env(monkeypatch):
    monkeypatch.setenv("ATTUNE_OPS_SESSIONS_BUDGET_USD", "0.25")
    b = session_summarizer.new_budget()
    assert b.cap_usd == 0.25


def test_new_budget_falls_back_on_invalid_env(monkeypatch):
    monkeypatch.setenv("ATTUNE_OPS_SESSIONS_BUDGET_USD", "not-a-float")
    b = session_summarizer.new_budget()
    assert b.cap_usd == session_summarizer.DEFAULT_BUDGET_USD


def test_new_budget_arg_wins_over_env(monkeypatch):
    monkeypatch.setenv("ATTUNE_OPS_SESSIONS_BUDGET_USD", "0.25")
    b = session_summarizer.new_budget(cap_usd=0.10)
    assert b.cap_usd == 0.10


def test_budget_latches_breached_on_record():
    b = session_summarizer.Budget(cap_usd=0.05)
    b.record(0.03)
    assert b.breached is False
    b.record(0.03)  # cumulative 0.06 > 0.05
    assert b.breached is True
    # Should stay latched even if a subsequent record is small
    b.record(0.001)
    assert b.breached is True


def test_budget_should_skip_returns_breached_state():
    # cap=0 is an effective off-switch: latched as breached at
    # construction so the FIRST call also skips.
    b = session_summarizer.Budget(cap_usd=0.0)
    assert b.should_skip() is True

    # Normal cap: starts un-breached, becomes breached after record.
    b2 = session_summarizer.Budget(cap_usd=0.05)
    assert b2.should_skip() is False
    b2.record(0.10)
    assert b2.should_skip() is True


# ---------------------------------------------------------------------------
# Happy path: Haiku call + cache write + redaction
# ---------------------------------------------------------------------------


def test_summarize_runs_haiku_and_writes_cache(tmp_path, monkeypatch):
    """Cache miss → redact → call Haiku → cache write → return haiku result."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    create_mock = _install_fake_anthropic(
        monkeypatch,
        response=_fake_haiku_response(
            "Worked on auth. Resume: finish JWT.", tokens_in=500, tokens_out=20
        ),
    )

    jsonl = _write_jsonl(
        tmp_path / "abc12345-c539-4057-ba26-24ce3dffec27.jsonl",
        [
            {"timestamp": "2026-05-14T10:00:00Z", "content": "Help me with auth"},
            {"timestamp": "2026-05-14T10:05:00Z", "content": "Try JWT"},
        ],
    )
    attune_home = tmp_path / "attune-home"

    result = session_summarizer.summarize_session(jsonl, attune_home=attune_home)

    assert result is not None
    assert result.source == "haiku"
    assert result.text == "Worked on auth. Resume: finish JWT."
    assert result.tokens_in == 500
    assert result.tokens_out == 20
    # Cost = (500 * 1.00 + 20 * 5.00) / 1_000_000 = 0.0006
    assert result.cost_usd == pytest.approx(0.0006, abs=1e-6)

    # Cache file should exist with the haiku source
    cache_path = session_summary_cache.cache_path_for(
        attune_home, "abc12345-c539-4057-ba26-24ce3dffec27"
    )
    assert cache_path.is_file()
    cached_raw = json.loads(cache_path.read_text())
    assert cached_raw["source"] == "haiku"
    assert cached_raw["summary"] == "Worked on auth. Resume: finish JWT."

    # The Anthropic call was made exactly once
    assert create_mock.call_count == 1


def test_summarize_returns_cached_on_second_call(tmp_path, monkeypatch):
    """Second call with the same file (mtime + tail unchanged) → cache hit."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    create_mock = _install_fake_anthropic(
        monkeypatch,
        response=_fake_haiku_response("Summary.", tokens_in=100, tokens_out=10),
    )

    jsonl = _write_jsonl(
        tmp_path / "session-001.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Hello"}],
    )
    attune_home = tmp_path / "attune-home"

    first = session_summarizer.summarize_session(jsonl, attune_home=attune_home)
    assert first is not None and first.source == "haiku"

    second = session_summarizer.summarize_session(jsonl, attune_home=attune_home)
    assert second is not None
    assert second.source == "cached"
    assert second.text == first.text
    # The LLM was called exactly once total — second was a cache hit.
    assert create_mock.call_count == 1


def test_summarize_redacts_before_sending(tmp_path, monkeypatch):
    """The text sent to Haiku must have secrets redacted (Decision 3)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    create_mock = _install_fake_anthropic(
        monkeypatch,
        response=_fake_haiku_response("Summary.", tokens_in=10, tokens_out=5),
    )

    secret_token = "sk-ant-" + "A" * 40  # Anthropic key shape
    jsonl = _write_jsonl(
        tmp_path / "session-002.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": f"Here is my key: {secret_token}"}],
    )

    session_summarizer.summarize_session(jsonl, attune_home=tmp_path / "attune-home")

    # Inspect what got sent
    assert create_mock.call_count == 1
    call_kwargs = create_mock.call_args.kwargs
    sent_text = call_kwargs["messages"][0]["content"]
    assert secret_token not in sent_text, "secret leaked into LLM call!"
    assert "<redacted>" in sent_text


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------


def test_summarize_skips_fresh_call_when_budget_breached(tmp_path, monkeypatch):
    """Cache miss + budget breached → None (no LLM call)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    create_mock = _install_fake_anthropic(
        monkeypatch,
        response=_fake_haiku_response("Summary."),
    )

    jsonl = _write_jsonl(
        tmp_path / "session-003.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Hello"}],
    )

    budget = session_summarizer.Budget(cap_usd=0.0)
    budget.record(0.001)  # immediate breach
    assert budget.breached

    result = session_summarizer.summarize_session(
        jsonl, attune_home=tmp_path / "attune-home", budget=budget
    )
    assert result is None
    # The LLM was NOT called.
    assert create_mock.call_count == 0


def test_summarize_returns_cached_even_when_budget_breached(tmp_path, monkeypatch):
    """A cache hit bypasses the budget — free reads are always allowed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    _install_fake_anthropic(
        monkeypatch,
        response=_fake_haiku_response("Cached!", tokens_in=50, tokens_out=5),
    )

    jsonl = _write_jsonl(
        tmp_path / "session-004.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Hello"}],
    )
    attune_home = tmp_path / "attune-home"

    # Prime the cache with a fresh budget
    fresh_budget = session_summarizer.Budget(cap_usd=1.0)
    first = session_summarizer.summarize_session(
        jsonl, attune_home=attune_home, budget=fresh_budget
    )
    assert first is not None and first.source == "haiku"

    # Now blow the budget on a SECOND budget and re-summarize
    breached_budget = session_summarizer.Budget(cap_usd=0.0)
    breached_budget.record(0.01)
    assert breached_budget.breached

    second = session_summarizer.summarize_session(
        jsonl, attune_home=attune_home, budget=breached_budget
    )
    assert second is not None
    assert second.source == "cached"


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_summarize_returns_none_on_sdk_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    _install_fake_anthropic(monkeypatch, exception=RuntimeError("API rate limited"))

    jsonl = _write_jsonl(
        tmp_path / "session-005.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Hello"}],
    )
    result = session_summarizer.summarize_session(jsonl, attune_home=tmp_path / "attune-home")
    assert result is None


def test_summarize_returns_none_when_anthropic_module_missing(tmp_path, monkeypatch):
    """ModuleNotFoundError on ``import anthropic`` → None (no crash)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    # Sentinel: setting sys.modules entry to None makes import raise.
    monkeypatch.setitem(sys.modules, "anthropic", None)

    jsonl = _write_jsonl(
        tmp_path / "session-006.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Hello"}],
    )
    result = session_summarizer.summarize_session(jsonl, attune_home=tmp_path / "attune-home")
    assert result is None


def test_summarize_returns_none_on_empty_response(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    empty = types.SimpleNamespace(
        content=[], usage=types.SimpleNamespace(input_tokens=0, output_tokens=0)
    )
    _install_fake_anthropic(monkeypatch, response=empty)

    jsonl = _write_jsonl(
        tmp_path / "session-007.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Hello"}],
    )
    result = session_summarizer.summarize_session(jsonl, attune_home=tmp_path / "attune-home")
    assert result is None


def test_summarize_returns_none_when_no_content_in_jsonl(tmp_path, monkeypatch):
    """JSONL with no ``content`` fields → no text to summarize → None."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    create_mock = _install_fake_anthropic(
        monkeypatch, response=_fake_haiku_response("Should not see this")
    )

    jsonl = _write_jsonl(
        tmp_path / "session-008.jsonl",
        [{"timestamp": "2026-05-14T10:00:00Z", "type": "queue-operation"}],
    )
    result = session_summarizer.summarize_session(jsonl, attune_home=tmp_path / "attune-home")
    assert result is None
    # LLM should NOT have been called
    assert create_mock.call_count == 0


def test_summarize_returns_none_when_jsonl_path_unreadable(tmp_path, monkeypatch):
    """Missing JSONL → None (cache key computation fails)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    _install_fake_anthropic(monkeypatch, response=_fake_haiku_response("Hi"))
    result = session_summarizer.summarize_session(
        tmp_path / "does-not-exist.jsonl", attune_home=tmp_path / "attune-home"
    )
    assert result is None


# ---------------------------------------------------------------------------
# Cost computation
# ---------------------------------------------------------------------------


def test_compute_cost_matches_registry_rates():
    """1M input + 1M output at $1/$5 per million = $6.00 total."""
    cost = session_summarizer._compute_cost_usd(1_000_000, 1_000_000)
    assert cost == pytest.approx(6.00, abs=1e-9)


def test_compute_cost_zero_tokens():
    assert session_summarizer._compute_cost_usd(0, 0) == 0.0


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------


def test_extract_content_collects_user_prompts(tmp_path):
    jsonl = _write_jsonl(
        tmp_path / "session.jsonl",
        [
            {"content": "First"},
            {"timestamp": "skip me"},  # no content
            {"content": "Second"},
            {"content": "Third"},
        ],
    )
    text = session_summarizer._extract_content_for_summary(jsonl, char_budget=1000)
    assert "First" in text
    assert "Second" in text
    assert "Third" in text


def test_extract_content_respects_char_budget(tmp_path):
    jsonl = _write_jsonl(
        tmp_path / "session.jsonl",
        [{"content": "X" * 100} for _ in range(20)],
    )
    text = session_summarizer._extract_content_for_summary(jsonl, char_budget=300)
    # Should stop accumulating once budget is exhausted; allowing for the
    # 2-char separator inflation, length stays close to budget.
    assert len(text) <= 320


def test_extract_content_returns_empty_on_missing_file(tmp_path):
    assert (
        session_summarizer._extract_content_for_summary(
            tmp_path / "missing.jsonl", char_budget=1000
        )
        == ""
    )


# ---------------------------------------------------------------------------
# Cache module integration smoke test
# ---------------------------------------------------------------------------


@patch.object(session_summary_cache, "save", side_effect=OSError("disk full"))
def test_cache_write_failure_does_not_crash(mock_save, tmp_path, monkeypatch):
    """Cache save errors are best-effort — summarizer still returns the result."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    _install_fake_anthropic(
        monkeypatch,
        response=_fake_haiku_response("Summary.", tokens_in=10, tokens_out=5),
    )
    jsonl = _write_jsonl(
        tmp_path / "session.jsonl",
        [{"content": "Hello"}],
    )
    result = session_summarizer.summarize_session(jsonl, attune_home=tmp_path / "attune-home")
    assert result is not None
    assert result.source == "haiku"
    # Save was attempted (and failed)
    assert mock_save.call_count == 1
