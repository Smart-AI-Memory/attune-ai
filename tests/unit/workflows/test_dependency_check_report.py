"""Tests for dependency_check_report module — format_dependency_check_report."""

from __future__ import annotations

from attune.workflows.dependency_check_report import format_dependency_check_report


def _base_result(**overrides):
    """Build a minimal result dict with sensible defaults."""
    base = {
        "risk_score": 0,
        "total_dependencies": 0,
        "summary": {},
        "vulnerability_count": 0,
        "outdated_count": 0,
        "recommendations": [],
        "security_report": "",
        "model_tier_used": "capable",
    }
    base.update(overrides)
    return base


def _base_input(**overrides):
    """Build a minimal input_data dict with sensible defaults."""
    base = {
        "python_count": 0,
        "node_count": 0,
        "files_found": [],
        "assessment": {},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Risk level classification
# ---------------------------------------------------------------------------


class TestRiskLevelClassification:
    """Risk icons and text based on risk_score thresholds."""

    def test_critical_risk_score_75(self):
        report = format_dependency_check_report(_base_result(risk_score=75), _base_input())
        assert "CRITICAL" in report

    def test_high_risk_score_50(self):
        report = format_dependency_check_report(_base_result(risk_score=50), _base_input())
        assert "HIGH RISK" in report

    def test_medium_risk_score_25(self):
        report = format_dependency_check_report(_base_result(risk_score=25), _base_input())
        assert "MEDIUM RISK" in report

    def test_low_risk_score_0(self):
        report = format_dependency_check_report(_base_result(risk_score=0), _base_input())
        assert "LOW RISK" in report


# ---------------------------------------------------------------------------
# Inventory section
# ---------------------------------------------------------------------------


class TestInventorySection:
    """Dependency inventory rendering."""

    def test_shows_total_dependencies(self):
        report = format_dependency_check_report(_base_result(total_dependencies=42), _base_input())
        assert "Total Dependencies: 42" in report

    def test_shows_python_count(self):
        report = format_dependency_check_report(_base_result(), _base_input(python_count=10))
        assert "Python: 10" in report

    def test_shows_node_count(self):
        report = format_dependency_check_report(_base_result(), _base_input(node_count=5))
        assert "Node.js: 5" in report

    def test_shows_files_found(self):
        report = format_dependency_check_report(
            _base_result(),
            _base_input(files_found=["requirements.txt", "package.json"]),
        )
        assert "Files Scanned: 2" in report
        assert "requirements.txt" in report

    def test_files_found_truncated_to_5(self):
        files = [f"file{i}.txt" for i in range(8)]
        report = format_dependency_check_report(_base_result(), _base_input(files_found=files))
        assert "file4.txt" in report
        assert "file5.txt" not in report

    def test_omits_python_count_when_zero(self):
        report = format_dependency_check_report(_base_result(), _base_input(python_count=0))
        assert "Python:" not in report


# ---------------------------------------------------------------------------
# Security findings section
# ---------------------------------------------------------------------------


class TestSecurityFindings:
    """Vulnerability count and severity breakdown."""

    def test_vulnerability_count(self):
        report = format_dependency_check_report(_base_result(vulnerability_count=5), _base_input())
        assert "Vulnerabilities: 5" in report

    def test_severity_breakdown(self):
        report = format_dependency_check_report(
            _base_result(summary={"critical": 2, "high": 1, "medium": 3}),
            _base_input(),
        )
        assert "Critical: 2" in report
        assert "High: 1" in report
        assert "Medium: 3" in report

    def test_outdated_count(self):
        report = format_dependency_check_report(_base_result(outdated_count=7), _base_input())
        assert "Outdated Packages: 7" in report


# ---------------------------------------------------------------------------
# Vulnerability details
# ---------------------------------------------------------------------------


class TestVulnerabilityDetails:
    """Vulnerable packages detail section."""

    def test_renders_vulnerability_entries(self):
        vulns = [
            {
                "severity": "critical",
                "package": "requests",
                "current_version": "2.20.0",
                "cve": "CVE-2023-001",
            },
        ]
        report = format_dependency_check_report(
            _base_result(),
            _base_input(assessment={"vulnerabilities": vulns}),
        )
        assert "VULNERABLE PACKAGES" in report
        assert "requests@2.20.0" in report
        assert "CVE-2023-001" in report

    def test_truncates_at_10_vulns(self):
        vulns = [
            {"severity": "medium", "package": f"pkg{i}", "current_version": "1.0", "cve": "N/A"}
            for i in range(15)
        ]
        report = format_dependency_check_report(
            _base_result(),
            _base_input(assessment={"vulnerabilities": vulns}),
        )
        assert "... and 5 more" in report

    def test_no_section_when_no_vulns(self):
        report = format_dependency_check_report(_base_result(), _base_input())
        assert "VULNERABLE PACKAGES" not in report


# ---------------------------------------------------------------------------
# Recommendations section
# ---------------------------------------------------------------------------


class TestRecommendations:
    """Remediation actions section."""

    def test_renders_recommendations(self):
        recs = [
            {"priority": 1, "package": "flask", "suggestion": "Upgrade to 3.0"},
            {"priority": 2, "package": "django", "suggestion": "Review config"},
        ]
        report = format_dependency_check_report(_base_result(recommendations=recs), _base_input())
        assert "REMEDIATION ACTIONS" in report
        assert "URGENT" in report
        assert "flask" in report

    def test_no_section_when_no_recs(self):
        report = format_dependency_check_report(_base_result(recommendations=[]), _base_input())
        assert "REMEDIATION ACTIONS" not in report

    def test_low_priority_label(self):
        recs = [
            {"priority": 99, "package": "x", "suggestion": "Optional"},
        ]
        report = format_dependency_check_report(_base_result(recommendations=recs), _base_input())
        assert "LOW" in report


# ---------------------------------------------------------------------------
# Security report (LLM analysis)
# ---------------------------------------------------------------------------


class TestSecurityReport:
    """LLM-generated detailed analysis section."""

    def test_renders_when_present(self):
        report = format_dependency_check_report(
            _base_result(security_report="Detailed analysis here."),
            _base_input(),
        )
        assert "DETAILED ANALYSIS" in report
        assert "Detailed analysis here." in report

    def test_skips_simulated_reports(self):
        report = format_dependency_check_report(
            _base_result(security_report="[Simulated] placeholder"),
            _base_input(),
        )
        assert "DETAILED ANALYSIS" not in report

    def test_truncates_long_reports(self):
        long_text = "A" * 2000
        report = format_dependency_check_report(
            _base_result(security_report=long_text),
            _base_input(),
        )
        assert "..." in report
        # The truncated text should be 1500 chars + "..."
        assert "A" * 1500 in report


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------


class TestFooter:
    """Report footer with model tier."""

    def test_footer_shows_model_tier(self):
        report = format_dependency_check_report(
            _base_result(model_tier_used="premium", total_dependencies=10),
            _base_input(),
        )
        assert "premium" in report
        assert "10 dependencies" in report
