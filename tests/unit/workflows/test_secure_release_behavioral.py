"""Behavioral tests for SecureReleasePipeline.

Tests initialization, mode validation, go/no-go logic,
risk calculation, and finding aggregation without running
real security workflows.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from attune.workflows.data_classes import CostReport, WorkflowResult
from attune.workflows.secure_release import (
    SecureReleasePipeline,
    SecureReleaseResult,
)


@pytest.mark.unit
class TestSecureReleaseAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        wf = SecureReleasePipeline()
        assert wf.name == "secure-release"

    def test_workflow_has_description(self) -> None:
        wf = SecureReleasePipeline()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0


@pytest.mark.unit
class TestSecureReleaseInit:
    """Test constructor parameters."""

    def test_default_mode_is_full(self) -> None:
        wf = SecureReleasePipeline()
        assert wf.mode == "full"

    def test_standard_mode(self) -> None:
        wf = SecureReleasePipeline(mode="standard")
        assert wf.mode == "standard"

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid mode"):
            SecureReleasePipeline(mode="invalid")

    def test_full_mode_enables_crew(self) -> None:
        wf = SecureReleasePipeline(mode="full")
        assert wf.use_crew is True

    def test_standard_mode_disables_crew(self) -> None:
        wf = SecureReleasePipeline(mode="standard")
        assert wf.use_crew is False

    def test_use_crew_override(self) -> None:
        wf = SecureReleasePipeline(mode="standard", use_crew=True)
        assert wf.use_crew is True

    def test_parallel_crew_default(self) -> None:
        wf = SecureReleasePipeline()
        assert wf.parallel_crew is True


@pytest.mark.unit
class TestSecureReleaseGoNoGo:
    """Test _determine_go_no_go logic."""

    def test_critical_findings_returns_no_go(self) -> None:
        wf = SecureReleasePipeline()
        result = wf._determine_go_no_go(
            risk_score=30.0,
            findings={"critical": 1, "high": 0, "total": 1},
            release_result=None,
        )
        assert result == "NO_GO"

    def test_high_risk_returns_no_go(self) -> None:
        wf = SecureReleasePipeline()
        result = wf._determine_go_no_go(
            risk_score=75.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=None,
        )
        assert result == "NO_GO"

    def test_many_high_findings_returns_conditional(self) -> None:
        wf = SecureReleasePipeline()
        result = wf._determine_go_no_go(
            risk_score=30.0,
            findings={"critical": 0, "high": 4, "total": 4},
            release_result=None,
        )
        assert result == "CONDITIONAL"

    def test_elevated_risk_returns_conditional(self) -> None:
        wf = SecureReleasePipeline()
        result = wf._determine_go_no_go(
            risk_score=50.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=None,
        )
        assert result == "CONDITIONAL"

    def test_release_not_approved_returns_conditional(self) -> None:
        wf = SecureReleasePipeline()
        mock_result = MagicMock()
        mock_result.final_output = {"approved": False}
        result = wf._determine_go_no_go(
            risk_score=20.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=mock_result,
        )
        assert result == "CONDITIONAL"

    def test_clean_results_returns_go(self) -> None:
        wf = SecureReleasePipeline()
        result = wf._determine_go_no_go(
            risk_score=20.0,
            findings={"critical": 0, "high": 0, "total": 0},
            release_result=None,
        )
        assert result == "GO"


@pytest.mark.unit
class TestSecureReleaseRiskCalculation:
    """Test _calculate_combined_risk logic."""

    def test_no_results_returns_zero(self) -> None:
        wf = SecureReleasePipeline()
        score = wf._calculate_combined_risk(None, None, None, None)
        assert score == 0.0

    def test_crew_report_weighted_higher(self) -> None:
        wf = SecureReleasePipeline()
        crew_report = {"risk_score": 50}
        score = wf._calculate_combined_risk(crew_report, None, None, None)
        assert score == 50.0

    def test_combined_score_capped_at_100(self) -> None:
        wf = SecureReleasePipeline()
        crew_report = {"risk_score": 100}
        mock_security = MagicMock()
        mock_security.final_output = {"assessment": {"risk_score": 100}}
        score = wf._calculate_combined_risk(crew_report, mock_security, None, None)
        assert score <= 100.0


@pytest.mark.unit
class TestSecureReleaseFindingAggregation:
    """Test _aggregate_findings logic."""

    def test_no_results_returns_zero_counts(self) -> None:
        wf = SecureReleasePipeline()
        findings = wf._aggregate_findings(None, None, None)
        assert findings["critical"] == 0
        assert findings["high"] == 0
        assert findings["total"] == 0

    def test_crew_findings_counted(self) -> None:
        wf = SecureReleasePipeline()
        crew_report = {
            "assessment": {
                "critical_findings": [{"title": "SQL injection"}],
                "high_findings": [{"title": "XSS"}],
            },
            "finding_count": 5,
        }
        findings = wf._aggregate_findings(crew_report, None, None)
        assert findings["critical"] == 1
        assert findings["high"] == 1
        assert findings["total"] == 5


@pytest.mark.unit
class TestSecureReleaseRecommendations:
    """Test _generate_recommendations logic."""

    def test_no_issues_recommends_release(self) -> None:
        wf = SecureReleasePipeline()
        blockers, warnings, recs = wf._generate_recommendations(None, None, None, None)
        assert len(blockers) == 0
        assert len(warnings) == 0
        assert any("ready for release" in r.lower() for r in recs)

    def test_critical_crew_findings_become_blockers(self) -> None:
        wf = SecureReleasePipeline()
        crew_report = {
            "assessment": {
                "critical_findings": [{"title": "SQL injection"}],
                "high_findings": [],
            },
        }
        blockers, warnings, recs = wf._generate_recommendations(crew_report, None, None, None)
        assert len(blockers) >= 1
        assert "SQL injection" in blockers[0]


@pytest.mark.unit
class TestPhantomKeyRegression:
    """#2219 — the aggregator must read the REAL SDK result shape.

    The pre-SDK ``final_output["assessment"]`` / ``"security_score"`` /
    ``"has_critical_issues"`` keys no longer exist; reading them zeroed
    a sub-audit's findings and produced GO on a planted-critical
    fixture (probe registry, 2026-08-23). These tests feed the shape
    the SDK adapter actually emits and pin fail-closed behavior.
    """

    @staticmethod
    def _sdk_result(score: float | None, findings: dict) -> MagicMock:
        result = MagicMock()
        result.final_output = {"_type": "WorkflowReport", "score": score}
        if score is None:
            result.final_output = {"_type": "WorkflowReport"}
        result.metadata = {"findings": findings}
        return result

    def test_severity_keyed_findings_are_counted(self) -> None:
        wf = SecureReleasePipeline()
        sec = self._sdk_result(15, {"CRITICAL": ["c1"], "HIGH": ["h1", "h2"], "LOW": []})
        findings = wf._aggregate_findings(None, sec, None)
        assert findings["critical"] == 1
        assert findings["high"] == 2
        assert findings["total"] == 3

    def test_category_keyed_findings_fail_closed_as_high(self) -> None:
        # Unknown-severity buckets are not ignorable in a release gate.
        wf = SecureReleasePipeline()
        sec = self._sdk_result(40, {"security": ["a", "b", "c"]})
        findings = wf._aggregate_findings(None, sec, None)
        assert findings["high"] == 3
        assert findings["total"] == 3

    def test_planted_critical_fixture_yields_no_go(self) -> None:
        # The exact probe scenario: sub-audit score 15/100 with a
        # CRITICAL finding must be NO_GO on BOTH paths (critical count
        # and risk >= 75) — never GO.
        wf = SecureReleasePipeline()
        sec = self._sdk_result(15, {"CRITICAL": ["c1"], "HIGH": ["h1", "h2"]})
        findings = wf._aggregate_findings(None, sec, None)
        risk = wf._calculate_combined_risk(None, sec, None, None)
        assert risk >= 75
        assert wf._determine_go_no_go(risk, findings, None) == "NO_GO"

    def test_score_read_from_sdk_shape(self) -> None:
        assert SecureReleasePipeline._report_score(self._sdk_result(15, {})) == 15.0
        assert SecureReleasePipeline._report_score(None) is None
        # The retired shape carries no score — None, never "healthy".
        old = MagicMock()
        old.final_output = {"assessment": {"risk_score": 100}}
        old.metadata = {}
        assert SecureReleasePipeline._report_score(old) is None

    def test_mixed_buckets_cannot_exempt_unknown_findings(self) -> None:
        # D11 lane finding: an empty recognized bucket (LOW: []) must
        # NOT exempt category-keyed findings from the fail-closed count.
        wf = SecureReleasePipeline()
        sec = self._sdk_result(40, {"LOW": [], "security": ["a", "b"]})
        findings = wf._aggregate_findings(None, sec, None)
        assert findings["high"] == 2
        assert findings["total"] == 2

    def test_code_review_findings_reach_total(self) -> None:
        # D11 lane finding: review counts must update total too.
        wf = SecureReleasePipeline()
        review = self._sdk_result(50, {"HIGH": ["h1"], "MEDIUM": ["m1"]})
        findings = wf._aggregate_findings(None, None, review)
        assert findings["total"] == 2

    @pytest.mark.parametrize("bad", [True, False, float("nan"), float("inf"), float("-inf"), "95"])
    def test_report_score_rejects_unusable_values(self, bad) -> None:
        # D11 lane finding: NaN propagates through risk where every
        # threshold comparison is False -> a malformed audit becomes GO.
        # Booleans/strings/non-finite values must read as "no evidence".
        wf_result = self._sdk_result(None, {})
        wf_result.final_output = {"_type": "WorkflowReport", "score": bad}
        assert SecureReleasePipeline._report_score(wf_result) is None

    def test_report_score_clamps_out_of_range(self) -> None:
        high = self._sdk_result(None, {})
        high.final_output = {"score": 250}
        low = self._sdk_result(None, {})
        low.final_output = {"score": -5}
        assert SecureReleasePipeline._report_score(high) == 100.0
        assert SecureReleasePipeline._report_score(low) == 0.0

    def test_extraction_drift_warning_on_scored_but_findingless_audit(self) -> None:
        # A sub-audit scoring below 100 with ZERO extractable findings
        # looks exactly like a clean audit — it must warn, not pass
        # silently.
        wf = SecureReleasePipeline()
        sec = self._sdk_result(60, {})
        _, warnings, _ = wf._generate_recommendations(None, sec, None, None)
        assert any("extraction may be broken" in w for w in warnings)


@pytest.mark.unit
class TestSecureReleaseResult:
    """Test SecureReleaseResult dataclass."""

    def test_to_dict(self) -> None:
        result = SecureReleaseResult(success=True, go_no_go="GO")
        d = result.to_dict()
        assert d["success"] is True
        assert d["go_no_go"] == "GO"
        assert "blockers" in d

    def test_formatted_report_returns_string(self) -> None:
        result = SecureReleaseResult(success=True, go_no_go="GO")
        report = result.formatted_report
        assert isinstance(report, str)
        assert "GO" in report


@pytest.mark.unit
class TestSecureReleaseFactoryMethods:
    """Test for_pr_review and for_release class methods."""

    def test_for_pr_review_small_change(self) -> None:
        wf = SecureReleasePipeline.for_pr_review(files_changed=5)
        assert wf.mode == "standard"

    def test_for_pr_review_large_change(self) -> None:
        wf = SecureReleasePipeline.for_pr_review(files_changed=15)
        assert wf.mode == "full"

    def test_for_release_uses_full_mode(self) -> None:
        wf = SecureReleasePipeline.for_release()
        assert wf.mode == "full"
        assert wf.crew_config.get("scan_depth") == "thorough"


@pytest.mark.unit
class TestSecureReleaseExecution:
    """Test execute flow with mocked sub-workflows."""

    @staticmethod
    def _make_mock_result(final_output: dict, metadata: dict | None = None) -> WorkflowResult:
        """Create a WorkflowResult for a successful sub-workflow."""
        from datetime import datetime

        mock_cost = CostReport(
            total_cost=0.01,
            baseline_cost=0.05,
            savings=0.04,
            savings_percent=80.0,
        )
        return WorkflowResult(
            success=True,
            stages=[],
            final_output=final_output,
            cost_report=mock_cost,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_duration_ms=100,
            metadata=metadata or {},
        )

    @pytest.mark.asyncio
    async def test_execute_with_mocked_workflows(self) -> None:
        """Given mocked sub-workflows, execute returns SecureReleaseResult."""
        from unittest.mock import AsyncMock, patch

        wf = SecureReleasePipeline(mode="standard")

        sec_result = self._make_mock_result({"assessment": {"risk_score": 10, "risk_level": "low"}})
        rel_result = self._make_mock_result({"approved": True, "confidence": "high"})

        mock_sec_wf = MagicMock()
        mock_sec_wf.execute = AsyncMock(return_value=sec_result)
        mock_rel_wf = MagicMock()
        mock_rel_wf.execute = AsyncMock(return_value=rel_result)

        with (
            patch(
                "attune.workflows.security_audit.SecurityAuditWorkflow",
                return_value=mock_sec_wf,
            ),
            patch(
                "attune.workflows.release_prep.ReleasePreparationWorkflow",
                return_value=mock_rel_wf,
            ),
        ):
            result = await wf.execute(path=".")

        assert isinstance(result, SecureReleaseResult)
        assert result.go_no_go == "GO"

    @pytest.mark.asyncio
    async def test_handles_workflow_error_gracefully(self) -> None:
        """Given sub-workflow failure, execute returns NO_GO."""
        from unittest.mock import AsyncMock, patch

        wf = SecureReleasePipeline(mode="standard")

        mock_sec_wf = MagicMock()
        mock_sec_wf.execute = AsyncMock(side_effect=RuntimeError("Security audit failed"))

        with patch(
            "attune.workflows.security_audit.SecurityAuditWorkflow",
            return_value=mock_sec_wf,
        ):
            result = await wf.execute(path=".")

        assert isinstance(result, SecureReleaseResult)
        assert result.go_no_go == "NO_GO"
        assert any("failed" in b.lower() for b in result.blockers)

    @staticmethod
    def _make_failed_result(error: str) -> WorkflowResult:
        """Create a WorkflowResult for a sub-workflow that errored.

        Mirrors the SDK-subprocess failure shape: success=False, no
        final_output, error set — returned, not raised.
        """
        from datetime import datetime

        return WorkflowResult(
            success=False,
            stages=[],
            final_output=None,
            cost_report=CostReport(
                total_cost=0.0,
                baseline_cost=0.0,
                savings=0.0,
                savings_percent=0.0,
            ),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_duration_ms=100,
            error=error,
            error_type="runtime",
        )

    @pytest.mark.asyncio
    async def test_all_gatekeepers_failed_is_no_go(self) -> None:
        """Regression (roundtable q-workflow-fleet-health-001, Sev1):
        both sub-workflows fail with an SDK subprocess error → zero
        findings because nothing ran. Zero findings with zero execution
        must NOT be a GO — a failed gatekeeper fails the gate.
        """
        from unittest.mock import AsyncMock, patch

        wf = SecureReleasePipeline(mode="standard")

        mock_sec_wf = MagicMock()
        mock_sec_wf.execute = AsyncMock(
            return_value=self._make_failed_result("SDK subprocess error"),
        )
        mock_rel_wf = MagicMock()
        mock_rel_wf.execute = AsyncMock(
            return_value=self._make_failed_result("SDK subprocess error"),
        )

        with (
            patch(
                "attune.workflows.security_audit.SecurityAuditWorkflow",
                return_value=mock_sec_wf,
            ),
            patch(
                "attune.workflows.release_prep.ReleasePreparationWorkflow",
                return_value=mock_rel_wf,
            ),
        ):
            result = await wf.execute(path=".")

        assert result.go_no_go == "NO_GO"
        assert result.success is False
        assert result.total_findings == 0  # nothing ran — and that is why it's NO_GO
        gatekeeper_blockers = [
            b for b in result.blockers if b.startswith("GATEKEEPER_EXECUTION_FAILED")
        ]
        assert any("security_audit" in b for b in gatekeeper_blockers)
        assert any("release_prep" in b for b in gatekeeper_blockers)
        assert not any("ready for release" in r.lower() for r in result.recommendations)

    @pytest.mark.asyncio
    async def test_one_failed_gatekeeper_is_no_go(self) -> None:
        """A single failed gatekeeper (release_prep) forces NO_GO even
        when the security audit ran to completion — and remediation
        advice derived from the gatekeeper that DID run survives
        (cross-review finding, PR #2208 D11 lane).
        """
        from unittest.mock import AsyncMock, patch

        wf = SecureReleasePipeline(mode="standard")

        # Real SDK shape (#2219): serialized WorkflowReport final_output
        # + severity-keyed metadata findings — the retired "assessment"
        # key would silently contribute nothing.
        sec_result = self._make_mock_result(
            {"_type": "WorkflowReport", "score": 45},
            metadata={"findings": {"HIGH": ["h1", "h2"], "MEDIUM": ["m1"]}},
        )

        mock_sec_wf = MagicMock()
        mock_sec_wf.execute = AsyncMock(return_value=sec_result)
        mock_rel_wf = MagicMock()
        mock_rel_wf.execute = AsyncMock(
            return_value=self._make_failed_result("SDK subprocess error"),
        )

        with (
            patch(
                "attune.workflows.security_audit.SecurityAuditWorkflow",
                return_value=mock_sec_wf,
            ),
            patch(
                "attune.workflows.release_prep.ReleasePreparationWorkflow",
                return_value=mock_rel_wf,
            ),
        ):
            result = await wf.execute(path=".")

        assert result.go_no_go == "NO_GO"
        assert result.success is False
        assert any(
            b.startswith("GATEKEEPER_EXECUTION_FAILED") and "release_prep" in b
            for b in result.blockers
        )
        # Advice derived from the completed security audit survives the
        # sentinel; only the "ready for release" fiction is dropped.
        assert any("warnings" in r.lower() for r in result.recommendations)
        assert not any("ready for release" in r.lower() for r in result.recommendations)

    @pytest.mark.asyncio
    async def test_failed_code_review_with_diff_is_no_go(self) -> None:
        """When a diff is supplied, code review is a gatekeeper too —
        its execution failure forces NO_GO.
        """
        from unittest.mock import AsyncMock, patch

        wf = SecureReleasePipeline(mode="standard")

        sec_result = self._make_mock_result({"assessment": {"risk_score": 5, "risk_level": "low"}})
        rel_result = self._make_mock_result({"approved": True, "confidence": "high"})

        mock_sec_wf = MagicMock()
        mock_sec_wf.execute = AsyncMock(return_value=sec_result)
        mock_rel_wf = MagicMock()
        mock_rel_wf.execute = AsyncMock(return_value=rel_result)
        mock_cr_wf = MagicMock()
        mock_cr_wf.execute = AsyncMock(
            return_value=self._make_failed_result("SDK subprocess error"),
        )

        with (
            patch(
                "attune.workflows.security_audit.SecurityAuditWorkflow",
                return_value=mock_sec_wf,
            ),
            patch(
                "attune.workflows.release_prep.ReleasePreparationWorkflow",
                return_value=mock_rel_wf,
            ),
            patch(
                "attune.workflows.code_review.CodeReviewWorkflow",
                return_value=mock_cr_wf,
            ),
        ):
            result = await wf.execute(path=".", diff="--- a/x.py\n+++ b/x.py\n")

        assert result.go_no_go == "NO_GO"
        assert any(
            b.startswith("GATEKEEPER_EXECUTION_FAILED") and "code_review" in b
            for b in result.blockers
        )

    @pytest.mark.asyncio
    async def test_result_contains_mode(self) -> None:
        """Given execution, result contains the pipeline mode."""
        from unittest.mock import AsyncMock, patch

        wf = SecureReleasePipeline(mode="standard")

        sec_result = self._make_mock_result({"assessment": {"risk_score": 5, "risk_level": "low"}})
        rel_result = self._make_mock_result({"approved": True, "confidence": "high"})

        mock_sec_wf = MagicMock()
        mock_sec_wf.execute = AsyncMock(return_value=sec_result)
        mock_rel_wf = MagicMock()
        mock_rel_wf.execute = AsyncMock(return_value=rel_result)

        with (
            patch(
                "attune.workflows.security_audit.SecurityAuditWorkflow",
                return_value=mock_sec_wf,
            ),
            patch(
                "attune.workflows.release_prep.ReleasePreparationWorkflow",
                return_value=mock_rel_wf,
            ),
        ):
            result = await wf.execute(path=".")

        assert result.mode == "standard"
