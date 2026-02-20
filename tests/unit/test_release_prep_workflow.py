"""Unit tests for ReleasePreparationWorkflow.

Tests cover workflow instantiation, configuration, stage definitions,
error handling, the default_context() classmethod, and the
format_release_prep_report() helper.

Uses unittest.mock to mock subprocess calls, LLM invocations,
and external imports.
"""

import json
import subprocess
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.release_prep import (
    RELEASE_PREP_STEPS,
    ReleasePreparationWorkflow,
    format_release_prep_report,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workflow():
    """Create a default ReleasePreparationWorkflow with auth strategy disabled."""
    return ReleasePreparationWorkflow(enable_auth_strategy=False)


@pytest.fixture
def workflow_with_crew():
    """Create a workflow with security crew enabled."""
    return ReleasePreparationWorkflow(
        use_security_crew=True,
        crew_config={"scan_depth": "deep"},
        enable_auth_strategy=False,
    )


@pytest.fixture
def clean_input_data():
    """Input data representing a clean codebase."""
    return {
        "path": "/tmp/test_project",
        "health": {
            "passed": True,
            "health_score": 100,
            "failed_checks": [],
            "checks": {
                "lint": {"passed": True, "errors": 0, "tool": "ruff"},
                "types": {"passed": True, "errors": 0, "tool": "mypy"},
                "tests": {"passed": True, "test_count": 50, "tool": "pytest"},
            },
        },
        "security": {
            "passed": True,
            "total_issues": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "issues": [],
            "tool": "bandit",
        },
        "changelog": {
            "total_commits": 5,
            "commits": [
                {"sha": "abc1234", "message": "feat: new feature", "category": "features"},
            ],
            "by_category": {"features": 3, "fixes": 2},
            "generated_at": "2026-02-13T00:00:00",
            "period": "1 week ago",
        },
    }


# ---------------------------------------------------------------------------
# Test: Workflow instantiation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWorkflowInstantiation:
    """Test workflow creation with various configurations."""

    def test_default_instantiation(self, workflow):
        """Test default workflow has correct name, stages, and tier map."""
        assert workflow.name == "release-prep"
        assert (
            workflow.description == "Pre-release quality gate with health, security, and changelog"
        )
        assert workflow.stages == ["health", "security", "changelog", "approve"]
        assert workflow.skip_approve_if_clean is True
        assert workflow.use_security_crew is False
        assert workflow.crew_config == {}
        assert workflow._has_blockers is False

    def test_skip_approve_disabled(self):
        """Test workflow with skip_approve_if_clean=False."""
        wf = ReleasePreparationWorkflow(
            skip_approve_if_clean=False,
            enable_auth_strategy=False,
        )
        assert wf.skip_approve_if_clean is False

    def test_security_crew_enabled(self, workflow_with_crew):
        """Test that enabling security crew adds crew_security stage."""
        assert "crew_security" in workflow_with_crew.stages
        assert workflow_with_crew.stages == [
            "health",
            "security",
            "crew_security",
            "changelog",
            "approve",
        ]
        assert workflow_with_crew.crew_config == {"scan_depth": "deep"}

    def test_security_crew_tier_map(self, workflow_with_crew):
        """Test tier map includes crew_security when enabled."""
        assert workflow_with_crew.tier_map["crew_security"] == ModelTier.PREMIUM
        assert workflow_with_crew.tier_map["health"] == ModelTier.CHEAP
        assert workflow_with_crew.tier_map["security"] == ModelTier.CAPABLE
        assert workflow_with_crew.tier_map["changelog"] == ModelTier.CAPABLE
        assert workflow_with_crew.tier_map["approve"] == ModelTier.PREMIUM

    def test_default_crew_config_is_empty_dict(self):
        """Test that crew_config defaults to empty dict when None."""
        wf = ReleasePreparationWorkflow(
            crew_config=None,
            enable_auth_strategy=False,
        )
        assert wf.crew_config == {}

    def test_enable_auth_strategy_default(self):
        """Test that auth strategy is enabled by default."""
        wf = ReleasePreparationWorkflow()
        assert wf.enable_auth_strategy is True


# ---------------------------------------------------------------------------
# Test: Configuration / step definitions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStepConfig:
    """Test RELEASE_PREP_STEPS configuration."""

    def test_approve_step_exists(self):
        """Test that the approve step is defined."""
        assert "approve" in RELEASE_PREP_STEPS

    def test_approve_step_properties(self):
        """Test approve step has correct configuration."""
        step = RELEASE_PREP_STEPS["approve"]
        assert step.name == "approve"
        assert step.task_type == "final_review"
        assert step.tier_hint == "premium"
        assert step.max_tokens == 2000

    def test_tier_map_values(self, workflow):
        """Test that tier map uses correct tiers for each stage."""
        assert workflow.tier_map["health"] == ModelTier.CHEAP
        assert workflow.tier_map["security"] == ModelTier.CAPABLE
        assert workflow.tier_map["changelog"] == ModelTier.CAPABLE
        assert workflow.tier_map["approve"] == ModelTier.PREMIUM


# ---------------------------------------------------------------------------
# Test: default_context classmethod
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaultContext:
    """Test the default_context classmethod."""

    def test_default_context_returns_workflow_context(self):
        """Test that default_context returns a WorkflowContext instance."""
        from attune.workflows.context import WorkflowContext

        ctx = ReleasePreparationWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)

    def test_default_context_has_prompt_service(self):
        """Test that default context includes a prompt service."""
        ctx = ReleasePreparationWorkflow.default_context()
        assert ctx.prompt is not None

    def test_default_context_has_parsing_service(self):
        """Test that default context includes a parsing service."""
        ctx = ReleasePreparationWorkflow.default_context()
        assert ctx.parsing is not None

    def test_default_context_with_xml_config(self):
        """Test that default_context passes xml_config to services."""
        xml_cfg = {"enforce_xml": True, "schema_version": "1.0"}
        ctx = ReleasePreparationWorkflow.default_context(xml_config=xml_cfg)
        assert ctx.prompt is not None
        assert ctx.parsing is not None


# ---------------------------------------------------------------------------
# Test: should_skip_stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestShouldSkipStage:
    """Test conditional stage skipping logic."""

    def test_skip_approve_when_clean(self, workflow):
        """Test that approve is skipped when no blockers."""
        workflow._has_blockers = False
        should_skip, reason = workflow.should_skip_stage("approve", {})
        assert should_skip is True
        assert reason == "All checks passed - auto-approved"

    def test_no_skip_approve_when_blockers(self, workflow):
        """Test that approve is not skipped when blockers exist."""
        workflow._has_blockers = True
        should_skip, reason = workflow.should_skip_stage("approve", {})
        assert should_skip is False
        assert reason is None

    def test_no_skip_approve_when_disabled(self):
        """Test that approve is never skipped when skip_approve_if_clean=False."""
        wf = ReleasePreparationWorkflow(
            skip_approve_if_clean=False,
            enable_auth_strategy=False,
        )
        wf._has_blockers = False
        should_skip, reason = wf.should_skip_stage("approve", {})
        assert should_skip is False
        assert reason is None

    def test_non_approve_stage_never_skipped(self, workflow):
        """Test that non-approve stages are never skipped."""
        for stage in ("health", "security", "changelog"):
            should_skip, reason = workflow.should_skip_stage(stage, {})
            assert should_skip is False
            assert reason is None


# ---------------------------------------------------------------------------
# Test: run_stage routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunStageRouting:
    """Test that run_stage routes to the correct stage method."""

    @pytest.mark.asyncio
    async def test_routes_to_health(self, workflow):
        """Test routing to _health stage."""
        with patch.object(workflow, "_health", new_callable=AsyncMock, return_value=({}, 0, 0)):
            await workflow.run_stage("health", ModelTier.CHEAP, {})
            workflow._health.assert_awaited_once_with({}, ModelTier.CHEAP)

    @pytest.mark.asyncio
    async def test_routes_to_security(self, workflow):
        """Test routing to _security stage."""
        with patch.object(workflow, "_security", new_callable=AsyncMock, return_value=({}, 0, 0)):
            await workflow.run_stage("security", ModelTier.CAPABLE, {})
            workflow._security.assert_awaited_once_with({}, ModelTier.CAPABLE)

    @pytest.mark.asyncio
    async def test_routes_to_changelog(self, workflow):
        """Test routing to _changelog stage."""
        with patch.object(workflow, "_changelog", new_callable=AsyncMock, return_value=({}, 0, 0)):
            await workflow.run_stage("changelog", ModelTier.CAPABLE, {})
            workflow._changelog.assert_awaited_once_with({}, ModelTier.CAPABLE)

    @pytest.mark.asyncio
    async def test_routes_to_approve(self, workflow):
        """Test routing to _approve stage."""
        with patch.object(workflow, "_approve", new_callable=AsyncMock, return_value=({}, 0, 0)):
            await workflow.run_stage("approve", ModelTier.PREMIUM, {})
            workflow._approve.assert_awaited_once_with({}, ModelTier.PREMIUM)

    @pytest.mark.asyncio
    async def test_routes_to_crew_security(self, workflow_with_crew):
        """Test routing to _crew_security stage."""
        with patch.object(
            workflow_with_crew, "_crew_security", new_callable=AsyncMock, return_value=({}, 0, 0)
        ):
            await workflow_with_crew.run_stage("crew_security", ModelTier.PREMIUM, {})
            workflow_with_crew._crew_security.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_stage_raises(self, workflow):
        """Test that unknown stage name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown stage: nonexistent"):
            await workflow.run_stage("nonexistent", ModelTier.CHEAP, {})


# ---------------------------------------------------------------------------
# Test: _health stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthStage:
    """Test the health check stage."""

    @pytest.mark.asyncio
    async def test_health_all_pass(self, workflow):
        """Test health stage when all tools pass."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "All checks passed"
        mock_result.stderr = ""

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, in_tok, out_tok = await workflow._health({"path": "."}, ModelTier.CHEAP)

        health = result["health"]
        assert health["passed"] is True
        assert health["health_score"] == 100
        assert health["failed_checks"] == []
        assert workflow._has_blockers is False

    @pytest.mark.asyncio
    async def test_health_lint_fails(self, workflow):
        """Test health stage when lint check fails."""
        call_count = 0

        def fake_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Lint fails
                result.returncode = 1
                result.stdout = "error: something\nerror: something else"
                result.stderr = ""
            else:
                # Others pass
                result.returncode = 0
                result.stdout = "ok"
                result.stderr = ""
            return result

        with patch("attune.workflows.release_prep_stages.subprocess.run", side_effect=fake_run):
            result, _, _ = await workflow._health({"path": "."}, ModelTier.CHEAP)

        health = result["health"]
        assert health["checks"]["lint"]["passed"] is False
        assert health["checks"]["lint"]["errors"] == 2
        assert "lint" in health["failed_checks"]
        assert health["health_score"] == 80
        assert workflow._has_blockers is True

    @pytest.mark.asyncio
    async def test_health_tool_timeout(self, workflow):
        """Test health stage when a tool times out."""

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="ruff", timeout=60)

        with patch("attune.workflows.release_prep_stages.subprocess.run", side_effect=fake_run):
            result, _, _ = await workflow._health({"path": "."}, ModelTier.CHEAP)

        health = result["health"]
        # When all tools timeout, they are skipped with passed=True
        assert health["checks"]["lint"]["skipped"] is True
        assert health["checks"]["types"]["skipped"] is True
        assert health["checks"]["tests"]["skipped"] is True
        assert health["passed"] is True

    @pytest.mark.asyncio
    async def test_health_tool_not_found(self, workflow):
        """Test health stage when a tool is not installed."""

        def fake_run(*args, **kwargs):
            raise FileNotFoundError("ruff not found")

        with patch("attune.workflows.release_prep_stages.subprocess.run", side_effect=fake_run):
            result, _, _ = await workflow._health({"path": "."}, ModelTier.CHEAP)

        health = result["health"]
        assert health["checks"]["lint"]["skipped"] is True
        assert health["passed"] is True

    @pytest.mark.asyncio
    async def test_health_preserves_input_data(self, workflow):
        """Test that health stage merges result with input data."""
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._health(
                {"path": ".", "extra_key": "extra_value"},
                ModelTier.CHEAP,
            )

        assert result["extra_key"] == "extra_value"
        assert "health" in result

    @pytest.mark.asyncio
    async def test_health_default_path(self, workflow):
        """Test health stage defaults to '.' if no path given."""
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch(
            "attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result
        ) as mock_run:
            await workflow._health({}, ModelTier.CHEAP)

        # Verify ruff was called with "." as path
        first_call = mock_run.call_args_list[0]
        assert "." in first_call[0][0]

    @pytest.mark.asyncio
    async def test_health_auth_strategy_with_directory(self):
        """Test health stage with auth strategy enabled on a directory."""
        import tempfile
        from pathlib import Path

        wf = ReleasePreparationWorkflow(enable_auth_strategy=True)

        mock_strategy = MagicMock()
        mock_mode = MagicMock()
        mock_mode.value = "api_key"
        mock_strategy.get_recommended_mode.return_value = mock_mode
        mock_strategy.estimate_cost.return_value = {"monetary_cost": 0.05}

        mock_result = MagicMock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a small Python file
            py_file = Path(tmpdir) / "test.py"
            py_file.write_text("x = 1\ny = 2\n")

            with (
                patch(
                    "attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result
                ),
                patch("attune.models.get_auth_strategy", return_value=mock_strategy),
                patch("attune.models.count_lines_of_code", return_value=10),
                patch("attune.models.get_module_size_category", return_value="small"),
            ):
                result, _, _ = await wf._health({"path": tmpdir}, ModelTier.CHEAP)

        assert wf._auth_mode_used == "api_key"

    @pytest.mark.asyncio
    async def test_health_auth_strategy_failure_graceful(self):
        """Test health stage handles auth strategy failure gracefully."""
        wf = ReleasePreparationWorkflow(enable_auth_strategy=True)

        mock_result = MagicMock(returncode=0, stdout="", stderr="")

        with (
            patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result),
            patch(
                "attune.models.get_auth_strategy",
                side_effect=RuntimeError("auth unavailable"),
            ),
            patch("attune.models.count_lines_of_code", return_value=100),
            patch("attune.models.get_module_size_category", return_value="small"),
        ):
            # Should not raise, should degrade gracefully
            result, _, _ = await wf._health({"path": "."}, ModelTier.CHEAP)

        assert "health" in result

    @pytest.mark.asyncio
    async def test_health_auth_strategy_subscription_mode(self):
        """Test health stage with subscription auth mode."""
        import tempfile
        from pathlib import Path

        wf = ReleasePreparationWorkflow(enable_auth_strategy=True)

        mock_strategy = MagicMock()
        mock_mode = MagicMock()
        mock_mode.value = "subscription"
        mock_strategy.get_recommended_mode.return_value = mock_mode
        mock_strategy.estimate_cost.return_value = {"quota_cost": "2 credits"}

        mock_result = MagicMock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = Path(tmpdir) / "test.py"
            py_file.write_text("x = 1\n")

            with (
                patch(
                    "attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result
                ),
                patch("attune.models.get_auth_strategy", return_value=mock_strategy),
                patch("attune.models.count_lines_of_code", return_value=500),
                patch("attune.models.get_module_size_category", return_value="medium"),
            ):
                result, _, _ = await wf._health({"path": tmpdir}, ModelTier.CHEAP)

        assert wf._auth_mode_used == "subscription"


# ---------------------------------------------------------------------------
# Test: _security stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityStage:
    """Test the security scan stage."""

    @pytest.mark.asyncio
    async def test_security_no_issues(self, workflow):
        """Test security stage with clean scan."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"results": []})
        mock_result.stderr = ""

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._security({"path": "."}, ModelTier.CAPABLE)

        security = result["security"]
        assert security["passed"] is True
        assert security["total_issues"] == 0
        assert security["high_severity"] == 0
        assert security["tool"] == "bandit"

    @pytest.mark.asyncio
    async def test_security_high_severity_sets_blockers(self, workflow):
        """Test that high severity issues set blockers flag."""
        findings = {
            "results": [
                {
                    "test_id": "B105",
                    "filename": "test.py",
                    "line_number": 10,
                    "issue_severity": "HIGH",
                    "issue_text": "Hardcoded password",
                    "issue_confidence": "HIGH",
                },
            ]
        }
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps(findings)
        mock_result.stderr = ""

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._security({"path": "."}, ModelTier.CAPABLE)

        security = result["security"]
        assert security["passed"] is False
        assert security["high_severity"] == 1
        assert workflow._has_blockers is True

    @pytest.mark.asyncio
    async def test_security_medium_severity_no_blockers(self, workflow):
        """Test that medium severity issues do not set blockers."""
        findings = {
            "results": [
                {
                    "test_id": "B101",
                    "filename": "test.py",
                    "line_number": 5,
                    "issue_severity": "MEDIUM",
                    "issue_text": "Assert used",
                    "issue_confidence": "HIGH",
                },
            ]
        }
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps(findings)
        mock_result.stderr = ""

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._security({"path": "."}, ModelTier.CAPABLE)

        security = result["security"]
        assert security["passed"] is True
        assert security["medium_severity"] == 1
        assert workflow._has_blockers is False

    @pytest.mark.asyncio
    async def test_security_invalid_json(self, workflow):
        """Test security stage handles invalid JSON gracefully."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "not valid json{"
        mock_result.stderr = ""

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._security({"path": "."}, ModelTier.CAPABLE)

        security = result["security"]
        assert security["total_issues"] == 0
        assert security["passed"] is True

    @pytest.mark.asyncio
    async def test_security_bandit_timeout(self, workflow):
        """Test security stage when bandit times out."""
        with patch(
            "attune.workflows.release_prep_stages.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="bandit", timeout=120),
        ):
            result, _, _ = await workflow._security({"path": "."}, ModelTier.CAPABLE)

        security = result["security"]
        assert security["total_issues"] == 0
        assert security["passed"] is True

    @pytest.mark.asyncio
    async def test_security_issues_capped_at_20(self, workflow):
        """Test that issues list is capped at 20 entries."""
        findings = {
            "results": [
                {
                    "test_id": f"B{i}",
                    "filename": f"file{i}.py",
                    "line_number": i,
                    "issue_severity": "MEDIUM",
                    "issue_text": f"Issue {i}",
                    "issue_confidence": "HIGH",
                }
                for i in range(30)
            ]
        }
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps(findings)
        mock_result.stderr = ""

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._security({"path": "."}, ModelTier.CAPABLE)

        security = result["security"]
        assert len(security["issues"]) == 20
        assert security["total_issues"] == 30


# ---------------------------------------------------------------------------
# Test: _changelog stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChangelogStage:
    """Test the changelog generation stage."""

    @pytest.mark.asyncio
    async def test_changelog_parses_commits(self, workflow):
        """Test changelog correctly parses git log output."""
        git_output = (
            "abc1234 feat: add new feature\n"
            "def5678 fix: resolve bug\n"
            "ghi9012 docs: update readme\n"
            "jkl3456 refactor: clean up module\n"
            "mno7890 test: add unit tests\n"
            "pqr1234 chore: update deps\n"
            "stu5678 misc: something else\n"
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = git_output
        mock_result.stderr = ""

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._changelog({"path": "."}, ModelTier.CAPABLE)

        changelog = result["changelog"]
        assert changelog["total_commits"] == 7
        assert changelog["by_category"]["features"] == 1
        assert changelog["by_category"]["fixes"] == 1
        assert changelog["by_category"]["docs"] == 1
        assert changelog["by_category"]["refactor"] == 1
        assert changelog["by_category"]["tests"] == 1
        assert changelog["by_category"]["chores"] == 1
        assert changelog["by_category"]["other"] == 1

    @pytest.mark.asyncio
    async def test_changelog_empty_commits(self, workflow):
        """Test changelog with no commits."""
        mock_result = MagicMock(returncode=0, stdout="", stderr="")

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._changelog({"path": "."}, ModelTier.CAPABLE)

        changelog = result["changelog"]
        assert changelog["total_commits"] == 0
        assert changelog["by_category"] == {}

    @pytest.mark.asyncio
    async def test_changelog_custom_since(self, workflow):
        """Test changelog uses custom since parameter."""
        mock_result = MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result
        ) as mock_run:
            await workflow._changelog(
                {"path": "/project", "since": "2 weeks ago"},
                ModelTier.CAPABLE,
            )

        args = mock_run.call_args[0][0]
        assert "--since=2 weeks ago" in args

    @pytest.mark.asyncio
    async def test_changelog_git_timeout(self, workflow):
        """Test changelog handles git timeout gracefully."""
        with patch(
            "attune.workflows.release_prep_stages.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
        ):
            result, _, _ = await workflow._changelog({"path": "."}, ModelTier.CAPABLE)

        changelog = result["changelog"]
        assert changelog["total_commits"] == 0

    @pytest.mark.asyncio
    async def test_changelog_skips_blank_lines(self, workflow):
        """Test changelog ignores blank lines in git output."""
        git_output = "\nabc1234 feat: add feature\n\ndef5678 fix: bug fix\n\n"
        mock_result = MagicMock(returncode=0, stdout=git_output, stderr="")

        with patch("attune.workflows.release_prep_stages.subprocess.run", return_value=mock_result):
            result, _, _ = await workflow._changelog({"path": "."}, ModelTier.CAPABLE)

        assert result["changelog"]["total_commits"] == 2


# ---------------------------------------------------------------------------
# Test: _crew_security stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCrewSecurityStage:
    """Test the crew security stage."""

    @pytest.mark.asyncio
    async def test_crew_security_import_error(self, workflow_with_crew):
        """Test crew_security falls back when security_adapters import fails."""
        with patch.dict("sys.modules", {"attune.workflows.security_adapters": None}):
            with patch("attune.workflows.release_prep.ReleasePreparationWorkflow._crew_security"):
                # Since we can't easily trigger ImportError mid-method,
                # test the fallback path directly
                pass

        # Test via the actual code path by mocking the import inside the method
        with patch(
            "builtins.__import__",
            side_effect=ImportError("no module"),
        ):
            # The ImportError inside _crew_security should be caught
            result, in_tok, out_tok = await workflow_with_crew._crew_security(
                {"path": "."}, ModelTier.PREMIUM
            )

        crew = result["crew_security"]
        assert crew["available"] is False
        assert crew["fallback"] is True

    @pytest.mark.asyncio
    async def test_crew_security_check_not_available(self, workflow_with_crew):
        """Test crew_security when _check_crew_available returns False."""
        mock_module = types.ModuleType("attune.workflows.security_adapters")
        mock_module._check_crew_available = MagicMock(return_value=False)
        mock_module._get_crew_audit = AsyncMock()
        mock_module.crew_report_to_workflow_format = MagicMock()
        mock_module.merge_security_results = MagicMock()

        with patch.dict(sys.modules, {"attune.workflows.security_adapters": mock_module}):
            result, in_tok, out_tok = await workflow_with_crew._crew_security(
                {"path": ".", "security": {}}, ModelTier.PREMIUM
            )

        crew = result["crew_security"]
        assert crew["available"] is False
        assert crew["fallback"] is True
        assert crew["reason"] == "SecurityAuditCrew not installed"
        assert in_tok == 0
        assert out_tok == 0

    @pytest.mark.asyncio
    async def test_crew_security_audit_returns_none(self, workflow_with_crew):
        """Test crew_security when _get_crew_audit returns None (timeout/failure)."""
        mock_module = types.ModuleType("attune.workflows.security_adapters")
        mock_module._check_crew_available = MagicMock(return_value=True)
        mock_module._get_crew_audit = AsyncMock(return_value=None)
        mock_module.crew_report_to_workflow_format = MagicMock()
        mock_module.merge_security_results = MagicMock()

        with patch.dict(sys.modules, {"attune.workflows.security_adapters": mock_module}):
            result, in_tok, out_tok = await workflow_with_crew._crew_security(
                {"path": ".", "security": {}}, ModelTier.PREMIUM
            )

        crew = result["crew_security"]
        assert crew["available"] is True
        assert crew["fallback"] is True
        assert "failed or timed out" in crew["reason"]

    @pytest.mark.asyncio
    async def test_crew_security_successful_audit(self, workflow_with_crew):
        """Test crew_security with a successful audit returning findings."""
        crew_report = {"audit": "data"}
        crew_results = {
            "findings": [{"id": "F1", "severity": "high"}],
            "finding_count": 1,
            "risk_score": 75,
            "risk_level": "high",
            "summary": "Found critical issues",
            "agents_used": ["vuln_hunter", "risk_assessor"],
            "assessment": {
                "critical_findings": ["crit1"],
                "high_findings": ["high1"],
            },
        }
        merged = {"merged": True}

        mock_module = types.ModuleType("attune.workflows.security_adapters")
        mock_module._check_crew_available = MagicMock(return_value=True)
        mock_module._get_crew_audit = AsyncMock(return_value=crew_report)
        mock_module.crew_report_to_workflow_format = MagicMock(return_value=crew_results)
        mock_module.merge_security_results = MagicMock(return_value=merged)

        with patch.dict(sys.modules, {"attune.workflows.security_adapters": mock_module}):
            result, in_tok, out_tok = await workflow_with_crew._crew_security(
                {"path": ".", "security": {"issues": [{"id": "existing"}]}},
                ModelTier.PREMIUM,
            )

        crew = result["crew_security"]
        assert crew["available"] is True
        assert crew["fallback"] is False
        assert crew["critical_count"] == 1
        assert crew["high_count"] == 1
        assert crew["risk_score"] == 75
        assert crew["finding_count"] == 1
        assert crew["merged_results"] == merged
        assert workflow_with_crew._has_blockers is True
        assert in_tok > 0
        assert out_tok > 0

    @pytest.mark.asyncio
    async def test_crew_security_no_critical_findings(self, workflow_with_crew):
        """Test crew_security with no critical/high findings does not set blockers."""
        crew_results = {
            "findings": [],
            "finding_count": 0,
            "risk_score": 10,
            "risk_level": "low",
            "summary": "Clean",
            "agents_used": ["vuln_hunter"],
            "assessment": {
                "critical_findings": [],
                "high_findings": [],
            },
        }

        mock_module = types.ModuleType("attune.workflows.security_adapters")
        mock_module._check_crew_available = MagicMock(return_value=True)
        mock_module._get_crew_audit = AsyncMock(return_value={"ok": True})
        mock_module.crew_report_to_workflow_format = MagicMock(return_value=crew_results)
        mock_module.merge_security_results = MagicMock(return_value={})

        with patch.dict(sys.modules, {"attune.workflows.security_adapters": mock_module}):
            result, _, _ = await workflow_with_crew._crew_security({"path": "."}, ModelTier.PREMIUM)

        assert result["crew_security"]["fallback"] is False
        assert workflow_with_crew._has_blockers is False


# ---------------------------------------------------------------------------
# Test: _approve stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApproveStage:
    """Test the approval/assessment stage."""

    @pytest.mark.asyncio
    async def test_approve_clean_release(self, workflow, clean_input_data):
        """Test approve stage for a clean release."""
        workflow._call_llm = AsyncMock(
            return_value=("Release looks good. Ready to ship.", 100, 200)
        )
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, in_tok, out_tok = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert result["approved"] is True
        assert result["confidence"] == "high"
        assert result["blockers"] == []
        assert result["recommendation"] == "Ready for release"
        assert result["model_tier_used"] == "premium"
        assert "formatted_report" in result

    @pytest.mark.asyncio
    async def test_approve_with_health_blockers(self, workflow, clean_input_data):
        """Test approve stage when health checks fail."""
        clean_input_data["health"]["passed"] = False
        clean_input_data["health"]["failed_checks"] = ["lint", "types"]

        workflow._call_llm = AsyncMock(return_value=("Issues found. Not ready.", 100, 200))
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert result["approved"] is False
        assert result["confidence"] == "low"
        assert len(result["blockers"]) == 2
        assert result["recommendation"] == "Address blockers before release"

    @pytest.mark.asyncio
    async def test_approve_with_security_blockers(self, workflow, clean_input_data):
        """Test approve stage when security issues exist."""
        clean_input_data["security"]["passed"] = False
        clean_input_data["security"]["high_severity"] = 3

        workflow._call_llm = AsyncMock(
            return_value=("Security issues must be addressed.", 100, 200)
        )
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert result["approved"] is False
        assert any("Security issues" in b for b in result["blockers"])

    @pytest.mark.asyncio
    async def test_approve_no_commits_blocker(self, workflow, clean_input_data):
        """Test approve stage when no commits in period."""
        clean_input_data["changelog"]["total_commits"] = 0

        workflow._call_llm = AsyncMock(return_value=("No changes to release.", 100, 200))
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert result["approved"] is False
        assert any("No commits" in b for b in result["blockers"])

    @pytest.mark.asyncio
    async def test_approve_medium_warnings(self, workflow, clean_input_data):
        """Test approve stage generates warnings for medium issues."""
        clean_input_data["security"]["medium_severity"] = 5

        workflow._call_llm = AsyncMock(return_value=("Some warnings but OK.", 100, 200))
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert result["approved"] is True
        assert result["confidence"] == "medium"
        assert any("medium security" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_approve_low_test_count_warning(self, workflow, clean_input_data):
        """Test approve stage warns about low test count."""
        clean_input_data["health"]["checks"]["tests"]["test_count"] = 3

        workflow._call_llm = AsyncMock(return_value=("Low test count noted.", 100, 200))
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert any("Low test count" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_approve_with_xml_enabled(self, workflow, clean_input_data):
        """Test approve stage uses XML prompt when enabled."""
        workflow._is_xml_enabled = MagicMock(return_value=True)
        workflow._render_xml_prompt = MagicMock(return_value="<xml>prompt</xml>")
        workflow._call_llm = AsyncMock(return_value=("<response>good</response>", 100, 200))
        workflow._parse_xml_response = MagicMock(
            return_value={"xml_parsed": True, "summary": "All clear"}
        )

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        workflow._render_xml_prompt.assert_called_once()
        assert result["xml_parsed"] is True
        assert result["summary"] == "All clear"

    @pytest.mark.asyncio
    async def test_approve_includes_auth_mode(self, workflow, clean_input_data):
        """Test that auth_mode_used is included when set."""
        workflow._auth_mode_used = "subscription"
        workflow._call_llm = AsyncMock(return_value=("Good to go.", 100, 200))
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert result["auth_mode_used"] == "subscription"

    @pytest.mark.asyncio
    async def test_approve_executor_fallback(self, workflow, clean_input_data):
        """Test approve falls back to _call_llm when executor fails."""
        workflow._executor = MagicMock()
        workflow.run_step_with_executor = AsyncMock(side_effect=RuntimeError("executor error"))
        workflow._call_llm = AsyncMock(return_value=("Fallback response.", 100, 200))
        workflow._is_xml_enabled = MagicMock(return_value=False)
        workflow._parse_xml_response = MagicMock(return_value={})

        result, _, _ = await workflow._approve(clean_input_data, ModelTier.PREMIUM)

        assert result["assessment"] == "Fallback response."
        workflow._call_llm.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test: format_release_prep_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatReport:
    """Test the format_release_prep_report helper function."""

    def test_approved_report(self, clean_input_data):
        """Test report formatting for an approved release."""
        result = {
            "approved": True,
            "confidence": "high",
            "blockers": [],
            "warnings": [],
            "health_score": 100,
            "commit_count": 5,
            "assessment": "All clear.",
            "recommendation": "Ready for release",
            "model_tier_used": "premium",
        }
        report = format_release_prep_report(result, clean_input_data)

        assert "READY FOR RELEASE" in report
        assert "HIGH" in report
        assert "HEALTH CHECKS" in report
        assert "SECURITY SCAN" in report
        assert "CHANGELOG" in report
        assert "premium" in report

    def test_not_approved_report(self):
        """Test report formatting for a not-approved release."""
        result = {
            "approved": False,
            "confidence": "low",
            "blockers": ["Health check failed: lint"],
            "warnings": [],
            "health_score": 80,
            "commit_count": 0,
            "assessment": "[Simulated] Not ready.",
            "recommendation": "Address blockers before release",
            "model_tier_used": "premium",
        }
        input_data = {
            "health": {
                "health_score": 80,
                "checks": {
                    "lint": {"passed": False, "errors": 5, "tool": "ruff"},
                },
            },
            "security": {
                "passed": False,
                "total_issues": 2,
                "high_severity": 1,
                "medium_severity": 1,
            },
        }
        report = format_release_prep_report(result, input_data)

        assert "NOT READY" in report
        assert "BLOCKERS" in report
        assert "Health check failed: lint" in report

    def test_report_skipped_checks(self):
        """Test report formatting for skipped checks."""
        result = {
            "approved": True,
            "confidence": "medium",
            "blockers": [],
            "warnings": ["Low test count: 0"],
            "health_score": 100,
            "commit_count": 1,
            "assessment": "OK with warnings.",
            "recommendation": "Ready for release",
            "model_tier_used": "capable",
        }
        input_data = {
            "health": {
                "health_score": 100,
                "checks": {
                    "lint": {"passed": True, "errors": 0, "tool": "ruff", "skipped": True},
                },
            },
        }
        report = format_release_prep_report(result, input_data)

        assert "SKIPPED" in report
        assert "WARNINGS" in report

    def test_report_long_assessment_truncated(self):
        """Test that long assessments are truncated in the report."""
        long_text = "A" * 2000
        result = {
            "approved": True,
            "confidence": "high",
            "blockers": [],
            "warnings": [],
            "health_score": 100,
            "commit_count": 5,
            "assessment": long_text,
            "recommendation": "Ready for release",
            "model_tier_used": "premium",
        }
        report = format_release_prep_report(result, {})

        assert "..." in report
        # The truncated assessment should be at most 1500 chars + "..."
        assert long_text[:1500] in report

    def test_report_simulated_assessment_excluded(self):
        """Test that simulated assessments are excluded from report."""
        result = {
            "approved": True,
            "confidence": "high",
            "blockers": [],
            "warnings": [],
            "health_score": 100,
            "commit_count": 5,
            "assessment": "[Simulated response]",
            "recommendation": "Ready for release",
            "model_tier_used": "premium",
        }
        report = format_release_prep_report(result, {})

        assert "DETAILED ASSESSMENT" not in report

    def test_report_empty_input_data(self):
        """Test report formatting with empty input data."""
        result = {
            "approved": True,
            "confidence": "high",
            "blockers": [],
            "warnings": [],
            "health_score": 0,
            "commit_count": 0,
            "assessment": "",
            "recommendation": "Ready for release",
            "model_tier_used": "cheap",
        }
        report = format_release_prep_report(result, {})

        assert "RELEASE PREPARATION REPORT" in report
        assert "READY FOR RELEASE" in report

    def test_report_changelog_categories(self):
        """Test that changelog categories appear in report."""
        result = {
            "approved": True,
            "confidence": "high",
            "blockers": [],
            "warnings": [],
            "health_score": 100,
            "commit_count": 10,
            "assessment": "",
            "recommendation": "Ready for release",
            "model_tier_used": "premium",
        }
        input_data = {
            "changelog": {
                "total_commits": 10,
                "by_category": {"features": 5, "fixes": 3, "docs": 2},
                "period": "1 week ago",
            },
        }
        report = format_release_prep_report(result, input_data)

        assert "features: 5" in report
        assert "fixes: 3" in report
        assert "docs: 2" in report
        assert "1 week ago" in report
