"""Tests for the unified voice formatter."""

from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime, timezone
from enum import Enum
from unittest.mock import patch

from attune.voice import personality
from attune.voice.formatter import (
    _extract_from_dict,
    _extract_from_workflow_result,
    _extract_result_data,
    format_error,
    format_mcp_response,
    format_output,
)
from attune.workflows.data_classes import CostReport, WorkflowResult


def _make_result(
    success: bool = True,
    final_output: dict | None = None,
    error: str | None = None,
    error_type: str | None = None,
    cost_report: CostReport | None = None,
) -> WorkflowResult:
    """Build a minimal WorkflowResult for testing."""
    now = datetime.now(timezone.utc)
    return WorkflowResult(
        success=success,
        stages=[],
        final_output=final_output or {"formatted_report": "Test report"},
        cost_report=cost_report
        or CostReport(
            total_cost=0.0042,
            baseline_cost=0.01,
            savings=0.0058,
            savings_percent=58.0,
        ),
        started_at=now,
        completed_at=now,
        total_duration_ms=1500,
        error=error,
        error_type=error_type,
    )


class TestFormatOutput:
    """Test the main format_output function."""

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_successful_result_has_greeting(self, _mock):
        """Successful results get a positive opening."""
        result = _make_result(success=True)
        output = format_output("code-review", result)
        assert personality.GREETING_SUCCESS in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_failed_result_has_failure_greeting(self, _mock):
        """Failed results get the failure opening."""
        result = _make_result(
            success=False,
            error="Something broke",
        )
        output = format_output("code-review", result)
        assert personality.GREETING_FAILURE in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_includes_report_text(self, _mock):
        """Output includes the formatted report."""
        result = _make_result(
            final_output={"formatted_report": "Found 3 issues"},
        )
        output = format_output("security-audit", result)
        assert "Found 3 issues" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_includes_cost_line(self, _mock):
        """Output includes cost information."""
        result = _make_result()
        output = format_output("test-gen", result)
        assert "$0.0042" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_includes_savings_percent(self, _mock):
        """Output shows savings when available."""
        result = _make_result()
        output = format_output("test-gen", result)
        assert "58%" in output

    @patch(
        "attune.voice.formatter.get_next_steps",
        return_value=["I'd run `attune workflow run test-gen` next — gaps found"],
    )
    def test_includes_next_steps(self, _mock):
        """Output includes next-step suggestions."""
        result = _make_result()
        output = format_output("code-review", result)
        assert "test-gen" in output
        assert personality.HEADER_NEXT_STEPS in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_score_commentary_included(self, _mock):
        """Output with a score includes commentary."""
        result = _make_result(
            final_output={"formatted_report": "report", "score": 92},
        )
        output = format_output("security-audit", result)
        assert personality.score_commentary(92) in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_error_details_included(self, _mock):
        """Failed output includes error message."""
        result = _make_result(
            success=False,
            error="API timeout",
            error_type="transient",
        )
        output = format_output("code-review", result)
        assert "API timeout" in output
        assert personality.HEADER_ERROR in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_compact_mode(self, _mock):
        """Compact mode produces output."""
        result = _make_result()
        output = format_output("code-review", result, compact=True)
        assert isinstance(output, str)

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_none_result(self, _mock):
        """None result handled gracefully."""
        output = format_output("code-review", None)
        assert personality.GREETING_SUCCESS in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_string_result(self, _mock):
        """String result passes through."""
        output = format_output("code-review", "All tests passed")
        assert "All tests passed" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_none_cost_report(self, _mock):
        """WorkflowResult with None cost_report handled gracefully."""
        now = datetime.now(timezone.utc)
        result = WorkflowResult(
            success=True,
            stages=[],
            final_output={"formatted_report": "report"},
            cost_report=None,
            started_at=now,
            completed_at=now,
            total_duration_ms=1000,
        )
        output = format_output("code-review", result)
        assert "report" in output
        # No cost line should appear
        assert personality.HEADER_COST not in output


class TestFormatError:
    """Test the format_error function."""

    def test_includes_error_message(self):
        """Error output includes the raw message."""
        output = format_error("Connection refused")
        assert "Connection refused" in output

    def test_includes_error_prefix(self):
        """Error output starts with the voiced prefix."""
        output = format_error("test error")
        assert personality.ERROR_PREFIX in output

    def test_transient_suggests_retry(self):
        """Transient errors include retry suggestion."""
        output = format_error(
            "timeout",
            error_type="transient",
            workflow_name="code-review",
        )
        assert "code-review" in output
        assert "again" in output.lower()

    def test_no_retry_for_non_transient(self):
        """Non-transient errors don't suggest retry."""
        output = format_error("bad input", error_type="validation")
        assert "again" not in output.lower()


class TestFormatMcpResponse:
    """Test the format_mcp_response function."""

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_preserves_original_fields(self, _mock):
        """MCP response keeps all original dict fields."""
        original = {"success": True, "score": 85, "findings": []}
        result = format_mcp_response("security-audit", original)
        assert result["success"] is True
        assert result["score"] == 85
        assert result["findings"] == []

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_adds_voice_summary(self, _mock):
        """MCP response includes voice_summary field."""
        result = format_mcp_response("code-review", {"success": True, "score": 92})
        assert "voice_summary" in result

    @patch(
        "attune.voice.formatter.get_next_steps",
        return_value=["Try `test-gen` — gaps found"],
    )
    def test_adds_next_steps(self, _mock):
        """MCP response includes next_steps when available."""
        result = format_mcp_response("code-review", {"success": True})
        assert "next_steps" in result
        assert len(result["next_steps"]) == 1

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_failure_voice_summary(self, _mock):
        """Failed MCP response gets failure summary."""
        result = format_mcp_response("code-review", {"success": False})
        assert result["voice_summary"] == personality.GREETING_FAILURE

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_handler_supplied_voice_summary_wins(self, _mock):
        """A handler-set voice_summary is preserved, not overwritten
        with the generic greeting (session_memory_* verbs phrase their
        own actions — capture/forget must not say "Here's what I found.")."""
        result = format_mcp_response(
            "session-memory-capture",
            {"ok": True, "voice_summary": "Stashed that finding for future recall."},
        )
        assert result["voice_summary"] == "Stashed that finding for future recall."

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_empty_voice_summary_falls_back_to_greeting(self, _mock):
        """An empty/None summary still gets the generic fallback."""
        result = format_mcp_response("code-review", {"success": True, "voice_summary": ""})
        assert result["voice_summary"] == personality.GREETING_SUCCESS

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_skips_underscore_prefixed_keys(self, _mock):
        """Dict fallback skips _-prefixed internal keys."""
        result = format_mcp_response(
            "code-review",
            {"success": True, "_internal": "hidden", "visible": "shown"},
        )
        assert "_internal" not in result.get("voice_summary", "")


class TestExtractResultData:
    """Test the _extract_result_data helper."""

    def test_string_result(self):
        """String results pass through."""
        success, score, text, cost, error = _extract_result_data("hello")
        assert success is True
        assert text == "hello"
        assert score is None

    def test_dict_result(self):
        """Dict results extract fields."""
        success, score, text, cost, error = _extract_from_dict(
            {"success": True, "score": 80, "info": "details"},
        )
        assert success is True
        assert score == 80

    def test_dict_skips_internal_keys(self):
        """Dict fallback skips _-prefixed keys."""
        _, _, text, _, _ = _extract_from_dict(
            {"_internal": "hidden", "visible": "shown"},
        )
        assert "_internal" not in (text or "")
        assert "visible" in (text or "")

    def test_none_result(self):
        """None result returns safe defaults."""
        success, score, text, cost, error = _extract_result_data(None)
        assert success is True
        assert text is None


class TestWorkflowReportRendering:
    """The _type=="WorkflowReport" branch (workflow-result-formatting T3)."""

    def _report_dict(self, **overrides):
        """Serialized WorkflowReport fixture, as final_output carries it."""
        from attune.workflows.output import (
            NextAction,
            NextStepsSection,
            ProseSection,
            WorkflowReport,
        )

        kwargs = {
            "title": "Code review",
            "summary": "3 issues found across 2 files.",
            "score": 88,
            "metadata": {"cost_usd": 1.23, "duration_s": 42.0},
            "sections": [
                ProseSection(
                    title="Overview",
                    tier="essential",
                    text="Looks solid overall.",
                ),
                NextStepsSection(
                    title="Next steps",
                    tier="essential",
                    items=[
                        NextAction(
                            text="Fix the loop",
                            command="attune workflow run fix-test",
                        )
                    ],
                ),
            ],
        }
        kwargs.update(overrides)
        return WorkflowReport(**kwargs).to_dict()

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_rendered_markdown_included(self, _mock, monkeypatch, tmp_path):
        """A serialized report renders via the markdown renderer."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(final_output=self._report_dict())
        output = format_output("code-review", result)
        assert "# Code review" in output
        assert "Looks solid overall." in output
        assert "Fix the loop" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_score_extracted_from_report(self, _mock, monkeypatch, tmp_path):
        """report.score drives the score commentary and score line."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(final_output=self._report_dict())
        output = format_output("code-review", result)
        assert personality.score_commentary(88) in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_no_repr_leak(self, _mock, monkeypatch, tmp_path):
        """Rendered output never contains dataclass repr fragments."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(final_output=self._report_dict())
        output = format_output("code-review", result)
        assert "<class '" not in output
        assert "WorkflowReport(" not in output
        assert "ProseSection(" not in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_cost_hidden_without_api_key(self, _mock, monkeypatch, tmp_path):
        """Auto show_cost: metadata cost line hidden for subscription users."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(final_output=self._report_dict(), cost_report=None)
        output = format_output("code-review", result)
        assert "Cost & time" not in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_cost_shown_with_api_key(self, _mock, monkeypatch, tmp_path):
        """Auto show_cost: metadata cost line shown for API users."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "FAKE_key_NOT_REAL")
        result = _make_result(final_output=self._report_dict(), cost_report=None)
        output = format_output("code-review", result)
        assert "Cost & time" in output
        assert "$1.23" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_rendered_report_skips_sparse_fallback(self, _mock, monkeypatch, tmp_path):
        """A short rendered report is authoritative — no findings fallback."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(
            final_output=self._report_dict(
                title="T", summary="", score=None, metadata={}, sections=[]
            ),
        )
        result.metadata = {"findings": {"security_issues": ["issue one"]}}
        output = format_output("security-audit", result)
        assert "# T" in output
        # The metadata-findings fallback heading must NOT replace the report.
        assert "## Security Issues" not in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_renderer_crash_shows_banner(self, _mock, monkeypatch, tmp_path):
        """A renderer bug stays visible (render_safe banner + fallback)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch(
            "attune.voice.report_renderer.render",
            side_effect=RuntimeError("boom"),
        ):
            result = _make_result(final_output=self._report_dict())
            output = format_output("code-review", result)
        assert "Report renderer error" in output
        assert "Code review" in output  # safety-net fallback still shows content


class TestUnmigratedSafetyNet:
    """The bare-object branch: banner + pretty-print (proposal §6)."""

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_banner_names_type_and_no_repr(self, _mock):
        """Bespoke dataclass gets the migration banner, never a repr."""

        @dataclass
        class FakeReadinessReport:
            approved: bool = True
            blockers: list = dc_field(default_factory=list)

        result = _make_result(final_output=FakeReadinessReport())
        output = format_output("release-prep", result)
        assert "Renderer not yet migrated for FakeReadinessReport" in output
        assert "FakeReadinessReport(" not in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_field_summaries(self, _mock):
        """Enums show .value; collections show counts; empties show (empty)."""

        class Confidence(Enum):
            HIGH = "high"

        @dataclass
        class FakeReport:
            confidence: Confidence = Confidence.HIGH
            gates: list = dc_field(default_factory=lambda: [1, 2, 3, 4])
            blockers: list = dc_field(default_factory=list)
            extras: dict = dc_field(default_factory=lambda: {"a": 1, "b": 2})

        result = _make_result(final_output=FakeReport())
        output = format_output("release-prep", result)
        assert "confidence: high" in output
        assert "gates: [4 items]" in output
        assert "blockers: (empty)" in output
        assert "extras: [2 keys]" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_nested_dataclass_indents(self, _mock):
        """One level of nested dataclass expands with deeper indentation."""

        @dataclass
        class Inner:
            passed: bool = True

        @dataclass
        class Outer:
            inner: Inner = dc_field(default_factory=Inner)

        result = _make_result(final_output=Outer())
        output = format_output("release-prep", result)
        assert "  inner: Inner" in output
        assert "    passed: True" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_long_string_field_truncated(self, _mock):
        """A long string field is capped, keeping lines readable."""

        @dataclass
        class FakeReport:
            notes: str = "x" * 300

        result = _make_result(final_output=FakeReport())
        output = format_output("release-prep", result)
        assert "x" * 300 not in output
        assert "..." in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_plain_object_with_dict(self, _mock):
        """Non-dataclass objects pretty-print their public attributes."""

        class Legacy:
            def __init__(self):
                self.status = "ok"
                self._private = "hidden"

        result = _make_result(final_output=Legacy())
        output = format_output("release-prep", result)
        assert "Renderer not yet migrated for Legacy" in output
        assert "status: ok" in output
        assert "_private" not in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_fieldless_value_stringifies(self, _mock):
        """A value with no fields still shows under the banner."""
        result = _make_result(final_output=42)
        output = format_output("release-prep", result)
        assert "Renderer not yet migrated for int" in output
        assert "42" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_string_final_output_passes_through(self, _mock):
        """SDK markdown text keeps passing through with no banner."""
        result = _make_result(final_output="## Findings\n\n- one\n- two\n- three!")
        output = format_output("bug-predict", result)
        assert "Renderer not yet migrated" not in output
        assert "## Findings" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_none_final_output_uses_summary_fallback(self, _mock):
        """final_output=None still reaches the summary fallback, no banner."""
        now = datetime.now(timezone.utc)
        result = WorkflowResult(
            success=True,
            stages=[],
            final_output=None,
            cost_report=None,
            started_at=now,
            completed_at=now,
            total_duration_ms=1000,
            summary="Run finished with no structured output.",
        )
        output = format_output("code-review", result)
        assert "Renderer not yet migrated" not in output
        assert "Run finished with no structured output." in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_deep_nesting_collapses_to_type_name(self, _mock):
        """Past the indent depth cap, nested dataclasses summarize by name."""

        @dataclass
        class Innermost:
            value: int = 1

        @dataclass
        class Inner:
            deepest: Innermost = dc_field(default_factory=Innermost)

        @dataclass
        class Outer:
            inner: Inner = dc_field(default_factory=Inner)

        result = _make_result(final_output=Outer())
        output = format_output("release-prep", result)
        assert "  inner: Inner" in output
        # Depth cap: the second nesting level shows the type name only.
        assert "deepest: Innermost" in output
        assert "value: 1" not in output


class TestReportDisclosureAndDedup:
    """T4: disclosure threading + wrapper dedup for report results."""

    def _detail_report_result(self):
        from attune.workflows.output import (
            NextAction,
            NextStepsSection,
            ProseSection,
            TableSection,
            WorkflowReport,
        )

        report = WorkflowReport(
            title="Code review",
            summary="3 issues found",
            score=88,
            sections=[
                ProseSection(title="Overview", tier="essential", text="Solid."),
                TableSection(
                    title="Hotspots",
                    tier="detail",
                    columns=["file", "risk"],
                    rows=[{"file": "a.py", "risk": "high"}],
                ),
                NextStepsSection(
                    title="Next steps",
                    tier="essential",
                    items=[NextAction(text="Fix the loop")],
                ),
            ],
        )
        return _make_result(final_output=report.to_dict(), cost_report=None)

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_summary_wraps_detail_sections(self, _mock, monkeypatch, tmp_path):
        """Default disclosure keeps detail sections inside <details>."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        out = format_output("code-review", self._detail_report_result())
        assert "<details><summary>Hotspots</summary>" in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_full_disclosure_inlines_detail_sections(self, _mock, monkeypatch, tmp_path):
        """disclosure='full' renders detail sections inline, no <details>."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        out = format_output("code-review", self._detail_report_result(), disclosure="full")
        assert "<details>" not in out
        assert "a.py" in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_score_line_not_duplicated(self, _mock, monkeypatch, tmp_path):
        """The renderer owns the score line; the wrapper must not repeat it."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        out = format_output("code-review", self._detail_report_result())
        assert out.count("88/100") == 1
        # Score commentary (greeting) still applies.
        assert personality.score_commentary(88) in out

    @patch(
        "attune.voice.formatter.get_next_steps",
        return_value=["I'd run `attune workflow run test-gen` next"],
    )
    def test_voice_next_steps_suppressed_for_reports(self, _mock, monkeypatch, tmp_path):
        """The report's NextStepsSection owns guidance — no voice dup."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        out = format_output("code-review", self._detail_report_result())
        assert personality.HEADER_NEXT_STEPS not in out
        assert "Fix the loop" in out  # the report's own next steps render

    @patch(
        "attune.voice.formatter.get_next_steps",
        return_value=["I'd run `attune workflow run test-gen` next"],
    )
    def test_legacy_results_keep_score_line_and_next_steps(self, _mock):
        """Non-report results keep today's wrapper behavior unchanged."""
        result = _make_result(
            final_output={"formatted_report": "plain report text", "score": 70},
        )
        out = format_output("code-review", result)
        assert "Score: 70/100" in out
        assert personality.HEADER_NEXT_STEPS in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_malformed_report_dict_degrades_to_legacy_handling(self, _mock, monkeypatch, tmp_path):
        """A corrupt report payload falls back to dict handling, no repr leak.

        Ported from PR #745 (parallel T3): reconstruction failure must
        not crash and must not surface str(WorkflowResult).
        """
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(
            final_output={
                "_type": "WorkflowReport",
                "sections": [{"kind": "no-such-kind"}],
                "formatted_report": "legacy fallback text",
            },
        )
        output = format_output("code-review", result)
        assert "WorkflowResult(" not in output
        assert "legacy fallback text" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_voice_cost_line_suppressed_for_rendered_reports(self, _mock, monkeypatch, tmp_path):
        """The renderer's show_cost gate owns cost display (ported from #745)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # _make_result default cost_report carries $0.0042 / 58% savings.
        result = _make_result(final_output=self._detail_report_result().final_output)
        output = format_output("code-review", result)
        assert personality.HEADER_COST not in output
        assert "$0.0042" not in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_voice_cost_line_kept_for_safety_net_results(self, _mock):
        """Unmigrated bespoke results keep the wrapper cost line."""

        @dataclass
        class FakeReport:
            approved: bool = True

        result = _make_result(final_output=FakeReport())
        output = format_output("release-prep", result)
        assert personality.HEADER_COST in output
        assert "$0.0042" in output


# ---------------------------------------------------------------------------
# CHARACTERIZATION PINS — _extract_from_workflow_result (radon D23)
#
# These tests pin the CURRENT behavior of the function exactly, tuple by
# tuple, so a follow-up complexity-reduction refactor can be proven
# behavior-preserving. Do not "fix" surprising behavior here (e.g. the
# heading-without-items fallback output) — update a pin only alongside an
# intentional, reviewed behavior change.
# ---------------------------------------------------------------------------


class TestExtractFromWorkflowResultCharacterization:
    """Exact-tuple behavior pins for _extract_from_workflow_result."""

    # Default _make_result cost_report: $0.0042 / 58% savings / 1500ms.
    DEFAULT_COST_LINE = "$0.0042 (saved 58% vs premium) | 1.5s"

    def _report_dict(self):
        """Minimal serialized WorkflowReport, as final_output carries it."""
        from attune.workflows.output import ProseSection, WorkflowReport

        return WorkflowReport(
            title="Code review",
            summary="3 issues found.",
            score=88,
            sections=[
                ProseSection(title="Overview", tier="essential", text="Solid."),
            ],
        ).to_dict()

    def _bare_result(
        self,
        *,
        final_output=None,
        summary=None,
        metadata=None,
        success=True,
        error=None,
        cost_report=None,
    ) -> WorkflowResult:
        """WorkflowResult with NO default cost_report/final_output filling."""
        now = datetime.now(timezone.utc)
        return WorkflowResult(
            success=success,
            stages=[],
            final_output=final_output,
            cost_report=cost_report,
            started_at=now,
            completed_at=now,
            total_duration_ms=1500,
            error=error,
            metadata=metadata or {},
            summary=summary,
        )

    # -- report-dict final_output (rendered path) ------------------------

    def test_pin_report_dict_renders_score_and_suppresses_cost_line(self):
        """Rendered report: score from report, cost_line None despite cost_report."""
        result = _make_result(final_output=self._report_dict())
        with patch("attune.config.resolve_show_cost", return_value=False):
            success, score, text, cost_line, error = _extract_from_workflow_result(result)
        assert (success, score, cost_line, error) == (True, 88, None, None)
        assert "# Code review" in text

    def test_pin_render_failure_degrades_to_legacy_dict_fields(self):
        """render_safe raising falls back to formatted_report/score from the dict."""
        fo = self._report_dict()
        fo["formatted_report"] = "legacy fallback text long enough to dodge the sparse fallback"
        result = _make_result(final_output=fo)
        with (
            patch("attune.config.resolve_show_cost", return_value=False),
            patch(
                "attune.voice.report_renderer.render_safe",
                side_effect=RuntimeError("boom"),
            ),
        ):
            out = _extract_from_workflow_result(result)
        assert out == (
            True,
            88,
            "legacy fallback text long enough to dodge the sparse fallback",
            self.DEFAULT_COST_LINE,
            None,
        )

    # -- legacy dict / str / bespoke object paths ------------------------

    def test_pin_legacy_dict_without_report(self):
        """Plain dict final_output: formatted_report/score picked, cost line built."""
        result = _make_result(final_output={"formatted_report": "x" * 60, "score": 70})
        out = _extract_from_workflow_result(result)
        assert out == (True, 70, "x" * 60, self.DEFAULT_COST_LINE, None)

    def test_pin_str_final_output_passthrough(self):
        """String final_output passes through untouched, score stays None."""
        text = "## Findings\n\n- one\n- two\n- three, padding to clear fifty chars"
        result = _make_result(final_output=text)
        out = _extract_from_workflow_result(result)
        assert out == (True, None, text, self.DEFAULT_COST_LINE, None)

    def test_pin_unmigrated_object_banner_skips_sparse_fallback(self):
        """Bespoke object: banner text is authoritative (rendered=True)."""

        @dataclass
        class FakeThing:
            approved: bool = True

        result = _make_result(final_output=FakeThing())
        result.summary = "should not appear"
        result.metadata = {"findings": {"security_issues": ["nope"]}}
        success, score, text, cost_line, error = _extract_from_workflow_result(result)
        assert text == (
            "⚠ Renderer not yet migrated for FakeThing. Raw fields:\n\n  approved: True"
        )
        assert "## Security Issues" not in text
        assert (success, score, cost_line, error) == (
            True,
            None,
            self.DEFAULT_COST_LINE,
            None,
        )

    # -- sparse fallback: summary + metadata findings --------------------

    def test_pin_sparse_fallback_summary_only(self):
        """No final_output: report_text becomes the bare summary."""
        result = self._bare_result(summary="Run finished.")
        out = _extract_from_workflow_result(result)
        assert out == (True, None, "Run finished.", None, None)

    def test_pin_sparse_fallback_summary_plus_findings_lists(self):
        """Findings dict: '## Title Cased' headings + '- item' lines, exact join."""
        result = self._bare_result(
            summary="Scan done.",
            metadata={
                "findings": {
                    "security_issues": ["issue a", "issue b"],
                    "code_smells": ["smell c"],
                },
            },
        )
        out = _extract_from_workflow_result(result)
        expected_text = (
            "Scan done.\n"
            "\n## Security Issues\n"
            "- issue a\n"
            "- issue b\n"
            "\n## Code Smells\n"
            "- smell c"
        )
        assert out == (True, None, expected_text, None, None)

    def test_pin_sparse_fallback_non_list_findings_value_emits_heading_only(self):
        """Non-list category value: heading still emitted, items silently skipped."""
        result = self._bare_result(metadata={"findings": {"raw_stats": {"n": 3}}})
        out = _extract_from_workflow_result(result)
        assert out == (True, None, "\n## Raw Stats", None, None)

    def test_pin_sparse_fallback_non_dict_findings_ignored(self):
        """findings that is not a dict contributes nothing — report_text stays None."""
        result = self._bare_result(metadata={"findings": ["not", "a", "dict"]})
        out = _extract_from_workflow_result(result)
        assert out == (True, None, None, None, None)

    def test_pin_empty_fallback_parts_leave_short_report_text_unchanged(self):
        """No summary/findings: a short report_text survives untouched."""
        result = self._bare_result(final_output={"formatted_report": "tiny"})
        out = _extract_from_workflow_result(result)
        assert out == (True, None, "tiny", None, None)

    def test_pin_sparse_fallback_replaces_short_report_text(self):
        """Fallback REPLACES (not appends to) a sub-50-char report_text."""
        result = self._bare_result(
            final_output={"formatted_report": "short"},
            summary="The summary wins.",
        )
        out = _extract_from_workflow_result(result)
        assert out == (True, None, "The summary wins.", None, None)

    # -- cost line variants ----------------------------------------------

    def test_pin_cost_line_with_savings(self):
        """savings_percent > 0: two-part cost line plus duration."""
        result = _make_result(final_output={"formatted_report": "x" * 60})
        _, _, _, cost_line, _ = _extract_from_workflow_result(result)
        assert cost_line == "$0.0042 (saved 58% vs premium) | 1.5s"

    def test_pin_cost_line_without_savings_segment(self):
        """savings_percent == 0: no '(saved ...)' segment, just cost | duration."""
        result = _make_result(
            final_output={"formatted_report": "x" * 60},
            cost_report=CostReport(
                total_cost=0.01,
                baseline_cost=0.01,
                savings=0.0,
                savings_percent=0.0,
            ),
        )
        out = _extract_from_workflow_result(result)
        assert out == (True, None, "x" * 60, "$0.0100 | 1.5s", None)

    def test_pin_none_cost_report_yields_none_cost_line(self):
        """cost_report None: cost_line is None, everything else unaffected."""
        result = self._bare_result(final_output={"formatted_report": "x" * 60})
        out = _extract_from_workflow_result(result)
        assert out == (True, None, "x" * 60, None, None)

    # -- error_msg gating --------------------------------------------------

    def test_pin_error_surfaces_only_on_failure(self):
        """result.error becomes error_msg only when success is False."""
        result = self._bare_result(
            success=False,
            error="boom",
            final_output={"formatted_report": "x" * 60},
        )
        out = _extract_from_workflow_result(result)
        assert out == (False, None, "x" * 60, None, "boom")

    def test_pin_error_masked_on_success(self):
        """A populated result.error is dropped when success is True."""
        result = self._bare_result(
            success=True,
            error="ignored",
            final_output={"formatted_report": "x" * 60},
        )
        out = _extract_from_workflow_result(result)
        assert out == (True, None, "x" * 60, None, None)
