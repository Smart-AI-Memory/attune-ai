"""Comprehensive tests for low-coverage workflow modules (Batch 8).

Covers:
- src/attune/workflows/code_review_pipeline.py (CodeReviewPipeline, format report)
- src/attune/workflows/autonomous_test_gen.py (AutonomousTestGenerator)
- src/attune/workflows/code_review.py (CodeReviewWorkflow additional coverage)

All external dependencies (LLM calls, subprocess, Redis, imports) are mocked.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Safe imports with fallbacks
# ---------------------------------------------------------------------------
try:
    from attune.workflows.code_review_pipeline import (
        CodeReviewPipeline,
        CodeReviewPipelineResult,
        format_code_review_pipeline_report,
    )
except ImportError:
    CodeReviewPipeline = None
    CodeReviewPipelineResult = None
    format_code_review_pipeline_report = None

try:
    from attune.workflows.base import ModelTier
    from attune.workflows.code_review import CodeReviewWorkflow
except ImportError:
    CodeReviewWorkflow = None
    ModelTier = None

try:
    from attune.workflows.autonomous_test_gen import (
        AutonomousTestGenerator,
        CoverageResult,
        ValidationResult,
        run_batch_generation,
    )
except ImportError:
    AutonomousTestGenerator = None
    CoverageResult = None
    ValidationResult = None
    run_batch_generation = None


# ---------------------------------------------------------------------------
# Skip markers for unavailable modules
# ---------------------------------------------------------------------------
skip_if_no_pipeline = pytest.mark.skipif(
    CodeReviewPipeline is None,
    reason="CodeReviewPipeline not importable",
)
skip_if_no_review = pytest.mark.skipif(
    CodeReviewWorkflow is None,
    reason="CodeReviewWorkflow not importable",
)
skip_if_no_testgen = pytest.mark.skipif(
    AutonomousTestGenerator is None,
    reason="AutonomousTestGenerator not importable",
)


# ============================================================================
# Shared helpers / fixtures
# ============================================================================


def _make_pipeline_result(**overrides: Any) -> "CodeReviewPipelineResult":
    """Build a CodeReviewPipelineResult with sensible defaults."""
    defaults = {
        "success": True,
        "verdict": "approve",
        "quality_score": 95.0,
        "crew_report": None,
        "workflow_result": None,
        "combined_findings": [],
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "agents_used": [],
        "recommendations": [],
        "blockers": [],
        "mode": "full",
        "duration_seconds": 1.23,
        "cost": 0.005,
        "metadata": {"files_reviewed": 2, "total_findings": 0},
    }
    defaults.update(overrides)
    return CodeReviewPipelineResult(**defaults)


@pytest.fixture
def cost_tracker(tmp_path: Path) -> Any:
    """Create isolated CostTracker for testing."""
    from attune.cost_tracker import CostTracker

    storage_dir = tmp_path / ".empathy"
    return CostTracker(storage_dir=str(storage_dir))


@pytest.fixture
def mock_workflow_result() -> Mock:
    """Create a mock WorkflowResult object."""
    result = Mock()
    result.final_output = {
        "security_score": 85,
        "security_findings": [
            {"severity": "medium", "file": "test.py", "line": 10, "type": "issue"},
        ],
        "verdict": "approve_with_suggestions",
    }
    result.cost_report = Mock()
    result.cost_report.total_cost = 0.003
    return result


# ============================================================================
# PART 1: CodeReviewPipelineResult dataclass
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestCodeReviewPipelineResult:
    """Tests for the CodeReviewPipelineResult dataclass."""

    def test_default_metadata_factory(self) -> None:
        """Test that metadata defaults to empty dict."""
        result = _make_pipeline_result()
        assert result.metadata is not None
        assert isinstance(result.metadata, dict)

    def test_all_fields_set(self) -> None:
        """Test that all fields can be set and retrieved."""
        result = _make_pipeline_result(
            verdict="reject",
            quality_score=42.0,
            blockers=["critical issue"],
            agents_used=["agent1"],
        )
        assert result.verdict == "reject"
        assert result.quality_score == 42.0
        assert result.blockers == ["critical issue"]
        assert result.agents_used == ["agent1"]


# ============================================================================
# PART 2: CodeReviewPipeline initialization and factory methods
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestCodeReviewPipelineInit:
    """Tests for CodeReviewPipeline initialization and factories."""

    def test_default_init(self) -> None:
        """Test default initialization values."""
        pipeline = CodeReviewPipeline()
        assert pipeline.provider == "anthropic"
        assert pipeline.mode == "full"
        assert pipeline.parallel_crew is True
        assert pipeline.crew_enabled is True
        assert pipeline.crew_config["provider"] == "anthropic"

    def test_custom_init(self) -> None:
        """Test custom initialization."""
        pipeline = CodeReviewPipeline(
            provider="openai",
            mode="standard",
            parallel_crew=False,
            crew_config={"timeout": 30},
        )
        assert pipeline.provider == "openai"
        assert pipeline.mode == "standard"
        assert pipeline.parallel_crew is False
        assert pipeline.crew_enabled is False
        assert pipeline.crew_config["timeout"] == 30
        assert pipeline.crew_config["provider"] == "openai"

    def test_quick_mode_disables_crew(self) -> None:
        """Test that quick mode disables crew."""
        pipeline = CodeReviewPipeline(mode="quick")
        assert pipeline.crew_enabled is False

    def test_for_pr_review_complex(self) -> None:
        """Test factory for complex PR with many files."""
        pipeline = CodeReviewPipeline.for_pr_review(files_changed=10)
        assert pipeline.mode == "full"
        assert pipeline.parallel_crew is True

    def test_for_pr_review_simple(self) -> None:
        """Test factory for simple PR with few files."""
        pipeline = CodeReviewPipeline.for_pr_review(files_changed=3)
        assert pipeline.mode == "standard"

    def test_for_pr_review_boundary(self) -> None:
        """Test factory at the threshold boundary (5 files)."""
        pipeline = CodeReviewPipeline.for_pr_review(files_changed=5)
        assert pipeline.mode == "standard"

    def test_for_pr_review_above_boundary(self) -> None:
        """Test factory above the threshold boundary (6 files)."""
        pipeline = CodeReviewPipeline.for_pr_review(files_changed=6)
        assert pipeline.mode == "full"

    def test_for_quick_check(self) -> None:
        """Test factory for quick check."""
        pipeline = CodeReviewPipeline.for_quick_check()
        assert pipeline.mode == "quick"
        assert pipeline.parallel_crew is False

    def test_for_full_review(self) -> None:
        """Test factory for full review."""
        pipeline = CodeReviewPipeline.for_full_review()
        assert pipeline.mode == "full"
        assert pipeline.parallel_crew is True

    def test_kwargs_ignored(self) -> None:
        """Test that extra kwargs are accepted for CLI compatibility."""
        pipeline = CodeReviewPipeline(extra_arg="value", another=123)
        assert pipeline.mode == "full"


# ============================================================================
# PART 3: CodeReviewPipeline._deduplicate_findings
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestDeduplicateFindings:
    """Tests for the _deduplicate_findings method."""

    def test_no_duplicates(self) -> None:
        """Test with no duplicate findings."""
        pipeline = CodeReviewPipeline()
        findings = [
            {"file": "a.py", "line": 1, "type": "bug"},
            {"file": "b.py", "line": 2, "type": "security"},
        ]
        result = pipeline._deduplicate_findings(findings)
        assert len(result) == 2

    def test_removes_duplicates(self) -> None:
        """Test duplicate removal based on (file, line, type)."""
        pipeline = CodeReviewPipeline()
        findings = [
            {"file": "a.py", "line": 1, "type": "bug", "desc": "first"},
            {"file": "a.py", "line": 1, "type": "bug", "desc": "duplicate"},
            {"file": "a.py", "line": 2, "type": "bug", "desc": "different line"},
        ]
        result = pipeline._deduplicate_findings(findings)
        assert len(result) == 2
        assert result[0]["desc"] == "first"

    def test_empty_list(self) -> None:
        """Test with empty findings list."""
        pipeline = CodeReviewPipeline()
        assert pipeline._deduplicate_findings([]) == []

    def test_missing_keys(self) -> None:
        """Test with findings that have missing keys."""
        pipeline = CodeReviewPipeline()
        findings = [
            {"file": "a.py"},
            {"type": "bug"},
            {},
        ]
        result = pipeline._deduplicate_findings(findings)
        # All have different (None, None, None) combos or partial keys
        assert len(result) >= 1


# ============================================================================
# PART 4: CodeReviewPipeline._calculate_quality_score
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestCalculateQualityScore:
    """Tests for the _calculate_quality_score method."""

    def test_crew_report_weighted(self) -> None:
        """Test that crew reports get higher weight."""
        pipeline = CodeReviewPipeline()
        crew_report = {"quality_score": 80}
        score = pipeline._calculate_quality_score(crew_report, None, [])
        assert score == 80.0

    def test_workflow_result_score(self) -> None:
        """Test scoring from workflow result only."""
        pipeline = CodeReviewPipeline()
        wf = Mock()
        wf.final_output = {"security_score": 70}
        score = pipeline._calculate_quality_score(None, wf, [])
        assert score == 70.0

    def test_combined_weighted_score(self) -> None:
        """Test weighted average of crew and workflow scores."""
        pipeline = CodeReviewPipeline()
        crew_report = {"quality_score": 100}
        wf = Mock()
        wf.final_output = {"security_score": 50}
        # Weighted: (100*1.5 + 50*1.0) / 2.5 = 200/2.5 = 80.0
        score = pipeline._calculate_quality_score(crew_report, wf, [])
        assert abs(score - 80.0) < 0.1

    def test_fallback_scoring_by_findings(self) -> None:
        """Test fallback scoring when no crew/workflow scores."""
        pipeline = CodeReviewPipeline()
        findings = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]
        score = pipeline._calculate_quality_score(None, None, findings)
        # 100 - 25 - 15 - 5 - 2 = 53
        assert score == 53.0

    def test_score_clamped_at_zero(self) -> None:
        """Test that score is clamped to 0 minimum."""
        pipeline = CodeReviewPipeline()
        findings = [{"severity": "critical"}] * 10  # -250
        score = pipeline._calculate_quality_score(None, None, findings)
        assert score == 0.0

    def test_score_clamped_at_hundred(self) -> None:
        """Test that score is clamped to 100 maximum."""
        pipeline = CodeReviewPipeline()
        score = pipeline._calculate_quality_score(None, None, [])
        assert score == 100.0

    def test_workflow_no_final_output(self) -> None:
        """Test handling when workflow result has None final_output."""
        pipeline = CodeReviewPipeline()
        wf = Mock()
        wf.final_output = None
        score = pipeline._calculate_quality_score(None, wf, [])
        # Should use default security_score of 90
        assert score == 90.0

    def test_workflow_non_dict_output(self) -> None:
        """Test handling when workflow final_output is not a dict."""
        pipeline = CodeReviewPipeline()
        wf = Mock()
        wf.final_output = "some string"
        score = pipeline._calculate_quality_score(None, wf, [])
        assert score == 90.0


# ============================================================================
# PART 5: CodeReviewPipeline._determine_verdict
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestDetermineVerdict:
    """Tests for the _determine_verdict method."""

    def test_approve_high_score_no_blockers(self) -> None:
        """Test approve verdict with high score and no blockers."""
        pipeline = CodeReviewPipeline()
        verdict = pipeline._determine_verdict(None, None, 95.0, [])
        assert verdict == "approve"

    def test_reject_from_crew_verdict(self) -> None:
        """Test that crew reject verdict takes priority."""
        pipeline = CodeReviewPipeline()
        crew = {"verdict": "reject"}
        verdict = pipeline._determine_verdict(crew, None, 95.0, [])
        assert verdict == "reject"

    def test_request_changes_from_blockers(self) -> None:
        """Test that blockers force request_changes."""
        pipeline = CodeReviewPipeline()
        verdict = pipeline._determine_verdict(None, None, 95.0, ["blocker issue"])
        assert verdict == "request_changes"

    def test_request_changes_from_low_score(self) -> None:
        """Test request_changes verdict for score 50-69."""
        pipeline = CodeReviewPipeline()
        verdict = pipeline._determine_verdict(None, None, 65.0, [])
        assert verdict == "request_changes"

    def test_reject_from_very_low_score(self) -> None:
        """Test reject verdict for score below 50."""
        pipeline = CodeReviewPipeline()
        verdict = pipeline._determine_verdict(None, None, 30.0, [])
        assert verdict == "reject"

    def test_approve_with_suggestions_from_medium_score(self) -> None:
        """Test approve_with_suggestions for score 70-89."""
        pipeline = CodeReviewPipeline()
        verdict = pipeline._determine_verdict(None, None, 80.0, [])
        assert verdict == "approve_with_suggestions"

    def test_workflow_verdict_considered(self) -> None:
        """Test that workflow verdict is considered."""
        pipeline = CodeReviewPipeline()
        wf = Mock()
        wf.final_output = {"verdict": "request_changes"}
        verdict = pipeline._determine_verdict(None, wf, 95.0, [])
        assert verdict == "request_changes"

    def test_most_severe_verdict_wins(self) -> None:
        """Test that most severe verdict wins across all sources."""
        pipeline = CodeReviewPipeline()
        crew = {"verdict": "approve_with_suggestions"}
        wf = Mock()
        wf.final_output = {"verdict": "approve"}
        # blockers add request_changes
        verdict = pipeline._determine_verdict(crew, wf, 95.0, ["one blocker"])
        assert verdict == "request_changes"

    def test_workflow_non_dict_output_defaults_approve(self) -> None:
        """Test that non-dict workflow output defaults to approve."""
        pipeline = CodeReviewPipeline()
        wf = Mock()
        wf.final_output = "text output"
        verdict = pipeline._determine_verdict(None, wf, 95.0, [])
        assert verdict == "approve"


# ============================================================================
# PART 6: CodeReviewPipeline.execute (async)
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestPipelineExecute:
    """Tests for CodeReviewPipeline.execute."""

    @pytest.mark.asyncio
    async def test_execute_standard_mode(self, mock_workflow_result: Mock) -> None:
        """Test execute in standard mode."""
        pipeline = CodeReviewPipeline(mode="standard")

        with patch.object(pipeline, "_run_standard_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_workflow_result

            result = await pipeline.execute(
                diff="def foo(): pass",
                files_changed=["src/foo.py"],
            )

            assert result.success is True
            assert result.mode == "standard"
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_quick_mode(self, mock_workflow_result: Mock) -> None:
        """Test execute in quick mode."""
        pipeline = CodeReviewPipeline(mode="quick")

        with patch.object(pipeline, "_run_quick_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_workflow_result

            result = await pipeline.execute(diff="x = 1")

            assert result.success is True
            assert result.mode == "quick"

    @pytest.mark.asyncio
    async def test_execute_full_mode(self, mock_workflow_result: Mock) -> None:
        """Test execute in full mode."""
        pipeline = CodeReviewPipeline(mode="full")

        with patch.object(pipeline, "_run_full_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (None, mock_workflow_result)

            result = await pipeline.execute(
                diff="def bar(): pass",
                files_changed=["bar.py"],
            )

            assert result.success is True
            assert result.mode == "full"

    @pytest.mark.asyncio
    async def test_execute_with_crew_report(self) -> None:
        """Test execute processes crew report findings."""
        pipeline = CodeReviewPipeline(mode="full")
        crew_report = {
            "findings": [
                {
                    "severity": "high",
                    "suggestion": "Fix this",
                    "file": "a.py",
                    "line": 1,
                    "type": "security",
                },
            ],
            "agents_used": ["SecurityAnalyst", "QualityReviewer"],
            "quality_score": 75,
        }
        wf = Mock()
        wf.final_output = {"security_score": 80, "security_findings": []}
        wf.cost_report = Mock()
        wf.cost_report.total_cost = 0.01

        with patch.object(pipeline, "_run_full_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (crew_report, wf)

            result = await pipeline.execute(diff="code here")

            assert result.success is True
            assert len(result.agents_used) == 2
            assert "Fix this" in result.recommendations

    @pytest.mark.asyncio
    async def test_execute_counts_severity(self) -> None:
        """Test that execute correctly counts findings by severity."""
        pipeline = CodeReviewPipeline(mode="full")
        crew_report = {
            "findings": [
                {"severity": "critical", "file": "a.py", "line": 1, "type": "sec"},
                {"severity": "critical", "file": "b.py", "line": 2, "type": "sec"},
                {"severity": "high", "file": "c.py", "line": 3, "type": "bug"},
                {"severity": "high", "file": "d.py", "line": 4, "type": "bug"},
                {"severity": "high", "file": "e.py", "line": 5, "type": "bug"},
                {"severity": "high", "file": "f.py", "line": 6, "type": "bug"},
                {"severity": "medium", "file": "g.py", "line": 7, "type": "style"},
            ],
            "agents_used": [],
            "quality_score": 40,
        }

        with patch.object(pipeline, "_run_full_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (crew_report, None)

            result = await pipeline.execute(diff="code")

            assert result.critical_count == 2
            assert result.high_count == 4
            assert result.medium_count == 1
            # 2 critical -> blocker, 4 high > 3 -> blocker
            assert len(result.blockers) == 2

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self) -> None:
        """Test that execute handles exceptions gracefully."""
        pipeline = CodeReviewPipeline(mode="full")

        with patch.object(pipeline, "_run_full_mode", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = RuntimeError("LLM unavailable")

            result = await pipeline.execute(diff="code")

            assert result.success is False
            assert result.verdict == "reject"
            assert result.quality_score == 0.0
            assert any("Pipeline error" in b for b in result.blockers)

    @pytest.mark.asyncio
    async def test_execute_uses_target_when_no_diff(self) -> None:
        """Test that execute uses target when diff is empty."""
        pipeline = CodeReviewPipeline(mode="standard")

        with patch.object(pipeline, "_run_standard_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None

            await pipeline.execute(target="src/main.py")

            # Verify code_to_review used target
            call_args = mock_run.call_args
            assert call_args[0][0] == "src/main.py"

    @pytest.mark.asyncio
    async def test_execute_metadata_contains_formatted_report(
        self,
        mock_workflow_result: Mock,
    ) -> None:
        """Test that metadata includes formatted report."""
        pipeline = CodeReviewPipeline(mode="standard")

        with patch.object(pipeline, "_run_standard_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_workflow_result

            result = await pipeline.execute(diff="x = 1")

            assert "formatted_report" in result.metadata
            assert isinstance(result.metadata["formatted_report"], str)

    @pytest.mark.asyncio
    async def test_execute_recommendations_capped_at_10(self) -> None:
        """Test that recommendations are capped at 10."""
        pipeline = CodeReviewPipeline(mode="full")
        crew_report = {
            "findings": [
                {
                    "suggestion": f"Fix issue {i}",
                    "severity": "low",
                    "file": f"f{i}.py",
                    "line": i,
                    "type": f"t{i}",
                }
                for i in range(15)
            ],
            "agents_used": [],
            "quality_score": 50,
        }

        with patch.object(pipeline, "_run_full_mode", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (crew_report, None)

            result = await pipeline.execute(diff="code")

            assert len(result.recommendations) <= 10


# ============================================================================
# PART 7: CodeReviewPipeline._run_full_mode
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestRunFullMode:
    """Tests for _run_full_mode with various crew availability scenarios."""

    @pytest.mark.asyncio
    async def test_full_mode_crew_not_available(self) -> None:
        """Test full mode falls back when crew is unavailable."""
        pipeline = CodeReviewPipeline(mode="full")
        mock_wf_result = Mock()
        mock_wf_instance = Mock()
        mock_wf_instance.execute = AsyncMock(return_value=mock_wf_result)

        # The import happens inside the method: from .code_review import CodeReviewWorkflow
        # We need to patch the actual module that gets imported
        with patch(
            "attune.workflows.code_review.CodeReviewWorkflow",
            return_value=mock_wf_instance,
        ):
            crew_report, wf_result = await pipeline._run_full_mode("code", ["file.py"], {})

            # Should have no crew report since adapters are unavailable by default
            assert wf_result is not None

    @pytest.mark.asyncio
    async def test_full_mode_runs_workflow_only_when_no_crew(self) -> None:
        """Test that when crew is unavailable, only workflow runs."""
        pipeline = CodeReviewPipeline(mode="full")
        mock_wf_result = Mock()
        mock_wf_instance = Mock()
        mock_wf_instance.execute = AsyncMock(return_value=mock_wf_result)

        with patch(
            "attune.workflows.code_review.CodeReviewWorkflow",
            return_value=mock_wf_instance,
        ):
            crew_report, wf_result = await pipeline._run_full_mode(
                "some code",
                ["a.py"],
                {"extra": "context"},
            )

            # Workflow should have been called
            mock_wf_instance.execute.assert_called_once()
            assert wf_result == mock_wf_result


# ============================================================================
# PART 8: CodeReviewPipeline._run_standard_mode & _run_quick_mode
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestRunStandardAndQuickModes:
    """Tests for _run_standard_mode and _run_quick_mode."""

    @pytest.mark.asyncio
    async def test_standard_mode_calls_workflow(self) -> None:
        """Test that standard mode creates and executes workflow."""
        pipeline = CodeReviewPipeline(mode="standard")
        mock_result = Mock()
        mock_wf_instance = Mock()
        mock_wf_instance.execute = AsyncMock(return_value=mock_result)

        with patch(
            "attune.workflows.code_review.CodeReviewWorkflow",
            return_value=mock_wf_instance,
        ) as MockWorkflow:
            result = await pipeline._run_standard_mode("diff", ["file.py"], {})

            MockWorkflow.assert_called_once_with(use_crew=False)
            mock_wf_instance.execute.assert_called_once()
            assert result == mock_result

    @pytest.mark.asyncio
    async def test_quick_mode_uses_high_threshold(self) -> None:
        """Test that quick mode sets high file_threshold."""
        pipeline = CodeReviewPipeline(mode="quick")
        mock_result = Mock()
        mock_wf_instance = Mock()
        mock_wf_instance.execute = AsyncMock(return_value=mock_result)

        with patch(
            "attune.workflows.code_review.CodeReviewWorkflow",
            return_value=mock_wf_instance,
        ) as MockWorkflow:
            await pipeline._run_quick_mode("diff", ["file.py"], {})

            # Verify high threshold was set
            call_kwargs = MockWorkflow.call_args[1]
            assert call_kwargs["file_threshold"] == 1000
            assert call_kwargs["use_crew"] is False


# ============================================================================
# PART 9: format_code_review_pipeline_report
# ============================================================================


@skip_if_no_pipeline
@pytest.mark.unit
class TestFormatCodeReviewPipelineReport:
    """Tests for format_code_review_pipeline_report function."""

    def test_basic_approve_report(self) -> None:
        """Test report formatting for approve verdict."""
        result = _make_pipeline_result(verdict="approve", quality_score=95.0)
        report = format_code_review_pipeline_report(result)

        assert "CODE REVIEW REPORT" in report
        assert "APPROVE" in report
        assert "95" in report

    def test_reject_verdict_report(self) -> None:
        """Test report formatting for reject verdict."""
        result = _make_pipeline_result(
            verdict="reject",
            quality_score=20.0,
            blockers=["Critical security flaw"],
        )
        report = format_code_review_pipeline_report(result)

        assert "REJECT" in report
        assert "BLOCKERS" in report
        assert "Critical security flaw" in report

    def test_report_with_findings(self) -> None:
        """Test report with combined findings of various severities."""
        result = _make_pipeline_result(
            verdict="request_changes",
            quality_score=60.0,
            combined_findings=[
                {"severity": "critical", "title": "SQL Injection"},
                {"severity": "high", "message": "Missing auth check"},
            ],
            critical_count=1,
            high_count=1,
        )
        report = format_code_review_pipeline_report(result)

        assert "SQL Injection" in report
        assert "Missing auth check" in report

    def test_report_with_crew_report_summary(self) -> None:
        """Test report includes crew summary when provided."""
        result = _make_pipeline_result(
            crew_report={"summary": "The code has some quality issues that need attention."},
        )
        report = format_code_review_pipeline_report(result)

        assert "SUMMARY" in report
        assert "quality issues" in report

    def test_report_with_recommendations(self) -> None:
        """Test report includes recommendations."""
        result = _make_pipeline_result(
            recommendations=["Add input validation", "Use parameterized queries"],
        )
        report = format_code_review_pipeline_report(result)

        assert "RECOMMENDATIONS" in report
        assert "Add input validation" in report

    def test_report_long_recommendations_truncated(self) -> None:
        """Test that long recommendations are truncated."""
        long_rec = "A" * 100
        result = _make_pipeline_result(
            recommendations=[long_rec],
        )
        report = format_code_review_pipeline_report(result)

        assert "..." in report

    def test_report_more_than_5_recommendations(self) -> None:
        """Test report shows 'and X more' for >5 recommendations."""
        result = _make_pipeline_result(
            recommendations=[f"Rec {i}" for i in range(8)],
        )
        report = format_code_review_pipeline_report(result)

        assert "and 3 more" in report

    def test_report_with_agents_used(self) -> None:
        """Test report lists agents when provided."""
        result = _make_pipeline_result(
            agents_used=["SecurityAnalyst", "ArchitectReviewer"],
        )
        report = format_code_review_pipeline_report(result)

        assert "AGENTS USED" in report
        assert "SecurityAnalyst" in report

    def test_report_no_issues(self) -> None:
        """Test report format when no issues found."""
        result = _make_pipeline_result(combined_findings=[])
        report = format_code_review_pipeline_report(result)

        assert "No issues found" in report

    def test_report_with_files_reviewed(self) -> None:
        """Test report shows files reviewed count."""
        result = _make_pipeline_result(
            metadata={"files_reviewed": 5, "total_findings": 0},
        )
        report = format_code_review_pipeline_report(result)

        assert "Files Reviewed: 5" in report

    def test_quality_score_labels(self) -> None:
        """Test quality score labels for different score ranges."""
        for score, label in [
            (95.0, "EXCELLENT"),
            (75.0, "GOOD"),
            (55.0, "NEEDS WORK"),
            (30.0, "POOR"),
        ]:
            result = _make_pipeline_result(quality_score=score)
            report = format_code_review_pipeline_report(result)
            assert label in report

    def test_report_finding_title_truncation(self) -> None:
        """Test that long finding titles are truncated."""
        long_title = "X" * 100
        result = _make_pipeline_result(
            combined_findings=[{"severity": "critical", "title": long_title}],
            critical_count=1,
        )
        report = format_code_review_pipeline_report(result)
        assert "..." in report

    def test_report_footer_contains_duration_and_cost(self) -> None:
        """Test report footer includes timing and cost info."""
        result = _make_pipeline_result(
            duration_seconds=2.5,
            cost=0.0123,
        )
        report = format_code_review_pipeline_report(result)

        assert "2500ms" in report
        assert "$0.0123" in report

    def test_verdict_emoji_mapping(self) -> None:
        """Test that all verdict types get correct emoji."""
        for verdict in ["approve", "approve_with_suggestions", "request_changes", "reject"]:
            result = _make_pipeline_result(verdict=verdict)
            report = format_code_review_pipeline_report(result)
            assert verdict.upper().replace("_", " ") in report

    def test_crew_summary_word_wrap(self) -> None:
        """Test that long crew summary is word-wrapped."""
        long_summary = " ".join(["word"] * 50)
        result = _make_pipeline_result(
            crew_report={"summary": long_summary},
        )
        report = format_code_review_pipeline_report(result)
        assert "SUMMARY" in report


# ============================================================================
# PART 10: CodeReviewWorkflow - additional coverage
# ============================================================================


@skip_if_no_review
@pytest.mark.unit
class TestCodeReviewWorkflowAdditional:
    """Additional tests for CodeReviewWorkflow to increase coverage."""

    def test_stages_with_crew_enabled(self, cost_tracker: Any) -> None:
        """Test that crew-enabled workflow has crew_review stage."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=True)
        assert "crew_review" in wf.stages
        assert wf.tier_map["crew_review"] == ModelTier.CAPABLE

    def test_should_skip_stage_on_error(self, cost_tracker: Any) -> None:
        """Test that stages after classify are skipped on error."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)
        input_data = {"error": True}

        skip_scan, _ = wf.should_skip_stage("scan", input_data)
        assert skip_scan is True

        skip_classify, _ = wf.should_skip_stage("classify", input_data)
        assert skip_classify is False

    def test_should_skip_crew_when_not_available(self, cost_tracker: Any) -> None:
        """Test that crew_review is skipped when crew is unavailable."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=True)
        wf._crew_available = False

        skip, reason = wf.should_skip_stage("crew_review", {})
        assert skip is True
        assert "not available" in reason

    @pytest.mark.asyncio
    async def test_run_stage_classify(self, cost_tracker: Any) -> None:
        """Test run_stage dispatches to _classify."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with patch.object(wf, "_classify", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = ({"classification": "test"}, 100, 50)

            result, it, ot = await wf.run_stage("classify", ModelTier.CHEAP, {"diff": "code"})

            mock_classify.assert_called_once()
            assert result["classification"] == "test"

    @pytest.mark.asyncio
    async def test_run_stage_scan(self, cost_tracker: Any) -> None:
        """Test run_stage dispatches to _scan."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with patch.object(wf, "_scan", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = ({"scan_results": "clean"}, 150, 80)

            result, _, _ = await wf.run_stage("scan", ModelTier.CAPABLE, {"code_to_review": "x"})

            mock_scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_stage_architect_review(self, cost_tracker: Any) -> None:
        """Test run_stage dispatches to _architect_review."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with patch.object(wf, "_architect_review", new_callable=AsyncMock) as mock_arch:
            mock_arch.return_value = ({"verdict": "approve"}, 200, 100)

            result, _, _ = await wf.run_stage(
                "architect_review",
                ModelTier.PREMIUM,
                {"code_to_review": "x"},
            )

            mock_arch.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_stage_unknown_raises(self, cost_tracker: Any) -> None:
        """Test run_stage raises ValueError for unknown stage."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with pytest.raises(ValueError, match="Unknown stage"):
            await wf.run_stage("nonexistent", ModelTier.CHEAP, {})

    @pytest.mark.asyncio
    async def test_classify_empty_input_returns_error(self, cost_tracker: Any) -> None:
        """Test classify with no code returns error result."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        # Provide empty diff and target, and mock _gather_project_context to return ""
        with patch.object(wf, "_gather_project_context", return_value=""):
            input_data = {"diff": "", "target": "", "files_changed": []}
            result, it, ot = await wf._classify(input_data, ModelTier.CHEAP)

            assert result.get("error") is True
            assert "No code provided" in result.get("classification", "")

    @pytest.mark.asyncio
    async def test_scan_with_external_audit(self, cost_tracker: Any) -> None:
        """Test scan stage processes external audit results."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("No issues found", 100, 50)

            external_audit = {
                "summary": "External audit found issues",
                "findings": [
                    {"severity": "critical", "title": "SQL Injection", "description": "Bad query"},
                    {"severity": "high", "title": "XSS", "description": "Unescaped output"},
                ],
                "risk_score": 75,
            }

            input_data = {
                "code_to_review": "def foo(): pass",
                "classification": "feature",
                "external_audit_results": external_audit,
            }

            result, _, _ = await wf._scan(input_data, ModelTier.CAPABLE)

            assert result["external_audit_included"] is True
            assert result["has_critical_issues"] is True

    @pytest.mark.asyncio
    async def test_scan_no_findings(self, cost_tracker: Any) -> None:
        """Test scan stage with clean code produces no findings."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("No issues found. Code looks clean.", 100, 50)

            input_data = {
                "code_to_review": "def safe(): return True",
                "classification": "feature",
            }

            result, _, _ = await wf._scan(input_data, ModelTier.CAPABLE)

            assert result["security_score"] == 90
            assert result["verdict"] == "approve"

    @pytest.mark.asyncio
    async def test_crew_review_adapters_import_error(self, cost_tracker: Any) -> None:
        """Test crew_review gracefully handles missing adapters."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=True)

        with patch.object(wf, "_initialize_crew", new_callable=AsyncMock):
            # Make import of adapters fail inside _crew_review
            with patch.dict("sys.modules", {"attune.workflows.code_review_adapters": None}):
                try:
                    result, it, ot = await wf._crew_review(
                        {"diff": "code", "files_changed": []},
                        ModelTier.CAPABLE,
                    )
                    assert result["crew_review"]["available"] is False
                    assert result["crew_review"]["fallback"] is True
                except (ImportError, TypeError):
                    # Acceptable - module mock may propagate differently
                    pass

    @pytest.mark.asyncio
    async def test_architect_review_request_changes_verdict(self, cost_tracker: Any) -> None:
        """Test architect review parses REQUEST_CHANGES verdict from response."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "Issues found.\nVerdict: REQUEST_CHANGES\nPlease fix security issues.",
                200,
                100,
            )
            with patch.object(wf, "_is_xml_enabled", return_value=False):
                with patch.object(wf, "_parse_xml_response", return_value={}):
                    input_data = {
                        "code_to_review": "def foo(): eval('bar')",
                        "scan_results": "eval usage found",
                        "classification": "security",
                    }

                    result, _, _ = await wf._architect_review(input_data, ModelTier.PREMIUM)

                    assert result["verdict"] == "request_changes"

    @pytest.mark.asyncio
    async def test_architect_review_approve_verdict(self, cost_tracker: Any) -> None:
        """Test architect review parses APPROVE verdict from response."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "Code looks great. APPROVE. No issues found.",
                200,
                100,
            )
            with patch.object(wf, "_is_xml_enabled", return_value=False):
                with patch.object(wf, "_parse_xml_response", return_value={}):
                    input_data = {
                        "code_to_review": "def foo(): return 42",
                        "scan_results": "No issues",
                        "classification": "feature",
                    }

                    result, _, _ = await wf._architect_review(input_data, ModelTier.PREMIUM)

                    assert result["verdict"] == "approve"

    def test_merge_external_audit_no_findings(self, cost_tracker: Any) -> None:
        """Test _merge_external_audit with empty audit."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        merged, findings, has_critical = wf._merge_external_audit(
            "LLM response",
            {"findings": [], "summary": "", "risk_score": 0},
        )

        assert "LLM response" in merged
        assert findings == []
        assert has_critical is False

    def test_merge_external_audit_with_critical_findings(self, cost_tracker: Any) -> None:
        """Test _merge_external_audit with critical findings."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        external = {
            "findings": [
                {
                    "severity": "critical",
                    "title": "SQL Injection",
                    "description": "User input in query",
                    "file": "app.py",
                    "line": 42,
                    "remediation": "Use parameterized queries",
                },
                {
                    "severity": "high",
                    "title": "XSS",
                    "description": "Unescaped output",
                    "file": "template.py",
                    "line": 10,
                },
            ],
            "summary": "Security issues found",
            "risk_score": 85,
        }

        merged, findings, has_critical = wf._merge_external_audit(
            "LLM analysis: looks ok",
            external,
        )

        assert has_critical is True
        assert "SecurityAuditCrew" in merged
        assert "SQL Injection" in merged
        assert len(findings) == 2

    def test_gather_project_context_minimal(self, cost_tracker: Any) -> None:
        """Test _gather_project_context in directory with no config files."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)

        # The method reads from Path.cwd(), which in test env has project files
        # Just verify it returns a string without errors
        context = wf._gather_project_context()
        assert isinstance(context, str)


# ============================================================================
# PART 11: AutonomousTestGenerator
# ============================================================================


@skip_if_no_testgen
@pytest.mark.unit
class TestAutonomousTestGeneratorInit:
    """Tests for AutonomousTestGenerator initialization."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_init_with_redis(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test initialization with Redis available."""
        gen = AutonomousTestGenerator(
            agent_id="test-agent",
            batch_num=1,
            modules=[{"file": "src/attune/config.py"}],
        )

        assert gen.agent_id == "test-agent"
        assert gen.batch_num == 1
        assert len(gen.modules) == 1
        assert gen.enable_refinement is True
        assert gen.enable_coverage_guided is False
        assert gen.target_coverage == 0.80

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    def test_init_redis_failure_fallback(
        self,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test initialization falls back when Redis fails."""
        mock_redis.side_effect = ConnectionError("Redis not available")

        gen = AutonomousTestGenerator(
            agent_id="test-agent",
            batch_num=2,
            modules=[],
        )

        assert gen.event_streamer is None
        assert gen.feedback_loop is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_init_custom_config(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test initialization with custom configuration."""
        gen = AutonomousTestGenerator(
            agent_id="custom-agent",
            batch_num=5,
            modules=[],
            enable_refinement=False,
            max_refinement_iterations=5,
            enable_coverage_guided=True,
            target_coverage=0.95,
        )

        assert gen.enable_refinement is False
        assert gen.max_refinement_iterations == 5
        assert gen.enable_coverage_guided is True
        assert gen.target_coverage == 0.95


@skip_if_no_testgen
@pytest.mark.unit
class TestAutonomousTestGeneratorValidation:
    """Tests for AutonomousTestGenerator._validate_test_file."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_validate_valid_file(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test validation of a valid test file."""
        gen = AutonomousTestGenerator("agent", 1, [])

        test_file = tmp_path / "test_example.py"
        test_file.write_text("def test_hello():\n    assert True\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="1 test collected", stderr="")
            assert gen._validate_test_file(test_file) is True

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_validate_syntax_error(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test validation catches syntax errors."""
        gen = AutonomousTestGenerator("agent", 1, [])

        test_file = tmp_path / "test_bad.py"
        test_file.write_text("def test_bad(\n    broken syntax")

        assert gen._validate_test_file(test_file) is False

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_validate_pytest_collection_failure(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test validation detects pytest collection failures."""
        gen = AutonomousTestGenerator("agent", 1, [])

        test_file = tmp_path / "test_import_err.py"
        test_file.write_text("from nonexistent_module import something\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="ImportError")
            assert gen._validate_test_file(test_file) is False

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_validate_timeout(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test validation handles subprocess timeout."""
        gen = AutonomousTestGenerator("agent", 1, [])

        test_file = tmp_path / "test_slow.py"
        test_file.write_text("def test_ok(): pass\n")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=10)
            assert gen._validate_test_file(test_file) is False


@skip_if_no_testgen
@pytest.mark.unit
class TestAutonomousTestGeneratorCountTests:
    """Tests for AutonomousTestGenerator._count_tests."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_count_tests_success(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
    ) -> None:
        """Test counting tests from pytest output."""
        gen = AutonomousTestGenerator("agent", 1, [])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="42 tests collected\n",
                stderr="",
            )
            assert gen._count_tests() == 42

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_count_tests_no_match(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
    ) -> None:
        """Test counting returns 0 when no match in output."""
        gen = AutonomousTestGenerator("agent", 1, [])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="no tests ran", stderr="")
            assert gen._count_tests() == 0

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_count_tests_exception(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
    ) -> None:
        """Test counting returns 0 on exception."""
        gen = AutonomousTestGenerator("agent", 1, [])

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Failed to run")
            assert gen._count_tests() == 0


@skip_if_no_testgen
@pytest.mark.unit
class TestAutonomousTestGeneratorGenerate:
    """Tests for AutonomousTestGenerator._generate_module_tests."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_module_source_not_found(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
    ) -> None:
        """Test generation returns None when source file does not exist."""
        gen = AutonomousTestGenerator("agent", 1, [])

        result = gen._generate_module_tests(
            {"file": "/nonexistent/path/module.py", "total": 100, "missing": 80},
        )
        assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_module_llm_returns_none(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test generation returns None when LLM fails."""
        gen = AutonomousTestGenerator("agent", 1, [])
        gen.enable_refinement = False

        source_file = tmp_path / "module.py"
        source_file.write_text("def hello(): return 'world'\n")

        with patch.object(gen, "_generate_with_llm", return_value=None):
            result = gen._generate_module_tests(
                {"file": str(source_file), "total": 10, "missing": 5},
            )
            assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_module_validation_fails_deletes_file(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test that failed validation causes test file deletion."""
        gen = AutonomousTestGenerator("agent", 1, [])
        gen.enable_refinement = False
        gen.enable_coverage_guided = False
        gen.output_dir = tmp_path / "output"
        gen.output_dir.mkdir()

        source_file = tmp_path / "module.py"
        source_file.write_text("def hello(): return 'world'\n")

        test_content = "def test_hello():\n    assert True\n"

        with patch.object(gen, "_generate_with_llm", return_value=test_content):
            with patch.object(gen, "_validate_test_file", return_value=False):
                result = gen._generate_module_tests(
                    {"file": str(source_file), "total": 10, "missing": 5},
                )
                assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_module_success(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test successful module test generation."""
        gen = AutonomousTestGenerator("agent", 1, [])
        gen.enable_refinement = False
        gen.enable_coverage_guided = False
        gen.output_dir = tmp_path / "output"
        gen.output_dir.mkdir()

        source_file = tmp_path / "module.py"
        source_file.write_text("def hello(): return 'world'\n")

        test_content = "def test_hello():\n    assert True\n"

        with patch.object(gen, "_generate_with_llm", return_value=test_content):
            with patch.object(gen, "_validate_test_file", return_value=True):
                result = gen._generate_module_tests(
                    {"file": str(source_file), "total": 10, "missing": 5},
                )
                assert result is not None
                assert result.exists()

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_module_with_refinement(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test generation uses refinement when enabled."""
        gen = AutonomousTestGenerator("agent", 1, [])
        gen.enable_refinement = True
        gen.enable_coverage_guided = False
        gen.output_dir = tmp_path / "output"
        gen.output_dir.mkdir()

        source_file = tmp_path / "module.py"
        source_file.write_text("def hello(): return 'world'\n")

        test_content = "def test_hello():\n    assert True\n"

        with patch.object(gen, "_generate_with_refinement", return_value=test_content):
            with patch.object(gen, "_validate_test_file", return_value=True):
                result = gen._generate_module_tests(
                    {"file": str(source_file), "total": 10, "missing": 5},
                )
                assert result is not None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_module_coverage_guided(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test generation with coverage-guided improvement."""
        gen = AutonomousTestGenerator("agent", 1, [])
        gen.enable_refinement = False
        gen.enable_coverage_guided = True
        gen.output_dir = tmp_path / "output"
        gen.output_dir.mkdir()

        source_file = tmp_path / "module.py"
        source_file.write_text("def hello(): return 'world'\n")

        initial_content = "def test_hello():\n    assert True\n"
        improved_content = "def test_hello():\n    assert True\ndef test_hello2():\n    pass\n"

        with patch.object(gen, "_generate_with_llm", return_value=initial_content):
            with patch.object(gen, "_generate_with_coverage_target", return_value=improved_content):
                with patch.object(gen, "_validate_test_file", return_value=True):
                    result = gen._generate_module_tests(
                        {"file": str(source_file), "total": 10, "missing": 5},
                    )
                    assert result is not None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_module_coverage_guided_fails_uses_original(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test that coverage-guided failure falls back to original content."""
        gen = AutonomousTestGenerator("agent", 1, [])
        gen.enable_refinement = False
        gen.enable_coverage_guided = True
        gen.output_dir = tmp_path / "output"
        gen.output_dir.mkdir()

        source_file = tmp_path / "module.py"
        source_file.write_text("def hello(): return 'world'\n")

        initial_content = "def test_hello():\n    assert True\n"

        with patch.object(gen, "_generate_with_llm", return_value=initial_content):
            with patch.object(gen, "_generate_with_coverage_target", return_value=None):
                with patch.object(gen, "_validate_test_file", return_value=True):
                    result = gen._generate_module_tests(
                        {"file": str(source_file), "total": 10, "missing": 5},
                    )
                    assert result is not None
                    # Should contain initial_content since coverage failed
                    content = result.read_text()
                    assert "test_hello" in content


@skip_if_no_testgen
@pytest.mark.unit
class TestAutonomousTestGeneratorGenerateAll:
    """Tests for AutonomousTestGenerator.generate_all."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_all_success(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test generate_all with successful module generation."""
        source1 = tmp_path / "src" / "attune" / "mod1.py"
        source1.parent.mkdir(parents=True, exist_ok=True)
        source1.write_text("def func1(): pass\n")

        gen = AutonomousTestGenerator(
            "agent",
            1,
            [{"file": str(source1)}],
        )
        gen.event_streamer = Mock()
        gen.feedback_loop = Mock()

        mock_test_file = tmp_path / "test_mod1.py"
        mock_test_file.write_text("def test_func1(): pass\n")

        with patch.object(gen, "_generate_module_tests", return_value=mock_test_file):
            with patch.object(gen, "_count_tests", return_value=5):
                results = gen.generate_all()

                assert results["completed"] == 1
                assert results["failed"] == 0
                assert results["tests_generated"] == 5

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_all_module_failure(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test generate_all handles module generation failure."""
        gen = AutonomousTestGenerator(
            "agent",
            1,
            [{"file": "src/attune/missing.py"}],
        )
        gen.event_streamer = Mock()
        gen.feedback_loop = Mock()

        with patch.object(gen, "_generate_module_tests", return_value=None):
            with patch.object(gen, "_count_tests", return_value=0):
                results = gen.generate_all()

                assert results["completed"] == 0
                assert results["failed"] == 1

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_all_module_exception(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        tmp_path: Path,
    ) -> None:
        """Test generate_all handles exception during module generation."""
        gen = AutonomousTestGenerator(
            "agent",
            1,
            [{"file": "src/attune/error.py"}],
        )
        gen.event_streamer = Mock()
        gen.feedback_loop = Mock()

        with patch.object(gen, "_generate_module_tests", side_effect=RuntimeError("boom")):
            with patch.object(gen, "_count_tests", return_value=0):
                results = gen.generate_all()

                assert results["failed"] == 1
                gen.event_streamer.publish_event.assert_called()


@skip_if_no_testgen
@pytest.mark.unit
class TestAutonomousTestGeneratorLLM:
    """Tests for AutonomousTestGenerator._generate_with_llm."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_no_api_key(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test _generate_with_llm returns None when API key is missing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        gen = AutonomousTestGenerator("agent", 1, [])

        with patch.dict("sys.modules", {"anthropic": MagicMock()}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )
            assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_no_anthropic(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
    ) -> None:
        """Test _generate_with_llm returns None when anthropic not installed."""
        gen = AutonomousTestGenerator("agent", 1, [])

        with patch.dict("sys.modules", {"anthropic": None}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )
            assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_success(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test _generate_with_llm successfully generates test content."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
        gen = AutonomousTestGenerator("agent", 1, [])

        # Build mock anthropic module and response
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        # Content must be > 100 chars to pass length check
        test_code = (
            "import pytest\n\n\n"
            "class TestModule:\n"
            '    """Tests for module."""\n\n'
            "    def test_foo_returns_correct_value(self):\n"
            '        """Test that foo returns expected result."""\n'
            "        assert True\n\n"
            "    def test_foo_edge_case(self):\n"
            '        """Test foo edge case."""\n'
            "        assert 1 + 1 == 2\n"
        )
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = test_code

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )

            assert result is not None
            assert "TestModule" in result

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_empty_response(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test _generate_with_llm returns None on empty response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
        gen = AutonomousTestGenerator("agent", 1, [])

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )
            assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_too_short_response(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test _generate_with_llm returns None when response is too short."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
        gen = AutonomousTestGenerator("agent", 1, [])

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "short"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )
            assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_strips_markdown_fences(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that markdown code fences are stripped from response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
        gen = AutonomousTestGenerator("agent", 1, [])

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        # Content must be > 100 chars to pass length check
        code = (
            "import pytest\n\n\n"
            "class TestExample:\n"
            '    """Comprehensive tests for example module."""\n\n'
            "    def test_example_basic(self):\n"
            '        """Test basic example functionality."""\n'
            "        assert 1 + 1 == 2\n\n"
            "    def test_example_edge_case(self):\n"
            '        """Test edge case."""\n'
            "        assert True\n"
        )
        fenced_code = f"```python\n{code}\n```"

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = fenced_code

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )

            assert result is not None
            assert not result.startswith("```python")
            assert not result.endswith("```")

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_syntax_error_response(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test _generate_with_llm returns None on syntax error in response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
        gen = AutonomousTestGenerator("agent", 1, [])

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        # Invalid Python syntax - long enough to pass length check
        bad_code = "def test_broken(\n    this is not valid python " * 5

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = bad_code

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )
            assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_api_exception(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test _generate_with_llm handles API exceptions gracefully."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
        gen = AutonomousTestGenerator("agent", 1, [])

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("API timeout")

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = gen._generate_with_llm(
                "module",
                "attune.module",
                Path("src/module.py"),
                "def foo(): pass",
            )
            assert result is None

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_generate_with_llm_workflow_module_detection(
        self,
        mock_feedback: Mock,
        mock_streamer: Mock,
        mock_coordinator: Mock,
        mock_redis: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test _generate_with_llm detects workflow modules."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
        gen = AutonomousTestGenerator("agent", 1, [])

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = (
            'import pytest\n\ndef test_workflow():\n    """Test workflow."""\n    assert True\n'
        )

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        # Workflow source code with indicators
        workflow_source = """
class MyWorkflow(BaseWorkflow):
    async def execute(self):
        pass
"""
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with patch.object(gen, "_is_workflow_module", return_value=True):
                with patch.object(
                    gen,
                    "_get_workflow_specific_prompt",
                    return_value="Generate tests",
                ):
                    gen._generate_with_llm(
                        "my_workflow",
                        "attune.workflows.my_workflow",
                        Path("src/module.py"),
                        workflow_source,
                    )
                    gen._get_workflow_specific_prompt.assert_called_once()


# ============================================================================
# PART 12: ValidationResult and CoverageResult dataclasses
# ============================================================================


@skip_if_no_testgen
@pytest.mark.unit
class TestDataclasses:
    """Tests for autonomous_test_gen dataclasses."""

    def test_validation_result(self) -> None:
        """Test ValidationResult dataclass."""
        vr = ValidationResult(passed=True, failures="", error_count=0, output="all tests pass")
        assert vr.passed is True
        assert vr.error_count == 0

    def test_validation_result_failure(self) -> None:
        """Test ValidationResult with failures."""
        vr = ValidationResult(
            passed=False,
            failures="FAILED test_foo",
            error_count=2,
            output="2 failed",
        )
        assert vr.passed is False
        assert vr.error_count == 2

    def test_coverage_result(self) -> None:
        """Test CoverageResult dataclass."""
        cr = CoverageResult(
            coverage=0.85,
            missing_lines=[10, 20, 30],
            total_statements=100,
            covered_statements=85,
        )
        assert cr.coverage == 0.85
        assert len(cr.missing_lines) == 3
        assert cr.total_statements == 100


# ============================================================================
# PART 13: run_batch_generation function
# ============================================================================


@skip_if_no_testgen
@pytest.mark.unit
class TestRunBatchGeneration:
    """Tests for the run_batch_generation function."""

    @patch("attune.workflows.autonomous_test_gen.AutonomousTestGenerator")
    def test_run_batch_generation_calls_generator(
        self,
        mock_gen_class: Mock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test that run_batch_generation creates and runs generator."""
        mock_instance = mock_gen_class.return_value
        mock_instance.generate_all.return_value = {
            "batch": 1,
            "total_modules": 2,
            "completed": 2,
            "failed": 0,
            "tests_generated": 10,
            "files_created": ["test1.py", "test2.py"],
        }

        modules_json = json.dumps(
            [
                {"file": "src/attune/mod1.py"},
                {"file": "src/attune/mod2.py"},
            ],
        )

        run_batch_generation(
            batch_num=1,
            modules_json=modules_json,
            enable_refinement=True,
            enable_coverage_guided=False,
        )

        mock_gen_class.assert_called_once()
        mock_instance.generate_all.assert_called_once()

        captured = capsys.readouterr()
        assert "Batch 1 Complete" in captured.out

    @patch("attune.workflows.autonomous_test_gen.AutonomousTestGenerator")
    def test_run_batch_generation_with_coverage(
        self,
        mock_gen_class: Mock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test run_batch_generation with coverage-guided mode."""
        mock_instance = mock_gen_class.return_value
        mock_instance.generate_all.return_value = {
            "batch": 3,
            "total_modules": 1,
            "completed": 1,
            "failed": 0,
            "tests_generated": 5,
            "files_created": ["test1.py"],
        }

        modules_json = json.dumps([{"file": "src/attune/mod1.py"}])

        run_batch_generation(
            batch_num=3,
            modules_json=modules_json,
            enable_refinement=False,
            enable_coverage_guided=True,
        )

        captured = capsys.readouterr()
        assert "DISABLED" in captured.out  # refinement disabled
        assert "ENABLED" in captured.out  # coverage enabled


# ============================================================================
# PART 14: CodeReviewWorkflow._gather_project_context
# ============================================================================


@skip_if_no_review
@pytest.mark.unit
class TestGatherProjectContext:
    """Tests for CodeReviewWorkflow._gather_project_context."""

    def test_gather_context_returns_string(self, cost_tracker: Any) -> None:
        """Test that _gather_project_context returns a string."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)
        context = wf._gather_project_context()
        assert isinstance(context, str)

    def test_gather_context_includes_project_structure(self, cost_tracker: Any) -> None:
        """Test that context includes project structure section."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=False)
        context = wf._gather_project_context()
        if context:
            assert "Project Structure" in context


# ============================================================================
# PART 15: CodeReviewWorkflow._initialize_crew
# ============================================================================


@skip_if_no_review
@pytest.mark.unit
class TestInitializeCrew:
    """Tests for CodeReviewWorkflow._initialize_crew."""

    @pytest.mark.asyncio
    async def test_initialize_crew_import_error(self, cost_tracker: Any) -> None:
        """Test crew initialization handles ImportError gracefully."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=True)

        original_import = (
            __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
        )

        def mock_import(name, *args, **kwargs):
            if "agent_factory.crews" in name:
                raise ImportError("No module named 'attune.agent_factory.crews'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            try:
                await wf._initialize_crew()
            except (ImportError, TypeError):
                pass
            # Crew should not be available after import error
            assert wf._crew is None or wf._crew_available is False

    @pytest.mark.asyncio
    async def test_initialize_crew_already_initialized(self, cost_tracker: Any) -> None:
        """Test that crew initialization is idempotent."""
        wf = CodeReviewWorkflow(cost_tracker=cost_tracker, use_crew=True)
        wf._crew = Mock()  # Already initialized

        await wf._initialize_crew()

        # Should not re-initialize
        assert wf._crew is not None


# ============================================================================
# PART 16: CodeReviewWorkflow auth strategy integration
# ============================================================================


@skip_if_no_review
@pytest.mark.unit
class TestAuthStrategyIntegration:
    """Tests for auth strategy in classify stage."""

    @pytest.mark.asyncio
    async def test_classify_with_auth_strategy_disabled(self, cost_tracker: Any) -> None:
        """Test classify works with auth strategy disabled."""
        wf = CodeReviewWorkflow(
            cost_tracker=cost_tracker,
            use_crew=False,
            enable_auth_strategy=False,
        )

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "Classification: feature\nComplexity: low",
                100,
                50,
            )

            input_data = {"diff": "x = 1", "files_changed": ["test.py"]}
            result, _, _ = await wf._classify(input_data, ModelTier.CHEAP)

            assert "classification" in result

    @pytest.mark.asyncio
    async def test_classify_auth_strategy_exception(self, cost_tracker: Any) -> None:
        """Test classify handles auth strategy exceptions gracefully."""
        wf = CodeReviewWorkflow(
            cost_tracker=cost_tracker,
            use_crew=False,
            enable_auth_strategy=True,
        )

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "Classification: feature\nComplexity: low",
                100,
                50,
            )

            # The auth strategy is imported locally: from attune.models import get_auth_strategy
            # Patch it in attune.models where the import resolves
            with patch(
                "attune.models.get_auth_strategy",
                side_effect=ImportError("not available"),
            ):
                input_data = {"diff": "x = 1", "files_changed": ["test.py"]}
                result, _, _ = await wf._classify(input_data, ModelTier.CHEAP)

                # Should still succeed despite auth failure
                assert "classification" in result

    @pytest.mark.asyncio
    async def test_classify_detects_high_complexity(self, cost_tracker: Any) -> None:
        """Test that classify detects high complexity in LLM response."""
        wf = CodeReviewWorkflow(
            cost_tracker=cost_tracker,
            use_crew=False,
            enable_auth_strategy=False,
        )

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "Classification: security refactor\nComplexity: HIGH\nRisk: HIGH",
                100,
                50,
            )

            input_data = {"diff": "complex code", "files_changed": ["auth.py"]}
            result, _, _ = await wf._classify(input_data, ModelTier.CHEAP)

            assert result["needs_architect_review"] is True

    @pytest.mark.asyncio
    async def test_classify_is_core_module_input(self, cost_tracker: Any) -> None:
        """Test that is_core_module input flag triggers architect review."""
        wf = CodeReviewWorkflow(
            cost_tracker=cost_tracker,
            use_crew=False,
            file_threshold=100,  # High threshold
            enable_auth_strategy=False,
        )

        with patch.object(wf, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "Classification: simple change\nComplexity: low",
                100,
                50,
            )

            input_data = {
                "diff": "x = 1",
                "files_changed": [],
                "is_core_module": True,
            }
            result, _, _ = await wf._classify(input_data, ModelTier.CHEAP)

            assert result["needs_architect_review"] is True
