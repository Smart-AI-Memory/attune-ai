"""Tests for security crew integration components.

Tests security adapters and SecureReleasePipeline. The
ReleasePreparationWorkflow is now SDK-native and no longer
supports crew_security stage injection.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock

import pytest

from attune.workflows.base import ModelTier

# ============================================================================
# Test Security Adapters (Foundation)
# ============================================================================


@pytest.mark.unit
class TestSecurityAdapters:
    """Test security adapter functions."""

    def test_check_crew_available_when_installed(self):
        """Test crew availability check when module exists."""
        from attune.workflows.security_adapters import _check_crew_available

        result = _check_crew_available()
        assert isinstance(result, bool)

    def test_crew_report_to_workflow_format(self):
        """Test converting SecurityReport to workflow format."""
        from attune.workflows.security_adapters import crew_report_to_workflow_format

        mock_report = MagicMock()
        mock_report.summary = "Found 2 issues"
        mock_report.risk_score = 45.0
        mock_report.audit_duration_seconds = 10.5
        mock_report.agents_used = ["lead", "hunter"]
        mock_report.memory_graph_hits = 0
        mock_report.metadata = {}

        mock_finding1 = MagicMock()
        mock_finding1.title = "SQL Injection"
        mock_finding1.description = "User input not sanitized"
        mock_finding1.severity = MagicMock(value="critical")
        mock_finding1.category = MagicMock(value="injection")
        mock_finding1.file_path = "src/api.py"
        mock_finding1.line_number = 42
        mock_finding1.code_snippet = "SELECT * FROM users"
        mock_finding1.remediation = "Use parameterized queries"
        mock_finding1.cwe_id = "CWE-89"
        mock_finding1.cvss_score = 9.8
        mock_finding1.confidence = 1.0

        mock_finding2 = MagicMock()
        mock_finding2.title = "XSS Vulnerability"
        mock_finding2.description = "Reflected XSS in search"
        mock_finding2.severity = MagicMock(value="high")
        mock_finding2.category = MagicMock(value="cross_site_scripting")
        mock_finding2.file_path = None
        mock_finding2.line_number = None
        mock_finding2.code_snippet = None
        mock_finding2.remediation = None
        mock_finding2.cwe_id = None
        mock_finding2.cvss_score = None
        mock_finding2.confidence = 0.9

        mock_report.findings = [mock_finding1, mock_finding2]

        result = crew_report_to_workflow_format(mock_report)

        assert result["summary"] == "Found 2 issues"
        assert result["risk_score"] == 45.0
        assert result["finding_count"] == 2
        assert len(result["findings"]) == 2
        assert result["crew_enabled"] is True
        assert len(result["assessment"]["critical_findings"]) == 1
        assert len(result["assessment"]["high_findings"]) == 1

    def test_workflow_findings_to_crew_format(self):
        """Test converting workflow findings to crew format."""
        from attune.workflows.security_adapters import workflow_findings_to_crew_format

        workflow_findings = [
            {
                "title": "Test Finding",
                "description": "Test description",
                "severity": "high",
                "category": "injection",
                "file": "test.py",
                "line": 10,
            },
        ]

        result = workflow_findings_to_crew_format(workflow_findings)

        assert len(result) == 1
        assert result[0]["title"] == "Test Finding"
        assert result[0]["severity"] == "high"
        assert result[0]["file_path"] == "test.py"

    def test_merge_security_results(self):
        """Test merging crew and workflow results."""
        from attune.workflows.security_adapters import merge_security_results

        crew_report = {
            "risk_score": 60.0,
            "findings": [
                {
                    "title": "Crew Finding",
                    "severity": "critical",
                    "type": "injection",
                    "file": "api.py",
                    "line": 10,
                },
            ],
            "assessment": {"risk_score": 60.0, "severity_breakdown": {"critical": 1}},
        }

        workflow_findings = {
            "risk_score": 40.0,
            "findings": [
                {
                    "title": "Workflow Finding",
                    "severity": "high",
                    "type": "xss",
                    "file": "view.py",
                    "line": 20,
                },
            ],
            "assessment": {"risk_score": 40.0, "severity_breakdown": {"high": 1}},
        }

        result = merge_security_results(crew_report, workflow_findings)

        assert len(result["findings"]) == 2
        assert result["risk_score"] >= 40.0
        assert result["merged"] is True
        assert result["crew_enabled"] is True

    def test_merge_security_results_crew_only(self):
        """Test merging with only crew results."""
        from attune.workflows.security_adapters import merge_security_results

        crew_report = {
            "risk_score": 75.0,
            "findings": [{"title": "Critical Issue", "severity": "critical"}],
            "crew_enabled": True,
        }

        result = merge_security_results(crew_report, None)

        assert result["risk_score"] == 75.0
        assert len(result["findings"]) == 1
        assert result["merged"] is False
        assert result["crew_enabled"] is True

    def test_merge_security_results_workflow_only(self):
        """Test merging with only workflow results."""
        from attune.workflows.security_adapters import merge_security_results

        workflow_findings = {
            "risk_score": 30.0,
            "findings": [{"title": "Minor Issue", "severity": "low"}],
        }

        result = merge_security_results(None, workflow_findings)

        assert result["risk_score"] == 30.0
        assert len(result["findings"]) == 1
        assert result["merged"] is False
        assert result["crew_enabled"] is False


# ============================================================================
# ReleasePreparationWorkflow — SDK-native validation
# ============================================================================


@pytest.mark.unit
class TestReleasePreparationSDKNative:
    """Test that ReleasePreparationWorkflow is SDK-native."""

    def test_workflow_is_sdk_native(self):
        """Test workflow has SDK-native attributes."""
        from attune.workflows import ReleasePreparationWorkflow

        wf = ReleasePreparationWorkflow()
        assert wf.name == "release-prep"
        assert wf.stages == ["agent-prep"]
        assert wf.tier_map == {"agent-prep": ModelTier.CAPABLE}
        assert "Agent SDK" in wf.description

    def test_no_crew_security_attribute(self):
        """Test workflow no longer has use_security_crew."""
        from attune.workflows import ReleasePreparationWorkflow

        wf = ReleasePreparationWorkflow()
        assert not hasattr(wf, "use_security_crew")


# ============================================================================
# SecureReleasePipeline composite workflow
# ============================================================================


@pytest.mark.unit
class TestSecureReleasePipeline:
    """Test SecureReleasePipeline composite workflow."""

    def test_pipeline_creation_modes(self):
        """Test pipeline creation with different modes."""
        from attune.workflows.secure_release import SecureReleasePipeline

        full = SecureReleasePipeline(mode="full")
        assert full.mode == "full"
        assert full.use_crew is True

        standard = SecureReleasePipeline(mode="standard")
        assert standard.mode == "standard"
        assert standard.use_crew is False

    def test_pipeline_factory_methods(self):
        """Test factory methods."""
        from attune.workflows.secure_release import SecureReleasePipeline

        pr = SecureReleasePipeline.for_pr_review(files_changed=5)
        assert pr.mode == "standard"

        pr_large = SecureReleasePipeline.for_pr_review(files_changed=15)
        assert pr_large.mode == "full"

        release = SecureReleasePipeline.for_release()
        assert release.mode == "full"
        assert release.crew_config.get("scan_depth") == "thorough"

    def test_result_dataclass(self):
        """Test SecureReleaseResult dataclass."""
        from attune.workflows.secure_release import SecureReleaseResult

        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            combined_risk_score=15.0,
            total_findings=2,
            critical_count=0,
            high_count=1,
            total_cost=0.05,
            total_duration_ms=5000,
            blockers=[],
            warnings=["Minor issue found"],
            recommendations=["Review before release"],
            mode="standard",
        )

        assert result.success is True
        assert result.go_no_go == "GO"

        data = result.to_dict()
        assert data["success"] is True
        assert data["go_no_go"] == "GO"
        assert data["combined_risk_score"] == 15.0

    def test_determine_go_no_go_logic(self):
        """Test go/no-go decision logic."""
        from attune.workflows.secure_release import SecureReleasePipeline

        pipeline = SecureReleasePipeline()

        go = pipeline._determine_go_no_go(20.0, {"critical": 1, "high": 0}, None)
        assert go == "NO_GO"

        go = pipeline._determine_go_no_go(80.0, {"critical": 0, "high": 0}, None)
        assert go == "NO_GO"

        go = pipeline._determine_go_no_go(40.0, {"critical": 0, "high": 5}, None)
        assert go == "CONDITIONAL"

        go = pipeline._determine_go_no_go(10.0, {"critical": 0, "high": 1}, None)
        assert go == "GO"

    def test_calculate_combined_risk(self):
        """Test combined risk calculation."""
        from attune.workflows.secure_release import SecureReleasePipeline

        pipeline = SecureReleasePipeline()

        risk = pipeline._calculate_combined_risk(None, None, None, None)
        assert risk == 0.0

        crew_report = {"risk_score": 50.0}
        risk = pipeline._calculate_combined_risk(crew_report, None, None, None)
        assert risk == 50.0


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestEndToEndIntegration:
    """Integration smoke tests."""

    def test_imports_work(self):
        """Test all exports are importable."""
        from attune.workflows.secure_release import SecureReleasePipeline, SecureReleaseResult
        from attune.workflows.security_adapters import _check_crew_available

        assert SecureReleasePipeline is not None
        assert SecureReleaseResult is not None
        assert _check_crew_available is not None

    def test_backward_compatibility(self):
        """Test existing workflows initialize with defaults."""
        from attune.workflows import (
            CodeReviewWorkflow,
            ReleasePreparationWorkflow,
            SecurityAuditWorkflow,
        )

        code_review = CodeReviewWorkflow()
        assert code_review is not None

        release_prep = ReleasePreparationWorkflow()
        assert release_prep is not None

        security_audit = SecurityAuditWorkflow()
        assert security_audit is not None
        assert security_audit.name == "security-audit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
