"""Tests for the memory feedback (noise) signal reader.

``estimate_feedback_signal`` turns ``memory_feedback`` rejection events
into a noise rate against findings stashed. The caption guard keeps it
framed as a noise share, never a quality score or savings figure.
"""

from __future__ import annotations

import json

from attune.ops.data import FEEDBACK_SIGNAL_CAPTION, estimate_feedback_signal


def _write_jsonl(path, events):
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_rejection_rate_math(tmp_path):
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(
        path,
        [
            {"event": "session_stash", "written": 5},
            {"event": "session_stash", "written": 5},
            {"event": "memory_feedback", "source": "recall_drop", "count": 1},
            {"event": "memory_feedback", "source": "reconciler", "count": 1},
        ],
    )

    sig = estimate_feedback_signal(path)

    assert sig["rejected"] == 2
    assert sig["findings_written"] == 10
    assert sig["rejection_rate"] == 0.2
    assert sig["by_source"] == {"recall_drop": 1, "reconciler": 1}


def test_zero_written_is_not_a_division_error(tmp_path):
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(path, [{"event": "memory_feedback", "source": "recall_drop", "count": 3}])

    sig = estimate_feedback_signal(path)

    assert sig["rejected"] == 3
    assert sig["findings_written"] == 0
    assert sig["rejection_rate"] == 0.0


def test_caption_present_and_not_a_savings_claim(tmp_path):
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(path, [{"event": "session_stash", "written": 4}])

    sig = estimate_feedback_signal(path)

    assert sig["caption"] == FEEDBACK_SIGNAL_CAPTION
    caption = sig["caption"].lower()
    assert "noise" in caption
    assert "not a quality score or a savings figure" in caption


def test_missing_file_is_zeroed(tmp_path):
    sig = estimate_feedback_signal(tmp_path / "nope.jsonl")

    assert sig["rejected"] == 0
    assert sig["findings_written"] == 0
    assert sig["rejection_rate"] == 0.0
    assert sig["by_source"] == {}
    assert sig["caption"] == FEEDBACK_SIGNAL_CAPTION
