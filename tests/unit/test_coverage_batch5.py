"""Comprehensive tests for secure_release, output, and parsing_mixin.

Targets maximum statement coverage for three low-coverage modules:
- src/attune/workflows/secure_release.py
- src/attune/workflows/output.py
- src/attune/workflows/parsing_mixin.py

All LLM calls and external dependencies are mocked.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import WorkflowResult for secure_release tests
from attune.workflows.data_classes import CostReport, WorkflowResult
from attune.workflows.parsing_mixin import ResponseParsingMixin
from attune.workflows.secure_release import (
    SecureReleasePipeline,
    SecureReleaseResult,
    format_secure_release_report,
)

# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def cost_tracker(tmp_path: Path) -> Any:
    """Create isolated CostTracker for testing.

    Args:
        tmp_path: pytest temporary directory

    Returns:
        CostTracker instance with isolated storage

    """
    from attune.cost_tracker import CostTracker

    storage_dir = tmp_path / ".empathy"
    return CostTracker(storage_dir=str(storage_dir))


def _make_cost_report(
    total_cost: float = 0.01,
    baseline_cost: float = 0.05,
) -> CostReport:
    """Create a CostReport for testing.

    Args:
        total_cost: Total cost value
        baseline_cost: Baseline cost value

    Returns:
        CostReport instance

    """
    return CostReport(
        total_cost=total_cost,
        baseline_cost=baseline_cost,
        savings=baseline_cost - total_cost,
        savings_percent=(
            ((baseline_cost - total_cost) / baseline_cost * 100) if baseline_cost else 0.0
        ),
    )


def _make_workflow_result(
    success: bool = True,
    final_output: dict | None = None,
    total_cost: float = 0.01,
    metadata: dict | None = None,
) -> WorkflowResult:
    """Create a WorkflowResult for testing.

    Args:
        success: Whether the workflow succeeded
        final_output: The final output dict
        total_cost: Total cost of the workflow

    Returns:
        WorkflowResult instance

    """
    now = datetime.now()
    return WorkflowResult(
        success=success,
        stages=[],
        final_output=final_output or {},
        cost_report=_make_cost_report(total_cost=total_cost),
        started_at=now,
        completed_at=now,
        total_duration_ms=100,
        metadata=metadata or {},
    )


# ============================================================================
# SecureReleaseResult Tests
# ============================================================================


@pytest.mark.unit
class TestSecureReleaseResult:
    """Tests for SecureReleaseResult dataclass."""

    def test_create_default(self) -> None:
        """Test creating SecureReleaseResult with defaults."""
        result = SecureReleaseResult(success=True, go_no_go="GO")
        assert result.success is True
        assert result.go_no_go == "GO"
        assert result.total_cost == 0.0
        assert result.blockers == []
        assert result.warnings == []
        assert result.recommendations == []
        assert result.mode == "full"

    def test_to_dict(self) -> None:
        """Test to_dict conversion."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            combined_risk_score=15.5,
            total_findings=3,
            critical_count=0,
            high_count=1,
            total_cost=0.05,
            total_duration_ms=2500,
            blockers=[],
            warnings=["Minor issue"],
            recommendations=["Review later"],
            mode="standard",
            crew_enabled=False,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["go_no_go"] == "GO"
        assert d["combined_risk_score"] == 15.5
        assert d["total_findings"] == 3
        assert d["warnings"] == ["Minor issue"]
        assert d["mode"] == "standard"

    def test_formatted_report_property(self) -> None:
        """Test formatted_report property returns report string."""
        result = SecureReleaseResult(success=True, go_no_go="GO")
        report = result.formatted_report
        assert "SECURE RELEASE REPORT" in report
        assert "GO" in report


# ============================================================================
# SecureReleasePipeline Initialization Tests
# ============================================================================


@pytest.mark.unit
class TestSecureReleasePipelineInit:
    """Tests for SecureReleasePipeline initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        pipeline = SecureReleasePipeline()
        assert pipeline.mode == "full"
        assert pipeline.use_crew is True
        assert pipeline.parallel_crew is True

    def test_standard_mode(self) -> None:
        """Test standard mode initialization."""
        pipeline = SecureReleasePipeline(mode="standard")
        assert pipeline.mode == "standard"
        assert pipeline.use_crew is False

    def test_use_crew_override(self) -> None:
        """Test explicit use_crew override."""
        pipeline = SecureReleasePipeline(mode="standard", use_crew=True)
        assert pipeline.use_crew is True

    def test_invalid_mode_raises(self) -> None:
        """Test invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid mode"):
            SecureReleasePipeline(mode="invalid")

    def test_crew_config_passed(self) -> None:
        """Test crew_config is stored."""
        config = {"scan_depth": "deep"}
        pipeline = SecureReleasePipeline(crew_config=config)
        assert pipeline.crew_config == config

    def test_for_pr_review_factory_small(self) -> None:
        """Test for_pr_review factory with small change set."""
        pipeline = SecureReleasePipeline.for_pr_review(files_changed=5)
        assert pipeline.mode == "standard"

    def test_for_pr_review_factory_large(self) -> None:
        """Test for_pr_review factory with large change set."""
        pipeline = SecureReleasePipeline.for_pr_review(files_changed=15)
        assert pipeline.mode == "full"

    def test_for_release_factory(self) -> None:
        """Test for_release factory."""
        pipeline = SecureReleasePipeline.for_release()
        assert pipeline.mode == "full"
        assert pipeline.crew_config == {"scan_depth": "thorough"}


# ============================================================================
# SecureReleasePipeline Helper Method Tests
# ============================================================================


@pytest.mark.unit
class TestSecureReleasePipelineHelpers:
    """Tests for SecureReleasePipeline internal methods."""

    def test_calculate_combined_risk_with_crew(self) -> None:
        """Test combined risk calculation with crew report."""
        pipeline = SecureReleasePipeline()
        crew_report = {"risk_score": 60}
        security_result = _make_workflow_result(
            final_output={"_type": "WorkflowReport", "score": 60}
        )
        score = pipeline._calculate_combined_risk(crew_report, security_result, None, None)
        # crew: 60 * 1.5 = 90, security: 40 * 1.0 = 40
        # total_weight = 2.5, weighted_sum = 130
        # result = 130 / 2.5 = 52.0
        assert score == pytest.approx(52.0)

    def test_calculate_combined_risk_empty(self) -> None:
        """Test combined risk with no sources."""
        pipeline = SecureReleasePipeline()
        score = pipeline._calculate_combined_risk(None, None, None, None)
        assert score == 0.0

    def test_calculate_combined_risk_with_code_review(self) -> None:
        """Test combined risk with code review results."""
        pipeline = SecureReleasePipeline()
        code_review = _make_workflow_result(final_output={"_type": "WorkflowReport", "score": 80})
        score = pipeline._calculate_combined_risk(None, None, code_review, None)
        # security_score=80 -> risk = 100 - 80 = 20
        # 20 * 0.8 / 0.8 = 20.0
        assert score == pytest.approx(20.0)

    def test_calculate_combined_risk_clamps_to_100(self) -> None:
        """Test combined risk never exceeds 100."""
        pipeline = SecureReleasePipeline()
        crew_report = {"risk_score": 100}
        security_result = _make_workflow_result(
            final_output={"_type": "WorkflowReport", "score": 0}
        )
        score = pipeline._calculate_combined_risk(crew_report, security_result, None, None)
        assert score <= 100.0

    def test_aggregate_findings_with_crew(self) -> None:
        """Test finding aggregation with crew report."""
        pipeline = SecureReleasePipeline()
        crew_report = {
            "assessment": {
                "critical_findings": [{"title": "RCE"}],
                "high_findings": [{"title": "XSS"}, {"title": "CSRF"}],
            },
            "finding_count": 5,
        }
        findings = pipeline._aggregate_findings(crew_report, None, None)
        assert findings["critical"] == 1
        assert findings["high"] == 2
        assert findings["total"] == 5

    def test_aggregate_findings_with_security_result(self) -> None:
        """Test finding aggregation with security result."""
        pipeline = SecureReleasePipeline()
        security_result = _make_workflow_result(
            final_output={"_type": "WorkflowReport", "score": 20},
            metadata={
                "findings": {
                    "CRITICAL": ["c1", "c2"],
                    "HIGH": ["h1", "h2", "h3"],
                    "MEDIUM": ["m1", "m2", "m3", "m4", "m5"],
                },
            },
        )
        findings = pipeline._aggregate_findings(None, security_result, None)
        assert findings["critical"] == 2
        assert findings["high"] == 3
        assert findings["total"] == 10

    def test_aggregate_findings_with_code_review_critical(self) -> None:
        """Test finding aggregation marks critical when code review has them."""
        pipeline = SecureReleasePipeline()
        code_review = _make_workflow_result(
            final_output={"score": 40}, metadata={"findings": {"CRITICAL": ["c1"]}}
        )
        findings = pipeline._aggregate_findings(None, None, code_review)
        assert findings["critical"] >= 1

    def test_aggregate_findings_empty(self) -> None:
        """Test finding aggregation with no sources."""
        pipeline = SecureReleasePipeline()
        findings = pipeline._aggregate_findings(None, None, None)
        assert findings == {"critical": 0, "high": 0, "total": 0}

    def test_determine_go_no_go_critical(self) -> None:
        """Test NO_GO when critical findings present."""
        pipeline = SecureReleasePipeline()
        result = pipeline._determine_go_no_go(
            risk_score=10.0,
            findings={"critical": 1, "high": 0, "total": 1},
            release_result=None,
        )
        assert result == "NO_GO"

    def test_determine_go_no_go_high_risk(self) -> None:
        """Test NO_GO when risk is very high."""
        pipeline = SecureReleasePipeline()
        result = pipeline._determine_go_no_go(
            risk_score=80.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=None,
        )
        assert result == "NO_GO"

    def test_determine_go_no_go_conditional_high_findings(self) -> None:
        """Test CONDITIONAL when many high findings."""
        pipeline = SecureReleasePipeline()
        result = pipeline._determine_go_no_go(
            risk_score=30.0,
            findings={"critical": 0, "high": 5, "total": 5},
            release_result=None,
        )
        assert result == "CONDITIONAL"

    def test_determine_go_no_go_conditional_risk(self) -> None:
        """Test CONDITIONAL when risk is moderate."""
        pipeline = SecureReleasePipeline()
        result = pipeline._determine_go_no_go(
            risk_score=55.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=None,
        )
        assert result == "CONDITIONAL"

    def test_determine_go_no_go_conditional_release_not_approved(self) -> None:
        """Test CONDITIONAL when release is not approved."""
        pipeline = SecureReleasePipeline()
        release_result = _make_workflow_result(final_output={"approved": False})
        result = pipeline._determine_go_no_go(
            risk_score=10.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=release_result,
        )
        assert result == "CONDITIONAL"

    def test_determine_go_no_go_go(self) -> None:
        """Test GO when everything is clean."""
        pipeline = SecureReleasePipeline()
        result = pipeline._determine_go_no_go(
            risk_score=10.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=None,
        )
        assert result == "GO"

    def test_generate_recommendations_all_clear(self) -> None:
        """Test recommendations when all checks pass."""
        pipeline = SecureReleasePipeline()
        blockers, warnings, recs = pipeline._generate_recommendations(None, None, None, None)
        assert blockers == []
        assert warnings == []
        assert "All checks passed" in recs[0]

    def test_generate_recommendations_with_crew_critical(self) -> None:
        """Test recommendations with crew critical findings."""
        pipeline = SecureReleasePipeline()
        crew_report = {
            "assessment": {
                "critical_findings": [
                    {"title": "SQL Injection"},
                    {"title": "RCE"},
                ],
                "high_findings": [{"title": "XSS"}],
            },
        }
        blockers, warnings, recs = pipeline._generate_recommendations(crew_report, None, None, None)
        assert len(blockers) == 2
        assert any("SQL Injection" in b for b in blockers)
        assert len(warnings) == 1

    def test_generate_recommendations_security_critical_risk(self) -> None:
        """Test recommendations with critical risk level."""
        pipeline = SecureReleasePipeline()
        security_result = _make_workflow_result(
            final_output={"score": 20},
            metadata={"findings": {"CRITICAL": ["c1"]}},
        )
        blockers, warnings, recs = pipeline._generate_recommendations(
            None,
            security_result,
            None,
            None,
        )
        assert any("critical" in b.lower() for b in blockers)

    def test_generate_recommendations_security_high_risk(self) -> None:
        """Test recommendations with high risk level."""
        pipeline = SecureReleasePipeline()
        security_result = _make_workflow_result(
            final_output={"score": 60}, metadata={"findings": {"HIGH": ["h1"]}}
        )
        blockers, warnings, recs = pipeline._generate_recommendations(
            None,
            security_result,
            None,
            None,
        )
        assert any("high" in w.lower() for w in warnings)

    def test_generate_recommendations_code_review_reject(self) -> None:
        """Test recommendations when code review rejects."""
        pipeline = SecureReleasePipeline()
        code_review = _make_workflow_result(
            final_output={"score": 30}, metadata={"findings": {"CRITICAL": ["c1"]}}
        )
        blockers, warnings, recs = pipeline._generate_recommendations(None, None, code_review, None)
        assert any("critical" in b.lower() for b in blockers)

    def test_generate_recommendations_code_review_request_changes(self) -> None:
        """Test recommendations when code review requests changes."""
        pipeline = SecureReleasePipeline()
        code_review = _make_workflow_result(
            final_output={"score": 70}, metadata={"findings": {"HIGH": ["h1"]}}
        )
        blockers, warnings, recs = pipeline._generate_recommendations(None, None, code_review, None)
        assert any("high" in w.lower() for w in warnings)

    def test_generate_recommendations_release_blockers(self) -> None:
        """Test recommendations pass through release blockers and warnings."""
        pipeline = SecureReleasePipeline()
        release_result = _make_workflow_result(
            final_output={
                "blockers": ["Missing changelog"],
                "warnings": ["Version bump needed"],
            },
        )
        blockers, warnings, recs = pipeline._generate_recommendations(
            None,
            None,
            None,
            release_result,
        )
        assert any("Missing changelog" in b for b in blockers)
        assert any("Version bump" in w for w in warnings)

    def test_generate_recommendations_with_warnings_only(self) -> None:
        """Test recommendations when only warnings present."""
        pipeline = SecureReleasePipeline()
        security_result = _make_workflow_result(
            final_output={"score": 60}, metadata={"findings": {"HIGH": ["h1"]}}
        )
        blockers, warnings, recs = pipeline._generate_recommendations(
            None,
            security_result,
            None,
            None,
        )
        assert any("accepted risks" in r.lower() for r in recs)


# ============================================================================
# format_secure_release_report Tests
# ============================================================================


@pytest.mark.unit
class TestFormatSecureReleaseReport:
    """Tests for format_secure_release_report function."""

    def test_go_report(self) -> None:
        """Test report for GO decision."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            mode="full",
            crew_enabled=True,
            total_cost=0.05,
            total_duration_ms=3000,
        )
        report = format_secure_release_report(result)
        assert "READY FOR RELEASE" in report
        assert "GO" in report
        assert "FULL" in report

    def test_no_go_report(self) -> None:
        """Test report for NO_GO decision."""
        result = SecureReleaseResult(
            success=False,
            go_no_go="NO_GO",
            blockers=["Critical vulnerability"],
            total_cost=0.03,
            total_duration_ms=2000,
        )
        report = format_secure_release_report(result)
        assert "RELEASE BLOCKED" in report
        assert "Critical vulnerability" in report
        assert "Address all blockers" in report

    def test_conditional_report(self) -> None:
        """Test report for CONDITIONAL decision."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="CONDITIONAL",
            warnings=["High risk in auth module"],
            total_cost=0.04,
            total_duration_ms=2500,
        )
        report = format_secure_release_report(result)
        assert "CONDITIONAL APPROVAL" in report
        assert "High risk in auth module" in report
        assert "Review warnings" in report

    def test_report_with_crew_results(self) -> None:
        """Test report includes crew results."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            crew_report={"risk_score": 20, "finding_count": 3},
            crew_enabled=True,
            total_cost=0.05,
            total_duration_ms=3000,
        )
        report = format_secure_release_report(result)
        assert "SecurityAuditCrew" in report
        assert "3 findings" in report

    def test_report_with_crew_high_risk(self) -> None:
        """Test report crew icon for high risk."""
        result = SecureReleaseResult(
            success=False,
            go_no_go="NO_GO",
            crew_report={"risk_score": 80, "finding_count": 10},
            crew_enabled=True,
            total_cost=0.05,
            total_duration_ms=3000,
        )
        report = format_secure_release_report(result)
        assert "SecurityAuditCrew" in report

    def test_report_crew_enabled_but_no_report(self) -> None:
        """Test report when crew was enabled but no report came back."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            crew_report=None,
            crew_enabled=True,
            total_cost=0.01,
            total_duration_ms=1000,
        )
        report = format_secure_release_report(result)
        assert "Skipped or failed" in report

    def test_report_with_security_audit(self) -> None:
        """Test report includes security audit results."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            security_audit=_make_workflow_result(
                final_output={"_type": "WorkflowReport", "score": 70},
            ),
            total_cost=0.02,
            total_duration_ms=2000,
        )
        report = format_secure_release_report(result)
        assert "SecurityAudit" in report
        assert "70" in report

    def test_report_with_code_review(self) -> None:
        """Test report includes code review results."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            code_review=_make_workflow_result(final_output={"score": 95}),
            total_cost=0.02,
            total_duration_ms=2000,
        )
        report = format_secure_release_report(result)
        assert "CodeReview" in report
        assert "95" in report

    def test_report_with_release_prep(self) -> None:
        """Test report includes release prep results."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            release_prep=_make_workflow_result(
                final_output={"approved": True, "confidence": "high"},
            ),
            total_cost=0.02,
            total_duration_ms=2000,
        )
        report = format_secure_release_report(result)
        assert "ReleasePrep" in report
        assert "Approved" in report
        assert "high" in report

    def test_report_with_release_prep_not_approved(self) -> None:
        """Test report when release prep not approved."""
        result = SecureReleaseResult(
            success=False,
            go_no_go="NO_GO",
            release_prep=_make_workflow_result(
                final_output={"approved": False, "confidence": "low"},
            ),
            total_cost=0.02,
            total_duration_ms=2000,
        )
        report = format_secure_release_report(result)
        assert "Not Approved" in report

    def test_report_with_recommendations(self) -> None:
        """Test report includes recommendations."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="CONDITIONAL",
            recommendations=["Review auth module", "Update dependencies"],
            total_cost=0.03,
            total_duration_ms=2000,
        )
        report = format_secure_release_report(result)
        assert "RECOMMENDATIONS" in report
        assert "Review auth module" in report

    def test_report_cost_and_duration(self) -> None:
        """Test report includes cost and duration."""
        result = SecureReleaseResult(
            success=True,
            go_no_go="GO",
            total_cost=0.1234,
            total_duration_ms=5678,
        )
        report = format_secure_release_report(result)
        assert "$0.1234" in report
        assert "5678ms" in report


# ============================================================================
# ResponseParsingMixin Tests
# ============================================================================


class MockParsingWorkflow(ResponseParsingMixin):
    """Mock workflow class that uses the ResponseParsingMixin.

    This provides the _get_xml_config method that the mixin expects.
    """

    def __init__(self, xml_config: dict | None = None) -> None:
        """Initialize with optional XML config.

        Args:
            xml_config: XML configuration to return from _get_xml_config

        """
        self._xml_config = xml_config or {}

    def _get_xml_config(self) -> dict:
        """Return XML configuration.

        Returns:
            XML configuration dict

        """
        return self._xml_config


@pytest.mark.unit
class TestResponseParsingMixinInferSeverity:
    """Tests for _infer_severity method."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.parser = MockParsingWorkflow()

    def test_infer_critical(self) -> None:
        """Test critical severity keywords."""
        assert self.parser._infer_severity("Critical SQL injection found") == "critical"
        assert self.parser._infer_severity("Remote Code Execution (RCE)") == "critical"
        assert self.parser._infer_severity("Severe vulnerability") == "critical"
        assert self.parser._infer_severity("Exploit detected") == "critical"

    def test_infer_high(self) -> None:
        """Test high severity keywords."""
        assert self.parser._infer_severity("Security issue in auth") == "high"
        assert self.parser._infer_severity("Unsafe deserialization") == "high"
        assert self.parser._infer_severity("Dangerous function call") == "high"
        assert self.parser._infer_severity("XSS in template") == "high"
        assert self.parser._infer_severity("CSRF token missing") == "high"
        assert self.parser._infer_severity("Password in plaintext") == "high"
        assert self.parser._infer_severity("Secret key exposed") == "high"

    def test_infer_medium(self) -> None:
        """Test medium severity keywords."""
        assert self.parser._infer_severity("Warning: deprecated API") == "medium"
        assert self.parser._infer_severity("Issue with input handling") == "medium"
        assert self.parser._infer_severity("Bug in loop logic") == "medium"
        assert self.parser._infer_severity("Error in validation") == "medium"
        assert self.parser._infer_severity("Deprecated function used") == "medium"
        assert self.parser._infer_severity("Memory leak detected") == "medium"

    def test_infer_low(self) -> None:
        """Test low severity keywords."""
        assert self.parser._infer_severity("Low priority refactor") == "low"
        assert self.parser._infer_severity("Minor style change") == "low"
        assert self.parser._infer_severity("Format inconsistency") == "low"
        assert self.parser._infer_severity("Typo in comment") == "low"

    def test_infer_info(self) -> None:
        """Test info severity for generic text."""
        assert self.parser._infer_severity("General observation") == "info"
        assert self.parser._infer_severity("") == "info"
        assert self.parser._infer_severity("No known keywords") == "info"


@pytest.mark.unit
class TestResponseParsingMixinInferCategory:
    """Tests for _infer_category method."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.parser = MockParsingWorkflow()

    def test_infer_security(self) -> None:
        """Test security category keywords."""
        assert self.parser._infer_category("SQL injection vulnerability") == "security"
        assert self.parser._infer_category("XSS in template") == "security"
        assert self.parser._infer_category("Authentication bypass") == "security"
        assert self.parser._infer_category("Encrypt data at rest") == "security"
        assert self.parser._infer_category("Password not hashed") == "security"
        assert self.parser._infer_category("Unsafe input handling") == "security"

    def test_infer_performance(self) -> None:
        """Test performance category keywords."""
        assert self.parser._infer_category("Performance bottleneck") == "performance"
        assert self.parser._infer_category("Slow query execution") == "performance"
        assert self.parser._infer_category("Memory usage too high") == "performance"
        assert self.parser._infer_category("Inefficient algorithm") == "performance"
        assert self.parser._infer_category("Cache miss rate") == "performance"
        assert self.parser._infer_category("Optimization needed") == "performance"

    def test_infer_maintainability(self) -> None:
        """Test maintainability category keywords."""
        assert self.parser._infer_category("Complex function") == "maintainability"
        assert self.parser._infer_category("Refactor needed") == "maintainability"
        assert self.parser._infer_category("Duplicate code") == "maintainability"
        assert self.parser._infer_category("Readability concern") == "maintainability"
        assert self.parser._infer_category("Missing documentation") == "maintainability"

    def test_infer_style(self) -> None:
        """Test style category keywords."""
        assert self.parser._infer_category("Style violation") == "style"
        assert self.parser._infer_category("Lint error") == "style"
        assert self.parser._infer_category("Format issue") == "style"
        assert self.parser._infer_category("Convention mismatch") == "style"
        assert self.parser._infer_category("Whitespace issue") == "style"

    def test_infer_correctness(self) -> None:
        """Test correctness as default category."""
        assert self.parser._infer_category("Some random text") == "correctness"
        assert self.parser._infer_category("") == "correctness"


@pytest.mark.unit
class TestResponseParsingMixinParseLocation:
    """Tests for _parse_location_string method."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.parser = MockParsingWorkflow()

    def test_empty_location_with_files(self) -> None:
        """Test empty location uses first file from files_changed."""
        file, line, col = self.parser._parse_location_string("", ["auth.py"])
        assert file == "auth.py"
        assert line == 1
        assert col == 1

    def test_empty_location_no_files(self) -> None:
        """Test empty location with no files_changed."""
        file, line, col = self.parser._parse_location_string("", [])
        assert file == ""
        assert line == 1
        assert col == 1

    def test_colon_format_file_line(self) -> None:
        """Test 'file.py:42' format."""
        file, line, col = self.parser._parse_location_string("src/auth.py:42", [])
        assert file == "src/auth.py"
        assert line == 42
        assert col == 1

    def test_colon_format_file_line_col(self) -> None:
        """Test 'file.py:42:10' format."""
        file, line, col = self.parser._parse_location_string("src/auth.py:42:10", [])
        assert file == "src/auth.py"
        assert line == 42
        assert col == 10

    def test_line_in_file_format(self) -> None:
        """Test 'line 42 in auth.py' format."""
        file, line, col = self.parser._parse_location_string("line 42 in auth.py", [])
        assert file == "auth.py"
        assert line == 42

    def test_file_line_format(self) -> None:
        """Test 'auth.py line 42' format."""
        file, line, col = self.parser._parse_location_string("auth.py line 42", [])
        assert file == "auth.py"
        assert line == 42

    def test_just_line_number(self) -> None:
        """Test 'line 42' with fallback to first file."""
        file, line, col = self.parser._parse_location_string("line 42", ["main.py"])
        assert file == "main.py"
        assert line == 42

    def test_just_line_number_no_files(self) -> None:
        """Test 'line 42' with no files available."""
        file, line, col = self.parser._parse_location_string("line 42", [])
        assert file == ""
        assert line == 42

    def test_unparseable_location(self) -> None:
        """Test unparseable location returns defaults."""
        file, line, col = self.parser._parse_location_string(
            "somewhere in the code",
            ["fallback.py"],
        )
        assert file == "fallback.py"
        assert line == 1
        assert col == 1

    def test_typescript_file(self) -> None:
        """Test parsing location with TypeScript file extension."""
        file, line, col = self.parser._parse_location_string("src/app.tsx:100", [])
        assert file == "src/app.tsx"
        assert line == 100


@pytest.mark.unit
class TestResponseParsingMixinExtractFindings:
    """Tests for _extract_findings_from_response method."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.parser = MockParsingWorkflow()

    def test_extract_from_file_line_pattern(self) -> None:
        """Test extraction from 'file.py:line: message' pattern."""
        response = "src/auth.py:42: SQL injection vulnerability detected"
        findings = self.parser._extract_findings_from_response(response, ["src/auth.py"])
        assert len(findings) == 1
        assert findings[0]["file"] == "src/auth.py"
        assert findings[0]["line"] == 42
        assert "SQL injection" in findings[0]["message"]
        assert findings[0]["severity"] == "critical"  # "injection" keyword

    def test_extract_from_file_line_col_pattern(self) -> None:
        """Test extraction from 'file.py:line:col: message' pattern."""
        response = "src/auth.py:42:10: Unsafe function call"
        findings = self.parser._extract_findings_from_response(response, [])
        assert len(findings) == 1
        assert findings[0]["column"] == 10

    def test_extract_from_in_file_pattern(self) -> None:
        """Test extraction from 'in file X line Y' pattern."""
        response = "Found issue in file src/utils.py line 100"
        findings = self.parser._extract_findings_from_response(response, [])
        assert len(findings) == 1
        assert findings[0]["file"] == "src/utils.py"
        assert findings[0]["line"] == 100

    def test_extract_from_file_paren_pattern(self) -> None:
        """Test extraction from 'file.py (line X, col Y)' pattern."""
        response = "Issue at auth.py (line 55, column 8)"
        findings = self.parser._extract_findings_from_response(response, [])
        assert len(findings) == 1
        assert findings[0]["file"] == "auth.py"
        assert findings[0]["line"] == 55
        assert findings[0]["column"] == 8

    def test_extract_deduplicates_by_file_line(self) -> None:
        """Test that findings are deduplicated by file:line."""
        response = """
        src/auth.py:42: First issue
        src/auth.py:42: Duplicate issue
        """
        findings = self.parser._extract_findings_from_response(response, [])
        assert len(findings) == 1

    def test_extract_multiple_findings(self) -> None:
        """Test extraction of multiple distinct findings."""
        response = """
        src/auth.py:10: Security issue
        src/utils.py:20: Performance problem
        src/db.py:30: Bug in query
        """
        findings = self.parser._extract_findings_from_response(response, [])
        assert len(findings) == 3

    def test_extract_no_findings(self) -> None:
        """Test extraction with no recognizable patterns."""
        response = "Everything looks great! No issues found."
        findings = self.parser._extract_findings_from_response(response, [])
        assert findings == []

    def test_extract_xml_findings(self) -> None:
        """Test extraction from XML format."""
        mock_parsed = MagicMock()
        mock_parsed.success = True
        mock_finding = MagicMock()
        mock_finding.to_dict.return_value = {
            "title": "SQL Injection",
            "severity": "critical",
            "location": "auth.py:42",
            "details": "Found in login function",
            "fix": "Use parameterized queries",
        }
        mock_parsed.findings = [mock_finding]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed

        with patch("attune.prompts.XmlResponseParser", return_value=mock_parser):
            response = "<findings><finding>test</finding></findings>"
            findings = self.parser._extract_findings_from_response(response, ["auth.py"])

        assert len(findings) == 1
        assert findings[0]["file"] == "auth.py"
        assert findings[0]["line"] == 42

    def test_extract_xml_findings_parse_failure_falls_back(self) -> None:
        """Test extraction falls back to regex when XML parsing fails."""
        mock_parsed = MagicMock()
        mock_parsed.success = False
        mock_parsed.findings = []

        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed

        with patch("attune.prompts.XmlResponseParser", return_value=mock_parser):
            response = "<findings></findings>\nsrc/auth.py:42: Issue here"
            findings = self.parser._extract_findings_from_response(response, ["src/auth.py"])

        assert len(findings) == 1
        assert findings[0]["file"] == "src/auth.py"

    def test_extract_javascript_file_extensions(self) -> None:
        """Test extraction handles JS/JSX/TS/TSX file extensions."""
        response = """
        src/app.tsx:10: Type error
        lib/utils.js:20: Missing return
        src/hook.jsx:5: Invalid hook call
        """
        findings = self.parser._extract_findings_from_response(response, [])
        assert len(findings) == 3

    def test_extract_java_go_rb_php_extensions(self) -> None:
        """Test extraction handles Java, Go, Ruby, PHP extensions."""
        response = """
        Main.java:50: Null pointer
        server.go:100: Error handling
        app.rb:30: undefined method
        index.php:15: SQL injection
        """
        findings = self.parser._extract_findings_from_response(response, [])
        assert len(findings) == 4


@pytest.mark.unit
class TestResponseParsingMixinEnrichFinding:
    """Tests for _enrich_finding_with_location method."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.parser = MockParsingWorkflow()

    def test_enrich_with_location(self) -> None:
        """Test enriching a finding with location data."""
        raw = {
            "title": "SQL Injection",
            "severity": "critical",
            "location": "auth.py:42:10",
            "details": "Found in login function",
            "fix": "Use parameterized queries",
        }
        result = self.parser._enrich_finding_with_location(raw, ["auth.py"])
        assert result["file"] == "auth.py"
        assert result["line"] == 42
        assert result["column"] == 10
        assert result["severity"] == "critical"
        assert result["message"] == "SQL Injection"
        assert result["recommendation"] == "Use parameterized queries"

    def test_enrich_without_location(self) -> None:
        """Test enriching with empty location falls back to first file."""
        raw = {
            "title": "Generic issue",
            "severity": "medium",
            "location": "",
            "details": "",
            "fix": "",
        }
        result = self.parser._enrich_finding_with_location(raw, ["main.py"])
        assert result["file"] == "main.py"
        assert result["line"] == 1

    def test_enrich_category_inference(self) -> None:
        """Test category is inferred from title + details."""
        raw = {
            "title": "Security: XSS vulnerability",
            "severity": "high",
            "location": "app.py:10",
            "details": "Input not sanitized",
            "fix": "",
        }
        result = self.parser._enrich_finding_with_location(raw, [])
        assert result["category"] == "security"


@pytest.mark.unit
class TestResponseParsingMixinParseXml:
    """Tests for _parse_xml_response method."""

    def test_parse_xml_disabled(self) -> None:
        """Test _parse_xml_response when XML enforcement is disabled."""
        parser = MockParsingWorkflow(xml_config={"enforce_response_xml": False})
        result = parser._parse_xml_response("some response text")
        assert result["_parsed_response"] is None
        assert result["_raw"] == "some response text"

    def test_parse_xml_default_config(self) -> None:
        """Test _parse_xml_response with default (empty) config."""
        parser = MockParsingWorkflow()
        result = parser._parse_xml_response("some text")
        assert result["_parsed_response"] is None

    def test_parse_xml_enabled(self) -> None:
        """Test _parse_xml_response when XML enforcement is enabled."""
        mock_parsed = MagicMock()
        mock_parsed.summary = "Test summary"
        mock_parsed.findings = []
        mock_parsed.checklist = []
        mock_parsed.success = True
        mock_parsed.errors = []

        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed

        parser = MockParsingWorkflow(
            xml_config={
                "enforce_response_xml": True,
                "fallback_on_parse_error": True,
            },
        )

        with patch(
            "attune.prompts.XmlResponseParser",
            return_value=mock_parser,
        ):
            result = parser._parse_xml_response("<response>test</response>")

        assert result["_parsed_response"] is mock_parsed
        assert result["summary"] == "Test summary"
        assert result["xml_parsed"] is True
        assert result["parse_errors"] == []

    def test_parse_xml_with_findings(self) -> None:
        """Test _parse_xml_response with findings in parsed response."""
        mock_finding = MagicMock()
        mock_finding.to_dict.return_value = {
            "title": "Issue",
            "severity": "high",
        }

        mock_parsed = MagicMock()
        mock_parsed.summary = "Found issues"
        mock_parsed.findings = [mock_finding]
        mock_parsed.checklist = ["item1"]
        mock_parsed.success = True
        mock_parsed.errors = []

        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed

        parser = MockParsingWorkflow(xml_config={"enforce_response_xml": True})

        with patch(
            "attune.prompts.XmlResponseParser",
            return_value=mock_parser,
        ):
            result = parser._parse_xml_response("<response>test</response>")

        assert len(result["findings"]) == 1
        assert result["findings"][0]["title"] == "Issue"
        assert result["checklist"] == ["item1"]


# ============================================================================
# SecureReleasePipeline Execute Tests
# ============================================================================


@pytest.mark.unit
class TestSecureReleasePipelineExecute:
    """Tests for SecureReleasePipeline execute method."""

    @pytest.mark.asyncio
    async def test_execute_standard_mode_success(self) -> None:
        """Test execute in standard mode (no crew) with all workflows mocked."""
        pipeline = SecureReleasePipeline(mode="standard")

        mock_security_result = _make_workflow_result(
            final_output={
                "assessment": {
                    "risk_score": 20,
                    "risk_level": "low",
                    "severity_breakdown": {"critical": 0, "high": 0, "medium": 2},
                },
            },
            total_cost=0.01,
        )
        mock_release_result = _make_workflow_result(
            final_output={"approved": True, "confidence": "high"},
            total_cost=0.02,
        )

        mock_security_cls = MagicMock()
        mock_security_cls.return_value.execute = AsyncMock(return_value=mock_security_result)

        mock_release_cls = MagicMock()
        mock_release_cls.return_value.execute = AsyncMock(return_value=mock_release_result)

        with (
            patch(
                "attune.workflows.security_audit.SecurityAuditWorkflow",
                mock_security_cls,
            ),
            patch(
                "attune.workflows.release_prep.ReleasePreparationWorkflow",
                mock_release_cls,
            ),
        ):
            result = await pipeline.execute(path="./src")

        assert result.go_no_go == "GO"
        assert result.success is True
        assert result.total_cost == pytest.approx(0.03)
        assert result.mode == "standard"

    @pytest.mark.asyncio
    async def test_execute_with_diff_includes_code_review(self) -> None:
        """Test execute includes code review when diff provided."""
        pipeline = SecureReleasePipeline(mode="standard")

        mock_security_result = _make_workflow_result(
            final_output={"assessment": {"risk_score": 10, "risk_level": "low"}},
            total_cost=0.01,
        )
        mock_code_review_result = _make_workflow_result(
            final_output={"verdict": "approve", "security_score": 90},
            total_cost=0.01,
        )
        mock_release_result = _make_workflow_result(
            final_output={"approved": True},
            total_cost=0.01,
        )

        mock_security_cls = MagicMock()
        mock_security_cls.return_value.execute = AsyncMock(return_value=mock_security_result)

        mock_code_cls = MagicMock()
        mock_code_cls.return_value.execute = AsyncMock(return_value=mock_code_review_result)

        mock_release_cls = MagicMock()
        mock_release_cls.return_value.execute = AsyncMock(return_value=mock_release_result)

        with (
            patch(
                "attune.workflows.security_audit.SecurityAuditWorkflow",
                mock_security_cls,
            ),
            patch(
                "attune.workflows.code_review.CodeReviewWorkflow",
                mock_code_cls,
            ),
            patch(
                "attune.workflows.release_prep.ReleasePreparationWorkflow",
                mock_release_cls,
            ),
        ):
            result = await pipeline.execute(
                path="./src",
                diff="some diff",
                files_changed=["auth.py"],
            )

        assert result.success is True
        assert result.code_review is not None
        assert result.total_cost == pytest.approx(0.03)

    @pytest.mark.asyncio
    async def test_execute_exception_returns_no_go(self) -> None:
        """Test execute returns NO_GO when an exception occurs."""
        pipeline = SecureReleasePipeline(mode="standard")

        mock_security_cls = MagicMock()
        mock_security_cls.return_value.execute = AsyncMock(
            side_effect=RuntimeError("LLM service unavailable"),
        )

        with patch(
            "attune.workflows.security_audit.SecurityAuditWorkflow",
            mock_security_cls,
        ):
            result = await pipeline.execute(path="./src")

        assert result.go_no_go == "NO_GO"
        assert result.success is False
        assert any("Pipeline failed" in b for b in result.blockers)
        assert result.combined_risk_score == 100.0
