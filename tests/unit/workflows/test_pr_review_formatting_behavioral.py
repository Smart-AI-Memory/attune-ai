"""Behavioral tests for PR review formatting module.

Tests format_pr_review_report() covering all report sections
including summary word-wrap, findings truncation, and score bars.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.pr_review_formatting import format_pr_review_report
from attune.workflows.pr_review_models import PRReviewResult


def _make_result(**overrides: object) -> PRReviewResult:
    """Build a PRReviewResult with sensible defaults."""
    defaults: dict = {
        "success": True,
        "verdict": "approve",
        "code_quality_score": 85.0,
        "security_risk_score": 10.0,
        "combined_score": 87.0,
        "code_review": None,
        "security_audit": None,
        "all_findings": [],
        "code_findings": [],
        "security_findings": [],
        "critical_count": 0,
        "high_count": 0,
        "blockers": [],
        "warnings": [],
        "recommendations": [],
        "summary": "",
        "agents_used": [],
        "duration_seconds": 1.5,
        "cost": 0.0123,
    }
    defaults.update(overrides)
    return PRReviewResult(**defaults)


@pytest.mark.unit
class TestFormatPrReviewReportVerdict:
    """Test verdict section formatting."""

    def test_approve_verdict_shows_check_emoji(self) -> None:
        """Given an approve verdict, report shows green check."""
        # Given
        result = _make_result(verdict="approve")
        # When
        report = format_pr_review_report(result)
        # Then
        assert "✅ VERDICT: APPROVE" in report

    def test_reject_verdict_shows_red_emoji(self) -> None:
        """Given a reject verdict, report shows red circle."""
        # Given
        result = _make_result(verdict="reject")
        # When
        report = format_pr_review_report(result)
        # Then
        assert "🔴 VERDICT: REJECT" in report

    def test_request_changes_replaces_underscores(self) -> None:
        """Given request_changes verdict, underscores become spaces."""
        # Given
        result = _make_result(verdict="request_changes")
        # When
        report = format_pr_review_report(result)
        # Then
        assert "REQUEST CHANGES" in report
        assert "REQUEST_CHANGES" not in report

    def test_unknown_verdict_shows_default_emoji(self) -> None:
        """Given an unknown verdict, report shows white circle."""
        # Given
        result = _make_result(verdict="custom_verdict")
        # When
        report = format_pr_review_report(result)
        # Then
        assert "⚪" in report


@pytest.mark.unit
class TestFormatPrReviewReportScores:
    """Test score bars and labels."""

    def test_code_quality_bar_reflects_score(self) -> None:
        """Given score of 80, bar should have 8 filled blocks."""
        # Given
        result = _make_result(code_quality_score=80.0)
        # When
        report = format_pr_review_report(result)
        # Then
        assert "Code Quality:" in report
        assert "80/100" in report

    def test_security_risk_low_label(self) -> None:
        """Given security risk < 30, label should be LOW."""
        # Given
        result = _make_result(security_risk_score=15.0)
        # When
        report = format_pr_review_report(result)
        # Then
        assert "(LOW)" in report

    def test_security_risk_medium_label(self) -> None:
        """Given security risk 30-59, label should be MEDIUM."""
        # Given
        result = _make_result(security_risk_score=45.0)
        # When
        report = format_pr_review_report(result)
        # Then
        assert "(MEDIUM)" in report

    def test_security_risk_high_label(self) -> None:
        """Given security risk >= 60, label should be HIGH."""
        # Given
        result = _make_result(security_risk_score=75.0)
        # When
        report = format_pr_review_report(result)
        # Then
        assert "(HIGH)" in report


@pytest.mark.unit
class TestFormatPrReviewReportSummary:
    """Test summary word-wrapping (lines 72-87)."""

    def test_short_summary_not_wrapped(self) -> None:
        """Given a short summary, it appears on one line."""
        # Given
        result = _make_result(summary="All good.")
        # When
        report = format_pr_review_report(result)
        # Then
        assert "SUMMARY" in report
        assert "All good." in report

    def test_long_summary_word_wraps(self) -> None:
        """Given a summary exceeding 58 chars, it wraps to next line."""
        # Given
        long_summary = "word " * 20  # 100 chars
        result = _make_result(summary=long_summary.strip())
        # When
        report = format_pr_review_report(result)
        # Then
        lines = report.split("\n")
        summary_idx = next(i for i, line in enumerate(lines) if line == "SUMMARY")
        # Lines between SUMMARY header and next blank should be <= 58 chars
        content_lines = []
        for line in lines[summary_idx + 2 :]:
            if line == "":
                break
            content_lines.append(line)
        assert len(content_lines) > 1  # Should have wrapped
        for cl in content_lines:
            assert len(cl) <= 58

    def test_empty_summary_omits_section(self) -> None:
        """Given empty summary, SUMMARY section is not shown."""
        # Given
        result = _make_result(summary="")
        # When
        report = format_pr_review_report(result)
        # Then
        assert "SUMMARY" not in report


@pytest.mark.unit
class TestFormatPrReviewReportBlockers:
    """Test blockers section (lines 90-96)."""

    def test_blockers_shown_with_header(self) -> None:
        """Given blockers, section header and items appear."""
        # Given
        result = _make_result(blockers=["Fix SQL injection", "Remove eval()"])
        # When
        report = format_pr_review_report(result)
        # Then
        assert "BLOCKERS" in report
        assert "Fix SQL injection" in report
        assert "Remove eval()" in report

    def test_no_blockers_omits_section(self) -> None:
        """Given no blockers, section is not shown."""
        # Given
        result = _make_result(blockers=[])
        # When
        report = format_pr_review_report(result)
        # Then
        assert "BLOCKERS" not in report


@pytest.mark.unit
class TestFormatPrReviewReportFindings:
    """Test findings section (lines 99-125)."""

    def test_findings_counts_displayed(self) -> None:
        """Given findings, counts for each severity shown."""
        # Given
        result = _make_result(
            all_findings=[{"severity": "high", "title": "Issue 1"}],
            code_findings=[{"severity": "high", "title": "Issue 1"}],
            security_findings=[],
            critical_count=0,
            high_count=1,
        )
        # When
        report = format_pr_review_report(result)
        # Then
        assert "Total: 1" in report
        assert "Critical: 0" in report
        assert "High: 1" in report

    def test_critical_findings_show_top_issues(self) -> None:
        """Given critical findings, top 5 shown with emoji."""
        # Given
        findings = [{"severity": "critical", "title": f"Critical bug {i}"} for i in range(7)]
        result = _make_result(
            all_findings=findings,
            critical_count=7,
            high_count=0,
        )
        # When
        report = format_pr_review_report(result)
        # Then
        assert "Top Issues:" in report
        assert "Critical bug 0" in report
        assert "Critical bug 4" in report
        assert "and 2 more critical/high issues" in report

    def test_long_finding_title_truncated(self) -> None:
        """Given a finding title > 50 chars, it gets truncated."""
        # Given
        long_title = "A" * 60
        findings = [{"severity": "critical", "title": long_title}]
        result = _make_result(
            all_findings=findings,
            critical_count=1,
        )
        # When
        report = format_pr_review_report(result)
        # Then
        assert "..." in report
        # Original 60-char title should not appear in full
        assert long_title not in report

    def test_finding_uses_message_fallback(self) -> None:
        """Given finding without title, falls back to message."""
        # Given
        findings = [{"severity": "high", "message": "Fallback msg"}]
        result = _make_result(
            all_findings=findings,
            high_count=1,
        )
        # When
        report = format_pr_review_report(result)
        # Then
        assert "Fallback msg" in report

    def test_no_findings_omits_section(self) -> None:
        """Given no findings, FINDINGS section is not shown."""
        # Given
        result = _make_result(all_findings=[])
        # When
        report = format_pr_review_report(result)
        # Then
        assert "FINDINGS" not in report


@pytest.mark.unit
class TestFormatPrReviewReportWarnings:
    """Test warnings section."""

    def test_warnings_displayed(self) -> None:
        """Given warnings, they appear in the report."""
        # Given
        result = _make_result(warnings=["Complexity is high"])
        # When
        report = format_pr_review_report(result)
        # Then
        assert "WARNINGS" in report
        assert "Complexity is high" in report

    def test_no_warnings_omits_section(self) -> None:
        """Given no warnings, WARNINGS section is not shown."""
        # Given
        result = _make_result(warnings=[])
        # When
        report = format_pr_review_report(result)
        # Then
        assert "WARNINGS" not in report


@pytest.mark.unit
class TestFormatPrReviewReportRecommendations:
    """Test recommendations section (lines 137-147)."""

    def test_recommendations_numbered(self) -> None:
        """Given recommendations, they are numbered."""
        # Given
        result = _make_result(
            recommendations=["Add tests", "Fix lint", "Update docs"],
        )
        # When
        report = format_pr_review_report(result)
        # Then
        assert "1. Add tests" in report
        assert "2. Fix lint" in report
        assert "3. Update docs" in report

    def test_more_than_five_shows_overflow(self) -> None:
        """Given > 5 recommendations, overflow count shown."""
        # Given
        recs = [f"Rec {i}" for i in range(8)]
        result = _make_result(recommendations=recs)
        # When
        report = format_pr_review_report(result)
        # Then
        assert "and 3 more" in report
        # Only first 5 shown
        assert "5. Rec 4" in report
        assert "6." not in report

    def test_long_recommendation_truncated(self) -> None:
        """Given a recommendation > 55 chars, it gets truncated."""
        # Given
        long_rec = "X" * 60
        result = _make_result(recommendations=[long_rec])
        # When
        report = format_pr_review_report(result)
        # Then
        assert "..." in report
        assert long_rec not in report


@pytest.mark.unit
class TestFormatPrReviewReportFooter:
    """Test footer with duration and cost."""

    def test_footer_shows_duration_in_ms(self) -> None:
        """Given duration_seconds, footer shows milliseconds."""
        # Given
        result = _make_result(duration_seconds=2.5, cost=0.0456)
        # When
        report = format_pr_review_report(result)
        # Then
        assert "2500ms" in report
        assert "$0.0456" in report

    def test_agents_used_listed(self) -> None:
        """Given agents_used, they appear comma-separated."""
        # Given
        result = _make_result(agents_used=["code_reviewer", "security_auditor"])
        # When
        report = format_pr_review_report(result)
        # Then
        assert "AGENTS USED" in report
        assert "code_reviewer, security_auditor" in report
