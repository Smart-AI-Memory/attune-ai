"""release-prep WorkflowReport migration (workflow-result-formatting T7).

Covers ``_to_workflow_report`` (the bespoke-to-universal converter) and
the migrated ``ReleasePrepTeamWorkflow.execute()`` contract: a
``WorkflowResult`` whose ``final_output`` is the serialized report, no
console printing from the workflow itself, and repr-leak / tier drift
guards over the rendered markdown (proposal test layers 1–2).
"""

import asyncio
import io
from contextlib import redirect_stdout
from unittest.mock import AsyncMock, patch

from attune.agents.release.release_models import (
    QualityGate,
    ReleaseAgentResult,
    ReleaseReadinessReport,
    Tier,
)
from attune.agents.release.release_prep_team import (
    ReleasePrepTeamWorkflow,
    _to_workflow_report,
)
from attune.voice.report_renderer import render
from attune.workflows.data_classes import WorkflowResult
from attune.workflows.output import (
    CalloutSection,
    ListSection,
    NextStepsSection,
    TableSection,
    WorkflowReport,
)


def _make_report(*, approved: bool = False) -> ReleaseReadinessReport:
    """Realistic readiness report covering every converter branch."""
    return ReleaseReadinessReport(
        approved=approved,
        confidence="medium",
        quality_gates=[
            QualityGate(name="coverage", threshold=80.0, actual=72.5, passed=False),
            QualityGate(name="security", threshold=0.0, actual=0.0, passed=True),
        ],
        agent_results=[
            ReleaseAgentResult(
                agent_id="h1",
                agent_role="health",
                success=True,
                tier_used=Tier.CAPABLE,
                score=88.0,
                confidence=0.9,
                execution_time_ms=4200,
            ),
        ],
        blockers=[] if approved else ["coverage below 80%"],
        warnings=["2 TODOs in src/"],
        summary="1 blocker found" if not approved else "All gates green",
        total_duration=42.0,
        total_cost=1.23,
    )


class TestToWorkflowReport:
    """The converter's section shapes and tiers."""

    def test_blocked_verdict_callout(self):
        """A blocked release gets a danger callout naming the verdict."""
        report = _to_workflow_report(_make_report(approved=False))
        callout = report.sections[0]
        assert isinstance(callout, CalloutSection)
        assert callout.emphasis == "danger"
        assert "BLOCKED" in callout.text

    def test_approved_verdict_callout(self):
        """An approved release gets an ok callout."""
        report = _to_workflow_report(_make_report(approved=True))
        callout = report.sections[0]
        assert callout.emphasis == "ok"
        assert "APPROVED" in callout.text

    def test_gates_table_essential_with_pass_counts(self):
        """Quality gates render as an essential table, title carries counts."""
        report = _to_workflow_report(_make_report())
        gates = report.sections[1]
        assert isinstance(gates, TableSection)
        assert gates.tier == "essential"
        assert "1/2 passed" in gates.title
        assert len(gates.rows) == 2

    def test_agent_breakdown_is_detail_tier(self):
        """Per-agent breakdown is detail — collapsed in summary mode."""
        report = _to_workflow_report(_make_report())
        agents = report.sections[2]
        assert isinstance(agents, TableSection)
        assert agents.tier == "detail"
        assert agents.rows[0]["Tier"] == "capable"

    def test_blockers_and_warnings_sections(self):
        """Blockers/warnings appear as essential lists when present."""
        report = _to_workflow_report(_make_report(approved=False))
        lists = [s for s in report.sections if isinstance(s, ListSection)]
        titles = {s.title for s in lists}
        assert titles == {"Blockers", "Warnings"}
        assert all(s.tier == "essential" for s in lists)

    def test_no_blockers_section_when_approved(self):
        """An approved report (no blockers) omits the Blockers section."""
        report = _to_workflow_report(_make_report(approved=True))
        titles = [s.title for s in report.sections if isinstance(s, ListSection)]
        assert "Blockers" not in titles

    def test_next_steps_blocked_names_each_blocker(self):
        """Blocked release: one actionable next step per blocker."""
        report = _to_workflow_report(_make_report(approved=False))
        steps = report.sections[-1]
        assert isinstance(steps, NextStepsSection)
        assert any("coverage below 80%" in a.text for a in steps.items)

    def test_next_steps_approved_points_at_secure_release(self):
        """Approved release: forward momentum to the security pipeline."""
        report = _to_workflow_report(_make_report(approved=True))
        steps = report.sections[-1]
        assert any(a.command == "attune workflow run secure-release" for a in steps.items)

    def test_metadata_carries_renderer_cost_keys(self):
        """cost_usd/duration_s match the renderer's _COST_KEYS names."""
        report = _to_workflow_report(_make_report())
        assert report.metadata["cost_usd"] == 1.23
        assert report.metadata["duration_s"] == 42.0
        assert report.metadata["approved"] is False

    def test_round_trips_through_dict(self):
        """to_dict()/from_dict() survives the serialization boundary."""
        d = _to_workflow_report(_make_report()).to_dict()
        assert WorkflowReport.is_report_dict(d)
        rebuilt = WorkflowReport.from_dict(d)
        assert rebuilt.title == "Release readiness"
        assert len(rebuilt.sections) == 6


class TestRenderedMarkdownGuards:
    """Proposal test layers 1–2 over the real converter output."""

    def test_no_repr_leak_in_rendered_markdown(self):
        """Layer 1: no dataclass repr fragments survive rendering."""
        markdown = render(_to_workflow_report(_make_report()))
        for fragment in (
            "ReleaseReadinessReport(",
            "QualityGate(",
            "ReleaseAgentResult(",
            "<class '",
            "Tier.CAPABLE",
        ):
            assert fragment not in markdown, fragment

    def test_tier_classification_in_summary_mode(self):
        """Layer 2: essential inline, detail collapsed, in summary mode."""
        markdown = render(_to_workflow_report(_make_report()), disclosure="summary")
        assert "Quality gates" in markdown.split("<details>")[0]
        assert "<details><summary>Per-agent breakdown</summary>" in markdown


class TestMigratedExecute:
    """ReleasePrepTeamWorkflow.execute() returns a WorkflowResult."""

    def _run(self, report: ReleaseReadinessReport) -> tuple[WorkflowResult, str]:
        with patch("attune.agents.release.release_prep_team.ReleasePrepTeam") as mock_team:
            mock_team.return_value.assess_readiness = AsyncMock(return_value=report)
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = asyncio.run(ReleasePrepTeamWorkflow().execute(path="."))
        return result, buf.getvalue()

    def test_returns_workflow_result_with_report_dict(self):
        """final_output carries the serialized WorkflowReport."""
        result, _ = self._run(_make_report())
        assert isinstance(result, WorkflowResult)
        assert WorkflowReport.is_report_dict(result.final_output)

    def test_success_true_even_when_blocked(self):
        """The assessment RAN; the verdict lives in the report metadata."""
        result, _ = self._run(_make_report(approved=False))
        assert result.success is True
        assert result.metadata["approved"] is False

    def test_no_console_print_from_workflow(self):
        """The old format_console_output() dump is gone — surfaces render."""
        _, stdout = self._run(_make_report())
        assert stdout == ""

    def test_target_kwarg_maps_to_path(self):
        """VSCode/CLI compatibility: target= overrides the default path."""
        with patch("attune.agents.release.release_prep_team.ReleasePrepTeam") as mock_team:
            mock_team.return_value.assess_readiness = AsyncMock(return_value=_make_report())
            asyncio.run(ReleasePrepTeamWorkflow().execute(target="src/attune"))
            mock_team.return_value.assess_readiness.assert_awaited_once_with(
                codebase_path="src/attune"
            )
