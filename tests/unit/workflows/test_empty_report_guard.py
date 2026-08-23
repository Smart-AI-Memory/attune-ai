"""A scored report with no sections must say so, not render blank.

The failure this guards is invisible from every angle that normally
signals trouble: the run exits 0, records `completed`, and carries a
score — it simply hands back nothing structured. `bug-predict` did
exactly that in 6 of 6 recorded runs over three weeks (census taken
2026-08-22 across `~/.attune/ops/runs/`), and the only reason it
surfaced was someone reading a report expecting findings.

Same shape as the vacuous-test class already in the corpus: a thing
that satisfies its check BY being empty.

The scored-vs-unscored split is the calibrated discriminator, not a
guess. In the same census `deep-review` had a section-less run too —
but with NO score, the signature of an aborted run, which is
legitimately empty. Flagging those would make the marker noise and get
it ignored, so both directions are pinned below.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging

from attune.workflows.agent_sdk_adapter import AgentSDKResultAdapter


def _report(*, score, findings=None, suggestions=None):
    return AgentSDKResultAdapter._to_workflow_report(
        title="wf",
        summary="prose summary",
        score=score,
        findings=findings or {},
        suggestions=suggestions or [],
        total_cost=None,
        duration_ms=1000,
    )


def _callouts(report):
    return [s for s in report.sections if getattr(s, "kind", None) == "callout"]


class TestScoredButEmptyIsMarked:
    def test_a_scored_report_with_no_sections_gets_a_loud_marker(self):
        report = _report(score=60)

        callouts = _callouts(report)

        assert len(callouts) == 1, "the blank report must not render blank"
        assert callouts[0].emphasis == "warn"
        assert "reporting defect" in callouts[0].text

    def test_the_marker_says_the_findings_are_in_the_prose(self):
        """Readers must know where to look, not just that it is broken."""
        report = _report(score=60)

        assert "summary" in _callouts(report)[0].text.lower()

    def test_the_score_and_summary_survive(self):
        """The marker adds; it must not swallow what the run did produce."""
        report = _report(score=60)

        assert report.score == 60
        assert report.summary == "prose summary"

    def test_it_logs_so_the_defect_is_visible_outside_the_report(self, caplog):
        with caplog.at_level(logging.WARNING):
            _report(score=60)

        assert any("no structured sections" in r.message for r in caplog.records)


class TestTheDiscriminatorHolds:
    """Calibration: only SCORED-and-empty is a defect."""

    def test_an_unscored_empty_report_is_left_alone(self):
        """An aborted run is legitimately section-less — do not flag it."""
        report = _report(score=None)

        assert _callouts(report) == []

    def test_a_report_with_findings_is_left_alone(self):
        report = _report(score=60, findings={"Security": [{"description": "x"}]})

        assert _callouts(report) == []
        assert report.sections, "the real sections must still be built"

    def test_sections_from_suggestions_alone_count_as_output(self):
        """Next-steps are structured output too — not a blank panel."""
        from attune.workflows.data_classes import NextAction

        report = _report(
            score=60,
            suggestions=[
                NextAction(
                    workflow_name="wf",
                    description="do a thing",
                    reasoning="because",
                )
            ],
        )

        assert _callouts(report) == [], "a next-steps section is real output"
