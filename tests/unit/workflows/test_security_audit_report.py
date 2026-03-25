"""Tests for security_audit_report module — format_security_report."""

from __future__ import annotations

from attune.workflows.security_audit_report import format_security_report


def _base_output(**overrides):
    """Build a minimal workflow output dict."""
    base = {
        "assessment": {
            "risk_level": "low",
            "risk_score": 10,
            "severity_breakdown": {},
        },
        "files_scanned": 0,
        "needs_review": [],
        "accepted_risks": [],
        "remediation_plan": "",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Header section
# ---------------------------------------------------------------------------


class TestHeader:
    """Header with risk level and score."""

    def test_risk_level_uppercase(self):
        report = format_security_report(
            _base_output(
                assessment={"risk_level": "high", "risk_score": 70, "severity_breakdown": {}}
            )
        )
        assert "Risk Level: HIGH" in report
        assert "Risk Score: 70/100" in report

    def test_report_title(self):
        report = format_security_report(_base_output())
        assert "SECURITY AUDIT REPORT" in report


# ---------------------------------------------------------------------------
# Severity breakdown
# ---------------------------------------------------------------------------


class TestSeverityBreakdown:
    """Severity summary section."""

    def test_all_severity_levels(self):
        breakdown = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        output = _base_output(
            assessment={"risk_level": "high", "risk_score": 80, "severity_breakdown": breakdown}
        )
        report = format_security_report(output)
        assert "Critical: 1" in report
        assert "High: 2" in report
        assert "Medium: 3" in report
        assert "Low: 4" in report

    def test_defaults_to_zero_for_missing_severities(self):
        output = _base_output(
            assessment={"risk_level": "low", "risk_score": 5, "severity_breakdown": {}}
        )
        report = format_security_report(output)
        assert "Critical: 0" in report
        assert "High: 0" in report


# ---------------------------------------------------------------------------
# Files scanned
# ---------------------------------------------------------------------------


class TestFilesScanned:
    """Files scanned count."""

    def test_shows_file_count(self):
        report = format_security_report(_base_output(files_scanned=150))
        assert "Files Scanned: 150" in report


# ---------------------------------------------------------------------------
# Findings requiring review
# ---------------------------------------------------------------------------


class TestNeedsReview:
    """Findings requiring review section."""

    def test_renders_finding_details(self):
        findings = [
            {
                "severity": "high",
                "type": "sql_injection",
                "file": "project/Empathy-framework/src/db.py",
                "line": 42,
                "match": "cursor.execute(query)",
                "owasp": "A03:2021",
                "is_test": False,
                "analysis": "User input not sanitized",
            },
        ]
        report = format_security_report(_base_output(needs_review=findings))
        assert "FINDINGS REQUIRING REVIEW" in report
        assert "[HIGH]" in report
        assert "sql_injection" in report
        assert "src/db.py:42" in report
        assert "cursor.execute(query)" in report
        assert "A03:2021" in report
        assert "User input not sanitized" in report

    def test_test_file_marker(self):
        findings = [
            {
                "severity": "medium",
                "type": "eval_usage",
                "file": "test_foo.py",
                "line": 10,
                "match": "eval(x)",
                "owasp": "",
                "is_test": True,
                "analysis": "",
            },
        ]
        report = format_security_report(_base_output(needs_review=findings))
        assert "[TEST FILE]" in report

    def test_no_section_when_empty(self):
        report = format_security_report(_base_output(needs_review=[]))
        assert "FINDINGS REQUIRING REVIEW" not in report

    def test_strips_empathy_framework_path_prefix(self):
        findings = [
            {
                "severity": "low",
                "type": "info_leak",
                "file": "/full/path/Empathy-framework/src/api.py",
                "line": 5,
                "match": "print(secret)",
                "owasp": "",
                "is_test": False,
                "analysis": "",
            },
        ]
        report = format_security_report(_base_output(needs_review=findings))
        assert "src/api.py:5" in report

    def test_analysis_omitted_when_empty(self):
        findings = [
            {
                "severity": "medium",
                "type": "xss",
                "file": "app.py",
                "line": 1,
                "match": "render(html)",
                "owasp": "",
                "is_test": False,
                "analysis": "",
            },
        ]
        report = format_security_report(_base_output(needs_review=findings))
        assert "Analysis:" not in report

    def test_match_truncated_to_50_chars(self):
        long_match = "A" * 80
        findings = [
            {
                "severity": "low",
                "type": "test",
                "file": "x.py",
                "line": 1,
                "match": long_match,
                "owasp": "",
                "is_test": False,
                "analysis": "",
            },
        ]
        report = format_security_report(_base_output(needs_review=findings))
        # The match line should contain at most 50 chars of the match
        match_lines = [line for line in report.split("\n") if "Match:" in line]
        assert len(match_lines) == 1
        match_value = match_lines[0].split("Match: ")[1]
        assert len(match_value) == 50


# ---------------------------------------------------------------------------
# Accepted risks
# ---------------------------------------------------------------------------


class TestAcceptedRisks:
    """Accepted risks section."""

    def test_renders_accepted_risks(self):
        accepted = [
            {
                "type": "hardcoded_secret",
                "file": "project/Empathy-framework/tests/conftest.py",
                "line": 10,
                "decision_reason": "Test fixture only",
            },
        ]
        report = format_security_report(_base_output(accepted_risks=accepted))
        assert "ACCEPTED RISKS" in report
        assert "hardcoded_secret" in report
        assert "Test fixture only" in report

    def test_no_section_when_empty(self):
        report = format_security_report(_base_output(accepted_risks=[]))
        assert "ACCEPTED RISKS" not in report

    def test_reason_omitted_when_empty(self):
        accepted = [
            {"type": "test", "file": "x.py", "line": 1, "decision_reason": ""},
        ]
        report = format_security_report(_base_output(accepted_risks=accepted))
        assert "Reason:" not in report


# ---------------------------------------------------------------------------
# Remediation plan
# ---------------------------------------------------------------------------


class TestRemediationPlan:
    """Remediation plan section."""

    def test_renders_when_present(self):
        report = format_security_report(_base_output(remediation_plan="Step 1: Fix SQL injection"))
        assert "REMEDIATION PLAN" in report
        assert "Step 1: Fix SQL injection" in report

    def test_no_section_when_empty(self):
        report = format_security_report(_base_output(remediation_plan=""))
        assert "REMEDIATION PLAN" not in report

    def test_no_section_when_whitespace_only(self):
        report = format_security_report(_base_output(remediation_plan="   "))
        assert "REMEDIATION PLAN" not in report


# ---------------------------------------------------------------------------
# Footer / action items
# ---------------------------------------------------------------------------


class TestFooter:
    """Footer section with action items."""

    def test_action_required_when_findings_exist(self):
        findings = [
            {
                "severity": "high",
                "type": "x",
                "file": "a.py",
                "line": 1,
                "match": "",
                "owasp": "",
                "is_test": False,
                "analysis": "",
            },
        ]
        report = format_security_report(_base_output(needs_review=findings))
        assert "ACTION REQUIRED:" in report
        assert "Review 1 finding(s)" in report

    def test_all_clear_when_no_findings(self):
        report = format_security_report(_base_output(needs_review=[]))
        assert "All clear" in report
