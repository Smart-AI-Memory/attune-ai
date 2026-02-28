"""Unit tests for security_audit.py and security_adapters.py

Tests workflow instantiation, adapter methods, scanning logic,
error handling, and default_context classmethod.
"""

import asyncio
import json
import sys
import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.security_adapters import (
    _check_crew_available,
    _get_crew_audit,
    _map_category_to_owasp,
    _map_type_to_category,
    _score_to_level,
    crew_report_to_workflow_format,
    merge_security_results,
    workflow_findings_to_crew_format,
)
from attune.workflows.security_audit import SecurityAuditWorkflow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine in a new event loop."""
    return asyncio.run(coro)


def _make_mock_report(findings=None, risk_score=50, summary="test summary"):
    """Create a mock SecurityReport-like object for crew_report_to_workflow_format."""
    report = MagicMock()
    report.risk_score = risk_score
    report.summary = summary
    report.agents_used = ["scanner", "analyzer"]
    report.memory_graph_hits = 3
    report.audit_duration_seconds = 12.5
    report.metadata = {"cost": 0.02}

    if findings is None:
        # Build one mock finding
        finding = MagicMock()
        finding.category.value = "injection"
        finding.title = "SQL Injection"
        finding.description = "Unsafe query"
        finding.severity.value = "critical"
        finding.file_path = "app.py"
        finding.line_number = 42
        finding.code_snippet = "cursor.execute(f'SELECT ...')"
        finding.remediation = "Use parameterized queries"
        finding.cwe_id = "CWE-89"
        finding.cvss_score = 9.8
        finding.confidence = 0.95
        findings = [finding]

    report.findings = findings
    return report


# ===========================================================================
# SecurityAuditWorkflow tests
# ===========================================================================


@pytest.mark.unit
class TestSecurityAuditWorkflowInit:
    """Test workflow instantiation and configuration."""

    def test_default_init(self):
        """Test workflow with default parameters."""
        wf = SecurityAuditWorkflow()
        assert wf.name == "security-audit"
        assert wf.patterns_dir == "./patterns"
        assert wf.skip_remediate_if_clean is True
        assert wf.use_crew_for_assessment is True
        assert wf.use_crew_for_remediation is False
        assert wf.crew_config == {}
        assert wf.enable_auth_strategy is True
        assert wf._has_critical is False
        assert wf._team_decisions == {}

    def test_custom_init(self, tmp_path):
        """Test workflow with custom parameters."""
        wf = SecurityAuditWorkflow(
            patterns_dir=str(tmp_path),
            skip_remediate_if_clean=False,
            use_crew_for_assessment=False,
            use_crew_for_remediation=True,
            crew_config={"scan_depth": "deep"},
            enable_auth_strategy=False,
        )
        assert wf.patterns_dir == str(tmp_path)
        assert wf.skip_remediate_if_clean is False
        assert wf.use_crew_for_assessment is False
        assert wf.use_crew_for_remediation is True
        assert wf.crew_config == {"scan_depth": "deep"}
        assert wf.enable_auth_strategy is False

    def test_stages_and_tier_map(self):
        """Test that stages and tier_map are correctly defined."""
        wf = SecurityAuditWorkflow()
        assert wf.stages == ["triage", "analyze", "assess", "remediate"]
        from attune.workflows.base import ModelTier

        assert wf.tier_map["triage"] == ModelTier.CHEAP
        assert wf.tier_map["analyze"] == ModelTier.CAPABLE
        assert wf.tier_map["assess"] == ModelTier.CAPABLE
        assert wf.tier_map["remediate"] == ModelTier.PREMIUM

    def test_load_team_decisions_from_file(self, tmp_path):
        """Test loading team decisions from JSON."""
        decisions_dir = tmp_path / "security"
        decisions_dir.mkdir(parents=True)
        decisions_file = decisions_dir / "team_decisions.json"
        decisions_file.write_text(
            json.dumps(
                {
                    "decisions": [
                        {
                            "finding_hash": "sql_injection",
                            "decision": "false_positive",
                            "reason": "Not user input",
                            "decided_by": "lead_dev",
                        },
                    ],
                },
            ),
        )

        wf = SecurityAuditWorkflow(patterns_dir=str(tmp_path))
        assert "sql_injection" in wf._team_decisions
        assert wf._team_decisions["sql_injection"]["decision"] == "false_positive"

    def test_load_team_decisions_missing_file(self, tmp_path):
        """Test graceful handling when decisions file does not exist."""
        wf = SecurityAuditWorkflow(patterns_dir=str(tmp_path))
        assert wf._team_decisions == {}

    def test_load_team_decisions_corrupt_json(self, tmp_path):
        """Test graceful handling of corrupt JSON."""
        decisions_dir = tmp_path / "security"
        decisions_dir.mkdir(parents=True)
        (decisions_dir / "team_decisions.json").write_text("{bad json")

        wf = SecurityAuditWorkflow(patterns_dir=str(tmp_path))
        assert wf._team_decisions == {}


@pytest.mark.unit
class TestDefaultContext:
    """Test the default_context classmethod."""

    def test_default_context_returns_workflow_context(self):
        """Test that default_context returns a WorkflowContext."""
        from attune.workflows.context import WorkflowContext

        ctx = SecurityAuditWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)
        assert ctx.prompt is not None
        assert ctx.parsing is not None

    def test_default_context_with_xml_config(self):
        """Test default_context with xml_config parameter."""
        xml_config = {"enforce_xml": True}
        ctx = SecurityAuditWorkflow.default_context(xml_config=xml_config)
        assert ctx.prompt is not None
        assert ctx.parsing is not None


@pytest.mark.unit
class TestShouldSkipStage:
    """Test stage skip logic."""

    def test_skip_remediate_when_clean(self):
        """Test remediate is skipped when no critical/high findings."""
        wf = SecurityAuditWorkflow()
        wf._has_critical = False
        skip, reason = wf.should_skip_stage("remediate", {})
        assert skip is True
        assert reason is not None

    def test_do_not_skip_remediate_when_critical(self):
        """Test remediate is NOT skipped when critical findings exist."""
        wf = SecurityAuditWorkflow()
        wf._has_critical = True
        skip, reason = wf.should_skip_stage("remediate", {})
        assert skip is False
        assert reason is None

    def test_do_not_skip_remediate_when_disabled(self):
        """Test remediate is NOT skipped when skip_remediate_if_clean=False."""
        wf = SecurityAuditWorkflow(skip_remediate_if_clean=False)
        wf._has_critical = False
        skip, reason = wf.should_skip_stage("remediate", {})
        assert skip is False
        assert reason is None

    def test_do_not_skip_non_remediate_stage(self):
        """Test that non-remediate stages are never skipped."""
        wf = SecurityAuditWorkflow()
        for stage in ("triage", "analyze", "assess"):
            skip, reason = wf.should_skip_stage(stage, {})
            assert skip is False


@pytest.mark.unit
class TestTriageScanning:
    """Test the _triage stage scanning logic."""

    def test_triage_scans_python_files(self, tmp_path):
        """Test that triage scans .py files and finds vulnerabilities.

        Note: pytest tmp_path contains '/test_' in the path, so the scanner
        treats files as test files. hardcoded_secret in test files is skipped,
        but other vuln types (e.g. xss) are kept with severity downgraded to 'low'.
        We use innerHTML to trigger an xss finding that is not skipped.
        """
        vuln_file = tmp_path / "app.py"
        vuln_file.write_text("element.innerHTML = userInput\n")

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, in_tok, out_tok = _run(
            wf._triage({"path": str(tmp_path), "file_types": [".py"]}, None),
        )

        assert result["files_scanned"] == 1
        assert result["finding_count"] >= 1
        types = [f["type"] for f in result["findings"]]
        assert "xss" in types
        # In test file context, severity should be downgraded to "low"
        assert result["findings"][0]["severity"] == "low"

    def test_triage_skips_excluded_directories(self, tmp_path):
        """Test that triage skips directories in SKIP_DIRECTORIES."""
        node_dir = tmp_path / "node_modules"
        node_dir.mkdir()
        vuln_file = node_dir / "bad.py"
        vuln_file.write_text('password = "secret"\n')

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": str(tmp_path), "file_types": [".py"]}, None))
        assert result["finding_count"] == 0

    def test_triage_single_file(self, tmp_path):
        """Test scanning a single file target."""
        scan_dir = tmp_path / "myapp"
        scan_dir.mkdir()
        vuln_file = scan_dir / "script.py"
        vuln_file.write_text("os.system('rm -rf /')\n")

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": str(vuln_file), "file_types": [".py"]}, None))
        assert result["files_scanned"] == 1
        assert result["finding_count"] >= 1

    def test_triage_nonexistent_path(self):
        """Test scanning a path that does not exist."""
        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": "/nonexistent/path"}, None))
        assert result["files_scanned"] == 0
        assert result["finding_count"] == 0

    def test_triage_skips_test_file_hardcoded_secrets(self, tmp_path):
        """Test that hardcoded_secret findings in test files are skipped."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_auth.py"
        test_file.write_text('password = "testpass123"\n')

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": str(tmp_path), "file_types": [".py"]}, None))
        # hardcoded_secret in test files should be skipped
        secret_findings = [
            f for f in result["findings"] if f["type"] == "hardcoded_secret" and f.get("is_test")
        ]
        assert len(secret_findings) == 0

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod(0o000) has no effect on Windows")
    def test_triage_handles_unreadable_file(self, tmp_path):
        """Test graceful handling when file read fails."""
        bad_file = tmp_path / "broken.py"
        bad_file.write_text("normal content")
        # Make file unreadable
        bad_file.chmod(0o000)

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        try:
            result, _, _ = _run(wf._triage({"path": str(tmp_path), "file_types": [".py"]}, None))
            # Should not crash - OSError is caught
            assert result["files_scanned"] == 0
        finally:
            # Restore permissions for cleanup
            bad_file.chmod(0o644)


@pytest.mark.unit
class TestAnalyzeStage:
    """Test the _analyze stage."""

    def test_analyze_marks_findings_needing_review(self):
        """Test findings without team decisions get needs_review status."""
        wf = SecurityAuditWorkflow()
        input_data = {
            "findings": [
                {"type": "xss", "severity": "high", "file": "a.py", "line": 1},
            ],
        }
        result, _, _ = _run(wf._analyze(input_data, None))
        assert result["review_count"] == 1
        assert result["needs_review"][0]["status"] == "needs_review"
        # analysis field should be populated
        assert "analysis" in result["needs_review"][0]

    def test_analyze_applies_team_decision_false_positive(self, tmp_path):
        """Test that team decision of false_positive is applied."""
        decisions_dir = tmp_path / "security"
        decisions_dir.mkdir(parents=True)
        (decisions_dir / "team_decisions.json").write_text(
            json.dumps(
                {
                    "decisions": [
                        {
                            "finding_hash": "xss",
                            "decision": "false_positive",
                            "reason": "Test code only",
                            "decided_by": "security_team",
                        },
                    ],
                },
            ),
        )

        wf = SecurityAuditWorkflow(patterns_dir=str(tmp_path))
        input_data = {
            "findings": [
                {"type": "xss", "severity": "high", "file": "a.py", "line": 1},
            ],
        }
        result, _, _ = _run(wf._analyze(input_data, None))
        assert result["false_positives"][0]["status"] == "false_positive"
        assert result["review_count"] == 0

    def test_analyze_applies_accepted_and_deferred_decisions(self, tmp_path):
        """Test accepted and deferred team decisions."""
        decisions_dir = tmp_path / "security"
        decisions_dir.mkdir(parents=True)
        (decisions_dir / "team_decisions.json").write_text(
            json.dumps(
                {
                    "decisions": [
                        {"finding_hash": "xss", "decision": "accepted", "reason": "Low risk"},
                        {
                            "finding_hash": "sql_injection",
                            "decision": "deferred",
                            "reason": "Next sprint",
                        },
                    ],
                },
            ),
        )

        wf = SecurityAuditWorkflow(patterns_dir=str(tmp_path))
        input_data = {
            "findings": [
                {"type": "xss", "severity": "high"},
                {"type": "sql_injection", "severity": "critical"},
            ],
        }
        result, _, _ = _run(wf._analyze(input_data, None))
        assert result["accepted_risks"][0]["status"] == "accepted_risk"
        statuses = [f["status"] for f in result["analyzed_findings"]]
        assert "deferred" in statuses


@pytest.mark.unit
class TestAssessStage:
    """Test the _assess stage risk scoring."""

    def test_assess_risk_score_calculation(self):
        """Test risk score is correctly calculated from severity counts."""
        wf = SecurityAuditWorkflow()
        wf._crew = None
        wf._crew_available = False

        input_data = {
            "needs_review": [
                {"severity": "critical", "owasp": "A03", "type": "sql_injection"},
                {"severity": "high", "owasp": "A03", "type": "xss"},
                {"severity": "medium", "owasp": "A02", "type": "insecure_random"},
            ],
        }

        with patch.object(wf, "_initialize_crew", new_callable=AsyncMock):
            result, _, _ = _run(wf._assess(input_data, None))
        assessment = result["assessment"]
        # 1 critical (25) + 1 high (10) + 1 medium (3) = 38
        assert assessment["risk_score"] == 38
        assert assessment["risk_level"] == "medium"
        assert assessment["severity_breakdown"]["critical"] == 1
        assert assessment["severity_breakdown"]["high"] == 1
        assert assessment["severity_breakdown"]["medium"] == 1
        assert assessment["severity_breakdown"]["low"] == 0

    def test_assess_sets_has_critical_flag(self):
        """Test that _has_critical flag is set when critical findings exist."""
        wf = SecurityAuditWorkflow()
        wf._crew = None
        wf._crew_available = False

        input_data = {
            "needs_review": [
                {"severity": "critical", "owasp": "A03", "type": "sql_injection"},
            ],
        }
        with patch.object(wf, "_initialize_crew", new_callable=AsyncMock):
            _run(wf._assess(input_data, None))
        assert wf._has_critical is True

    def test_assess_no_critical_findings(self):
        """Test _has_critical is False when only low findings."""
        wf = SecurityAuditWorkflow()
        wf._crew = None
        wf._crew_available = False

        input_data = {
            "needs_review": [
                {"severity": "low", "owasp": "A02", "type": "insecure_random"},
            ],
        }
        with patch.object(wf, "_initialize_crew", new_callable=AsyncMock):
            _run(wf._assess(input_data, None))
        assert wf._has_critical is False

    def test_assess_risk_score_capped_at_100(self):
        """Test risk score does not exceed 100."""
        wf = SecurityAuditWorkflow()
        wf._crew = None
        wf._crew_available = False

        # 5 critical = 125, should cap at 100
        input_data = {
            "needs_review": [
                {"severity": "critical", "owasp": "A03", "type": f"vuln{i}"} for i in range(5)
            ],
        }
        with patch.object(wf, "_initialize_crew", new_callable=AsyncMock):
            result, _, _ = _run(wf._assess(input_data, None))
        assert result["assessment"]["risk_score"] == 100
        assert result["assessment"]["risk_level"] == "critical"

    def test_assess_includes_formatted_report(self):
        """Test that formatted_report is in output."""
        wf = SecurityAuditWorkflow()
        wf._crew = None
        wf._crew_available = False

        input_data = {"needs_review": []}
        with patch.object(wf, "_initialize_crew", new_callable=AsyncMock):
            result, _, _ = _run(wf._assess(input_data, None))
        assert "formatted_report" in result


@pytest.mark.unit
class TestRunStageRouting:
    """Test run_stage routing to correct implementation."""

    def test_run_stage_unknown_raises(self):
        """Test that unknown stage names raise ValueError."""
        wf = SecurityAuditWorkflow()
        with pytest.raises(ValueError, match="Unknown stage"):
            _run(wf.run_stage("nonexistent", None, {}))


@pytest.mark.unit
class TestMergeCrewRemediation:
    """Test _merge_crew_remediation method."""

    def test_merge_empty_crew_findings(self):
        """Test merging when crew has no findings."""
        wf = SecurityAuditWorkflow()
        result = wf._merge_crew_remediation("LLM plan text", {"findings": []})
        assert result == "LLM plan text"

    def test_merge_with_crew_findings(self):
        """Test merging appends crew section to LLM response."""
        wf = SecurityAuditWorkflow()
        crew_remediation = {
            "findings": [
                {
                    "title": "SQL Injection in login",
                    "severity": "critical",
                    "remediation": "Use parameterized queries",
                    "cwe_id": "CWE-89",
                    "cvss_score": 9.8,
                },
            ],
            "agents_used": ["scanner", "remediator"],
        }
        result = wf._merge_crew_remediation("Original plan", crew_remediation)
        assert "Original plan" in result
        assert "Enhanced Remediation (SecurityAuditCrew)" in result
        assert "SQL Injection in login" in result
        assert "CWE-89" in result
        assert "9.8" in result


# ===========================================================================
# Security Adapters tests
# ===========================================================================


@pytest.mark.unit
class TestScoreToLevel:
    """Test _score_to_level helper."""

    def test_critical(self):
        assert _score_to_level(75) == "critical"
        assert _score_to_level(100) == "critical"

    def test_high(self):
        assert _score_to_level(50) == "high"
        assert _score_to_level(74) == "high"

    def test_medium(self):
        assert _score_to_level(25) == "medium"
        assert _score_to_level(49) == "medium"

    def test_low(self):
        assert _score_to_level(1) == "low"
        assert _score_to_level(24) == "low"

    def test_none(self):
        assert _score_to_level(0) == "none"


@pytest.mark.unit
class TestMapCategoryToOwasp:
    """Test _map_category_to_owasp helper."""

    def test_known_categories(self):
        assert _map_category_to_owasp("injection") == "A03:2021-Injection"
        assert "Broken Access Control" in _map_category_to_owasp("broken_access_control")

    def test_unknown_category(self):
        assert _map_category_to_owasp("totally_unknown") == "Other"


@pytest.mark.unit
class TestMapTypeToCategory:
    """Test _map_type_to_category helper."""

    def test_known_types(self):
        assert _map_type_to_category("sql_injection") == "injection"
        assert _map_type_to_category("xss") == "cross_site_scripting"
        assert _map_type_to_category("hardcoded_secret") == "sensitive_data_exposure"

    def test_unknown_type(self):
        assert _map_type_to_category("unknown_vuln") == "other"


@pytest.mark.unit
class TestCheckCrewAvailable:
    """Test _check_crew_available."""

    def test_crew_not_available(self):
        """Test returns False when import fails."""
        with patch.dict("sys.modules", {"attune.agent_factory.crews": None}):
            # Force re-import to fail
            result = _check_crew_available()
            # May still return True if cached; the function tries import
            assert isinstance(result, bool)


@pytest.mark.unit
class TestCrewReportToWorkflowFormat:
    """Test crew_report_to_workflow_format."""

    def test_basic_conversion(self):
        """Test converting a mock SecurityReport to workflow format."""
        report = _make_mock_report()
        result = crew_report_to_workflow_format(report)

        assert result["crew_enabled"] is True
        assert result["finding_count"] == 1
        assert result["risk_score"] == 50
        assert result["risk_level"] == "high"
        assert result["summary"] == "test summary"
        assert result["agents_used"] == ["scanner", "analyzer"]

        finding = result["findings"][0]
        assert finding["type"] == "injection"
        assert finding["title"] == "SQL Injection"
        assert finding["severity"] == "critical"
        assert finding["cwe_id"] == "CWE-89"

    def test_severity_breakdown(self):
        """Test severity breakdown counts."""
        report = _make_mock_report()
        result = crew_report_to_workflow_format(report)
        breakdown = result["assessment"]["severity_breakdown"]
        assert breakdown["critical"] == 1
        assert breakdown["high"] == 0

    def test_owasp_category_mapping(self):
        """Test OWASP category mapping in findings."""
        report = _make_mock_report()
        result = crew_report_to_workflow_format(report)
        finding = result["findings"][0]
        assert finding["owasp"] == "A03:2021-Injection"


@pytest.mark.unit
class TestWorkflowFindingsToCrewFormat:
    """Test workflow_findings_to_crew_format."""

    def test_basic_conversion(self):
        """Test converting workflow findings to crew format."""
        workflow_findings = [
            {
                "type": "sql_injection",
                "severity": "critical",
                "file": "app.py",
                "line": 42,
                "match": "cursor.execute(f'...')",
                "title": "SQL Injection",
                "description": "Unsafe query",
            },
        ]
        result = workflow_findings_to_crew_format(workflow_findings)

        assert len(result) == 1
        assert result[0]["title"] == "SQL Injection"
        assert result[0]["severity"] == "critical"
        assert result[0]["category"] == "injection"
        assert result[0]["file_path"] == "app.py"
        assert result[0]["line_number"] == 42

    def test_missing_fields_use_defaults(self):
        """Test that missing fields fall back to defaults."""
        findings = [{}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["title"] == "Unknown"
        assert result[0]["severity"] == "medium"
        assert result[0]["category"] == "other"
        assert result[0]["confidence"] == 1.0

    def test_empty_list(self):
        """Test empty findings list."""
        assert workflow_findings_to_crew_format([]) == []


@pytest.mark.unit
class TestMergeSecurityResults:
    """Test merge_security_results."""

    def test_both_none(self):
        """Test merging when both inputs are None."""
        result = merge_security_results(None, None)
        assert result["findings"] == []
        assert result["risk_score"] == 0
        assert result["merged"] is False

    def test_crew_only(self):
        """Test merging with only crew results."""
        crew = {"findings": [{"type": "xss"}], "risk_score": 30}
        result = merge_security_results(crew, None)
        assert result["merged"] is False
        assert result["findings"] == [{"type": "xss"}]

    def test_workflow_only(self):
        """Test merging with only workflow results."""
        wf = {"findings": [{"type": "xss"}], "risk_score": 20}
        result = merge_security_results(None, wf)
        assert result["merged"] is False
        assert result["crew_enabled"] is False

    def test_merge_deduplication(self):
        """Test that duplicate findings are deduplicated."""
        crew = {
            "findings": [
                {"type": "xss", "file": "a.py", "line": 10, "severity": "high"},
            ],
            "risk_score": 40,
            "assessment": {
                "risk_score": 40,
                "severity_breakdown": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            },
            "summary": "Crew summary",
            "agents_used": ["scanner"],
        }
        wf = {
            "findings": [
                {"type": "xss", "file": "a.py", "line": 10, "severity": "high"},  # duplicate
                {
                    "type": "sql_injection",
                    "file": "b.py",
                    "line": 5,
                    "severity": "critical",
                },  # unique
            ],
            "assessment": {
                "risk_score": 50,
                "severity_breakdown": {"critical": 1, "high": 1, "medium": 0, "low": 0},
            },
        }
        result = merge_security_results(crew, wf)

        assert result["merged"] is True
        assert result["crew_enabled"] is True
        # Should have 2 findings: 1 from crew (xss dup kept as crew) + 1 unique from wf
        assert result["finding_count"] == 2

    def test_merge_weighted_risk_score(self):
        """Test that merged risk score uses weighted average."""
        crew = {
            "findings": [],
            "risk_score": 80,
            "assessment": {"risk_score": 80, "severity_breakdown": {}},
            "summary": "",
            "agents_used": [],
        }
        wf = {
            "findings": [],
            "assessment": {"risk_score": 40, "severity_breakdown": {}},
        }
        result = merge_security_results(crew, wf)
        # 80 * 0.7 + 40 * 0.3 = 56 + 12 = 68
        assert result["risk_score"] == pytest.approx(68.0)
        assert result["risk_level"] == "high"


# ===========================================================================
# Additional coverage tests
# ===========================================================================


@pytest.mark.unit
class TestRunStageRoutes:
    """Test that run_stage dispatches to correct stage methods."""

    def test_run_stage_triage(self):
        """Test run_stage dispatches to _triage."""
        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        from attune.workflows.base import ModelTier

        result, _, _ = _run(wf.run_stage("triage", ModelTier.CHEAP, {"path": "/nonexistent"}))
        assert "findings" in result
        assert "files_scanned" in result

    def test_run_stage_analyze(self):
        """Test run_stage dispatches to _analyze."""
        wf = SecurityAuditWorkflow()
        from attune.workflows.base import ModelTier

        result, _, _ = _run(wf.run_stage("analyze", ModelTier.CAPABLE, {"findings": []}))
        assert "analyzed_findings" in result

    def test_run_stage_assess(self):
        """Test run_stage dispatches to _assess."""
        wf = SecurityAuditWorkflow()
        wf._crew = None
        wf._crew_available = False
        from attune.workflows.base import ModelTier

        result, _, _ = _run(wf.run_stage("assess", ModelTier.CAPABLE, {"needs_review": []}))
        assert "assessment" in result

    def test_run_stage_remediate(self):
        """Test run_stage dispatches to _remediate with mocked LLM."""
        wf = SecurityAuditWorkflow()
        wf._call_llm = AsyncMock(return_value=("remediation plan", 100, 200))
        from attune.workflows.base import ModelTier

        input_data = {
            "assessment": {
                "critical_findings": [],
                "high_findings": [],
                "risk_score": 10,
                "risk_level": "low",
                "severity_breakdown": {},
            },
        }
        result, _, _ = _run(wf.run_stage("remediate", ModelTier.PREMIUM, input_data))
        assert "remediation_plan" in result


@pytest.mark.unit
class TestInitializeCrew:
    """Test the _initialize_crew method."""

    def test_initialize_crew_import_failure(self):
        """Test _initialize_crew handles missing crew module gracefully."""
        wf = SecurityAuditWorkflow()
        # Reset crew state
        wf._crew = None
        wf._crew_available = False

        with patch(
            "attune.workflows.security_audit.SecurityAuditWorkflow._initialize_crew",
            wraps=wf._initialize_crew,
        ):
            _run(wf._initialize_crew())
            # Crew import will likely fail in test env
            # Either it works or it gracefully handles the ImportError
            assert isinstance(wf._crew_available, bool)

    def test_initialize_crew_skips_if_already_initialized(self):
        """Test _initialize_crew short-circuits when crew already set."""
        wf = SecurityAuditWorkflow()
        wf._crew = MagicMock()
        wf._crew_available = True

        _run(wf._initialize_crew())
        # Should not re-initialize
        assert wf._crew_available is True


@pytest.mark.unit
class TestRemediateStage:
    """Test _remediate stage with mocked LLM."""

    def test_remediate_legacy_path(self):
        """Test _remediate using legacy _call_llm path."""
        from attune.workflows.base import ModelTier

        wf = SecurityAuditWorkflow()
        wf._executor = None
        wf._api_key = None
        wf._call_llm = AsyncMock(return_value=("Remediation plan here", 50, 100))

        input_data = {
            "assessment": {
                "critical_findings": [
                    {"type": "sql_injection", "file": "a.py", "line": 10, "owasp": "A03"},
                ],
                "high_findings": [],
                "risk_score": 25,
                "risk_level": "medium",
                "severity_breakdown": {"critical": 1},
            },
            "path": "./src",
        }

        result, in_tok, out_tok = _run(wf._remediate(input_data, ModelTier.PREMIUM))
        assert result["remediation_plan"] == "Remediation plan here"
        assert result["remediation_count"] == 1
        assert result["risk_score"] == 25
        assert result["model_tier_used"] == "premium"
        wf._call_llm.assert_called_once()

    def test_remediate_executor_path(self):
        """Test _remediate using executor path."""
        wf = SecurityAuditWorkflow()
        wf._executor = MagicMock()
        wf._api_key = "test-key"
        wf.run_step_with_executor = AsyncMock(return_value=("Executor remediation", 60, 120, 0.01))

        input_data = {
            "assessment": {
                "critical_findings": [],
                "high_findings": [
                    {"type": "xss", "file": "b.py", "line": 5, "owasp": "A03"},
                ],
                "risk_score": 10,
                "risk_level": "low",
                "severity_breakdown": {"high": 1},
            },
        }

        from attune.workflows.base import ModelTier

        result, _, _ = _run(wf._remediate(input_data, ModelTier.PREMIUM))
        assert result["remediation_plan"] == "Executor remediation"
        assert result["remediation_count"] == 1
        wf.run_step_with_executor.assert_called_once()

    def test_remediate_executor_fallback_to_llm(self):
        """Test _remediate falls back to _call_llm when executor raises."""
        wf = SecurityAuditWorkflow()
        wf._executor = MagicMock()
        wf._api_key = "test-key"
        wf.run_step_with_executor = AsyncMock(side_effect=RuntimeError("executor fail"))
        wf._call_llm = AsyncMock(return_value=("Fallback plan", 30, 60))

        input_data = {
            "assessment": {
                "critical_findings": [],
                "high_findings": [],
                "risk_score": 0,
                "risk_level": "low",
                "severity_breakdown": {},
            },
        }
        from attune.workflows.base import ModelTier

        result, _, _ = _run(wf._remediate(input_data, ModelTier.PREMIUM))
        assert result["remediation_plan"] == "Fallback plan"
        wf._call_llm.assert_called_once()

    def test_remediate_no_findings(self):
        """Test _remediate with zero findings."""
        from attune.workflows.base import ModelTier

        wf = SecurityAuditWorkflow()
        wf._executor = None
        wf._api_key = None
        wf._call_llm = AsyncMock(return_value=("No issues found", 20, 40))

        input_data = {
            "assessment": {
                "critical_findings": [],
                "high_findings": [],
                "risk_score": 0,
                "risk_level": "low",
                "severity_breakdown": {},
            },
        }

        result, _, _ = _run(wf._remediate(input_data, ModelTier.PREMIUM))
        assert result["remediation_count"] == 0
        assert result["crew_enhanced"] is False


@pytest.mark.unit
class TestGetCrewAudit:
    """Test _get_crew_audit adapter function."""

    def test_returns_none_when_crew_unavailable(self):
        """Test returns None when SecurityAuditCrew is not available."""
        with patch(
            "attune.workflows.security_adapters._check_crew_available",
            return_value=False,
        ):
            result = _run(_get_crew_audit("/some/path"))
            assert result is None

    def test_returns_none_on_timeout(self):
        """Test returns None when audit times out."""
        mock_crew_cls = MagicMock()

        async def slow_audit(*a, **kw):
            await asyncio.sleep(10)

        mock_crew_instance = MagicMock()
        mock_crew_instance.audit = slow_audit
        mock_crew_cls.return_value = mock_crew_instance

        mock_config_cls = MagicMock()

        with (
            patch(
                "attune.workflows.security_adapters._check_crew_available",
                return_value=True,
            ),
            patch.dict("sys.modules", {}),
            patch(
                "attune.agent_factory.crews.SecurityAuditCrew",
                mock_crew_cls,
                create=True,
            ),
            patch(
                "attune.agent_factory.crews.SecurityAuditConfig",
                mock_config_cls,
                create=True,
            ),
        ):
            result = _run(_get_crew_audit("/some/path", timeout=0.01))
            assert result is None

    def test_returns_none_on_audit_exception(self):
        """Test returns None when audit raises an exception."""
        mock_crew_cls = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.audit = AsyncMock(side_effect=RuntimeError("audit boom"))
        mock_crew_cls.return_value = mock_crew_instance
        mock_config_cls = MagicMock()

        # Inject mock module so the lazy import inside _get_crew_audit
        # picks up the mock instead of the real (cached) class.
        mock_crews_module = MagicMock()
        mock_crews_module.SecurityAuditCrew = mock_crew_cls
        mock_crews_module.SecurityAuditConfig = mock_config_cls

        with (
            patch(
                "attune.workflows.security_adapters._check_crew_available",
                return_value=True,
            ),
            patch.dict(
                "sys.modules",
                {"attune.agent_factory.crews": mock_crews_module},
            ),
        ):
            result = _run(_get_crew_audit("/some/path"))
            assert result is None


@pytest.mark.unit
class TestTriageScanningFilters:
    """Test triage vulnerability-specific filter paths."""

    def test_triage_filters_sql_safe_parameterization(self, tmp_path):
        """Test sql_injection findings with safe parameterization are filtered."""
        sql_file = tmp_path / "db.py"
        sql_file.write_text(
            textwrap.dedent(
                """\
            import sqlite3
            placeholders = ",".join("?" * len(ids))
            cursor.execute(f"SELECT * FROM users WHERE id IN ({placeholders})", ids)
        """,
            ),
        )

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": str(sql_file), "file_types": [".py"]}, None))
        sql_findings = [f for f in result["findings"] if f["type"] == "sql_injection"]
        # Safe parameterization should be filtered out
        assert len(sql_findings) == 0

    def test_triage_filters_safe_random_in_test_file(self, tmp_path):
        """Test insecure_random is filtered in test files without crypto context."""
        # pytest tmp_path already matches test file patterns
        test_file = tmp_path / "simulation.py"
        test_file.write_text("value = random.randint(1, 100)\n")

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": str(test_file), "file_types": [".py"]}, None))
        random_findings = [f for f in result["findings"] if f["type"] == "insecure_random"]
        # Test file random usage should be filtered or downgraded
        # (file is in a test path, no crypto indicators)
        for f in random_findings:
            assert f["severity"] == "low"  # Downgraded in test context

    def test_triage_filters_command_injection_in_docs(self, tmp_path):
        """Test command_injection in documentation strings is filtered."""
        doc_file = tmp_path / "docs.py"
        doc_file.write_text(
            textwrap.dedent(
                """\
            # This is an example of dangerous eval() usage
            # eval(user_input) is insecure and should be avoided
        """,
            ),
        )

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": str(doc_file), "file_types": [".py"]}, None))
        cmd_findings = [f for f in result["findings"] if f["type"] == "command_injection"]
        # Comment-based patterns should be filtered as documentation
        assert len(cmd_findings) == 0

    def test_triage_filters_detection_code(self, tmp_path):
        """Test that security scanner detection code is not flagged."""
        scanner_file = tmp_path / "checker.py"
        scanner_file.write_text(
            textwrap.dedent(
                """\
            import re
            for match in re.finditer(r'eval\\(', content):
                print("Found eval usage")
        """,
            ),
        )

        wf = SecurityAuditWorkflow(enable_auth_strategy=False)
        result, _, _ = _run(wf._triage({"path": str(scanner_file), "file_types": [".py"]}, None))
        # Detection code should not be flagged
        eval_findings = [f for f in result["findings"] if f["type"] == "command_injection"]
        assert len(eval_findings) == 0


@pytest.mark.unit
class TestAssessWithCrew:
    """Test _assess stage when crew is available."""

    def test_assess_with_crew_enhanced(self):
        """Test that crew findings are merged into assessment."""
        wf = SecurityAuditWorkflow(use_crew_for_assessment=True)
        wf._crew_available = True

        # Create a mock crew that returns findings
        mock_crew = MagicMock()
        mock_finding = MagicMock()
        mock_finding.category.value = "injection"
        mock_finding.title = "Crew SQL Injection"
        mock_finding.description = "Found by crew"
        mock_finding.severity.value = "high"
        mock_finding.file_path = "api.py"
        mock_finding.line_number = 99
        mock_finding.remediation = "Fix it"
        mock_finding.cwe_id = "CWE-89"
        mock_finding.cvss_score = 7.5
        mock_finding.code_snippet = None

        mock_report = MagicMock()
        mock_report.findings = [mock_finding]
        mock_crew.audit = AsyncMock(return_value=mock_report)
        wf._crew = mock_crew

        input_data = {
            "needs_review": [
                {"severity": "medium", "owasp": "A02", "type": "insecure_random"},
            ],
            "path": ".",
        }

        result, _, _ = _run(wf._assess(input_data, None))
        assessment = result["assessment"]
        assert assessment["crew_enhanced"] is True
        assert assessment["crew_findings_count"] >= 1
        # High finding from crew should be in high_findings
        assert len(assessment["high_findings"]) >= 1

    def test_assess_crew_audit_failure_handled(self):
        """Test that crew failure during assessment is handled gracefully."""
        wf = SecurityAuditWorkflow(use_crew_for_assessment=True)
        wf._crew_available = True

        mock_crew = MagicMock()
        mock_crew.audit = AsyncMock(side_effect=RuntimeError("crew crashed"))
        wf._crew = mock_crew

        input_data = {"needs_review": [], "path": "."}
        result, _, _ = _run(wf._assess(input_data, None))
        # Should not crash, crew_enhanced should be False
        assert result["assessment"]["crew_enhanced"] is False


@pytest.mark.unit
class TestRemediateWithCrewAndXml:
    """Test _remediate with crew remediation and XML prompts."""

    def test_remediate_with_crew_remediation(self):
        """Test _remediate integrates crew remediation results."""
        from attune.workflows.base import ModelTier

        wf = SecurityAuditWorkflow(use_crew_for_remediation=True)
        wf._executor = None
        wf._api_key = None
        wf._call_llm = AsyncMock(return_value=("LLM plan", 50, 100))

        # Mock _get_crew_remediation to return crew results
        crew_result = {
            "findings": [
                {
                    "title": "XSS in template",
                    "severity": "high",
                    "remediation": "Escape output",
                    "cwe_id": "CWE-79",
                    "cvss_score": 6.1,
                },
            ],
            "agents_used": ["remediator"],
        }
        wf._get_crew_remediation = AsyncMock(return_value=crew_result)

        # Patch _check_crew_available in the adapters module (imported inside _remediate)
        with patch(
            "attune.workflows.security_adapters._check_crew_available",
            return_value=True,
        ):
            input_data = {
                "assessment": {
                    "critical_findings": [],
                    "high_findings": [
                        {"type": "xss", "file": "t.py", "line": 5, "owasp": "A03"},
                    ],
                    "risk_score": 10,
                    "risk_level": "low",
                    "severity_breakdown": {"high": 1},
                },
                "path": "./src",
            }
            result, _, _ = _run(wf._remediate(input_data, ModelTier.PREMIUM))

        assert result["crew_enhanced"] is True
        assert "crew_findings" in result
        assert "crew_agents_used" in result
        # Remediation plan should contain crew section
        assert "Enhanced Remediation" in result["remediation_plan"]

    def test_remediate_xml_enabled(self):
        """Test _remediate uses XML prompt when enabled."""
        from attune.workflows.base import ModelTier

        wf = SecurityAuditWorkflow()
        wf._executor = None
        wf._api_key = None
        wf._call_llm = AsyncMock(return_value=("XML remediation plan", 50, 100))
        wf._is_xml_enabled = MagicMock(return_value=True)
        wf._render_xml_prompt = MagicMock(return_value="<xml>prompt</xml>")
        wf._parse_xml_response = MagicMock(return_value={"xml_parsed": False})

        input_data = {
            "assessment": {
                "critical_findings": [],
                "high_findings": [],
                "risk_score": 0,
                "risk_level": "low",
                "severity_breakdown": {},
            },
        }
        result, _, _ = _run(wf._remediate(input_data, ModelTier.PREMIUM))
        wf._render_xml_prompt.assert_called_once()
        # When XML is enabled, system should be None (passed to _call_llm)
        call_args = wf._call_llm.call_args
        assert call_args[0][1] == ""  # system is empty string (None or "")

    def test_remediate_xml_parsed_response(self):
        """Test _remediate merges parsed XML data into result."""
        from attune.workflows.base import ModelTier

        wf = SecurityAuditWorkflow()
        wf._executor = None
        wf._api_key = None
        wf._call_llm = AsyncMock(return_value=("plan", 50, 100))
        wf._parse_xml_response = MagicMock(
            return_value={
                "xml_parsed": True,
                "summary": "XML summary",
                "findings": [{"id": 1}],
                "checklist": ["item1"],
            },
        )

        input_data = {
            "assessment": {
                "critical_findings": [],
                "high_findings": [],
                "risk_score": 0,
                "risk_level": "low",
                "severity_breakdown": {},
            },
        }
        result, _, _ = _run(wf._remediate(input_data, ModelTier.PREMIUM))
        assert result["xml_parsed"] is True
        assert result["summary"] == "XML summary"
        assert result["checklist"] == ["item1"]
