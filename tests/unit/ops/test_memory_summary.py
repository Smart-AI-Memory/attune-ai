"""Tests for the short-term memory telemetry analyzer.

Covers ``read_memory_summary`` (cost aggregation) and
``estimate_intervention_signal`` (labeled benefit estimate) in
``attune.ops.data``. Two regression guards are load-bearing:

- The ``ts`` field bug: memory events use ``ts`` (not ``timestamp``);
  reading the wrong key silently empties the by_day bucket, the exact
  class of bug documented for the usage reader.
- The savings-claim guard: the intervention estimate must ship its
  honesty caption and must NOT present a numeric savings percentage,
  per ``memory_cost_claim_grounding``.
"""

from __future__ import annotations

import json
import re

from attune.ops.data import (
    INTERVENTION_SIGNAL_CAPTION,
    estimate_intervention_signal,
    read_memory_summary,
)


def _write_jsonl(path, events):
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _sample_events():
    return [
        {
            "v": "1.0",
            "ts": "2026-07-08T01:00:00.000Z",
            "event": "session_recall",
            "session_id": "s1",
            "entries": 5,
            "injected_chars": 400,
            "est_tokens": 100,
        },
        {
            "v": "1.0",
            "ts": "2026-07-08T02:00:00.000Z",
            "event": "jit_recall",
            "session_id": "s1",
            "tool": "Bash",
            "rules": ["zsh-eqword-expansion"],
            "injected_chars": 200,
            "est_tokens": 50,
        },
        {
            "v": "1.0",
            "ts": "2026-07-09T03:00:00.000Z",
            "event": "jit_recall",
            "session_id": "s2",
            "tool": "Edit",
            "rules": ["zsh-eqword-expansion", "formatter-strips-import"],
            "injected_chars": 320,
            "est_tokens": 80,
        },
    ]


# ---------------------------------------------------------------------------
# read_memory_summary
# ---------------------------------------------------------------------------


def test_aggregates_totals(tmp_path):
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(path, _sample_events())

    summary = read_memory_summary(path)

    assert summary["total_events"] == 3
    assert summary["total_est_tokens"] == 230
    assert summary["distinct_sessions"] == 2
    assert summary["by_event"]["jit_recall"] == {"n": 2, "est_tokens": 130}
    assert summary["by_event"]["session_recall"] == {"n": 1, "est_tokens": 100}
    # 230 tokens / 2 sessions
    assert summary["per_session_avg_tokens"] == 115.0


def test_reads_ts_field_into_by_day(tmp_path):
    """Regression: by_day must populate from the ``ts`` key.

    An event carrying only ``ts`` (the writer's canonical field) must
    land in by_day. Reading ``timestamp`` instead would leave by_day
    empty — the silent zero-KPI bug the usage reader already fixed.
    """
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(path, _sample_events())

    summary = read_memory_summary(path)

    assert set(summary["by_day"]) == {"2026-07-08", "2026-07-09"}
    assert summary["by_day"]["2026-07-08"] == {"n": 2, "est_tokens": 150}


def test_skips_malformed_lines(tmp_path):
    path = tmp_path / "memory_events.jsonl"
    path.write_text(
        json.dumps(_sample_events()[0]) + "\nNOT JSON\n" + json.dumps(_sample_events()[1]) + "\n",
        encoding="utf-8",
    )

    summary = read_memory_summary(path)

    assert summary["total_events"] == 2


def test_missing_file_is_zeroed(tmp_path):
    summary = read_memory_summary(tmp_path / "does-not-exist.jsonl")

    assert summary["total_events"] == 0
    assert summary["total_est_tokens"] == 0
    assert summary["by_event"] == {}
    assert summary["per_session_avg_tokens"] == 0.0


# ---------------------------------------------------------------------------
# estimate_intervention_signal
# ---------------------------------------------------------------------------


def test_intervention_signal_counts_rule_surfacings(tmp_path):
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(path, _sample_events())

    sig = estimate_intervention_signal(path)

    # Two jit_recall events: one rule + two rules = 3 surfacings.
    assert sig["rule_surfacings"] == 3
    assert sig["distinct_rules"] == 2
    # zsh-eqword-expansion fired twice → ranks first.
    assert sig["top_rules"][0] == ["zsh-eqword-expansion", 2]


def test_intervention_signal_ships_honesty_caption(tmp_path):
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(path, _sample_events())

    sig = estimate_intervention_signal(path)

    assert sig["caption"] == INTERVENTION_SIGNAL_CAPTION
    caption = sig["caption"].lower()
    assert "estimate" in caption
    assert "upper bound" in caption


def test_intervention_signal_presents_no_savings_percentage(tmp_path):
    """Guard: the estimate must never render a numeric savings figure.

    The caption may say the words "savings"/"percentage" while NEGATING
    such a claim; what is forbidden is an actual number-as-savings. This
    asserts no ``NN% saved`` / ``saves NN`` construction is present.
    """
    path = tmp_path / "memory_events.jsonl"
    _write_jsonl(path, _sample_events())

    sig = estimate_intervention_signal(path)
    blob = json.dumps(sig).lower()

    # No "<number>%" and no "saves <number>" / "saved <number>".
    assert not re.search(r"\d+\s*%", blob)
    assert not re.search(r"sav(e|es|ed|ings)\s+\d", blob)


def test_intervention_signal_missing_file_is_zeroed(tmp_path):
    sig = estimate_intervention_signal(tmp_path / "nope.jsonl")

    assert sig["rule_surfacings"] == 0
    assert sig["distinct_rules"] == 0
    assert sig["top_rules"] == []
    assert sig["caption"] == INTERVENTION_SIGNAL_CAPTION
