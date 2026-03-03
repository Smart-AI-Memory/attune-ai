"""Tests for DocAuditWorkflow.

Covers workflow class attributes, constructor, and each stage
(audit, plan, execute, verify) with mocked check results.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import patch

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.doc_audit.checks import CheckResult
from attune.workflows.doc_audit.workflow import DocAuditWorkflow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_check(
    check_id: str,
    status: str = "pass",
    auto_fixable: bool = False,
    details: str = "ok",
    file: str | None = None,
) -> CheckResult:
    """Return a minimal CheckResult for use in tests."""
    return CheckResult(
        id=check_id,
        name=check_id.replace("-", " ").title(),
        status=status,
        details=details,
        file=file,
        auto_fixable=auto_fixable,
    )


def _pass_checks(n: int = 10) -> list[CheckResult]:
    """Return n passing CheckResult objects."""
    return [_make_check(f"check-{i}", status="pass") for i in range(n)]


def _mixed_checks() -> list[CheckResult]:
    """Return a list with 8 passing and 2 failing checks."""
    checks = [_make_check(f"check-{i}", status="pass") for i in range(8)]
    checks.append(
        _make_check(
            "test-count",
            status="fail",
            auto_fixable=True,
            details="README badge says 100 tests but pytest collected 146.",
            file="README.md",
        )
    )
    checks.append(
        _make_check(
            "workflow-count",
            status="warn",
            auto_fixable=False,
            details="README claims 5 workflows but 10 are registered.",
        )
    )
    return checks


# ---------------------------------------------------------------------------
# TestDocAuditWorkflowConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocAuditWorkflowConfig:
    """Verify DocAuditWorkflow class attributes are set correctly."""

    def test_name(self):
        """Workflow name is 'doc-audit'."""
        assert DocAuditWorkflow.name == "doc-audit"

    def test_description(self):
        """Workflow description is a non-empty string."""
        assert isinstance(DocAuditWorkflow.description, str)
        assert DocAuditWorkflow.description

    def test_stages(self):
        """Workflow stages list contains all four stage names."""
        assert DocAuditWorkflow.stages == ["audit", "plan", "execute", "verify"]

    def test_tier_map_keys(self):
        """Tier map contains one entry per stage."""
        expected_keys = {"audit", "plan", "execute", "verify"}
        assert set(DocAuditWorkflow.tier_map.keys()) == expected_keys

    def test_tier_map_audit_is_cheap(self):
        """Audit stage uses the CHEAP model tier."""
        assert DocAuditWorkflow.tier_map["audit"] == ModelTier.CHEAP

    def test_tier_map_plan_is_capable(self):
        """Plan stage uses the CAPABLE model tier."""
        assert DocAuditWorkflow.tier_map["plan"] == ModelTier.CAPABLE

    def test_tier_map_execute_is_capable(self):
        """Execute stage uses the CAPABLE model tier."""
        assert DocAuditWorkflow.tier_map["execute"] == ModelTier.CAPABLE

    def test_tier_map_verify_is_cheap(self):
        """Verify stage uses the CHEAP model tier."""
        assert DocAuditWorkflow.tier_map["verify"] == ModelTier.CHEAP


# ---------------------------------------------------------------------------
# TestDocAuditWorkflowInit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocAuditWorkflowInit:
    """Test DocAuditWorkflow constructor defaults and custom parameters."""

    def test_default_auto_fix(self):
        """auto_fix defaults to True."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        assert wf.auto_fix is True

    def test_default_build_docs(self):
        """build_docs defaults to True."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        assert wf.build_docs is True

    def test_default_strict(self):
        """strict defaults to True."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        assert wf.strict is True

    def test_default_project_root(self):
        """project_root defaults to '.'."""
        wf = DocAuditWorkflow()
        assert wf.project_root == "."

    def test_custom_project_root(self):
        """project_root can be set to a custom path."""
        wf = DocAuditWorkflow(project_root="/tmp/myproject")
        assert wf.project_root == "/tmp/myproject"

    def test_custom_auto_fix_false(self):
        """auto_fix can be set to False."""
        wf = DocAuditWorkflow(project_root="/tmp/test", auto_fix=False)
        assert wf.auto_fix is False

    def test_custom_build_docs_false(self):
        """build_docs can be set to False."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=False)
        assert wf.build_docs is False

    def test_custom_strict_false(self):
        """strict can be set to False."""
        wf = DocAuditWorkflow(project_root="/tmp/test", strict=False)
        assert wf.strict is False

    def test_audit_score_initialised_to_zero(self):
        """_audit_score is initialised to 0."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        assert wf._audit_score == 0

    @pytest.mark.asyncio
    async def test_run_stage_raises_for_unknown_stage(self):
        """run_stage raises ValueError for an unrecognised stage name."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        with pytest.raises(ValueError, match="Unknown stage"):
            await wf.run_stage("nonexistent", ModelTier.CHEAP, {})


# ---------------------------------------------------------------------------
# TestAuditStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditStage:
    """Tests for the _audit stage of DocAuditWorkflow."""

    @pytest.mark.asyncio
    async def test_audit_returns_score_and_checks(self):
        """Audit stage returns a score and a list of serialised checks."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        checks = _pass_checks(10)
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=checks,
        ):
            output, in_tok, out_tok = await wf._audit({})

        assert output["score"] == 100
        assert len(output["checks"]) == 10
        assert isinstance(in_tok, int)
        assert isinstance(out_tok, int)

    @pytest.mark.asyncio
    async def test_audit_score_all_pass(self):
        """Score is 100 when all checks pass."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=_pass_checks(10),
        ):
            output, _, _ = await wf._audit({})

        assert output["score"] == 100

    @pytest.mark.asyncio
    async def test_audit_score_mixed_pass_fail(self):
        """Score reflects proportion of passing checks (strict mode)."""
        wf = DocAuditWorkflow(project_root="/tmp/test", strict=True)
        checks = _mixed_checks()  # 8 pass, 1 fail, 1 warn
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=checks,
        ):
            output, _, _ = await wf._audit({})

        # 8 pass out of 10 = 80
        assert output["score"] == 80

    @pytest.mark.asyncio
    async def test_audit_score_non_strict_warns_count_as_pass(self):
        """In non-strict mode, warnings count as passing."""
        wf = DocAuditWorkflow(project_root="/tmp/test", strict=False)
        checks = _mixed_checks()  # 8 pass, 1 fail, 1 warn
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=checks,
        ):
            output, _, _ = await wf._audit({})

        # 8 pass + 1 warn = 9 out of 10 = 90
        assert output["score"] == 90

    @pytest.mark.asyncio
    async def test_audit_stores_score_on_instance(self):
        """_audit_score attribute is updated after the audit stage runs."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=_pass_checks(4),
        ):
            await wf._audit({})

        assert wf._audit_score == 100

    @pytest.mark.asyncio
    async def test_audit_uses_project_root_from_input(self):
        """Audit stage passes project_root from input_data to run_all_checks."""
        wf = DocAuditWorkflow(project_root="/default/root")
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=[],
        ) as mock_checks:
            await wf._audit({"project_root": "/custom/root"})

        mock_checks.assert_called_once_with("/custom/root")

    @pytest.mark.asyncio
    async def test_audit_serialises_check_result_fields(self):
        """Each serialised check has required keys."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=[_make_check("test-count", status="fail")],
        ):
            output, _, _ = await wf._audit({})

        check = output["checks"][0]
        for key in ("id", "name", "status", "details", "file", "line", "auto_fixable"):
            assert key in check, f"Missing key '{key}' in serialised check"

    @pytest.mark.asyncio
    async def test_audit_empty_checks_returns_100(self):
        """Score is 100 when there are no checks at all."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=[],
        ):
            output, _, _ = await wf._audit({})

        assert output["score"] == 100


# ---------------------------------------------------------------------------
# TestPlanStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlanStage:
    """Tests for the _plan stage of DocAuditWorkflow."""

    @pytest.mark.asyncio
    async def test_plan_generates_fixes_for_failing_checks(self):
        """Plan stage creates a fix entry for every failing check."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        checks = [
            {
                "id": "test-count",
                "status": "fail",
                "details": "Badge wrong.",
                "auto_fixable": True,
                "file": "README.md",
            },
            {
                "id": "workflow-count",
                "status": "pass",
                "details": "All good.",
                "auto_fixable": False,
                "file": None,
            },
        ]
        output, _, _ = await wf._plan({"checks": checks})

        assert len(output["fixes"]) == 1
        assert output["fixes"][0]["check_id"] == "test-count"

    @pytest.mark.asyncio
    async def test_plan_includes_warn_checks(self):
        """Plan stage creates fix entries for warning checks too."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        checks = [
            {
                "id": "skill-count",
                "status": "warn",
                "details": "Badge missing.",
                "auto_fixable": False,
                "file": None,
            },
        ]
        output, _, _ = await wf._plan({"checks": checks})

        assert len(output["fixes"]) == 1
        assert output["fixes"][0]["check_id"] == "skill-count"

    @pytest.mark.asyncio
    async def test_plan_fix_has_auto_fixable_flag(self):
        """Each fix entry carries the auto_fixable flag from the check."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        checks = [
            {
                "id": "test-count",
                "status": "fail",
                "details": "Wrong.",
                "auto_fixable": True,
                "file": "README.md",
            },
        ]
        output, _, _ = await wf._plan({"checks": checks})

        assert output["fixes"][0]["auto_fixable"] is True

    @pytest.mark.asyncio
    async def test_plan_no_fixes_when_all_pass(self):
        """Plan stage returns empty fixes list when all checks pass."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        checks = [
            {"id": f"c-{i}", "status": "pass", "details": "ok", "auto_fixable": False}
            for i in range(5)
        ]
        output, _, _ = await wf._plan({"checks": checks})

        assert output["fixes"] == []

    @pytest.mark.asyncio
    async def test_plan_preserves_input_data(self):
        """Plan stage output merges input_data into the returned dict."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        input_data = {"checks": [], "score": 100, "project_root": "/tmp"}
        output, _, _ = await wf._plan(input_data)

        assert output["score"] == 100
        assert output["project_root"] == "/tmp"

    @pytest.mark.asyncio
    async def test_plan_fix_description_comes_from_check_details(self):
        """Fix description is taken from the check's details field."""
        wf = DocAuditWorkflow(project_root="/tmp/test")
        checks = [
            {
                "id": "mcp-tool-count",
                "status": "fail",
                "details": "README claims 5 MCP tools but 3 found.",
                "auto_fixable": True,
                "file": "README.md",
            },
        ]
        output, _, _ = await wf._plan({"checks": checks})

        assert output["fixes"][0]["description"] == "README claims 5 MCP tools but 3 found."


# ---------------------------------------------------------------------------
# TestExecuteStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecuteStage:
    """Tests for the _execute stage of DocAuditWorkflow."""

    @pytest.mark.asyncio
    async def test_execute_skips_all_when_auto_fix_disabled(self):
        """When auto_fix=False, no files are modified."""
        wf = DocAuditWorkflow(project_root="/tmp/test", auto_fix=False)
        fixes = [
            {"check_id": "test-count", "auto_fixable": True, "description": "x", "file": None},
        ]
        input_data = {"fixes": fixes, "checks": [], "project_root": "/tmp/test"}
        output, _, _ = await wf._execute(input_data)

        assert output["applied"] == 0
        assert output["files_modified"] == []

    @pytest.mark.asyncio
    async def test_execute_counts_manual_fixes(self):
        """Non-auto-fixable fixes are counted as manual."""
        wf = DocAuditWorkflow(project_root="/tmp/test", auto_fix=True)
        fixes = [
            {
                "check_id": "stale-references",
                "auto_fixable": False,
                "description": "Manual fix required.",
                "file": None,
            },
        ]
        input_data = {"fixes": fixes, "checks": [], "project_root": "/tmp/test"}
        output, _, _ = await wf._execute(input_data)

        assert output["manual"] == 1
        assert output["applied"] == 0

    @pytest.mark.asyncio
    async def test_execute_applies_auto_fixable_count_fix(self, tmp_path):
        """auto_fixable test-count fix patches README badge count."""
        readme = tmp_path / "README.md"
        readme.write_text("[![Tests](tests-100-brightgreen)](url)\n", encoding="utf-8")
        wf = DocAuditWorkflow(project_root=str(tmp_path), auto_fix=True)
        checks_by_id = {
            "test-count": {
                "id": "test-count",
                "status": "fail",
                "details": "README badge says 100 tests but pytest collected 146.",
                "auto_fixable": True,
                "file": str(readme),
            }
        }
        fixes = [
            {
                "check_id": "test-count",
                "auto_fixable": True,
                "description": "Badge wrong.",
                "file": str(readme),
            }
        ]
        input_data = {
            "fixes": fixes,
            "checks": list(checks_by_id.values()),
            "project_root": str(tmp_path),
        }
        output, _, _ = await wf._execute(input_data)

        assert output["applied"] == 1
        assert str(readme) in output["files_modified"]
        updated = readme.read_text(encoding="utf-8")
        assert "tests-146-" in updated

    @pytest.mark.asyncio
    async def test_execute_files_modified_contains_no_duplicates(self, tmp_path):
        """The same file is not listed twice in files_modified."""
        readme = tmp_path / "README.md"
        readme.write_text("tests-100-brightgreen\n10 workflows\n", encoding="utf-8")
        wf = DocAuditWorkflow(project_root=str(tmp_path), auto_fix=True)
        checks = [
            {
                "id": "test-count",
                "status": "fail",
                "details": "README badge says 100 tests but pytest collected 50.",
                "auto_fixable": True,
                "file": str(readme),
            },
            {
                "id": "workflow-count",
                "status": "fail",
                "details": "README claims 10 workflows but 5 are registered.",
                "auto_fixable": True,
                "file": str(readme),
            },
        ]
        fixes = [
            {"check_id": "test-count", "auto_fixable": True, "description": "x", "file": None},
            {"check_id": "workflow-count", "auto_fixable": True, "description": "y", "file": None},
        ]
        input_data = {
            "fixes": fixes,
            "checks": checks,
            "project_root": str(tmp_path),
        }
        output, _, _ = await wf._execute(input_data)

        # README should appear at most once in files_modified
        assert output["files_modified"].count(str(readme)) <= 1

    @pytest.mark.asyncio
    async def test_execute_preserves_input_data(self):
        """Execute stage output merges original input_data keys."""
        wf = DocAuditWorkflow(project_root="/tmp/test", auto_fix=False)
        input_data = {"fixes": [], "checks": [], "project_root": "/tmp", "score": 75}
        output, _, _ = await wf._execute(input_data)

        assert output["score"] == 75


# ---------------------------------------------------------------------------
# TestVerifyStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVerifyStage:
    """Tests for the _verify stage of DocAuditWorkflow."""

    @pytest.mark.asyncio
    async def test_verify_returns_before_and_after_score(self):
        """Verify stage returns both before_score and after_score."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=False)
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=_pass_checks(10),
        ):
            output, _, _ = await wf._verify({"score": 80, "project_root": "/tmp"})

        assert output["before_score"] == 80
        assert output["after_score"] == 100

    @pytest.mark.asyncio
    async def test_verify_improved_flag_true_when_score_increases(self):
        """improved is True when after_score >= before_score."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=False)
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=_pass_checks(10),
        ):
            output, _, _ = await wf._verify({"score": 80})

        assert output["improved"] is True

    @pytest.mark.asyncio
    async def test_verify_improved_flag_false_when_score_decreases(self):
        """improved is False when after_score < before_score."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=False)
        failing_checks = [_make_check(f"c-{i}", status="fail") for i in range(10)]
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=failing_checks,
        ):
            output, _, _ = await wf._verify({"score": 90})

        assert output["improved"] is False

    @pytest.mark.asyncio
    async def test_verify_mkdocs_skipped_when_build_docs_false(self):
        """mkdocs_build is None when build_docs=False."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=False)
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=_pass_checks(5),
        ):
            output, _, _ = await wf._verify({"score": 100})

        assert output["mkdocs_build"] is None

    @pytest.mark.asyncio
    async def test_verify_mkdocs_called_when_build_docs_true(self):
        """_run_mkdocs_build is invoked when build_docs=True."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=True)
        with (
            patch(
                "attune.workflows.doc_audit.workflow.run_all_checks",
                return_value=_pass_checks(5),
            ),
            patch.object(wf, "_run_mkdocs_build", return_value=True) as mock_build,
        ):
            output, _, _ = await wf._verify({"score": 100, "project_root": "/tmp"})

        mock_build.assert_called_once()
        assert output["mkdocs_build"] is True

    @pytest.mark.asyncio
    async def test_verify_after_checks_included_in_output(self):
        """Output contains after_checks with serialised check results."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=False)
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=_pass_checks(3),
        ):
            output, _, _ = await wf._verify({"score": 100})

        assert "after_checks" in output
        assert len(output["after_checks"]) == 3

    @pytest.mark.asyncio
    async def test_verify_uses_instance_audit_score_as_fallback(self):
        """before_score falls back to _audit_score if not in input_data."""
        wf = DocAuditWorkflow(project_root="/tmp/test", build_docs=False)
        wf._audit_score = 70
        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=_pass_checks(10),
        ):
            output, _, _ = await wf._verify({})  # no "score" key

        assert output["before_score"] == 70
