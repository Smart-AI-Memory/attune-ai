"""Tests for the discovery-sweep triage board renderer.

Spec: docs/specs/discovery-sweep-rich-surface/ (FR-1).
"""

from __future__ import annotations

import pytest

from attune.workflows.discovery_sweep.board import sweep_to_board_html

pytestmark = pytest.mark.unit


def _finding(**over):
    base = {
        "source": "security-audit",
        "severity": "high",
        "title": "Something risky",
        "description": "desc",
        "file": "src/x.py",
        "line": 12,
        "confidence": 0.9,
    }
    base.update(over)
    return base


def _result(queue=None, questions=None, rejected=None, meta=None):
    return {
        "queue": queue or [],
        "questions": questions or [],
        "rejected": rejected or [],
        "metadata": meta or {"spent_usd": 0.0, "budget_usd": 10.0, "sources": [], "duration_ms": 0},
    }


class TestStructure:
    def test_renders_three_columns_and_counts(self):
        html = sweep_to_board_html(
            _result(queue=[_finding()], questions=[], rejected=[]),
        )
        assert "Queue — act now" in html
        assert "Questions — needs a look" in html
        assert "Rejected — filtered" in html
        # the queue count badge shows 1
        assert '<span class="ds-count">1</span>' in html

    def test_empty_buckets_say_none(self):
        html = sweep_to_board_html(_result())
        assert html.count("none") >= 3  # one per empty column

    def test_footer_shows_spend_sources_duration(self):
        html = sweep_to_board_html(
            _result(
                meta={
                    "spent_usd": 2.5,
                    "budget_usd": 10.0,
                    "sources": ["pattern-scan"],
                    "duration_ms": 1200,
                }
            )
        )
        assert "$2.50 / $10.00 spent" in html
        assert "1200 ms" in html
        assert "pattern-scan" in html

    def test_failures_flagged_in_footer(self):
        html = sweep_to_board_html(
            _result(
                meta={
                    "spent_usd": 0,
                    "budget_usd": 10.0,
                    "sources": ["s"],
                    "failures": ["perf-audit"],
                    "duration_ms": 0,
                }
            )
        )
        assert "1 source(s) failed" in html


class TestSeverity:
    def test_queue_sorted_critical_first(self):
        html = sweep_to_board_html(
            _result(
                queue=[
                    _finding(severity="low", title="LOW-ITEM"),
                    _finding(severity="critical", title="CRIT-ITEM"),
                ]
            )
        )
        assert html.index("CRIT-ITEM") < html.index("LOW-ITEM")

    def test_unknown_severity_does_not_crash(self):
        html = sweep_to_board_html(_result(queue=[_finding(severity="bogus")]))
        assert "Something risky" in html


class TestFieldRendering:
    def test_missing_location_renders_dash(self):
        html = sweep_to_board_html(_result(queue=[_finding(file=None, line=None)]))
        assert "—" in html

    def test_file_without_line(self):
        html = sweep_to_board_html(_result(queue=[_finding(file="src/y.py", line=None)]))
        assert "src/y.py" in html
        assert "src/y.py:" not in html  # no dangling colon

    def test_question_shows_reason_and_next_step(self):
        html = sweep_to_board_html(
            _result(
                questions=[
                    {"finding": _finding(), "reason": "missing line", "next_step": "open the file"}
                ]
            )
        )
        assert "missing line" in html
        assert "open the file" in html

    def test_rejected_collapsed_with_rule(self):
        html = sweep_to_board_html(
            _result(rejected=[{"finding": _finding(), "rule": "below threshold"}])
        )
        assert "<details>" in html
        assert "1 filtered out" in html
        assert "below threshold" in html


class TestInjectionSafety:
    def test_finding_text_is_escaped(self):
        html = sweep_to_board_html(
            _result(queue=[_finding(title="<script>alert(1)</script>", file="a<b>", source="x&y")])
        )
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert "a&lt;b&gt;" in html
        assert "x&amp;y" in html

    def test_board_carries_no_script_tag(self):
        # the board is display-only — no executable JS at all.
        html = sweep_to_board_html(_result(queue=[_finding()]))
        assert "<script" not in html.lower()
