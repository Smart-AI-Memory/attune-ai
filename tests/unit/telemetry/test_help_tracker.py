"""Tests for HelpTracker."""

from __future__ import annotations

import json

import pytest

from attune.telemetry.help_tracker import HelpTracker


@pytest.fixture(autouse=True)
def _reenable_telemetry(monkeypatch):
    """Re-enable help telemetry in this module — the global conftest
    disables it by default to protect the user's real JSONL."""
    monkeypatch.delenv("ATTUNE_HELP_TELEMETRY", raising=False)


def _read_events(path):
    # encoding="utf-8" is load-bearing on Windows — the tracker writes
    # JSONL with explicit utf-8, and Windows' default cp1252 decode on
    # Path.read_text() would mangle non-ASCII topics (ñoño → �o�o,
    # 日本語 → mojibake, etc.) on the round-trip.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_log_writes_one_event_per_call(tmp_path):
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log(
        source="help_lookup",
        mode="progressive",
        topic="security-audit",
        success=True,
        found=True,
        duration_ms=12.4,
    )

    events = _read_events(tracker.path)
    assert len(events) == 1
    assert events[0]["source"] == "help_lookup"
    assert events[0]["topic"] == "security-audit"
    assert events[0]["success"] is True
    assert events[0]["found"] is True
    assert events[0]["duration_ms"] == 12.4
    assert events[0]["v"] == "1.0"


def test_log_appends(tmp_path):
    tracker = HelpTracker(log_dir=tmp_path)
    for topic in ["a", "b", "c"]:
        tracker.log(
            source="help_lookup",
            mode="progressive",
            topic=topic,
            success=True,
            found=True,
        )

    events = _read_events(tracker.path)
    assert [e["topic"] for e in events] == ["a", "b", "c"]


def test_log_honors_opt_out(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HELP_TELEMETRY", "0")
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log(
        source="help_lookup",
        mode="progressive",
        topic="security-audit",
        success=True,
        found=True,
    )

    assert not tracker.path.exists()


def test_log_never_raises_on_write_error(tmp_path, monkeypatch):
    tracker = HelpTracker(log_dir=tmp_path / "nested")
    # Replace the dir with a file so mkdir would fail
    (tmp_path / "nested").write_text("block")

    # Should not raise
    tracker.log(
        source="help_lookup",
        mode="progressive",
        topic="x",
        success=True,
        found=True,
    )


def test_metadata_round_trips(tmp_path):
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log(
        source="help_lookup",
        mode="progressive",
        topic="security-audit",
        success=True,
        found=True,
        metadata={"depth_level": 2, "tags": ["security", "scanning"]},
    )

    event = _read_events(tracker.path)[0]
    assert event["metadata"]["depth_level"] == 2
    assert event["metadata"]["tags"] == ["security", "scanning"]


@pytest.mark.parametrize("topic", ["ñoño", "日本語", "🎉"])
def test_unicode_topics_round_trip(tmp_path, topic):
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log(
        source="help_lookup",
        mode="progressive",
        topic=topic,
        success=True,
        found=True,
    )

    assert _read_events(tracker.path)[0]["topic"] == topic


# ------------------------------------------------------------------
# log_unmatched — FAQ-Generator channel 1
# ------------------------------------------------------------------


def test_log_unmatched_writes_channel1_event(tmp_path):
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log_unmatched(query="how do I rotate api keys", mode="progressive")

    events = _read_events(tracker.unmatched_path)
    assert len(events) == 1
    assert events[0]["query"] == "how do I rotate api keys"
    assert events[0]["mode"] == "progressive"
    assert events[0]["source"] == "help_lookup"
    assert events[0]["v"] == "1.0"
    assert "ts" in events[0]


def test_log_unmatched_goes_to_separate_file(tmp_path):
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log_unmatched(query="x", mode="progressive")

    assert tracker.unmatched_path.name == "help_unmatched.jsonl"
    assert not tracker.path.exists()


def test_log_unmatched_appends(tmp_path):
    tracker = HelpTracker(log_dir=tmp_path)
    for query in ["a", "b", "c"]:
        tracker.log_unmatched(query=query, mode="progressive")

    events = _read_events(tracker.unmatched_path)
    assert [e["query"] for e in events] == ["a", "b", "c"]


def test_log_unmatched_honors_opt_out(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HELP_TELEMETRY", "0")
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log_unmatched(query="x", mode="progressive")

    assert not tracker.unmatched_path.exists()


def test_log_unmatched_never_raises_on_write_error(tmp_path):
    tracker = HelpTracker(log_dir=tmp_path / "nested")
    # Replace the dir with a file so mkdir would fail
    (tmp_path / "nested").write_text("block")

    # Should not raise
    tracker.log_unmatched(query="x", mode="progressive")


@pytest.mark.parametrize("query", ["ñoño", "日本語", "🎉"])
def test_log_unmatched_unicode_round_trips(tmp_path, query):
    tracker = HelpTracker(log_dir=tmp_path)
    tracker.log_unmatched(query=query, mode="progressive")

    assert _read_events(tracker.unmatched_path)[0]["query"] == query
