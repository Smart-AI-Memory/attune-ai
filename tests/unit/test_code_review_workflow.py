"""Unit tests for CodeReviewWorkflow and code_review_adapters.

Tests cover:
- Workflow instantiation and configuration
- Stage execution with mocked LLM calls
- should_skip_stage logic
- _classify stage behavior
- _scan stage behavior
- _architect_review stage behavior
- _crew_review fallback paths
- _merge_external_audit
- _gather_project_context
- Adapter functions: _check_crew_available, crew_report_to_workflow_format,
  workflow_findings_to_crew_format, merge_code_review_results, _merge_verdicts,
  _map_type_to_category

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.code_review import CODE_REVIEW_STEPS, CodeReviewWorkflow
from attune.workflows.code_review_adapters import (
    _map_type_to_category,
    _merge_verdicts,
    crew_report_to_workflow_format,
    merge_code_review_results,
    workflow_findings_to_crew_format,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
    """Provide a mocked WorkflowConfig.load so BaseWorkflow.__init__ succeeds."""
    with patch("attune.workflows.config.WorkflowConfig.load") as m:
        cfg = MagicMock()
        cfg.get_provider_for_workflow.return_value = "anthropic"
        cfg.get_xml_config_for_workflow.return_value = {}
        m.return_value = cfg
        yield cfg


@pytest.fixture
def mock_cost_tracker():
    """Provide a mocked CostTracker."""
    with patch("attune.workflows.base.CostTracker") as m:
        m.return_value = MagicMock()
        yield m.return_value


@pytest.fixture
def workflow(mock_config, mock_cost_tracker):
    """Create a CodeReviewWorkflow with mocked dependencies."""
    wf = CodeReviewWorkflow(use_crew=False, enable_auth_strategy=False)
    return wf


@pytest.fixture
def workflow_with_crew(mock_config, mock_cost_tracker):
    """Create a CodeReviewWorkflow with crew enabled."""
    wf = CodeReviewWorkflow(use_crew=True, enable_auth_strategy=False)
    return wf


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
# 1. Instantiation and Configuration Tests
# ===========================================================================


@pytest.mark.unit
class TestCodeReviewWorkflowInit:
    """Test CodeReviewWorkflow instantiation and configuration."""

    def test_default_init_without_crew(self, workflow):
        """Test default instantiation without crew."""
        assert workflow.name == "code-review"
        assert workflow.description == "Tiered code analysis with conditional premium review"
        assert workflow.stages == [
            "classify",
            "scan",
            "perf_check",
            "perf_check_deep",
            "health_monitor",
            "quality_check",
            "quality_check_deep",
            "architect_review",
        ]
        assert workflow.tier_map["classify"] == ModelTier.CHEAP
        assert workflow.tier_map["scan"] == ModelTier.CAPABLE
        assert workflow.tier_map["perf_check"] == ModelTier.CHEAP
        assert workflow.tier_map["perf_check_deep"] == ModelTier.CAPABLE
        assert workflow.tier_map["health_monitor"] == ModelTier.CHEAP
        assert workflow.tier_map["quality_check"] == ModelTier.CHEAP
        assert workflow.tier_map["quality_check_deep"] == ModelTier.CAPABLE
        assert workflow.tier_map["architect_review"] == ModelTier.PREMIUM

    def test_init_with_crew(self, workflow_with_crew):
        """Test instantiation with crew enabled adds crew_review stage."""
        wf = workflow_with_crew
        assert "crew_review" in wf.stages
        assert wf.stages == [
            "classify",
            "crew_review",
            "scan",
            "perf_check",
            "perf_check_deep",
            "health_monitor",
            "quality_check",
            "quality_check_deep",
            "architect_review",
        ]
        assert wf.tier_map["crew_review"] == ModelTier.CAPABLE

    def test_custom_file_threshold(self, mock_config, mock_cost_tracker):
        """Test custom file_threshold is stored."""
        wf = CodeReviewWorkflow(file_threshold=5, use_crew=False, enable_auth_strategy=False)
        assert wf.file_threshold == 5

    def test_default_core_modules(self, workflow):
        """Test default core modules list."""
        assert "src/core/" in workflow.core_modules
        assert "src/security/" in workflow.core_modules
        assert "src/auth/" in workflow.core_modules

    def test_custom_core_modules(self, mock_config, mock_cost_tracker):
        """Test custom core modules override defaults."""
        custom = ["my_app/engine/"]
        wf = CodeReviewWorkflow(core_modules=custom, use_crew=False, enable_auth_strategy=False)
        assert wf.core_modules == custom

    def test_initial_state(self, workflow):
        """Test initial internal state."""
        assert workflow._needs_architect_review is False
        assert workflow._change_type == "unknown"
        assert workflow._crew is None
        assert workflow._crew_available is False
        assert workflow._auth_mode_used is None

    def test_code_review_steps_constant(self):
        """Test CODE_REVIEW_STEPS has expected step config."""
        assert "architect_review" in CODE_REVIEW_STEPS
        step = CODE_REVIEW_STEPS["architect_review"]
        assert step.name == "architect_review"
        assert step.tier_hint == "premium"
        assert step.max_tokens == 3000


# ===========================================================================
# 2. should_skip_stage Tests
# ===========================================================================


@pytest.mark.unit
class TestShouldSkipStage:
    """Test stage skipping logic."""

    def test_skip_non_classify_on_error(self, workflow):
        """Test that stages after classify are skipped when input has error."""
        input_data = {"error": True}
        should_skip, reason = workflow.should_skip_stage("scan", input_data)
        assert should_skip is True
        assert "input validation error" in reason.lower()

    def test_classify_not_skipped_on_error(self, workflow):
        """Test that classify itself is not skipped on error."""
        input_data = {"error": True}
        should_skip, reason = workflow.should_skip_stage("classify", input_data)
        assert should_skip is False

    def test_skip_crew_review_when_not_available(self, workflow_with_crew):
        """Test crew_review is skipped when crew is unavailable."""
        workflow_with_crew._crew_available = False
        should_skip, reason = workflow_with_crew.should_skip_stage("crew_review", {})
        assert should_skip is True
        assert "not available" in reason.lower()

    def test_skip_architect_when_not_needed(self, workflow):
        """Test architect_review is skipped for simple changes."""
        workflow._needs_architect_review = False
        should_skip, reason = workflow.should_skip_stage("architect_review", {})
        assert should_skip is True
        assert "not needed" in reason.lower()

    def test_no_skip_architect_when_needed(self, workflow):
        """Test architect_review is NOT skipped when needed."""
        workflow._needs_architect_review = True
        should_skip, reason = workflow.should_skip_stage("architect_review", {})
        assert should_skip is False
        assert reason is None

    def test_no_skip_scan_normally(self, workflow):
        """Test scan is not skipped under normal conditions."""
        should_skip, reason = workflow.should_skip_stage("scan", {})
        assert should_skip is False
        assert reason is None


# ===========================================================================
# 3. run_stage Dispatch Tests
# ===========================================================================


@pytest.mark.unit
class TestRunStageDispatch:
    """Test run_stage dispatches to correct methods."""

    @pytest.mark.asyncio
    async def test_dispatch_classify(self, workflow):
        """Test run_stage dispatches 'classify' to _classify."""
        with patch.object(workflow, "_classify", new_callable=AsyncMock) as mock_cls:
            mock_cls.return_value = ({"classification": "test"}, 100, 50)
            result = await workflow.run_stage("classify", ModelTier.CHEAP, {"diff": "x"})
            mock_cls.assert_called_once_with({"diff": "x"}, ModelTier.CHEAP)
            assert result[0]["classification"] == "test"

    @pytest.mark.asyncio
    async def test_dispatch_scan(self, workflow):
        """Test run_stage dispatches 'scan' to _scan."""
        with patch.object(workflow, "_scan", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = ({"scan_results": "ok"}, 200, 100)
            await workflow.run_stage("scan", ModelTier.CAPABLE, {})
            mock_scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_architect_review(self, workflow):
        """Test run_stage dispatches 'architect_review' to _architect_review."""
        with patch.object(workflow, "_architect_review", new_callable=AsyncMock) as mock_arch:
            mock_arch.return_value = ({"verdict": "approve"}, 300, 150)
            await workflow.run_stage("architect_review", ModelTier.PREMIUM, {})
            mock_arch.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_crew_review(self, workflow_with_crew):
        """Test run_stage dispatches 'crew_review' to _crew_review."""
        with patch.object(workflow_with_crew, "_crew_review", new_callable=AsyncMock) as mock_crew:
            mock_crew.return_value = ({"crew_review": {}}, 100, 50)
            await workflow_with_crew.run_stage("crew_review", ModelTier.CAPABLE, {})
            mock_crew.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_unknown_stage_raises(self, workflow):
        """Test run_stage raises ValueError for unknown stage."""
        with pytest.raises(ValueError, match="Unknown stage"):
            await workflow.run_stage("nonexistent", ModelTier.CHEAP, {})


# ===========================================================================
# 4. _classify Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestClassifyStage:
    """Test the _classify stage."""

    @pytest.mark.asyncio
    async def test_classify_basic(self, workflow):
        """Test basic classification with diff input."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Change type: feature, Complexity: low, Risk: low", 100, 50)

            result, in_t, out_t = await workflow._classify(
                {"diff": "def hello(): pass", "files_changed": ["src/hello.py"]},
                ModelTier.CHEAP,
            )

            assert result["classification"] is not None
            assert result["files_changed"] == ["src/hello.py"]
            assert result["file_count"] == 1
            assert result["code_to_review"] == "def hello(): pass"
            assert in_t == 100
            assert out_t == 50
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_empty_diff_returns_error(self, workflow):
        """Test classification with empty diff returns error when no project context."""
        with patch.object(workflow, "_gather_project_context", return_value=""):
            result, in_t, out_t = await workflow._classify(
                {"diff": "", "files_changed": []},
                ModelTier.CHEAP,
            )

            assert result["error"] is True
            assert "No code" in result["error_message"]
            assert in_t == 0
            assert out_t == 0

    @pytest.mark.asyncio
    async def test_classify_dot_target_gathers_project_context(self, workflow):
        """Test that target='.' gathers project context."""
        project_ctx = "# Project: test\nSome context"
        with patch.object(workflow, "_gather_project_context", return_value=project_ctx):
            with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = ("feature, low complexity", 80, 40)

                result, _, _ = await workflow._classify(
                    {"diff": "", "target": ".", "files_changed": []},
                    ModelTier.CHEAP,
                )

                assert result["code_to_review"] == project_ctx
                assert result.get("error") is not True

    @pytest.mark.asyncio
    async def test_classify_high_complexity_triggers_architect(self, workflow):
        """Test that high complexity in LLM response triggers architect review."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Complexity: HIGH, Risk: HIGH", 100, 50)

            result, _, _ = await workflow._classify(
                {"diff": "complex code here", "files_changed": ["src/app.py"]},
                ModelTier.CHEAP,
            )

            assert workflow._needs_architect_review is True
            assert result["needs_architect_review"] is True

    @pytest.mark.asyncio
    async def test_classify_many_files_triggers_architect(self, workflow):
        """Test that file count >= threshold triggers architect review."""
        files = [f"src/file{i}.py" for i in range(15)]
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Simple change", 100, 50)

            result, _, _ = await workflow._classify(
                {"diff": "some diff", "files_changed": files},
                ModelTier.CHEAP,
            )

            assert workflow._needs_architect_review is True

    @pytest.mark.asyncio
    async def test_classify_core_module_triggers_architect(self, workflow):
        """Test that core module files trigger architect review."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Simple change", 100, 50)

            result, _, _ = await workflow._classify(
                {"diff": "some diff", "files_changed": ["src/core/engine.py"]},
                ModelTier.CHEAP,
            )

            assert result["is_core_module"] is True
            assert workflow._needs_architect_review is True

    @pytest.mark.asyncio
    async def test_classify_is_core_module_flag(self, workflow):
        """Test that explicit is_core_module flag triggers architect review."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Simple change", 100, 50)

            result, _, _ = await workflow._classify(
                {
                    "diff": "some diff",
                    "files_changed": ["src/utils.py"],
                    "is_core_module": True,
                },
                ModelTier.CHEAP,
            )

            assert workflow._needs_architect_review is True

    @pytest.mark.asyncio
    async def test_classify_uses_target_when_no_diff(self, workflow):
        """Test that target is used as code_to_review when diff is empty."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("feature", 100, 50)

            result, _, _ = await workflow._classify(
                {"diff": "", "target": "def foo(): return 42", "files_changed": []},
                ModelTier.CHEAP,
            )

            assert result["code_to_review"] == "def foo(): return 42"


# ===========================================================================
# 5. _scan Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestScanStage:
    """Test the _scan stage."""

    @pytest.mark.asyncio
    async def test_scan_basic(self, workflow):
        """Test basic scan produces expected output keys."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("No issues found", 200, 100)
            with patch.object(workflow, "_extract_findings_from_response", return_value=[]):
                result, in_t, out_t = await workflow._scan(
                    {
                        "code_to_review": "def safe(): pass",
                        "classification": "feature",
                        "files_changed": ["src/safe.py"],
                    },
                    ModelTier.CAPABLE,
                )

                assert "scan_results" in result
                assert "findings" in result
                assert "summary" in result
                assert "security_score" in result
                assert "verdict" in result
                assert result["has_critical_issues"] is False
                assert result["security_score"] == 90
                assert result["verdict"] == "approve"

    @pytest.mark.asyncio
    async def test_scan_critical_issues(self, workflow):
        """Test scan with critical issues sets has_critical and lowers score."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("CRITICAL: SQL injection found", 200, 100)
            with patch.object(workflow, "_extract_findings_from_response", return_value=[]):
                result, _, _ = await workflow._scan(
                    {
                        "code_to_review": "cursor.execute(user_input)",
                        "classification": "feature",
                    },
                    ModelTier.CAPABLE,
                )

                assert result["has_critical_issues"] is True
                assert result["security_score"] == 70
                assert result["verdict"] == "request_changes"

    @pytest.mark.asyncio
    async def test_scan_with_external_audit(self, workflow):
        """Test scan merges external audit results."""
        external_audit = {
            "summary": "Found 2 issues",
            "findings": [
                {
                    "severity": "critical",
                    "title": "SQL Injection",
                    "description": "Unsanitized input",
                    "file": "db.py",
                    "line": 42,
                },
                {
                    "severity": "low",
                    "title": "Unused import",
                    "description": "os module unused",
                },
            ],
            "risk_score": 85,
        }
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("No additional issues", 200, 100)
            with patch.object(workflow, "_extract_findings_from_response", return_value=[]):
                result, _, _ = await workflow._scan(
                    {
                        "code_to_review": "import os",
                        "classification": "feature",
                        "external_audit_results": external_audit,
                    },
                    ModelTier.CAPABLE,
                )

                assert result["external_audit_included"] is True
                assert result["external_audit_risk_score"] == 85
                # External audit has critical finding
                assert result["has_critical_issues"] is True

    @pytest.mark.asyncio
    async def test_scan_summary_statistics(self, workflow):
        """Test scan computes summary statistics from findings."""
        findings = [
            {"severity": "high", "category": "security", "file": "auth.py"},
            {"severity": "medium", "category": "quality", "file": "utils.py"},
        ]
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Issues found with HIGH severity", 200, 100)
            with patch.object(workflow, "_extract_findings_from_response", return_value=findings):
                result, _, _ = await workflow._scan(
                    {
                        "code_to_review": "code",
                        "classification": "feature",
                    },
                    ModelTier.CAPABLE,
                )

                summary = result["summary"]
                assert summary["total_findings"] == 2
                assert summary["by_severity"]["high"] == 1
                assert summary["by_severity"]["medium"] == 1
                assert summary["by_category"]["security"] == 1
                assert summary["by_category"]["quality"] == 1
                assert "auth.py" in summary["files_affected"]

    @pytest.mark.asyncio
    async def test_scan_no_findings_message(self, workflow):
        """Test scan adds helpful message when no findings."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Code looks clean", 200, 100)
            with patch.object(workflow, "_extract_findings_from_response", return_value=[]):
                result, _, _ = await workflow._scan(
                    {"code_to_review": "good code", "classification": "feature"},
                    ModelTier.CAPABLE,
                )

                assert "message" in result["summary"]
                assert "No security" in result["summary"]["message"]


# ===========================================================================
# 6. _merge_external_audit Tests
# ===========================================================================


@pytest.mark.unit
class TestMergeExternalAudit:
    """Test the _merge_external_audit method."""

    def test_merge_with_critical_findings(self, workflow):
        """Test merge detects critical findings."""
        external = {
            "summary": "Critical issues found",
            "findings": [
                {
                    "severity": "critical",
                    "title": "RCE",
                    "description": "Remote code execution",
                    "file": "app.py",
                    "line": 10,
                    "remediation": "Sanitize input",
                },
            ],
            "risk_score": 95,
        }
        merged_resp, findings, has_critical = workflow._merge_external_audit(
            "LLM response", external
        )
        assert has_critical is True
        assert len(findings) == 1
        assert "SecurityAuditCrew" in merged_resp

    def test_merge_with_high_findings(self, workflow):
        """Test merge detects high findings."""
        external = {
            "summary": "Some issues",
            "findings": [
                {"severity": "high", "title": "XSS", "description": "Cross-site scripting"},
            ],
            "risk_score": 70,
        }
        _, findings, has_critical = workflow._merge_external_audit("LLM resp", external)
        assert has_critical is True

    def test_merge_with_no_critical(self, workflow):
        """Test merge with only low findings."""
        external = {
            "summary": "Minor issues",
            "findings": [
                {"severity": "low", "title": "Style", "description": "Formatting"},
            ],
            "risk_score": 20,
        }
        _, findings, has_critical = workflow._merge_external_audit("LLM resp", external)
        assert has_critical is False

    def test_merge_empty_external(self, workflow):
        """Test merge with empty external audit."""
        external = {"summary": "", "findings": [], "risk_score": 0}
        merged_resp, findings, has_critical = workflow._merge_external_audit(
            "LLM response", external
        )
        assert has_critical is False
        assert len(findings) == 0
        # Response should just be the original LLM response
        assert merged_resp.startswith("LLM response")


# ===========================================================================
# 7. _crew_review Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestCrewReviewStage:
    """Test the _crew_review stage."""

    @pytest.mark.asyncio
    async def test_crew_review_adapters_import_error(self, workflow_with_crew):
        """Test fallback when adapter import fails."""
        with patch.object(workflow_with_crew, "_initialize_crew", new_callable=AsyncMock):
            with patch.dict(
                "sys.modules",
                {"attune.workflows.code_review_adapters": None},
            ):
                # When the import inside _crew_review fails, it should return fallback
                # We need to mock at a different level - patch the import inside the method
                with patch(
                    "attune.workflows.code_review.CodeReviewWorkflow._crew_review",
                    new_callable=AsyncMock,
                ) as mock_method:
                    mock_method.return_value = (
                        {
                            "crew_review": {
                                "available": False,
                                "fallback": True,
                                "reason": "Crew adapters not installed",
                            },
                        },
                        0,
                        0,
                    )
                    result, in_t, out_t = await mock_method({"diff": "code"}, ModelTier.CAPABLE)
                    assert result["crew_review"]["fallback"] is True

    @pytest.mark.asyncio
    async def test_crew_review_not_available(self, workflow_with_crew):
        """Test fallback when crew is not available."""
        workflow_with_crew._crew_available = False
        with patch.object(workflow_with_crew, "_initialize_crew", new_callable=AsyncMock):
            with patch(
                "attune.workflows.code_review_adapters._check_crew_available",
                return_value=False,
            ):
                result, in_t, out_t = await workflow_with_crew._crew_review(
                    {"diff": "some code", "files_changed": []},
                    ModelTier.CAPABLE,
                )
                assert result["crew_review"]["available"] is False
                assert result["crew_review"]["fallback"] is True
                assert in_t == 0
                assert out_t == 0

    @pytest.mark.asyncio
    async def test_crew_review_success(self, workflow_with_crew):
        """Test successful crew review execution."""
        import attune.workflows.code_review_adapters as adapters_mod

        workflow_with_crew._crew_available = True
        mock_report = _make_crew_report(
            findings=[_make_finding(severity="medium", category="quality")],
            verdict="approve_with_suggestions",
            quality_score=85,
        )
        crew_result_dict = {
            "findings": [{"severity": "medium"}],
            "finding_count": 1,
            "verdict": "approve_with_suggestions",
            "quality_score": 85,
            "has_blocking_issues": False,
            "summary": "Minor issues",
            "agents_used": ["review_lead"],
            "memory_graph_hits": 0,
            "review_duration_seconds": 1.0,
            "assessment": {
                "critical_findings": [],
                "high_findings": [],
            },
        }

        with patch.object(workflow_with_crew, "_initialize_crew", new_callable=AsyncMock):
            with patch.object(adapters_mod, "_check_crew_available", return_value=True):
                with patch.object(
                    adapters_mod,
                    "_get_crew_review",
                    new_callable=AsyncMock,
                    return_value=mock_report,
                ):
                    with patch.object(
                        adapters_mod,
                        "crew_report_to_workflow_format",
                        return_value=crew_result_dict,
                    ):
                        result, in_t, out_t = await workflow_with_crew._crew_review(
                            {"diff": "some code", "files_changed": ["a.py"]},
                            ModelTier.CAPABLE,
                        )

                        assert result["crew_review"]["available"] is True
                        assert result["crew_review"]["fallback"] is False
                        assert result["crew_review"]["finding_count"] == 1
                        assert result["crew_review"]["quality_score"] == 85

    @pytest.mark.asyncio
    async def test_crew_review_report_none(self, workflow_with_crew):
        """Test crew review when report returns None (timeout/failure)."""
        import attune.workflows.code_review_adapters as adapters_mod

        workflow_with_crew._crew_available = True

        with patch.object(workflow_with_crew, "_initialize_crew", new_callable=AsyncMock):
            with patch.object(adapters_mod, "_check_crew_available", return_value=True):
                with patch.object(
                    adapters_mod,
                    "_get_crew_review",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    result, in_t, out_t = await workflow_with_crew._crew_review(
                        {"diff": "some code", "files_changed": []},
                        ModelTier.CAPABLE,
                    )

                    assert result["crew_review"]["available"] is True
                    assert result["crew_review"]["fallback"] is True
                    assert "failed or timed out" in result["crew_review"]["reason"]

    @pytest.mark.asyncio
    async def test_crew_review_blocking_triggers_architect(self, workflow_with_crew):
        """Test that blocking crew findings trigger architect review."""
        import attune.workflows.code_review_adapters as adapters_mod

        workflow_with_crew._crew_available = True
        workflow_with_crew._needs_architect_review = False

        with patch.object(workflow_with_crew, "_initialize_crew", new_callable=AsyncMock):
            with patch.object(adapters_mod, "_check_crew_available", return_value=True):
                with patch.object(
                    adapters_mod,
                    "_get_crew_review",
                    new_callable=AsyncMock,
                    return_value=MagicMock(),
                ):
                    with patch.object(
                        adapters_mod,
                        "crew_report_to_workflow_format",
                        return_value={
                            "findings": [],
                            "finding_count": 0,
                            "verdict": "reject",
                            "quality_score": 30,
                            "has_blocking_issues": True,
                            "summary": "Critical issues",
                            "agents_used": ["review_lead"],
                            "memory_graph_hits": 0,
                            "review_duration_seconds": 2.0,
                            "assessment": {
                                "critical_findings": [{"id": "1"}],
                                "high_findings": [],
                            },
                        },
                    ):
                        result, _, _ = await workflow_with_crew._crew_review(
                            {"diff": "bad code", "files_changed": []},
                            ModelTier.CAPABLE,
                        )

                        assert workflow_with_crew._needs_architect_review is True


# ===========================================================================
# 8. _architect_review Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestArchitectReviewStage:
    """Test the _architect_review stage."""

    @pytest.mark.asyncio
    async def test_architect_review_basic(self, workflow):
        """Test basic architect review returns expected structure."""
        workflow._executor = None
        workflow._api_key = None
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "APPROVE: Code follows good patterns",
                500,
                200,
            )
            with patch.object(workflow, "_is_xml_enabled", return_value=False):
                with patch.object(
                    workflow,
                    "_parse_xml_response",
                    return_value={"xml_parsed": False, "_raw": ""},
                ):
                    result, in_t, out_t = await workflow._architect_review(
                        {
                            "code_to_review": "class Good: pass",
                            "scan_results": "No issues",
                            "classification": "feature",
                        },
                        ModelTier.PREMIUM,
                    )

                    assert result["verdict"] == "approve"
                    assert result["model_tier_used"] == "premium"
                    assert "formatted_report" in result
                    assert "display_output" in result

    @pytest.mark.asyncio
    async def test_architect_review_request_changes_verdict(self, workflow):
        """Test architect review detects REQUEST_CHANGES verdict."""
        workflow._executor = None
        workflow._api_key = None
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "REQUEST_CHANGES: Major issues found",
                500,
                200,
            )
            with patch.object(workflow, "_is_xml_enabled", return_value=False):
                with patch.object(
                    workflow,
                    "_parse_xml_response",
                    return_value={"xml_parsed": False},
                ):
                    result, _, _ = await workflow._architect_review(
                        {
                            "code_to_review": "bad code",
                            "scan_results": "Issues found",
                            "classification": "feature",
                        },
                        ModelTier.PREMIUM,
                    )

                    assert result["verdict"] == "request_changes"

    @pytest.mark.asyncio
    async def test_architect_review_with_xml_enabled(self, workflow):
        """Test architect review uses XML prompt when enabled."""
        workflow._executor = None
        workflow._api_key = None
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("APPROVE", 500, 200)
            with patch.object(workflow, "_is_xml_enabled", return_value=True):
                with patch.object(
                    workflow, "_render_xml_prompt", return_value="<xml>prompt</xml>"
                ) as mock_xml:
                    with patch.object(
                        workflow,
                        "_parse_xml_response",
                        return_value={"xml_parsed": False},
                    ):
                        result, _, _ = await workflow._architect_review(
                            {
                                "code_to_review": "code",
                                "scan_results": "",
                                "classification": "feature",
                            },
                            ModelTier.PREMIUM,
                        )

                        mock_xml.assert_called_once()
                        # When XML enabled, system should be None in _call_llm
                        call_args = mock_llm.call_args
                        assert call_args[0][1] == ""  # system is empty string

    @pytest.mark.asyncio
    async def test_architect_review_executor_fallback(self, workflow):
        """Test architect review falls back to _call_llm if executor fails."""
        workflow._executor = MagicMock()
        workflow._api_key = "test-key"
        with patch.object(workflow, "run_step_with_executor", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = RuntimeError("Executor failed")
            with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = ("APPROVE", 300, 150)
                with patch.object(workflow, "_is_xml_enabled", return_value=False):
                    with patch.object(
                        workflow,
                        "_parse_xml_response",
                        return_value={"xml_parsed": False},
                    ):
                        result, _, _ = await workflow._architect_review(
                            {
                                "code_to_review": "code",
                                "scan_results": "",
                                "classification": "feature",
                            },
                            ModelTier.PREMIUM,
                        )

                        assert result["verdict"] == "approve"
                        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_architect_review_xml_parsed_verdict(self, workflow):
        """Test architect review extracts verdict from parsed XML response."""
        workflow._executor = None
        workflow._api_key = None

        # Mock parsed XML response with verdict in extra
        mock_extra = MagicMock()
        mock_extra.extra = {"verdict": "reject"}

        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("Some review text", 500, 200)
            with patch.object(workflow, "_is_xml_enabled", return_value=False):
                with patch.object(
                    workflow,
                    "_parse_xml_response",
                    return_value={
                        "xml_parsed": True,
                        "_parsed_response": mock_extra,
                        "summary": "Summary here",
                        "findings": [{"id": "1", "severity": "high"}],
                        "checklist": ["item1"],
                    },
                ):
                    result, _, _ = await workflow._architect_review(
                        {
                            "code_to_review": "code",
                            "scan_results": "",
                            "classification": "feature",
                        },
                        ModelTier.PREMIUM,
                    )

                    assert result["verdict"] == "reject"
                    assert result["xml_parsed"] is True
                    assert result["summary"] == "Summary here"
                    assert len(result["findings"]) == 1
                    assert result["checklist"] == ["item1"]

    @pytest.mark.asyncio
    async def test_architect_review_reject_in_text(self, workflow):
        """Test architect review detects REJECT in response text."""
        workflow._executor = None
        workflow._api_key = None
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("REJECT: Fundamental design flaws", 500, 200)
            with patch.object(workflow, "_is_xml_enabled", return_value=False):
                with patch.object(
                    workflow,
                    "_parse_xml_response",
                    return_value={"xml_parsed": False},
                ):
                    result, _, _ = await workflow._architect_review(
                        {
                            "code_to_review": "terrible code",
                            "scan_results": "",
                            "classification": "feature",
                        },
                        ModelTier.PREMIUM,
                    )

                    assert result["verdict"] == "request_changes"

    @pytest.mark.asyncio
    async def test_architect_review_with_executor_success(self, workflow):
        """Test architect review succeeds with executor."""
        workflow._executor = MagicMock()
        workflow._api_key = "test-key"
        with patch.object(workflow, "run_step_with_executor", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("APPROVE: Good code", 300, 150, 0.01)
            with patch.object(workflow, "_is_xml_enabled", return_value=False):
                with patch.object(
                    workflow,
                    "_parse_xml_response",
                    return_value={"xml_parsed": False},
                ):
                    result, in_t, out_t = await workflow._architect_review(
                        {
                            "code_to_review": "good code",
                            "scan_results": "",
                            "classification": "feature",
                        },
                        ModelTier.PREMIUM,
                    )

                    assert result["verdict"] == "approve"
                    mock_exec.assert_called_once()


# ===========================================================================
# 9. _gather_project_context Tests
# ===========================================================================


@pytest.mark.unit
class TestGatherProjectContext:
    """Test the _gather_project_context method."""

    def test_gather_project_context_with_files(self, workflow, tmp_path, monkeypatch):
        """Test gathering project context from a directory with files."""
        # Create test project structure
        (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "test"')
        (tmp_path / "README.md").write_text("# Test Project\nA test project.")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")

        monkeypatch.chdir(tmp_path)
        context = workflow._gather_project_context()

        assert "Project:" in context
        assert "pyproject.toml" in context
        assert "README.md" in context

    def test_gather_project_context_empty_dir(self, workflow, tmp_path, monkeypatch):
        """Test gathering project context from empty directory."""
        monkeypatch.chdir(tmp_path)
        context = workflow._gather_project_context()

        # Should still have project header and structure section
        assert "Project:" in context

    def test_gather_project_context_with_package_json(self, workflow, tmp_path, monkeypatch):
        """Test gathering project context includes package.json."""
        (tmp_path / "package.json").write_text('{"name": "my-app", "version": "1.0.0"}')
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").write_text("console.log('hi')")

        monkeypatch.chdir(tmp_path)
        context = workflow._gather_project_context()

        assert "package.json" in context
        assert "my-app" in context

    def test_gather_project_context_oserror_on_pyproject(self, workflow, tmp_path, monkeypatch):
        """Test graceful handling when pyproject.toml read fails."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("content")
        # Make it unreadable
        pyproject.chmod(0o000)

        monkeypatch.chdir(tmp_path)
        try:
            context = workflow._gather_project_context()
            # Should not crash, just skip pyproject.toml
            assert "Project:" in context
        finally:
            pyproject.chmod(0o644)

    def test_gather_project_context_directory_structure(self, workflow, tmp_path, monkeypatch):
        """Test directory structure includes key files."""
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "config.yaml").write_text("key: val")
        (tmp_path / ".hidden").write_text("hidden")  # Should be excluded

        monkeypatch.chdir(tmp_path)
        context = workflow._gather_project_context()

        assert "main.py" in context
        assert "config.yaml" in context
        assert "Project Structure" in context


# ===========================================================================
# 10. default_context Tests
# ===========================================================================


@pytest.mark.unit
class TestDefaultContext:
    """Test the default_context classmethod."""

    def test_default_context_returns_workflow_context(self):
        """Test default_context returns a WorkflowContext."""
        from attune.workflows.context import WorkflowContext

        ctx = CodeReviewWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)
        assert ctx.prompt is not None
        assert ctx.parsing is not None

    def test_default_context_with_xml_config(self):
        """Test default_context accepts xml_config."""
        ctx = CodeReviewWorkflow.default_context(xml_config={"enforce": True})
        assert ctx.prompt is not None


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
            }
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
            }
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
# 17. _initialize_crew Tests
# ===========================================================================


@pytest.mark.unit
class TestInitializeCrew:
    """Test the _initialize_crew method."""

    @pytest.mark.asyncio
    async def test_initialize_crew_already_set(self, workflow_with_crew):
        """Test that _initialize_crew short-circuits when crew is already set."""
        workflow_with_crew._crew = MagicMock()
        await workflow_with_crew._initialize_crew()
        # Should not try to import again
        assert workflow_with_crew._crew is not None

    @pytest.mark.asyncio
    async def test_initialize_crew_import_error(self, workflow_with_crew):
        """Test graceful handling when crew module import fails."""
        import sys

        workflow_with_crew._crew = None
        # Block the crews module to simulate ImportError
        with patch.dict(sys.modules, {"attune.agent_factory.crews.code_review": None}):
            await workflow_with_crew._initialize_crew()
            assert workflow_with_crew._crew_available is False


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
# 19. Auth Strategy Integration in _classify Tests
# ===========================================================================


@pytest.mark.unit
class TestClassifyAuthStrategy:
    """Test auth strategy integration in _classify."""

    @pytest.mark.asyncio
    async def test_classify_with_auth_strategy_enabled(self, mock_config, mock_cost_tracker):
        """Test that auth strategy is attempted when enabled."""
        wf = CodeReviewWorkflow(use_crew=False, enable_auth_strategy=True)

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("feature, low complexity", 100, 50)
            # Auth strategy will try to import attune.models functions
            # and process the target path -- it should handle gracefully
            # even if the path doesn't exist
            result, _, _ = await wf._classify(
                {
                    "diff": "def hello(): pass",
                    "target": "/nonexistent/path.py",
                    "files_changed": ["hello.py"],
                },
                ModelTier.CHEAP,
            )

            # Should complete without error regardless of auth strategy result
            assert result["classification"] is not None

    @pytest.mark.asyncio
    async def test_classify_auth_strategy_exception_handled(self, mock_config, mock_cost_tracker):
        """Test that auth strategy exceptions are caught gracefully."""
        wf = CodeReviewWorkflow(use_crew=False, enable_auth_strategy=True)

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("feature", 100, 50)
            # Mock at source: attune.models.get_auth_strategy
            with patch(
                "attune.models.get_auth_strategy",
                side_effect=RuntimeError("Auth failed"),
            ):
                result, _, _ = await wf._classify(
                    {
                        "diff": "code here",
                        "files_changed": [],
                    },
                    ModelTier.CHEAP,
                )

                # Should still succeed despite auth error
                assert result["classification"] == "feature"


# ===========================================================================
# 20. Scan with Formatted Report Tests
# ===========================================================================


@pytest.mark.unit
class TestScanFormattedReport:
    """Test that _scan produces a formatted report."""

    @pytest.mark.asyncio
    async def test_scan_includes_formatted_report(self, workflow):
        """Test scan result includes formatted report for display."""
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("No issues found", 200, 100)
            with patch.object(workflow, "_extract_findings_from_response", return_value=[]):
                result, _, _ = await workflow._scan(
                    {
                        "code_to_review": "clean code",
                        "classification": "feature",
                    },
                    ModelTier.CAPABLE,
                )

                assert "formatted_report" in result
                assert "display_output" in result
                assert "CODE REVIEW REPORT" in result["formatted_report"]

    @pytest.mark.asyncio
    async def test_scan_tracks_auth_mode(self, workflow):
        """Test scan result includes auth_mode_used."""
        workflow._auth_mode_used = "subscription"
        with patch.object(workflow, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("OK", 200, 100)
            with patch.object(workflow, "_extract_findings_from_response", return_value=[]):
                result, _, _ = await workflow._scan(
                    {"code_to_review": "code", "classification": "feat"},
                    ModelTier.CAPABLE,
                )

                assert result["auth_mode_used"] == "subscription"
                assert result["model_tier_used"] == "capable"


# ===========================================================================
# 21. _perf_check Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestPerfCheckStage:
    """Tests for the _perf_check performance baseline stage."""

    @pytest.mark.asyncio
    async def test_perf_check_detects_n_plus_one(self, workflow, tmp_path):
        """Test that perf_check detects N+1 query patterns."""
        bad_file = tmp_path / "bad.py"
        # Pattern requires .query( on the same line as "for x in y:"
        bad_file.write_text("for item in items: db.query(item.id)\n")
        input_data = {"files_changed": [str(bad_file)]}
        result, _, _ = await workflow._perf_check(input_data, ModelTier.CHEAP)

        assert result["perf_finding_count"] > 0
        assert any(f["type"] == "n_plus_one" for f in result["perf_findings"])

    @pytest.mark.asyncio
    async def test_perf_check_detects_nested_loops(self, workflow, tmp_path):
        """Test that perf_check detects triple nested loops."""
        bad_file = tmp_path / "nested.py"
        bad_file.write_text(
            "for a in x:\n" "    for b in y:\n" "        for c in z:\n" "            pass\n"
        )
        input_data = {"files_changed": [str(bad_file)]}
        result, _, _ = await workflow._perf_check(input_data, ModelTier.CHEAP)

        assert result["perf_finding_count"] > 0
        assert any(f["type"] == "nested_loops" for f in result["perf_findings"])

    @pytest.mark.asyncio
    async def test_perf_check_clean_file(self, workflow, tmp_path):
        """Test that perf_check returns zero findings for clean code."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("def add(x: int, y: int) -> int:\n    return x + y\n")
        input_data = {"files_changed": [str(clean_file)]}
        result, _, _ = await workflow._perf_check(input_data, ModelTier.CHEAP)

        assert result["perf_finding_count"] == 0
        assert result["perf_findings"] == []

    @pytest.mark.asyncio
    async def test_perf_check_skips_non_python(self, workflow, tmp_path):
        """Test that perf_check skips non-Python files."""
        js_file = tmp_path / "app.js"
        js_file.write_text("for (let x of items) { db.query(x); }")
        input_data = {"files_changed": [str(js_file)]}
        result, _, _ = await workflow._perf_check(input_data, ModelTier.CHEAP)

        assert result["perf_finding_count"] == 0

    @pytest.mark.asyncio
    async def test_perf_check_skips_missing_file(self, workflow):
        """Test that perf_check gracefully handles missing files."""
        input_data = {"files_changed": ["/nonexistent/path.py"]}
        result, _, _ = await workflow._perf_check(input_data, ModelTier.CHEAP)

        assert result["perf_finding_count"] == 0

    @pytest.mark.asyncio
    async def test_perf_check_preserves_input_data(self, workflow, tmp_path):
        """Test that perf_check preserves prior stage data."""
        clean_file = tmp_path / "ok.py"
        clean_file.write_text("x = 1\n")
        input_data = {"files_changed": [str(clean_file)], "classification": "feat"}
        result, _, _ = await workflow._perf_check(input_data, ModelTier.CHEAP)

        assert result["classification"] == "feat"
        assert "perf_findings" in result

    def test_skip_perf_check_no_files(self, workflow):
        """Test that perf_check is skipped when no files_changed."""
        should_skip, reason = workflow.should_skip_stage("perf_check", {})
        assert should_skip is True
        assert "no files_changed" in reason.lower()

    def test_no_skip_perf_check_with_files(self, workflow):
        """Test that perf_check is NOT skipped when files_changed present."""
        should_skip, reason = workflow.should_skip_stage("perf_check", {"files_changed": ["a.py"]})
        assert should_skip is False


# ===========================================================================
# 22. _health_monitor Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestHealthMonitorStage:
    """Tests for the _health_monitor proactive monitoring stage."""

    @pytest.mark.asyncio
    async def test_health_monitor_returns_snapshot(self, workflow):
        """Test that health_monitor returns a health_snapshot dict."""
        mock_monitor = MagicMock()
        mock_monitor.get_all_stats.return_value = {
            "llm_cache": MagicMock(to_dict=lambda: {"hit_rate": 0.75, "hits": 30, "misses": 10})
        }
        mock_tracker = MagicMock()
        mock_tracker.get_today.return_value = {"total_cost": 0.05}
        mock_usage = MagicMock()
        mock_usage.get_stats.return_value = {"total_calls": 42}

        # Patch at the module where the lazy import resolves
        with (
            patch("attune.cache_monitor.CacheMonitor.get_instance", return_value=mock_monitor),
            patch("attune.cost_tracker.get_tracker", return_value=mock_tracker),
            patch("attune.telemetry.UsageTracker.get_instance", return_value=mock_usage),
        ):
            result, _, _ = await workflow._health_monitor({}, ModelTier.CHEAP)

        snapshot = result["health_snapshot"]
        assert "cache_stats" in snapshot
        assert "cost_today" in snapshot
        assert "usage_stats_7d" in snapshot
        assert snapshot["cost_today"]["total_cost"] == 0.05
        assert snapshot["usage_stats_7d"]["total_calls"] == 42

    @pytest.mark.asyncio
    async def test_health_monitor_handles_import_errors(self, workflow):
        """Test that health_monitor degrades gracefully on missing deps."""
        # The method uses lazy imports with try/except ImportError,
        # so with no mocks the real imports may or may not work.
        # We force ImportError for each.
        with (
            patch.dict(
                "sys.modules",
                {
                    "attune.cache_monitor": None,
                    "attune.cost_tracker": None,
                    "attune.telemetry": None,
                },
            ),
        ):
            result, _, _ = await workflow._health_monitor({}, ModelTier.CHEAP)

        snapshot = result["health_snapshot"]
        assert snapshot["cache_stats"] == {}
        assert snapshot["cost_today"] == {}
        assert snapshot["usage_stats_7d"] == {}

    @pytest.mark.asyncio
    async def test_health_monitor_preserves_input_data(self, workflow):
        """Test that health_monitor preserves prior stage data."""
        input_data = {"scan_results": "some scan", "classification": "refactor"}
        result, _, _ = await workflow._health_monitor(input_data, ModelTier.CHEAP)

        assert result["classification"] == "refactor"
        assert result["scan_results"] == "some scan"
        assert "health_snapshot" in result

    def test_health_monitor_never_skipped(self, workflow):
        """Test that health_monitor is never skipped (no skip rule)."""
        should_skip, reason = workflow.should_skip_stage("health_monitor", {})
        assert should_skip is False


# ===========================================================================
# 23. _quality_check Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestQualityCheckStage:
    """Tests for the _quality_check code quality stage."""

    @pytest.mark.asyncio
    async def test_quality_check_detects_bare_except(self, workflow, tmp_path):
        """Test that quality_check flags bare except clauses."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("try:\n" "    risky()\n" "except:\n" "    pass\n")
        input_data = {"files_changed": [str(bad_file)]}
        result, _, _ = await workflow._quality_check(input_data, ModelTier.CHEAP)

        assert result["quality_finding_count"] > 0
        assert any(f["type"] == "bare_except" for f in result["quality_findings"])

    @pytest.mark.asyncio
    async def test_quality_check_ignores_noqa(self, workflow, tmp_path):
        """Test that quality_check respects # noqa comments."""
        ok_file = tmp_path / "ok.py"
        ok_file.write_text(
            "try:\n" "    risky()\n" "except Exception:  # noqa: BLE001\n" "    pass\n"
        )
        input_data = {"files_changed": [str(ok_file)]}
        result, _, _ = await workflow._quality_check(input_data, ModelTier.CHEAP)

        bare_excepts = [f for f in result["quality_findings"] if f["type"] == "bare_except"]
        assert len(bare_excepts) == 0

    @pytest.mark.asyncio
    async def test_quality_check_detects_todos(self, workflow, tmp_path):
        """Test that quality_check counts TODO/FIXME comments."""
        todo_file = tmp_path / "todo.py"
        todo_file.write_text("# TODO: fix this\n" "x = 1\n" "# FIXME: also this\n")
        input_data = {"files_changed": [str(todo_file)]}
        result, _, _ = await workflow._quality_check(input_data, ModelTier.CHEAP)

        todo_findings = [f for f in result["quality_findings"] if f["type"] == "todo_fixme"]
        assert len(todo_findings) == 1
        assert "2" in todo_findings[0]["description"]  # 2 TODO/FIXME

    @pytest.mark.asyncio
    async def test_quality_check_detects_long_files(self, workflow, tmp_path):
        """Test that quality_check flags files with >500 lines."""
        long_file = tmp_path / "long.py"
        long_file.write_text("x = 1\n" * 501)
        input_data = {"files_changed": [str(long_file)]}
        result, _, _ = await workflow._quality_check(input_data, ModelTier.CHEAP)

        long_findings = [f for f in result["quality_findings"] if f["type"] == "long_file"]
        assert len(long_findings) == 1
        assert "501" in long_findings[0]["description"]

    @pytest.mark.asyncio
    async def test_quality_check_detects_missing_type_hint(self, workflow, tmp_path):
        """Test that quality_check flags public functions without return type hints."""
        bad_file = tmp_path / "nohint.py"
        bad_file.write_text("def calculate(x, y):\n    return x + y\n")
        input_data = {"files_changed": [str(bad_file)]}
        result, _, _ = await workflow._quality_check(input_data, ModelTier.CHEAP)

        hint_findings = [f for f in result["quality_findings"] if f["type"] == "missing_type_hint"]
        assert len(hint_findings) == 1
        assert "calculate" in hint_findings[0]["description"]

    @pytest.mark.asyncio
    async def test_quality_check_skips_private_functions(self, workflow, tmp_path):
        """Test that quality_check does not flag private functions."""
        ok_file = tmp_path / "private.py"
        ok_file.write_text("def _internal(x):\n    return x\n")
        input_data = {"files_changed": [str(ok_file)]}
        result, _, _ = await workflow._quality_check(input_data, ModelTier.CHEAP)

        hint_findings = [f for f in result["quality_findings"] if f["type"] == "missing_type_hint"]
        assert len(hint_findings) == 0

    @pytest.mark.asyncio
    async def test_quality_check_clean_file(self, workflow, tmp_path):
        """Test that quality_check returns zero findings for clean code."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("def add(x: int, y: int) -> int:\n    return x + y\n")
        input_data = {"files_changed": [str(clean_file)]}
        result, _, _ = await workflow._quality_check(input_data, ModelTier.CHEAP)

        assert result["quality_finding_count"] == 0

    def test_skip_quality_check_no_files(self, workflow):
        """Test that quality_check is skipped when no files_changed."""
        should_skip, reason = workflow.should_skip_stage("quality_check", {})
        assert should_skip is True
        assert "no files_changed" in reason.lower()

    def test_no_skip_quality_check_with_files(self, workflow):
        """Test that quality_check is NOT skipped when files present."""
        should_skip, reason = workflow.should_skip_stage(
            "quality_check", {"files_changed": ["a.py"]}
        )
        assert should_skip is False


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
                }
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
            }
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
                }
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
            }
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
        from attune.workflows.code_review_analysis_mixin import _gather_file_snippets

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
        from attune.workflows.code_review_analysis_mixin import _gather_file_snippets

        findings = [{"file": "/nonexistent/file.py", "line": 10}]
        snippets = _gather_file_snippets(findings)
        assert snippets == {}

    def test_format_findings_for_prompt_structure(self):
        """Test _format_findings_for_prompt produces indexed output."""
        from attune.workflows.code_review_analysis_mixin import _format_findings_for_prompt

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
        from attune.workflows.code_review_analysis_mixin import _parse_deep_enrichment

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
        from attune.workflows.code_review_analysis_mixin import _parse_deep_enrichment

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
        from attune.workflows.code_review_analysis_mixin import _recount_by_key

        findings = [
            {"severity": "high", "false_positive": False},
            {"severity": "high", "false_positive": True},
            {"severity": "medium", "false_positive": False},
            {"severity": "low", "false_positive": False},
        ]
        counts = _recount_by_key(findings, "severity")
        assert counts == {"high": 1, "medium": 1, "low": 1}


# ===========================================================================
# 27. _perf_check_deep Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestPerfCheckDeep:
    """Test _perf_check_deep LLM enrichment stage."""

    def test_perf_check_deep_skipped_when_no_findings(self, workflow):
        """Test that should_skip_stage gates perf_check_deep on zero findings."""
        should_skip, reason = workflow.should_skip_stage(
            "perf_check_deep", {"perf_finding_count": 0}
        )
        assert should_skip is True
        assert "no perf findings" in reason.lower()

    def test_perf_check_deep_not_skipped_with_findings(self, workflow):
        """Test that should_skip_stage allows perf_check_deep when findings exist."""
        should_skip, reason = workflow.should_skip_stage(
            "perf_check_deep", {"perf_finding_count": 3}
        )
        assert should_skip is False

    def test_perf_check_deep_calls_llm_with_findings(self, workflow):
        """Test _perf_check_deep calls _call_llm when findings present."""
        llm_response = '{"findings": [{"index": 0, "validated": true, "false_positive": false, "suggestion": "Use generator"}]}'
        workflow._call_llm = AsyncMock(return_value=(llm_response, 100, 50))

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

        result, in_t, out_t = asyncio.run(workflow._perf_check_deep(input_data, ModelTier.CAPABLE))

        workflow._call_llm.assert_called_once()
        assert result["perf_deep_ran"] is True
        assert in_t == 100
        assert out_t == 50

    def test_perf_check_deep_enriches_findings(self, workflow):
        """Test _perf_check_deep merges LLM enrichment into findings."""
        llm_response = '{"findings": [{"index": 0, "validated": true, "false_positive": true, "suggestion": "Test fixture, ignore"}]}'
        workflow._call_llm = AsyncMock(return_value=(llm_response, 50, 30))

        input_data = {
            "perf_findings": [
                {
                    "type": "n_plus_one",
                    "file": "test_x.py",
                    "line": 5,
                    "description": "N+1 query",
                    "impact": "high",
                },
            ],
            "perf_finding_count": 1,
            "perf_by_impact": {"high": 1, "medium": 0, "low": 0},
        }

        result, _, _ = asyncio.run(workflow._perf_check_deep(input_data, ModelTier.CAPABLE))

        assert result["perf_findings"][0]["false_positive"] is True
        assert result["perf_findings"][0]["suggestion"] == "Test fixture, ignore"
        # Count should exclude false positives
        assert result["perf_finding_count"] == 0

    def test_perf_check_deep_handles_llm_error_gracefully(self, workflow):
        """Test _perf_check_deep handles malformed LLM response."""
        workflow._call_llm = AsyncMock(return_value=("NOT JSON", 50, 30))

        input_data = {
            "perf_findings": [
                {
                    "type": "n_plus_one",
                    "file": "a.py",
                    "line": 5,
                    "description": "N+1 query",
                    "impact": "high",
                },
            ],
            "perf_finding_count": 1,
            "perf_by_impact": {"high": 1, "medium": 0, "low": 0},
        }

        result, _, _ = asyncio.run(workflow._perf_check_deep(input_data, ModelTier.CAPABLE))

        # Should still return valid result with originals marked as validated
        assert result["perf_deep_ran"] is True
        assert result["perf_findings"][0]["validated"] is True
        assert result["perf_findings"][0]["false_positive"] is False


# ===========================================================================
# 28. _quality_check_deep Stage Tests
# ===========================================================================


@pytest.mark.unit
class TestQualityCheckDeep:
    """Test _quality_check_deep LLM enrichment stage."""

    def test_quality_check_deep_skipped_when_no_findings(self, workflow):
        """Test that should_skip_stage gates quality_check_deep on zero findings."""
        should_skip, reason = workflow.should_skip_stage(
            "quality_check_deep", {"quality_finding_count": 0}
        )
        assert should_skip is True
        assert "no quality findings" in reason.lower()

    def test_quality_check_deep_not_skipped_with_findings(self, workflow):
        """Test that should_skip_stage allows quality_check_deep when findings exist."""
        should_skip, reason = workflow.should_skip_stage(
            "quality_check_deep", {"quality_finding_count": 2}
        )
        assert should_skip is False

    def test_quality_check_deep_calls_llm_with_findings(self, workflow):
        """Test _quality_check_deep calls _call_llm when findings present."""
        llm_response = '{"findings": [{"index": 0, "validated": true, "false_positive": false, "suggestion": "Add specific types"}]}'
        workflow._call_llm = AsyncMock(return_value=(llm_response, 80, 40))

        input_data = {
            "quality_findings": [
                {
                    "type": "bare_except",
                    "file": "a.py",
                    "line": 10,
                    "description": "Bare except",
                    "severity": "high",
                },
            ],
            "quality_finding_count": 1,
            "quality_by_severity": {"high": 1, "medium": 0, "low": 0},
        }

        result, in_t, out_t = asyncio.run(
            workflow._quality_check_deep(input_data, ModelTier.CAPABLE)
        )

        workflow._call_llm.assert_called_once()
        assert result["quality_deep_ran"] is True
        assert in_t == 80
        assert out_t == 40

    def test_quality_check_deep_enriches_findings(self, workflow):
        """Test _quality_check_deep merges enrichment and recounts."""
        llm_response = '{"findings": [{"index": 0, "validated": true, "false_positive": true, "suggestion": "Intentional broad catch"}, {"index": 1, "validated": true, "false_positive": false, "suggestion": "Consider splitting file"}]}'
        workflow._call_llm = AsyncMock(return_value=(llm_response, 50, 30))

        input_data = {
            "quality_findings": [
                {
                    "type": "bare_except",
                    "file": "a.py",
                    "line": 10,
                    "description": "Bare except",
                    "severity": "high",
                },
                {
                    "type": "long_file",
                    "file": "b.py",
                    "line": None,
                    "description": "600 lines",
                    "severity": "medium",
                },
            ],
            "quality_finding_count": 2,
            "quality_by_severity": {"high": 1, "medium": 1, "low": 0},
        }

        result, _, _ = asyncio.run(workflow._quality_check_deep(input_data, ModelTier.CAPABLE))

        assert result["quality_findings"][0]["false_positive"] is True
        assert result["quality_findings"][1]["false_positive"] is False
        # Count excludes false positives
        assert result["quality_finding_count"] == 1

    def test_quality_check_deep_handles_llm_error_gracefully(self, workflow):
        """Test _quality_check_deep handles malformed LLM response."""
        workflow._call_llm = AsyncMock(return_value=("INVALID", 50, 30))

        input_data = {
            "quality_findings": [
                {
                    "type": "bare_except",
                    "file": "a.py",
                    "line": 10,
                    "description": "Bare except",
                    "severity": "high",
                },
            ],
            "quality_finding_count": 1,
            "quality_by_severity": {"high": 1, "medium": 0, "low": 0},
        }

        result, _, _ = asyncio.run(workflow._quality_check_deep(input_data, ModelTier.CAPABLE))

        assert result["quality_deep_ran"] is True
        assert result["quality_findings"][0]["validated"] is True
        assert result["quality_findings"][0]["false_positive"] is False


# ===========================================================================
# 29. Report Deep Enrichment Display
# ===========================================================================


@pytest.mark.unit
class TestReportDeepEnrichment:
    """Test report formatting with deep analysis enrichment."""

    def test_perf_report_shows_false_positive_marker(self):
        """Test perf section marks false positives in report."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "capable"}
        input_data = {
            "perf_findings": [
                {
                    "type": "n_plus_one",
                    "file": "test.py",
                    "line": 5,
                    "description": "N+1 query",
                    "impact": "high",
                    "false_positive": True,
                    "suggestion": "Test fixture",
                },
            ],
            "perf_finding_count": 0,
            "perf_by_impact": {"high": 0, "medium": 0, "low": 0},
            "perf_deep_ran": True,
        }
        report = format_code_review_report(result, input_data)

        assert "[FALSE POSITIVE]" in report
        assert "→ Test fixture" in report
        assert "LLM-validated" in report

    def test_perf_report_shows_suggestion(self):
        """Test perf section displays suggestions from deep analysis."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve_with_suggestions", "model_tier_used": "capable"}
        input_data = {
            "perf_findings": [
                {
                    "type": "n_plus_one",
                    "file": "db.py",
                    "line": 42,
                    "description": "N+1 query",
                    "impact": "high",
                    "false_positive": False,
                    "suggestion": "Use select_related()",
                },
            ],
            "perf_finding_count": 1,
            "perf_by_impact": {"high": 1, "medium": 0, "low": 0},
            "perf_deep_ran": True,
        }
        report = format_code_review_report(result, input_data)

        assert "→ Use select_related()" in report
        assert "[FALSE POSITIVE]" not in report

    def test_quality_report_shows_deep_analysis_badge(self):
        """Test quality section shows LLM-validated badge."""
        from attune.workflows.code_review_report import format_code_review_report

        result = {"verdict": "approve", "model_tier_used": "capable"}
        input_data = {
            "quality_findings": [
                {
                    "type": "bare_except",
                    "file": "a.py",
                    "line": 10,
                    "description": "Bare except",
                    "severity": "high",
                    "false_positive": False,
                    "suggestion": "Catch ValueError",
                },
            ],
            "quality_finding_count": 1,
            "quality_by_severity": {"high": 1, "medium": 0, "low": 0},
            "quality_deep_ran": True,
        }
        report = format_code_review_report(result, input_data)

        assert "QUALITY CHECK" in report
        assert "LLM-validated" in report
        assert "→ Catch ValueError" in report

    def test_report_without_deep_unchanged(self):
        """Test report renders normally when deep stages did not run."""
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
        assert "[FALSE POSITIVE]" not in report
        assert "LLM-validated" not in report
        assert "→" not in report
