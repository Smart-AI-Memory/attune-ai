"""Tests for the workflow-result data model (workflow-result-formatting T1).

Covers the pure-data ``WorkflowReport`` / ``Section`` model: serialization
round-trip across the SDK/MCP/JSON boundary, the ``.findings`` back-compat
property, the ``.from_findings`` constructor, and the drift-guard that the
report carries no rendering method (rendering lives in
``attune.voice.report_renderer``).
"""

from __future__ import annotations

from attune.workflows.output import (
    CalloutSection,
    Finding,
    FindingsSection,
    ListSection,
    NextAction,
    NextStepsSection,
    ProseSection,
    Section,
    TableSection,
    WorkflowReport,
    next_steps_section_from_suggestions,
    report_dict_with_next_steps,
)


class _Suggestion:
    """Minimal stand-in for data_classes.NextAction (description + name)."""

    def __init__(self, workflow_name: str, description: str) -> None:
        self.workflow_name = workflow_name
        self.description = description


class TestNextStepsSectionFromSuggestions:
    def test_real_workflow_gets_runnable_command(self) -> None:
        section = next_steps_section_from_suggestions(
            [_Suggestion("security-audit", "Re-run the audit")]
        )
        assert section is not None
        assert section.items[0].command == "/workflows run security-audit"
        assert section.items[0].text == "Re-run the audit"

    def test_generic_followup_has_no_command(self) -> None:
        section = next_steps_section_from_suggestions(
            [_Suggestion("agent-followup", "Look into it")]
        )
        assert section is not None
        assert section.items[0].command is None

    def test_empty_returns_none(self) -> None:
        assert next_steps_section_from_suggestions([]) is None


class TestReportDictWithNextSteps:
    def _report_with_flat_steps(self) -> dict:
        rep = WorkflowReport(
            title="X",
            summary="s",
            score=1,
            metadata={},
            sections=[
                ListSection(title="security", tier="essential", items=["finding"]),
                NextStepsSection(
                    title="Next steps",
                    tier="essential",
                    items=[NextAction(text="stale flat step", command=None)],
                ),
            ],
        )
        return rep.to_dict()

    def test_swaps_in_rich_commands_and_replaces_old_section(self) -> None:
        out = report_dict_with_next_steps(
            self._report_with_flat_steps(),
            [_Suggestion("code-review", "Review the diff")],
        )
        steps = [s for s in out["sections"] if s["kind"] == "next-steps"]
        assert len(steps) == 1  # replaced, not duplicated
        assert steps[0]["items"][0]["command"] == "/dev review"
        # the non-next-steps section is preserved
        assert any(s["kind"] == "list" for s in out["sections"])

    def test_non_report_passes_through(self) -> None:
        assert (
            report_dict_with_next_steps("raw markdown", [_Suggestion("x", "y")]) == "raw markdown"
        )

    def test_empty_suggestions_preserves_report_unchanged(self) -> None:
        rep = self._report_with_flat_steps()
        assert report_dict_with_next_steps(rep, []) is rep


def _full_report() -> WorkflowReport:
    """A report exercising every section kind and both leaf types."""
    return WorkflowReport(
        title="Release readiness",
        summary="Release APPROVED",
        score=98,
        metadata={"total_cost": 0.0, "total_duration": 90.9},
        sections=[
            CalloutSection(title="Verdict", tier="essential", text="APPROVED", emphasis="ok"),
            ProseSection(title="Notes", tier="useful", text="all gates pass"),
            TableSection(
                title="Gates",
                tier="essential",
                columns=["Gate", "Pass"],
                rows=[{"Gate": "Security", "Pass": "yes"}],
            ),
            ListSection(title="Warnings", tier="essential", items=["none"]),
            FindingsSection(
                title="Findings",
                tier="detail",
                findings=[Finding(severity="high", file="a.py", line=10, message="boom")],
            ),
            NextStepsSection(
                title="Next steps",
                tier="essential",
                items=[NextAction(text="Cut the release", command="attune release prep")],
            ),
        ],
    )


class TestRoundTrip:
    def test_report_round_trips_through_dict(self) -> None:
        report = _full_report()
        restored = WorkflowReport.from_dict(report.to_dict())
        # Compare via re-serialization (stable structural equality).
        assert restored.to_dict() == report.to_dict()

    def test_to_dict_has_type_discriminator(self) -> None:
        assert _full_report().to_dict()["_type"] == "WorkflowReport"

    def test_each_section_kind_survives(self) -> None:
        restored = WorkflowReport.from_dict(_full_report().to_dict())
        kinds = [s.kind for s in restored.sections]
        assert kinds == ["callout", "prose", "table", "list", "findings", "next-steps"]

    def test_subclasses_reconstruct_to_right_types(self) -> None:
        restored = WorkflowReport.from_dict(_full_report().to_dict())
        by_kind = {type(s).__name__ for s in restored.sections}
        assert by_kind == {
            "CalloutSection",
            "ProseSection",
            "TableSection",
            "ListSection",
            "FindingsSection",
            "NextStepsSection",
        }

    def test_nested_finding_round_trips(self) -> None:
        restored = WorkflowReport.from_dict(_full_report().to_dict())
        f = restored.findings[0]
        assert (f.severity, f.file, f.line, f.message) == ("high", "a.py", 10, "boom")

    def test_nested_next_action_round_trips(self) -> None:
        restored = WorkflowReport.from_dict(_full_report().to_dict())
        ns = next(s for s in restored.sections if isinstance(s, NextStepsSection))
        assert ns.items[0].command == "attune release prep"

    def test_unknown_section_kind_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Unknown section kind"):
            WorkflowReport.from_dict(
                {"sections": [{"kind": "bogus", "title": "x", "tier": "useful"}]}
            )


class TestFindingsProperty:
    def test_findings_aggregates_across_sections(self) -> None:
        report = WorkflowReport(
            title="t",
            sections=[
                FindingsSection(title="A", tier="useful", findings=[Finding("high", "a.py")]),
                ProseSection(title="mid", tier="useful", text="x"),
                FindingsSection(title="B", tier="detail", findings=[Finding("low", "b.py")]),
            ],
        )
        assert [f.file for f in report.findings] == ["a.py", "b.py"]

    def test_findings_empty_when_no_findings_section(self) -> None:
        assert WorkflowReport(title="t").findings == []


class TestFromFindings:
    def test_builds_single_findings_section(self) -> None:
        report = WorkflowReport.from_findings("Scan", [Finding("high", "a.py")])
        assert len(report.sections) == 1
        assert isinstance(report.sections[0], FindingsSection)
        assert report.findings[0].file == "a.py"

    def test_passes_through_kwargs(self) -> None:
        report = WorkflowReport.from_findings("Scan", [], score=42, summary="s")
        assert report.score == 42
        assert report.summary == "s"


class TestDetection:
    def test_is_report_dict_true_for_serialized(self) -> None:
        assert WorkflowReport.is_report_dict(_full_report().to_dict()) is True

    def test_is_report_dict_false_for_plain_dict(self) -> None:
        assert WorkflowReport.is_report_dict({"formatted_report": "x"}) is False
        assert WorkflowReport.is_report_dict("a string") is False


class TestDriftGuards:
    def test_report_has_no_render_method(self) -> None:
        # Rendering is the renderer's job (voice.report_renderer), never the
        # data model's. Guards against re-introducing the old rich path.
        assert not hasattr(WorkflowReport, "render")
        assert not hasattr(WorkflowReport, "add_section")

    def test_old_rich_symbols_are_gone(self) -> None:
        import attune.workflows.output as output_mod

        for removed in ("ReportSection", "FindingsTable", "MetricsPanel", "format_workflow_result"):
            assert not hasattr(output_mod, removed), f"{removed} should be deleted"

    def test_section_base_carries_title_and_tier(self) -> None:
        s: Section = CalloutSection(title="T", tier="essential", text="x")
        assert (s.title, s.tier) == ("T", "essential")
