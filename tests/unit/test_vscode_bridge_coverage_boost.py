"""Comprehensive coverage tests for VSCode Bridge module.

Tests ReviewFinding, CodeReviewResult dataclasses, and bridge functions
that enable Claude Code CLI output to appear in VS Code webview panels.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import json
from pathlib import Path

import pytest

import attune.vscode_bridge as vscode_module

ReviewFinding = vscode_module.ReviewFinding
CodeReviewResult = vscode_module.CodeReviewResult
get_empathy_dir = vscode_module.get_empathy_dir
write_code_review_results = vscode_module.write_code_review_results
write_pr_review_results = vscode_module.write_pr_review_results
send_to_vscode = vscode_module.send_to_vscode


@pytest.mark.unit
class TestReviewFinding:
    """Test ReviewFinding dataclass."""

    def test_review_finding_creation_with_required_fields(self):
        """Test creating ReviewFinding with required fields only."""
        finding = ReviewFinding(
            id="F001",
            file="app.py",
            line=42,
            severity="high",
            category="security",
            message="SQL injection vulnerability detected",
        )

        assert finding.id == "F001"
        assert finding.file == "app.py"
        assert finding.line == 42
        assert finding.severity == "high"
        assert finding.category == "security"
        assert finding.message == "SQL injection vulnerability detected"

    def test_review_finding_creation_with_all_fields(self):
        """Test creating ReviewFinding with all fields."""
        finding = ReviewFinding(
            id="F002",
            file="utils.py",
            line=123,
            severity="medium",
            category="performance",
            message="Inefficient loop detected",
            column=5,
            details="Loop performs O(n²) operations",
            recommendation="Use set lookup for O(1) complexity",
        )

        assert finding.id == "F002"
        assert finding.column == 5
        assert finding.details == "Loop performs O(n²) operations"
        assert finding.recommendation == "Use set lookup for O(1) complexity"

    def test_review_finding_defaults(self):
        """Test that optional fields have correct defaults."""
        finding = ReviewFinding(
            id="F003",
            file="test.py",
            line=1,
            severity="low",
            category="style",
            message="Line too long",
        )

        assert finding.column == 1
        assert finding.details is None
        assert finding.recommendation is None

    def test_review_finding_severity_values(self):
        """Test different severity levels."""
        severities = ["critical", "high", "medium", "low", "info"]

        for sev in severities:
            finding = ReviewFinding(
                id=f"F-{sev}",
                file="test.py",
                line=1,
                severity=sev,
                category="correctness",
                message="Test message",
            )
            assert finding.severity == sev

    def test_review_finding_category_values(self):
        """Test different category values."""
        categories = [
            "security",
            "performance",
            "maintainability",
            "style",
            "correctness",
        ]

        for cat in categories:
            finding = ReviewFinding(
                id=f"F-{cat}",
                file="test.py",
                line=1,
                severity="medium",
                category=cat,
                message="Test message",
            )
            assert finding.category == cat


@pytest.mark.unit
class TestCodeReviewResult:
    """Test CodeReviewResult dataclass."""

    def test_code_review_result_creation(self):
        """Test creating CodeReviewResult with all fields."""
        findings = [
            {
                "id": "F001",
                "file": "app.py",
                "line": 42,
                "severity": "high",
                "category": "security",
                "message": "SQL injection",
            }
        ]
        summary = {
            "total_findings": 1,
            "by_severity": {"high": 1},
            "by_category": {"security": 1},
            "files_affected": ["app.py"],
        }

        result = CodeReviewResult(
            findings=findings,
            summary=summary,
            verdict="request_changes",
            security_score=65,
            formatted_report="# Review Report\n\nFound 1 issue",
            model_tier_used="capable",
            timestamp="2026-01-31T10:00:00",
        )

        assert result.findings == findings
        assert result.summary == summary
        assert result.verdict == "request_changes"
        assert result.security_score == 65
        assert result.formatted_report == "# Review Report\n\nFound 1 issue"
        assert result.model_tier_used == "capable"
        assert result.timestamp == "2026-01-31T10:00:00"

    def test_code_review_result_verdict_values(self):
        """Test different verdict values."""
        verdicts = [
            "approve",
            "approve_with_suggestions",
            "request_changes",
            "reject",
        ]

        for verdict in verdicts:
            result = CodeReviewResult(
                findings=[],
                summary={},
                verdict=verdict,
                security_score=85,
                formatted_report="",
                model_tier_used="cheap",
                timestamp="2026-01-31T10:00:00",
            )
            assert result.verdict == verdict


@pytest.mark.unit
class TestGetEmpathyDir:
    """Test get_empathy_dir function."""

    def test_get_empathy_dir_creates_directory(self, tmp_path, monkeypatch):
        """Test that get_empathy_dir creates .attune directory."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        empathy_dir = get_empathy_dir()

        assert empathy_dir == Path(".attune")
        assert empathy_dir.exists()
        assert empathy_dir.is_dir()

    def test_get_empathy_dir_returns_existing_directory(self, tmp_path, monkeypatch):
        """Test that get_empathy_dir works with existing directory."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create directory first
        (tmp_path / ".attune").mkdir()

        empathy_dir = get_empathy_dir()

        assert empathy_dir == Path(".attune")
        assert empathy_dir.exists()


@pytest.mark.unit
class TestWriteCodeReviewResults:
    """Test write_code_review_results function."""

    def test_write_code_review_results_minimal(self, tmp_path, monkeypatch):
        """Test writing code review results with minimal parameters."""
        monkeypatch.chdir(tmp_path)

        output_path = write_code_review_results()

        assert output_path == Path(".attune/code-review-results.json")
        assert output_path.exists()

        # Read and verify
        with open(output_path) as f:
            data = json.load(f)

        assert data["findings"] == []
        assert data["verdict"] == "approve_with_suggestions"
        assert data["security_score"] == 85
        assert data["formatted_report"] == ""
        assert data["model_tier_used"] == "capable"
        assert "timestamp" in data

    def test_write_code_review_results_with_findings(self, tmp_path, monkeypatch):
        """Test writing code review results with findings."""
        monkeypatch.chdir(tmp_path)

        findings = [
            {
                "id": "F001",
                "file": "app.py",
                "line": 42,
                "severity": "high",
                "category": "security",
                "message": "SQL injection vulnerability",
            },
            {
                "id": "F002",
                "file": "utils.py",
                "line": 10,
                "severity": "medium",
                "category": "performance",
                "message": "Inefficient algorithm",
            },
        ]

        output_path = write_code_review_results(
            findings=findings,
            verdict="request_changes",
            security_score=65,
            formatted_report="# Review\n\nFound 2 issues",
            model_tier_used="premium",
        )

        # Read and verify
        with open(output_path) as f:
            data = json.load(f)

        assert len(data["findings"]) == 2
        assert data["findings"][0]["id"] == "F001"
        assert data["findings"][1]["severity"] == "medium"
        assert data["verdict"] == "request_changes"
        assert data["security_score"] == 65
        assert data["model_tier_used"] == "premium"

    def test_write_code_review_results_builds_summary(self, tmp_path, monkeypatch):
        """Test that summary is automatically built from findings."""
        monkeypatch.chdir(tmp_path)

        findings = [
            {
                "id": "F001",
                "file": "app.py",
                "line": 42,
                "severity": "high",
                "category": "security",
                "message": "Issue 1",
            },
            {
                "id": "F002",
                "file": "app.py",
                "line": 50,
                "severity": "medium",
                "category": "performance",
                "message": "Issue 2",
            },
            {
                "id": "F003",
                "file": "utils.py",
                "line": 10,
                "severity": "high",
                "category": "security",
                "message": "Issue 3",
            },
        ]

        output_path = write_code_review_results(findings=findings)

        # Read and verify summary
        with open(output_path) as f:
            data = json.load(f)

        summary = data["summary"]
        assert summary["total_findings"] == 3
        assert summary["by_severity"] == {"high": 2, "medium": 1}
        assert summary["by_category"] == {"security": 2, "performance": 1}
        assert set(summary["files_affected"]) == {"app.py", "utils.py"}

    def test_write_code_review_results_with_custom_summary(self, tmp_path, monkeypatch):
        """Test that custom summary is used when provided."""
        monkeypatch.chdir(tmp_path)

        findings = [{"id": "F001", "file": "test.py", "line": 1}]
        custom_summary = {
            "total_findings": 999,
            "custom_field": "custom_value",
        }

        output_path = write_code_review_results(
            findings=findings,
            summary=custom_summary,
        )

        # Read and verify
        with open(output_path) as f:
            data = json.load(f)

        assert data["summary"]["total_findings"] == 999
        assert data["summary"]["custom_field"] == "custom_value"

    def test_write_code_review_results_handles_missing_fields(self, tmp_path, monkeypatch):
        """Test that missing fields in findings are handled gracefully."""
        monkeypatch.chdir(tmp_path)

        # Findings with missing optional fields
        findings = [
            {"id": "F001"},  # Missing severity, category, file
            {
                "id": "F002",
                "severity": "low",
            },  # Missing category, file
        ]

        output_path = write_code_review_results(findings=findings)

        # Should not crash, verify summary uses defaults
        with open(output_path) as f:
            data = json.load(f)

        summary = data["summary"]
        assert summary["total_findings"] == 2
        assert "info" in summary["by_severity"]  # Default severity
        assert "correctness" in summary["by_category"]  # Default category

    def test_write_code_review_results_different_model_tiers(self, tmp_path, monkeypatch):
        """Test writing results with different model tiers."""
        monkeypatch.chdir(tmp_path)

        for tier in ["cheap", "capable", "premium"]:
            output_path = write_code_review_results(model_tier_used=tier)

            with open(output_path) as f:
                data = json.load(f)

            assert data["model_tier_used"] == tier

    def test_write_code_review_results_timestamp_format(self, tmp_path, monkeypatch):
        """Test that timestamp is in ISO format."""
        monkeypatch.chdir(tmp_path)

        output_path = write_code_review_results()

        with open(output_path) as f:
            data = json.load(f)

        # Verify timestamp is ISO format (basic check)
        assert "T" in data["timestamp"]
        assert len(data["timestamp"]) > 10  # Should be full datetime


@pytest.mark.unit
class TestWritePRReviewResults:
    """Test write_pr_review_results function."""

    def test_write_pr_review_results_minimal(self, tmp_path, monkeypatch):
        """Test writing PR review results with minimal parameters."""
        monkeypatch.chdir(tmp_path)

        findings = [
            {
                "id": "F001",
                "file": "app.py",
                "line": 42,
                "severity": "high",
                "message": "Security issue",
            }
        ]

        output_path = write_pr_review_results(
            pr_number=123,
            title="Add new feature",
            findings=findings,
        )

        assert output_path.exists()

        # Read and verify
        with open(output_path) as f:
            data = json.load(f)

        assert data["findings"] == findings
        assert data["verdict"] == "approve_with_suggestions"
        assert data["model_tier_used"] == "capable"

    def test_write_pr_review_results_formatted_report(self, tmp_path, monkeypatch):
        """Test that PR review generates formatted report."""
        monkeypatch.chdir(tmp_path)

        findings = [
            {
                "id": "F001",
                "file": "app.py",
                "line": 42,
                "severity": "high",
                "message": "Security vulnerability",
            },
            {
                "id": "F002",
                "file": "utils.py",
                "line": 10,
                "severity": "medium",
                "message": "Code smell",
            },
        ]

        output_path = write_pr_review_results(
            pr_number=456,
            title="Fix authentication",
            findings=findings,
            summary_text="Found 2 issues that need attention",
        )

        # Read and verify
        with open(output_path) as f:
            data = json.load(f)

        report = data["formatted_report"]
        assert "PR #456: Fix authentication" in report
        assert "Found 2 issues that need attention" in report
        assert "Findings (2)" in report
        assert "HIGH" in report
        assert "app.py:42" in report
        assert "MEDIUM" in report
        assert "utils.py:10" in report

    def test_write_pr_review_results_with_verdict(self, tmp_path, monkeypatch):
        """Test writing PR review with different verdicts."""
        monkeypatch.chdir(tmp_path)

        findings = [{"id": "F001", "file": "test.py", "line": 1}]

        for verdict in ["approve", "request_changes", "reject"]:
            output_path = write_pr_review_results(
                pr_number=789,
                title="Test PR",
                findings=findings,
                verdict=verdict,
            )

            with open(output_path) as f:
                data = json.load(f)

            assert data["verdict"] == verdict

    def test_write_pr_review_results_string_pr_number(self, tmp_path, monkeypatch):
        """Test that PR number can be string or int."""
        monkeypatch.chdir(tmp_path)

        findings = []

        # String PR number
        output_path = write_pr_review_results(
            pr_number="PR-123",
            title="Test",
            findings=findings,
        )

        with open(output_path) as f:
            data = json.load(f)

        assert "PR-123" in data["formatted_report"]


@pytest.mark.unit
class TestSendToVSCode:
    """Test send_to_vscode convenience function."""

    def test_send_to_vscode_minimal(self, tmp_path, monkeypatch):
        """Test send_to_vscode with minimal parameters."""
        monkeypatch.chdir(tmp_path)

        result = send_to_vscode("Review complete")

        assert "Results written to" in result
        assert "code-review-results.json" in result
        assert "VS Code will update automatically" in result

        # Verify file was created
        output_path = Path(".attune/code-review-results.json")
        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["formatted_report"] == "Review complete"
        assert data["verdict"] == "approve_with_suggestions"

    def test_send_to_vscode_with_findings(self, tmp_path, monkeypatch):
        """Test send_to_vscode with findings."""
        monkeypatch.chdir(tmp_path)

        findings = [
            {
                "id": "F001",
                "file": "app.py",
                "line": 42,
                "severity": "critical",
                "message": "Critical issue",
            }
        ]

        result = send_to_vscode(
            message="Found critical issue",
            findings=findings,
            verdict="reject",
        )

        assert "Results written to" in result

        # Verify file
        output_path = Path(".attune/code-review-results.json")
        with open(output_path) as f:
            data = json.load(f)

        assert len(data["findings"]) == 1
        assert data["findings"][0]["severity"] == "critical"
        assert data["formatted_report"] == "Found critical issue"
        assert data["verdict"] == "reject"

    def test_send_to_vscode_empty_findings_list(self, tmp_path, monkeypatch):
        """Test send_to_vscode with empty findings list."""
        monkeypatch.chdir(tmp_path)

        send_to_vscode("All good", findings=[], verdict="approve")

        # Verify file
        output_path = Path(".attune/code-review-results.json")
        with open(output_path) as f:
            data = json.load(f)

        assert data["findings"] == []
        assert data["verdict"] == "approve"

    def test_send_to_vscode_returns_correct_path(self, tmp_path, monkeypatch):
        """Test that send_to_vscode returns correct path in message."""
        monkeypatch.chdir(tmp_path)

        result = send_to_vscode("Test message")

        # Extract path from message
        assert ".attune" in result
        assert "code-review-results.json" in result

        # Verify path exists
        extracted_path = result.split("to ")[1].split(" - ")[0]
        assert Path(extracted_path).exists()


@pytest.mark.unit
class TestIntegration:
    """Integration tests for vscode_bridge module."""

    def test_full_code_review_workflow(self, tmp_path, monkeypatch):
        """Test complete code review workflow."""
        monkeypatch.chdir(tmp_path)

        # Step 1: Create findings
        findings = [
            {
                "id": "SEC-001",
                "file": "api/auth.py",
                "line": 45,
                "severity": "critical",
                "category": "security",
                "message": "Hardcoded credentials detected",
                "column": 12,
                "details": "API key found in source code",
                "recommendation": "Use environment variables",
            },
            {
                "id": "PERF-001",
                "file": "api/handlers.py",
                "line": 123,
                "severity": "medium",
                "category": "performance",
                "message": "N+1 query detected",
                "column": 8,
                "details": "Loop makes individual DB queries",
                "recommendation": "Use batch query or JOIN",
            },
        ]

        # Step 2: Write review results
        output_path = write_code_review_results(
            findings=findings,
            verdict="request_changes",
            security_score=45,
            formatted_report="# Security Review\n\nFound critical issues",
            model_tier_used="premium",
        )

        # Step 3: Verify complete result
        with open(output_path) as f:
            data = json.load(f)

        # Verify all data is present
        assert len(data["findings"]) == 2
        assert data["summary"]["total_findings"] == 2
        assert data["summary"]["by_severity"] == {"critical": 1, "medium": 1}
        assert data["summary"]["by_category"] == {"security": 1, "performance": 1}
        assert set(data["summary"]["files_affected"]) == {
            "api/auth.py",
            "api/handlers.py",
        }
        assert data["verdict"] == "request_changes"
        assert data["security_score"] == 45
        assert "Security Review" in data["formatted_report"]
        assert data["model_tier_used"] == "premium"
        assert "timestamp" in data

    def test_full_pr_review_workflow(self, tmp_path, monkeypatch):
        """Test complete PR review workflow."""
        monkeypatch.chdir(tmp_path)

        findings = [
            {
                "id": "STYLE-001",
                "file": "README.md",
                "line": 1,
                "severity": "low",
                "category": "style",
                "message": "Missing description",
            }
        ]

        output_path = write_pr_review_results(
            pr_number=789,
            title="Update documentation",
            findings=findings,
            verdict="approve_with_suggestions",
            summary_text="Minor style improvements recommended",
        )

        # Verify result
        with open(output_path) as f:
            data = json.load(f)

        assert "PR #789" in data["formatted_report"]
        assert "Update documentation" in data["formatted_report"]
        assert "Minor style improvements" in data["formatted_report"]
        assert data["verdict"] == "approve_with_suggestions"
