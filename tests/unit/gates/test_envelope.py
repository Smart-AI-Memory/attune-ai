"""Tests for the spend-gate envelope (T1).

Clock is pinned for all window logic (edge-of-bucket timing
lesson) and the envelope file lives under ``tmp_path`` (never a
literal ``~``/``/tmp`` — Windows path lessons).
"""

from __future__ import annotations

import json

import pytest

from attune.gates.envelope import (
    DEFAULT_TTL_SECONDS,
    Envelope,
    load_envelope,
    load_or_new,
    save_envelope,
)

# Pinned clock — a fixed epoch so window math is deterministic.
NOW = 1_700_000_000.0


def test_default_ttl_aligns_to_anthropic_window() -> None:
    assert DEFAULT_TTL_SECONDS == 5 * 60 * 60


def test_new_envelope_is_unauthorized_and_empty() -> None:
    env = Envelope.new(NOW, cap_usd=5.0, meter="api")
    assert env.window_start == NOW
    assert env.authorized is False
    assert env.spent_usd == 0.0
    assert env.cap_usd == 5.0
    assert env.meter == "api"
    assert env.ttl_seconds == DEFAULT_TTL_SECONDS


def test_round_trip_through_file(tmp_path) -> None:
    path = tmp_path / "spend_gate" / "envelope.json"
    env = Envelope(
        window_start=NOW,
        authorized=True,
        cap_usd=10.0,
        spent_usd=2.5,
        meter="api",
    )
    save_envelope(env, path)
    assert path.exists()
    loaded = load_envelope(path)
    assert loaded == env


def test_saved_file_is_valid_json_with_trailing_newline(tmp_path) -> None:
    path = tmp_path / "envelope.json"
    save_envelope(Envelope.new(NOW, cap_usd=1.0), path)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    json.loads(text)  # parses


def test_load_missing_returns_none(tmp_path) -> None:
    assert load_envelope(tmp_path / "nope.json") is None


def test_load_corrupt_returns_none(tmp_path) -> None:
    path = tmp_path / "envelope.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert load_envelope(path) is None


def test_load_missing_required_field_returns_none(tmp_path) -> None:
    path = tmp_path / "envelope.json"
    path.write_text(json.dumps({"ttl_seconds": 10}), encoding="utf-8")
    # No window_start -> KeyError -> fail-safe None.
    assert load_envelope(path) is None


def test_is_expired_at_and_past_window() -> None:
    env = Envelope.new(NOW, ttl_seconds=100.0)
    assert env.is_expired(NOW + 99.0) is False
    assert env.is_expired(NOW + 100.0) is True  # boundary is expired
    assert env.is_expired(NOW + 101.0) is True


def test_is_expired_within_window() -> None:
    env = Envelope.new(NOW, ttl_seconds=DEFAULT_TTL_SECONDS)
    assert env.is_expired(NOW + 60.0) is False


def test_is_exhausted_post_hoc() -> None:
    # Below cap → not exhausted (later runs proceed silently).
    assert Envelope(window_start=NOW, cap_usd=5.0, spent_usd=4.0).is_exhausted is False
    # At cap → exhausted (>= , not just >).
    assert Envelope(window_start=NOW, cap_usd=5.0, spent_usd=5.0).is_exhausted is True
    # Over cap → exhausted.
    assert Envelope(window_start=NOW, cap_usd=5.0, spent_usd=6.0).is_exhausted is True


def test_partial_spend_below_cap_is_not_exhausted() -> None:
    # The dogfood regression: one run's spend on a cap-sized-as-band
    # window must NOT re-gate the next run.
    env = Envelope(window_start=NOW, cap_usd=2.0, spent_usd=0.16, authorized=True)
    assert env.is_exhausted is False


def test_disabled_envelope_never_exhausted() -> None:
    env = Envelope(window_start=NOW, cap_usd=0.0, spent_usd=100.0)
    assert env.disabled is True
    assert env.is_exhausted is False


def test_disabled_latch_on_nonpositive_cap() -> None:
    assert Envelope(window_start=NOW, cap_usd=0.0).disabled is True
    assert Envelope(window_start=NOW, cap_usd=-1.0).disabled is True
    assert Envelope(window_start=NOW, cap_usd=0.01).disabled is False


def test_record_accumulates() -> None:
    env = Envelope.new(NOW, cap_usd=10.0)
    env.record(1.5)
    env.record(2.0)
    assert env.spent_usd == 3.5


def test_record_rejects_negative() -> None:
    env = Envelope.new(NOW, cap_usd=10.0)
    with pytest.raises(ValueError, match="non-negative"):
        env.record(-1.0)


def test_load_or_new_fresh_when_missing(tmp_path) -> None:
    env = load_or_new(NOW, tmp_path / "nope.json", cap_usd=5.0)
    assert env.window_start == NOW
    assert env.authorized is False
    assert env.cap_usd == 5.0


def test_load_or_new_fresh_when_expired(tmp_path) -> None:
    path = tmp_path / "envelope.json"
    save_envelope(
        Envelope(window_start=NOW, ttl_seconds=100.0, authorized=True),
        path,
    )
    env = load_or_new(NOW + 200.0, path, cap_usd=5.0)
    assert env.window_start == NOW + 200.0  # fresh window
    assert env.authorized is False


def test_load_or_new_returns_live_envelope(tmp_path) -> None:
    path = tmp_path / "envelope.json"
    live = Envelope(
        window_start=NOW,
        ttl_seconds=DEFAULT_TTL_SECONDS,
        authorized=True,
        cap_usd=5.0,
        spent_usd=1.0,
    )
    save_envelope(live, path)
    env = load_or_new(NOW + 60.0, path)
    assert env.authorized is True
    assert env.spent_usd == 1.0
    assert env.window_start == NOW  # unchanged — same window
