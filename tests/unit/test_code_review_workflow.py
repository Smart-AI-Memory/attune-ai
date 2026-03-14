"""Unit tests for code_review_adapters and code_review_report.

Tests cover adapter functions and report formatting that are
independent of the CodeReviewWorkflow execution engine.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.code_review_adapters import (
    _map_type_to_category,
    _merge_verdicts,
    crew_report_to_workflow_format,
    merge_code_review_results,
    workflow_findings_to_crew_format,
)


def _make_crew_report(
    *,
    findings=None,
    verdict="approve",
    quality_score=95,
    has_blocking=False,
    summary="All good",
    agents_used=None,
    memory_graph_hits=0,
    review_duration_seconds=1.5,
    metadata=None,
):
    """Build a mock CodeReviewReport-like object for adapter tests."""
    if findings is None:
        findings = []
    report = MagicMock()
    report.findings = findings
    report.verdict = MagicMock(value=verdict)
    report.quality_score = quality_score
    report.has_blocking_issues = has_blocking
    report.summary = summary
    report.agents_used = agents_used or ["review_lead"]
    report.memory_graph_hits = memory_graph_hits
    report.review_duration_seconds = review_duration_seconds
    report.metadata = metadata or {}
    return report


def _make_finding(
    *,
    title="Test finding",
    description="A test finding",
    severity="medium",
    category="quality",
    file_path="src/main.py",
    line_number=10,
    code_snippet="x = 1",
    suggestion="Rename x",
    before_code="x = 1",
    after_code="count = 1",
    confidence=0.9,
):
    """Build a mock ReviewFinding-like object."""
    f = MagicMock()
    f.title = title
    f.description = description
    f.severity = MagicMock(value=severity)
    f.category = MagicMock(value=category)
    f.file_path = file_path
    f.line_number = line_number
    f.code_snippet = code_snippet
    f.suggestion = suggestion
    f.before_code = before_code
    f.after_code = after_code
    f.confidence = confidence
    return f


# ===========================================================================
# 11. Adapter: _merge_verdicts Tests
# ===========================================================================


@pytest.mark.unit
class TestMergeVerdicts:
    """Test _merge_verdicts function."""

    def test_same_verdict(self):
        """Test merging same verdicts returns that verdict."""
        assert _merge_verdicts("approve", "approve") == "approve"

    def test_more_severe_wins(self):
        """Test that the more severe verdict wins."""
        assert _merge_verdicts("approve", "reject") == "reject"
        assert _merge_verdicts("reject", "approve") == "reject"

    def test_request_changes_beats_approve(self):
        """Test request_changes is more severe than approve."""
        assert _merge_verdicts("approve", "request_changes") == "request_changes"

    def test_approve_with_suggestions_middle(self):
        """Test approve_with_suggestions is between approve and request_changes."""
        assert _merge_verdicts("approve", "approve_with_suggestions") == "approve_with_suggestions"
        assert _merge_verdicts("approve_with_suggestions", "request_changes") == "request_changes"

    def test_hyphen_normalization(self):
        """Test that hyphens are normalized to underscores."""
        assert _merge_verdicts("request-changes", "approve") == "request_changes"

    def test_case_insensitive(self):
        """Test case insensitive comparison."""
        assert _merge_verdicts("APPROVE", "REJECT") == "reject"

    def test_unknown_verdict_defaults_to_approve(self):
        """Test unknown verdict treated as approve (least severe)."""
        assert _merge_verdicts("unknown", "request_changes") == "request_changes"


# ===========================================================================
# 12. Adapter: _map_type_to_category Tests
# ===========================================================================


@pytest.mark.unit
class TestMapTypeToCategory:
    """Test _map_type_to_category function."""

    def test_security_types(self):
        """Test security vulnerability types map correctly."""
        assert _map_type_to_category("sql_injection") == "security"
        assert _map_type_to_category("xss") == "security"
        assert _map_type_to_category("command_injection") == "security"
        assert _map_type_to_category("path_traversal") == "security"

    def test_quality_types(self):
        """Test quality types map correctly."""
        assert _map_type_to_category("code_smell") == "quality"
        assert _map_type_to_category("complexity") == "quality"
        assert _map_type_to_category("duplicate") == "quality"

    def test_performance_types(self):
        """Test performance types map correctly."""
        assert _map_type_to_category("performance") == "performance"
        assert _map_type_to_category("n_plus_one") == "performance"

    def test_architecture_types(self):
        """Test architecture types map correctly."""
        assert _map_type_to_category("architecture") == "architecture"
        assert _map_type_to_category("design") == "architecture"
        assert _map_type_to_category("solid") == "architecture"

    def test_testing_types(self):
        """Test testing types map correctly."""
        assert _map_type_to_category("test") == "testing"
        assert _map_type_to_category("coverage") == "testing"

    def test_unknown_type_maps_to_other(self):
        """Test unknown type defaults to 'other'."""
        assert _map_type_to_category("something_unknown") == "other"

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        assert _map_type_to_category("SQL_INJECTION") == "security"
        assert _map_type_to_category("XSS") == "security"


# ===========================================================================
# 13. Adapter: crew_report_to_workflow_format Tests
# ===========================================================================


@pytest.mark.unit
class TestCrewReportToWorkflowFormat:
    """Test crew_report_to_workflow_format function."""

    def test_empty_report(self):
        """Test converting report with no findings."""
        report = _make_crew_report()
        result = crew_report_to_workflow_format(report)
        assert result["crew_enabled"] is True
        assert result["findings"] == []
        assert result["finding_count"] == 0
        assert result["verdict"] == "approve"
        assert result["quality_score"] == 95

    def test_report_with_findings(self):
        """Test converting report with findings."""
        findings = [
            _make_finding(
                title="XSS Bug",
                severity="high",
                category="security",
                file_path="web.py",
                line_number=42,
            ),
            _make_finding(
                title="Unused var",
                severity="low",
                category="quality",
            ),
        ]
        report = _make_crew_report(findings=findings, verdict="request_changes")
        result = crew_report_to_workflow_format(report)

        assert result["finding_count"] == 2
        assert result["verdict"] == "request_changes"
        assert result["findings"][0]["title"] == "XSS Bug"
        assert result["findings"][0]["severity"] == "high"
        assert result["findings"][0]["type"] == "security"
        assert result["findings"][0]["file"] == "web.py"
        assert result["findings"][0]["line"] == 42

    def test_severity_breakdown(self):
        """Test severity breakdown counts."""
        findings = [
            _make_finding(severity="critical"),
            _make_finding(severity="high"),
            _make_finding(severity="high"),
            _make_finding(severity="medium"),
        ]
        report = _make_crew_report(findings=findings)
        result = crew_report_to_workflow_format(report)
        assessment = result["assessment"]

        assert assessment["severity_breakdown"]["critical"] == 1
        assert assessment["severity_breakdown"]["high"] == 2
        assert assessment["severity_breakdown"]["medium"] == 1

    def test_category_breakdown(self):
        """Test category breakdown counts."""
        findings = [
            _make_finding(category="security"),
            _make_finding(category="security"),
            _make_finding(category="quality"),
        ]
        report = _make_crew_report(findings=findings)
        result = crew_report_to_workflow_format(report)

        assert result["assessment"]["by_category"]["security"] == 2
        assert result["assessment"]["by_category"]["quality"] == 1

    def test_metadata_passthrough(self):
        """Test metadata is passed through."""
        report = _make_crew_report(metadata={"cost": 0.05, "run_id": "abc123"})
        result = crew_report_to_workflow_format(report)
        assert result["metadata"] == {"cost": 0.05, "run_id": "abc123"}
        assert result["cost"] == 0.05


# ===========================================================================
# 14. Adapter: workflow_findings_to_crew_format Tests
# ===========================================================================


@pytest.mark.unit
class TestWorkflowFindingsToCrewFormat:
    """Test workflow_findings_to_crew_format function."""

    def test_empty_findings(self):
        """Test converting empty findings list."""
        result = workflow_findings_to_crew_format([])
        assert result == []

    def test_basic_finding_conversion(self):
        """Test converting a basic finding."""
        findings = [
            {
                "title": "SQL Injection",
                "description": "Unsanitized query",
                "severity": "critical",
                "type": "sql_injection",
                "file": "db.py",
                "line": 42,
                "code_snippet": "cursor.execute(q)",
                "suggestion": "Use parameterized queries",
                "confidence": 0.95,
            },
        ]
        result = workflow_findings_to_crew_format(findings)
        assert len(result) == 1
        assert result[0]["title"] == "SQL Injection"
        assert result[0]["severity"] == "critical"
        assert result[0]["category"] == "security"
        assert result[0]["file_path"] == "db.py"
        assert result[0]["line_number"] == 42

    def test_missing_fields_use_defaults(self):
        """Test that missing fields use sensible defaults."""
        findings = [{"type": "unknown_issue"}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["title"] == "unknown_issue"  # Falls back to type
        assert result[0]["severity"] == "medium"
        assert result[0]["confidence"] == 1.0

    def test_alternative_field_names(self):
        """Test fallback field names (match -> description, remediation -> suggestion)."""
        findings = [
            {
                "type": "xss",
                "match": "innerHTML = userInput",
                "remediation": "Use textContent instead",
            },
        ]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["description"] == "innerHTML = userInput"
        assert result[0]["suggestion"] == "Use textContent instead"


# ===========================================================================
# 15. Adapter: merge_code_review_results Tests
# ===========================================================================


@pytest.mark.unit
class TestMergeCodeReviewResults:
    """Test merge_code_review_results function."""

    def test_both_none(self):
        """Test merge with both inputs None."""
        result = merge_code_review_results(None, None)
        assert result["findings"] == []
        assert result["quality_score"] == 100
        assert result["verdict"] == "approve"
        assert result["merged"] is False

    def test_only_crew_report(self):
        """Test merge with only crew report."""
        crew = {
            "findings": [{"file": "a.py", "severity": "high"}],
            "quality_score": 80,
            "verdict": "request_changes",
        }
        result = merge_code_review_results(crew, None)
        assert result["merged"] is False
        assert result["quality_score"] == 80

    def test_only_workflow_findings(self):
        """Test merge with only workflow findings."""
        wf = {
            "findings": [{"file": "b.py", "severity": "low"}],
            "security_score": 95,
            "verdict": "approve",
        }
        result = merge_code_review_results(None, wf)
        assert result["merged"] is False
        assert result["crew_enabled"] is False

    def test_merge_deduplicates(self):
        """Test merge deduplicates findings by (file, line, type)."""
        crew = {
            "findings": [
                {"file": "a.py", "line": 10, "type": "security", "severity": "high"},
            ],
            "quality_score": 85,
            "verdict": "approve",
            "summary": "Crew summary",
            "agents_used": ["agent1"],
            "assessment": {"severity_breakdown": {"high": 1}},
        }
        wf = {
            "findings": [
                {"file": "a.py", "line": 10, "type": "security", "severity": "high"},
                {"file": "b.py", "line": 20, "type": "quality", "severity": "low"},
            ],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {"high": 0, "low": 1}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["merged"] is True
        # Duplicate (a.py:10:security) should only appear once
        assert result["finding_count"] == 2

    def test_merge_weighted_score(self):
        """Test merged quality score uses weighted average."""
        crew = {
            "findings": [],
            "quality_score": 100,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {}},
        }
        wf = {
            "findings": [],
            "security_score": 80,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        # Expected: 100 * 0.7 + 80 * 0.3 = 70 + 24 = 94
        assert result["quality_score"] == 94.0

    def test_merge_takes_more_severe_verdict(self):
        """Test merge uses the more severe verdict."""
        crew = {
            "findings": [],
            "quality_score": 90,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "request_changes",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["verdict"] == "request_changes"

    def test_merge_has_blocking_issues(self):
        """Test has_blocking_issues is set correctly."""
        crew = {
            "findings": [{"severity": "critical"}],
            "quality_score": 50,
            "verdict": "reject",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {"critical": 1}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["has_blocking_issues"] is True


# ===========================================================================
# 16. Adapter: _check_crew_available Tests
# ===========================================================================


@pytest.mark.unit
class TestCheckCrewAvailable:
    """Test _check_crew_available function."""

    def test_crew_available_returns_bool(self):
        """Test _check_crew_available returns a boolean."""
        from attune.workflows.code_review_adapters import _check_crew_available

        result = _check_crew_available()
        assert isinstance(result, bool)

    def test_crew_not_available_on_import_error(self):
        """Test returns False when CodeReviewCrew import fails."""
        import sys
        from unittest.mock import patch as _patch

        from attune.workflows.code_review_adapters import _check_crew_available

        # Temporarily make the import fail by blocking the module
        with _patch.dict(sys.modules, {"attune.agent_factory.crews": None}):
            result = _check_crew_available()
            assert result is False


# ===========================================================================
# 18. _get_crew_review Adapter Tests
# ===========================================================================


@pytest.mark.unit
class TestGetCrewReview:
    """Test the _get_crew_review adapter function."""

    @pytest.mark.asyncio
    async def test_get_crew_review_not_available(self):
        """Test returns None when crew not available."""
        import sys

        from attune.workflows.code_review_adapters import _get_crew_review

        with patch.dict(sys.modules, {"attune.agent_factory.crews": None}):
            result = await _get_crew_review(diff="test code")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_crew_review_timeout(self):
        """Test returns None on timeout."""
        import attune.workflows.code_review_adapters as adapters_mod

        mock_crew = MagicMock()

        async def slow_review(**kwargs):
            await asyncio.sleep(10)

        mock_crew.review = slow_review

        mock_crews_mod = MagicMock()
        mock_crews_mod.CodeReviewConfig.return_value = MagicMock()
        mock_crews_mod.CodeReviewCrew.return_value = mock_crew

        with patch.object(adapters_mod, "_check_crew_available", return_value=True):
            with patch.dict("sys.modules", {"attune.agent_factory.crews": mock_crews_mod}):
                result = await adapters_mod._get_crew_review(diff="code", timeout=0.01)
                assert result is None

    @pytest.mark.asyncio
    async def test_get_crew_review_exception(self):
        """Test returns None on unexpected exception."""
        import attune.workflows.code_review_adapters as adapters_mod

        with patch.object(adapters_mod, "_check_crew_available", return_value=True):
            # Make the inner import of CodeReviewConfig raise
            with patch.dict(
                "sys.modules",
                {"attune.agent_factory.crews": None},
            ):
                result = await adapters_mod._get_crew_review(diff="code")
                assert result is None


# ===========================================================================
# 24. Report Formatter - New Sections
# ===========================================================================


@pytest.mark.unit
class TestReportNewSections:
    """Tests for the new perf/health/quality sections in the report."""

    def test_report_includes_perf_section(self):
        """Test that report includes PERFORMANCE CHECK when perf data present."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {
            "perf_findings": [
                {
                    "type": "n_plus_one",
                    "file": "a.py",
                    "line": 10,
                    "description": "N+1 query",
                    "impact": "high",
                },
            ],
            "perf_finding_count": 1,
            "perf_by_impact": {"high": 1, "medium": 0, "low": 0},
        }
        report = format_code_review_report(result, input_data)
        assert "PERFORMANCE CHECK" in report
        assert "N+1 query" in report

    def test_report_includes_health_section(self):
        """Test that report includes HEALTH MONITOR when snapshot present."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {
            "health_snapshot": {
                "cache_stats": {"llm": {"hit_rate": 0.8}},
                "cost_today": {"total_cost": 0.05},
                "usage_stats_7d": {"total_calls": 42},
            },
        }
        report = format_code_review_report(result, input_data)
        assert "HEALTH MONITOR" in report
        assert "80%" in report
        assert "$0.05" in report
        assert "42" in report

    def test_report_includes_quality_section(self):
        """Test that report includes QUALITY CHECK when quality data present."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {
            "quality_findings": [
                {
                    "type": "bare_except",
                    "file": "a.py",
                    "line": 3,
                    "description": "Bare except",
                    "severity": "high",
                },
            ],
            "quality_finding_count": 1,
            "quality_by_severity": {"high": 1, "medium": 0, "low": 0},
        }
        report = format_code_review_report(result, input_data)
        assert "QUALITY CHECK" in report
        assert "Bare except" in report

    def test_report_shows_clean_perf(self):
        """Test that report shows clean message when no perf findings."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {
            "perf_findings": [],
            "perf_finding_count": 0,
            "perf_by_impact": {"high": 0, "medium": 0, "low": 0},
        }
        report = format_code_review_report(result, input_data)
        assert "PERFORMANCE CHECK" in report
        assert "No performance anti-patterns" in report

    def test_report_shows_clean_quality(self):
        """Test that report shows clean message when no quality findings."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {
            "quality_findings": [],
            "quality_finding_count": 0,
            "quality_by_severity": {"high": 0, "medium": 0, "low": 0},
        }
        report = format_code_review_report(result, input_data)
        assert "QUALITY CHECK" in report
        assert "No quality issues" in report


# ===========================================================================
# 25. Report Coverage Boost Tests
# ===========================================================================


@pytest.mark.unit
class TestReportCoverageBoost:
    """Tests to improve report formatter coverage (error path, security findings, arch review)."""

    def test_report_error_input_path(self):
        """Test report renders INPUT ERROR when error flag is set."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {"error": True, "error_message": "No code provided for review."}
        report = format_code_review_report(result, input_data)

        assert "INPUT ERROR" in report
        assert "No code provided for review." in report
        # Should NOT contain the normal sections
        assert "SECURITY ANALYSIS" not in report

    def test_report_error_input_default_message(self):
        """Test report uses default error message when none provided."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {"error": True}
        report = format_code_review_report(result, input_data)

        assert "INPUT ERROR" in report
        assert "No code provided for review." in report

    def test_report_security_findings_display(self):
        """Test report renders security findings with severity icons."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "request_changes", "model_tier_used": "capable"}
        input_data = {
            "has_critical_issues": True,
            "security_score": 60,
            "security_findings": [
                {"severity": "critical", "title": "SQL Injection in db.py"},
                {"severity": "high", "title": "XSS in template"},
                {"severity": "medium", "title": "Missing CSRF token"},
                {"severity": "low", "title": "Cookie without httponly"},
            ],
        }
        report = format_code_review_report(result, input_data)

        assert "SECURITY ANALYSIS" in report
        assert "60/100" in report
        assert "SQL Injection in db.py" in report
        assert "[CRITICAL]" in report
        assert "[HIGH]" in report
        assert "[MEDIUM]" in report
        assert "[LOW]" in report

    def test_report_architectural_review_section(self):
        """Test report renders architectural review text."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {
            "verdict": "approve_with_suggestions",
            "model_tier_used": "premium",
            "architectural_review": (
                "The code follows SOLID principles well. "
                "Consider extracting the validation logic."
            ),
            "recommendations": [
                "Extract validation into a separate module",
                "Add integration tests for the pipeline",
            ],
        }
        input_data = {}
        report = format_code_review_report(result, input_data)

        assert "ARCHITECTURAL REVIEW" in report
        assert "SOLID principles" in report
        assert "RECOMMENDATIONS" in report
        assert "1. Extract validation" in report
        assert "2. Add integration tests" in report

    def test_report_crew_review_section(self):
        """Test report renders crew review when available."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "capable"}
        input_data = {
            "crew_review": {
                "available": True,
                "fallback": False,
                "quality_score": 88,
                "finding_count": 3,
                "agents_used": ["review_lead", "security_agent"],
                "summary": "Minor quality improvements recommended.",
            },
        }
        report = format_code_review_report(result, input_data)

        assert "CREW REVIEW ANALYSIS" in report
        assert "88/100" in report
        assert "3" in report
        assert "review_lead, security_agent" in report
        assert "Minor quality improvements" in report

    def test_report_scan_results_truncation(self):
        """Test report truncates long scan results."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "capable"}
        long_scan = "X" * 1000
        input_data = {"scan_results": long_scan}
        report = format_code_review_report(result, input_data)

        assert "Scan Summary:" in report
        assert "..." in report

    def test_report_no_content_message(self):
        """Test report shows helpful message when no content sections present."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "unknown", "model_tier_used": "cheap"}
        input_data = {}
        report = format_code_review_report(result, input_data)

        assert "NO ISSUES FOUND" in report
        assert "No code was provided" in report

    def test_report_classification_section(self):
        """Test report renders classification summary."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "cheap"}
        input_data = {"classification": "Feature: Adding new API endpoint for user search"}
        report = format_code_review_report(result, input_data)

        assert "CLASSIFICATION" in report
        assert "Adding new API endpoint" in report


# ===========================================================================
# 26. Deep Stage Helper Functions
# ===========================================================================


@pytest.mark.unit
class TestDeepStageHelpers:
    """Test helper functions for deep analysis stages."""

    def test_gather_file_snippets_reads_context_lines(self, tmp_path):
        """Test _gather_file_snippets reads surrounding lines."""
        from attune.workflows.code_review import _gather_file_snippets

        test_file = tmp_path / "sample.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
        findings = [{"file": str(test_file), "line": 4}]
        snippets = _gather_file_snippets(findings, context_lines=2)

        assert str(test_file) in snippets
        assert 4 in snippets[str(test_file)]
        snippet_text = snippets[str(test_file)][4]
        assert "line2" in snippet_text
        assert "line4" in snippet_text
        assert "line6" in snippet_text

    def test_gather_file_snippets_missing_file_skipped(self):
        """Test _gather_file_snippets skips nonexistent files."""
        from attune.workflows.code_review import _gather_file_snippets

        findings = [{"file": "/nonexistent/file.py", "line": 10}]
        snippets = _gather_file_snippets(findings)
        assert snippets == {}

    def test_format_findings_for_prompt_structure(self):
        """Test _format_findings_for_prompt produces indexed output."""
        from attune.workflows.code_review import _format_findings_for_prompt

        findings = [
            {
                "file": "a.py",
                "line": 10,
                "type": "bare_except",
                "description": "Bare except",
                "severity": "high",
            },
            {
                "file": "b.py",
                "line": 20,
                "type": "todo_fixme",
                "description": "TODO found",
                "severity": "low",
            },
        ]
        result = _format_findings_for_prompt(findings, {})
        assert "[0]" in result
        assert "[1]" in result
        assert "bare_except" in result
        assert "todo_fixme" in result

    def test_parse_deep_enrichment_valid_json(self):
        """Test _parse_deep_enrichment parses valid JSON response."""
        from attune.workflows.code_review import _parse_deep_enrichment

        originals = [
            {"type": "bare_except", "severity": "high", "file": "a.py", "line": 10},
            {"type": "todo_fixme", "severity": "low", "file": "b.py", "line": 20},
        ]
        response = '{"findings": [{"index": 0, "validated": true, "false_positive": false, "suggestion": "Use specific exceptions"}, {"index": 1, "validated": true, "false_positive": true, "suggestion": "Test fixture"}]}'
        enriched = _parse_deep_enrichment(response, originals)

        assert len(enriched) == 2
        assert enriched[0]["validated"] is True
        assert enriched[0]["false_positive"] is False
        assert enriched[0]["suggestion"] == "Use specific exceptions"
        assert enriched[1]["false_positive"] is True

    def test_parse_deep_enrichment_malformed_json_returns_originals(self):
        """Test _parse_deep_enrichment handles malformed JSON gracefully."""
        from attune.workflows.code_review import _parse_deep_enrichment

        originals = [
            {"type": "bare_except", "severity": "high", "file": "a.py", "line": 10},
        ]
        response = "This is not valid JSON at all"
        enriched = _parse_deep_enrichment(response, originals)

        assert len(enriched) == 1
        assert enriched[0]["validated"] is True
        assert enriched[0]["false_positive"] is False
        # Original fields preserved
        assert enriched[0]["type"] == "bare_except"

    def test_recount_by_key_excludes_false_positives(self):
        """Test _recount_by_key excludes false positives from counts."""
        from attune.workflows.code_review import _recount_by_key

        findings = [
            {"severity": "high", "false_positive": False},
            {"severity": "high", "false_positive": True},
            {"severity": "medium", "false_positive": False},
            {"severity": "low", "false_positive": False},
        ]
        counts = _recount_by_key(findings, "severity")
        assert counts == {"high": 1, "medium": 1, "low": 1}
