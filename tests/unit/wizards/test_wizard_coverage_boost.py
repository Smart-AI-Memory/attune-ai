"""Additional tests to boost wizard coverage above 80%.

Covers:
- SecurityWizard: init, workflow delegation, build_prompt_context, process_step_result
- RefactorWizard: init, workflow delegation, build_prompt_context, process_step_result
- ReleasePrepWizard: build_prompt_context, process_step_result, _wants_changelog
- BaseWizard: _run_llm_step, _run_decompose_step paths

Created: 2026-02-15
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.prompts import PromptContext
from attune.wizards.base import BaseWizard, StepType, WizardConfig, WizardStep
from attune.wizards.builtin.refactor_wizard import RefactorWizard
from attune.wizards.builtin.release_prep_wizard import ReleasePrepWizard, _wants_changelog
from attune.wizards.builtin.security_wizard import SecurityWizard
from attune.wizards.session import WizardSession

# =========================================================================
# _wants_changelog helper
# =========================================================================


class TestWantsChangelog:
    """Test _wants_changelog helper."""

    def test_yes(self):
        """Test 'Yes' returns True."""
        session = WizardSession(wizard_id="release-prep")
        session.set("generate_changelog", "Yes")
        assert _wants_changelog(session) is True

    def test_true_str(self):
        """Test 'true' returns True."""
        session = WizardSession(wizard_id="release-prep")
        session.set("generate_changelog", "true")
        assert _wants_changelog(session) is True

    def test_no(self):
        """Test 'No' returns False."""
        session = WizardSession(wizard_id="release-prep")
        session.set("generate_changelog", "No")
        assert _wants_changelog(session) is False

    def test_default_yes(self):
        """Test default (not set) returns True."""
        session = WizardSession(wizard_id="release-prep")
        assert _wants_changelog(session) is True


# =========================================================================
# SecurityWizard detailed tests
# =========================================================================


class TestSecurityWizardInit:
    """Test SecurityWizard initialization and workflow delegation."""

    def test_init_creates_workflow_state(self):
        """Test init creates workflow state dict."""
        wizard = SecurityWizard()
        assert wizard._security_workflow is None
        assert wizard._workflow_state == {}

    def test_get_or_create_workflow_caches(self):
        """Test workflow is cached after creation."""
        wizard = SecurityWizard()
        mock_workflow = MagicMock()
        wizard._security_workflow = mock_workflow

        result = wizard._get_or_create_workflow()
        assert result is mock_workflow

    def test_get_or_create_workflow_import_error(self):
        """Test graceful handling of import error."""
        wizard = SecurityWizard()

        with patch.dict(
            "sys.modules",
            {"attune.workflows.security_audit": None},
        ):
            result = wizard._get_or_create_workflow()
            assert result is None

    def test_get_or_create_workflow_constructs_real_workflow(self):
        """The REAL construction path returns a workflow, not None.

        Regression guard: the wizard used to pass legacy kwargs
        (skip_remediate_if_clean, use_crew_*, enable_auth_strategy)
        that the SDK-native SecurityAuditWorkflow rejects with
        TypeError — swallowed by the broad except, so the wizard
        silently always fell back to the LLM path. No mocks here on
        purpose: this must exercise the real constructor.
        """
        from attune.workflows.security_audit import SecurityAuditWorkflow

        wizard = SecurityWizard()
        result = wizard._get_or_create_workflow()

        assert isinstance(result, SecurityAuditWorkflow)
        # And the cache now holds it for subsequent calls.
        assert wizard._security_workflow is result

    def test_build_prompt_context_scan(self):
        """Test build_prompt_context for scan step."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.set("target_path", "src/attune/config.py")
        wizard._session.set("focus_areas", "OWASP Top 10")

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        ctx = wizard.build_prompt_context(scan_step)

        assert ctx.role  # Has a role
        assert "src/attune/config.py" in str(ctx.input_payload) or "config.py" in str(ctx)

    def test_build_prompt_context_generate_fixes(self):
        """Test build_prompt_context for generate_fixes step."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.step_results["scan"] = {
            "findings": [{"severity": "high", "description": "SQL injection"}]
        }

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        ctx = wizard.build_prompt_context(fixes_step)

        assert "remediation" in ctx.role.lower() or "security" in ctx.role.lower()
        assert "SQL injection" in ctx.input_payload

    def test_build_prompt_context_decompose(self):
        """Test build_prompt_context for decompose_remediation step."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.step_results["scan"] = {"findings": []}
        wizard._session.step_results["generate_fixes"] = {"fixes": []}

        decompose_step = next(s for s in SecurityWizard.steps if s.id == "decompose_remediation")
        ctx = wizard.build_prompt_context(decompose_step)

        assert "remediation" in ctx.role.lower() or "planner" in ctx.role.lower()

    def test_build_prompt_context_fallback(self):
        """Test build_prompt_context for unknown step."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        dummy = WizardStep(id="unknown", name="Unknown")
        ctx = wizard.build_prompt_context(dummy)
        assert ctx.role == "assistant"

    def test_process_step_result_scan(self):
        """Test process_step_result stores scan findings."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        wizard.process_step_result(scan_step, {"findings": ["issue1"]})

        assert wizard._session.get("scan_findings") == {"findings": ["issue1"]}

    def test_process_step_result_fixes(self):
        """Test process_step_result stores fix data."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        wizard.process_step_result(fixes_step, {"fixes": ["fix1"]})

        assert wizard._session.get("fixes") == {"fixes": ["fix1"]}

    @pytest.mark.asyncio
    async def test_run_scan_via_workflow(self):
        """Test _run_scan_via_workflow calls workflow stages."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.set("target_path", "src/")

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"findings": [{"severity": "high"}], "files_scanned": 10}, 100, 50),
                ({"analyzed_findings": [{"id": 1}]}, 200, 100),
                ({"assessment": {"severity_breakdown": {"critical": 1}}}, 150, 75),
            ]
        )
        wizard._security_workflow = mock_workflow

        await wizard._run_scan_via_workflow()

        assert mock_workflow.run_stage.call_count == 3
        assert "scan" in wizard._session.steps_completed
        assert wizard._session.get("scan_findings") is not None

    @pytest.mark.asyncio
    async def test_run_scan_via_workflow_no_workflow(self):
        """Test _run_scan_via_workflow raises when no workflow."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        with patch.object(wizard, "_get_or_create_workflow", return_value=None):
            with pytest.raises(RuntimeError, match="not available"):
                await wizard._run_scan_via_workflow()

    @pytest.mark.asyncio
    async def test_run_fixes_via_workflow(self):
        """Test _run_fixes_via_workflow calls remediate stage."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.set("target_path", "src/")
        wizard._workflow_state = {
            "triage": {"findings": []},
            "analyze": {"analyzed_findings": []},
            "assess": {"assessment": {}},
        }

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            return_value=({"remediation_plan": "Fix all", "fixes": ["f1"]}, 300, 200)
        )
        wizard._security_workflow = mock_workflow

        await wizard._run_fixes_via_workflow()

        mock_workflow.run_stage.assert_called_once()
        assert "generate_fixes" in wizard._session.steps_completed

    @pytest.mark.asyncio
    async def test_run_fixes_via_workflow_no_workflow(self):
        """Test _run_fixes_via_workflow raises when no workflow."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        with patch.object(wizard, "_get_or_create_workflow", return_value=None):
            with pytest.raises(RuntimeError, match="not available"):
                await wizard._run_fixes_via_workflow()

    @pytest.mark.asyncio
    async def test_run_llm_step_delegates_scan(self):
        """Test _run_llm_step delegates scan to workflow."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.set("target_path", "src/")

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"findings": [], "files_scanned": 5}, 100, 50),
                ({"analyzed_findings": []}, 200, 100),
                ({"assessment": {}}, 150, 75),
            ]
        )
        wizard._security_workflow = mock_workflow

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        await wizard._run_llm_step(scan_step)

        assert mock_workflow.run_stage.call_count == 3

    @pytest.mark.asyncio
    async def test_run_llm_step_fallback_on_error(self):
        """Test _run_llm_step falls back to base on workflow error."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.set("target_path", "src/")

        # Make workflow scan fail
        wizard._security_workflow = MagicMock()
        wizard._security_workflow.run_stage = AsyncMock(side_effect=RuntimeError("boom"))

        # Mock the base class _run_llm_step
        with patch.object(BaseWizard, "_run_llm_step", new_callable=AsyncMock) as mock_base:
            scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
            await wizard._run_llm_step(scan_step)
            mock_base.assert_called_once_with(scan_step)


# =========================================================================
# RefactorWizard detailed tests
# =========================================================================


class TestRefactorWizardDetailed:
    """Detailed tests for RefactorWizard."""

    def test_init_creates_workflow_ref(self):
        """Test init creates None workflow reference."""
        wizard = RefactorWizard()
        assert wizard._refactor_workflow is None

    def test_get_or_create_workflow_caches(self):
        """Test workflow is cached."""
        wizard = RefactorWizard()
        mock_wf = MagicMock()
        wizard._refactor_workflow = mock_wf

        assert wizard._get_or_create_workflow() is mock_wf

    def test_get_or_create_workflow_import_error(self):
        """Test graceful handling of import error."""
        wizard = RefactorWizard()
        with patch.dict(
            "sys.modules",
            {"attune.workflows.refactor_plan": None},
        ):
            assert wizard._get_or_create_workflow() is None

    def test_build_prompt_context_analyze(self):
        """Test build_prompt_context for analyze step."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        wizard._session.set("refactor_type", "Extract methods")
        wizard._session.set("target_file", "src/app.py")
        wizard._session.set("goal", "Improve readability")

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        ctx = wizard.build_prompt_context(analyze_step)

        assert "architect" in ctx.role.lower()
        assert "Extract methods" in ctx.goal
        assert "src/app.py" in ctx.goal

    def test_build_prompt_context_decompose(self):
        """Test build_prompt_context for decompose step."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        wizard._session.step_results["analyze"] = {"summary": "Complex methods found"}

        decompose_step = next(s for s in RefactorWizard.steps if s.id == "decompose_steps")
        ctx = wizard.build_prompt_context(decompose_step)

        assert "planner" in ctx.role.lower()

    def test_build_prompt_context_fallback(self):
        """Test build_prompt_context for unknown step."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")

        dummy = WizardStep(id="unknown", name="Unknown")
        ctx = wizard.build_prompt_context(dummy)
        assert ctx.role == "assistant"

    def test_process_step_result_analyze(self):
        """Test process_step_result stores analysis."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        wizard.process_step_result(analyze_step, {"summary": "needs refactoring"})

        assert wizard._session.get("refactor_analysis") == {"summary": "needs refactoring"}

    @pytest.mark.asyncio
    async def test_run_analysis_via_workflow(self):
        """Test _run_analysis_via_workflow calls all 4 stages."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        wizard._session.set("target_file", "src/app.py")
        wizard._session.set("refactor_type", "Extract methods")
        wizard._session.set("goal", "Readability")

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"debt_items": ["item1"]}, 50, 25),
                ({"analysis": {"score": 5}}, 100, 50),
                ({"priorities": ["p1"]}, 100, 50),
                (
                    {"refactoring_plan": "plan", "summary": "done", "formatted_report": "report"},
                    200,
                    100,
                ),
            ]
        )
        wizard._refactor_workflow = mock_workflow

        await wizard._run_analysis_via_workflow()

        assert mock_workflow.run_stage.call_count == 4
        assert "analyze" in wizard._session.steps_completed

    @pytest.mark.asyncio
    async def test_run_analysis_via_workflow_no_workflow(self):
        """Test raises when workflow not available."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")

        with patch.object(wizard, "_get_or_create_workflow", return_value=None):
            with pytest.raises(RuntimeError, match="not available"):
                await wizard._run_analysis_via_workflow()

    @pytest.mark.asyncio
    async def test_run_llm_step_delegates_analyze(self):
        """Test _run_llm_step delegates analyze to workflow."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        wizard._session.set("target_file", "src/app.py")

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"debt_items": []}, 50, 25),
                ({"analysis": {}}, 100, 50),
                ({"priorities": []}, 100, 50),
                ({"refactoring_plan": "", "summary": "", "formatted_report": ""}, 200, 100),
            ]
        )
        wizard._refactor_workflow = mock_workflow

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        await wizard._run_llm_step(analyze_step)

        assert mock_workflow.run_stage.call_count == 4

    @pytest.mark.asyncio
    async def test_run_llm_step_fallback_on_error(self):
        """Test _run_llm_step falls back on workflow error."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")

        wizard._refactor_workflow = MagicMock()
        wizard._refactor_workflow.run_stage = AsyncMock(side_effect=RuntimeError("boom"))

        with patch.object(BaseWizard, "_run_llm_step", new_callable=AsyncMock) as mock_base:
            analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
            await wizard._run_llm_step(analyze_step)
            mock_base.assert_called_once_with(analyze_step)


# =========================================================================
# ReleasePrepWizard detailed tests
# =========================================================================


class TestReleasePrepWizardDetailed:
    """Detailed tests for ReleasePrepWizard."""

    def test_build_prompt_context_readiness_check(self):
        """Test build_prompt_context for readiness_check step."""
        wizard = ReleasePrepWizard()
        wizard._session = WizardSession(wizard_id="release-prep")
        wizard._session.set("version_type", "Minor (new features)")
        wizard._session.set("run_tests", "Yes")

        step = next(s for s in ReleasePrepWizard.steps if s.id == "readiness_check")
        ctx = wizard.build_prompt_context(step)

        assert "release" in ctx.role.lower()
        assert "minor" in ctx.goal.lower()

    def test_build_prompt_context_changelog(self):
        """Test build_prompt_context for changelog step."""
        wizard = ReleasePrepWizard()
        wizard._session = WizardSession(wizard_id="release-prep")

        step = next(s for s in ReleasePrepWizard.steps if s.id == "changelog")
        ctx = wizard.build_prompt_context(step)

        assert "writer" in ctx.role.lower() or "technical" in ctx.role.lower()

    def test_build_prompt_context_decompose(self):
        """Test build_prompt_context for decompose_release step."""
        wizard = ReleasePrepWizard()
        wizard._session = WizardSession(wizard_id="release-prep")
        wizard._session.step_results["readiness_check"] = {"status": "ready"}
        wizard._session.set("version_type", "Patch (bug fixes)")

        step = next(s for s in ReleasePrepWizard.steps if s.id == "decompose_release")
        ctx = wizard.build_prompt_context(step)

        assert "planner" in ctx.role.lower() or "release" in ctx.role.lower()

    def test_build_prompt_context_fallback(self):
        """Test build_prompt_context for unknown step."""
        wizard = ReleasePrepWizard()
        wizard._session = WizardSession(wizard_id="release-prep")

        dummy = WizardStep(id="unknown", name="Unknown")
        ctx = wizard.build_prompt_context(dummy)
        assert ctx.role == "assistant"

    def test_process_step_result_readiness(self):
        """Test process_step_result for readiness check."""
        wizard = ReleasePrepWizard()
        wizard._session = WizardSession(wizard_id="release-prep")

        step = next(s for s in ReleasePrepWizard.steps if s.id == "readiness_check")
        wizard.process_step_result(step, {"status": "ready", "blockers": 0})

        assert wizard._session.get("readiness_report") == {"status": "ready", "blockers": 0}

    def test_process_step_result_changelog(self):
        """Test process_step_result for changelog."""
        wizard = ReleasePrepWizard()
        wizard._session = WizardSession(wizard_id="release-prep")

        step = next(s for s in ReleasePrepWizard.steps if s.id == "changelog")
        wizard.process_step_result(step, {"changelog": "## v2.8.0\n- New wizards"})

        assert wizard._session.get("changelog_draft") == {"changelog": "## v2.8.0\n- New wizards"}


# =========================================================================
# BaseWizard LLM and decompose step coverage
# =========================================================================


class ConcreteTestWizard(BaseWizard):
    """Concrete wizard for testing base LLM/decompose paths."""

    config = WizardConfig(wizard_id="cov-test", name="Coverage", description="Test")
    steps = []

    def build_prompt_context(self, step):
        return PromptContext(
            role="tester",
            goal="test goal",
            instructions=["do the thing"],
            constraints=["be fast"],
            input_type="test_input",
            input_payload="test data",
        )

    def process_step_result(self, step, result):
        assert self._session is not None
        self._session.set(f"{step.id}_result", result)


class TestBaseWizardLLMStep:
    """Test BaseWizard._run_llm_step."""

    @pytest.mark.asyncio
    async def test_llm_step_tuple_result(self):
        """Test LLM step with tuple (response, in_tokens, out_tokens)."""
        wizard = ConcreteTestWizard()
        wizard._session = WizardSession(wizard_id="cov-test")

        wizard._workflow._render_xml_prompt = MagicMock(return_value="<prompt/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("LLM response", 100, 50))
        wizard._workflow._parse_xml_response = MagicMock(return_value={"summary": "parsed"})

        step = WizardStep(id="llm1", name="LLM Step", step_type=StepType.LLM_CALL)
        await wizard._run_llm_step(step)

        assert "llm1" in wizard._session.steps_completed
        assert wizard._session.get("llm1_result") == {"summary": "parsed"}

    @pytest.mark.asyncio
    async def test_llm_step_string_result(self):
        """Test LLM step with plain string result."""
        wizard = ConcreteTestWizard()
        wizard._session = WizardSession(wizard_id="cov-test")

        wizard._workflow._render_xml_prompt = MagicMock(return_value="<prompt/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("plain response", 100, 50))
        wizard._workflow._parse_xml_response = MagicMock(return_value=None)

        step = WizardStep(id="llm2", name="LLM Step", step_type=StepType.LLM_CALL)
        await wizard._run_llm_step(step)

        result = wizard._session.step_results["llm2"]
        assert "raw_response" in result

    @pytest.mark.asyncio
    async def test_llm_step_empty_parse(self):
        """Test LLM step when parsing returns empty."""
        wizard = ConcreteTestWizard()
        wizard._session = WizardSession(wizard_id="cov-test")

        wizard._workflow._render_xml_prompt = MagicMock(return_value="<prompt/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("response", 100, 50))
        wizard._workflow._parse_xml_response = MagicMock(return_value={})

        step = WizardStep(id="llm3", name="LLM Step", step_type=StepType.LLM_CALL)
        await wizard._run_llm_step(step)

        result = wizard._session.step_results["llm3"]
        assert "raw_response" in result


class TestBaseWizardDecomposeStep:
    """Test BaseWizard._run_decompose_step."""

    @pytest.mark.asyncio
    async def test_decompose_step(self):
        """Test decompose step creates tasks."""
        wizard = ConcreteTestWizard()
        wizard._session = WizardSession(wizard_id="cov-test")

        with patch("attune.wizards.decomposer.TaskDecomposer") as MockDecomposer:
            mock_instance = MagicMock()
            mock_task = MagicMock()
            mock_task.to_dict.return_value = {"task_id": "1", "name": "fix"}
            mock_instance.decompose = AsyncMock(return_value=[mock_task])
            MockDecomposer.return_value = mock_instance

            step = WizardStep(
                id="decompose",
                name="Decompose",
                step_type=StepType.TASK_DECOMPOSE,
            )
            await wizard._run_decompose_step(step)

        assert "decompose" in wizard._session.steps_completed
        assert len(wizard._session.tasks) == 1
        assert wizard._session.tasks[0]["task_id"] == "1"
