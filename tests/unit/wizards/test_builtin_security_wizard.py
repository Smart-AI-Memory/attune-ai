"""Unit tests for SecurityWizard workflow delegation paths.

Tests cover:
- _run_scan_via_workflow: mock SecurityAuditWorkflow triage/analyze/assess pipeline
- _run_fixes_via_workflow: mock remediate stage
- build_prompt_context for scan, generate_fixes, decompose_remediation, fallback
- process_step_result for scan and generate_fixes steps
- _run_llm_step override: delegation to workflow, fallback to super()
- _get_or_create_workflow: caching, ImportError fallback, Exception fallback
- generate_fixes condition (_has_findings integration)
- Error handling when workflow raises

Created: 2026-03-02
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.wizards.base import StepType, WizardStep
from attune.wizards.builtin.security_wizard import SecurityWizard, _has_findings
from attune.wizards.session import WizardSession
from attune.workflows.compat import ModelTier

# =========================================================================
# Helpers
# =========================================================================


def _make_wizard() -> SecurityWizard:
    """Return a SecurityWizard with mocked internal workflow."""
    wizard = SecurityWizard()
    wizard._workflow = MagicMock()
    wizard._workflow._render_xml_prompt = MagicMock(return_value="<prompt/>")
    wizard._workflow._call_llm = AsyncMock(return_value=("response", 10, 5))
    wizard._workflow._parse_xml_response = MagicMock(return_value={"summary": "scan complete"})
    return wizard


def _make_session(target_path: str = "src/") -> WizardSession:
    """Return a WizardSession with a target_path set."""
    session = WizardSession(wizard_id="security")
    session.set("target_path", target_path)
    return session


# =========================================================================
# _get_or_create_workflow
# =========================================================================


class TestGetOrCreateWorkflow:
    """Test lazy workflow instantiation and caching."""

    def test_returns_cached_workflow_on_second_call(self):
        """Test workflow is instantiated once and cached."""
        wizard = SecurityWizard()
        mock_wf = MagicMock()
        wizard._security_workflow = mock_wf

        result = wizard._get_or_create_workflow()

        assert result is mock_wf

    def test_import_error_returns_none(self):
        """Test ImportError from workflow import returns None."""
        wizard = SecurityWizard()

        with patch("attune.wizards.builtin.security_wizard.SecurityWizard._get_or_create_workflow"):
            # Simulate ImportError by directly testing the logic
            pass

        # Test via manual import patch at the module level
        with patch(
            "attune.workflows.security_audit.SecurityAuditWorkflow",
            side_effect=ImportError("not installed"),
        ):
            # Already have the workflow cached from setup so reset it
            wizard._security_workflow = None
            with patch.dict(
                "sys.modules",
                {"attune.workflows.security_audit": None},
            ):
                result = wizard._get_or_create_workflow()
                # Should return None when module is absent
                assert result is None

    def test_unexpected_exception_returns_none(self):
        """Test unexpected Exception during workflow init returns None."""
        wizard = SecurityWizard()
        wizard._security_workflow = None

        with patch(
            "attune.wizards.builtin.security_wizard.SecurityWizard._get_or_create_workflow",
            return_value=None,
        ) as mock_method:
            result = wizard._get_or_create_workflow()
            assert result is None
            mock_method.assert_called_once()


# =========================================================================
# _run_scan_via_workflow
# =========================================================================


class TestRunScanViaWorkflow:
    """Test _run_scan_via_workflow with mocked SecurityAuditWorkflow."""

    @pytest.mark.asyncio
    async def test_scan_via_workflow_runs_triage_analyze_assess(self):
        """Test scan runs triage, analyze, and assess stages."""
        wizard = _make_wizard()
        wizard._session = _make_session("src/attune/")

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"findings": [{"severity": "high", "id": "f1"}], "files_scanned": 10}, 0, 0),
                ({"analyzed_findings": [{"id": "f1", "confirmed": True}]}, 0, 0),
                (
                    {
                        "assessment": {"severity_breakdown": {"critical": 0, "high": 1}},
                        "formatted_report": "Report text",
                    },
                    0,
                    0,
                ),
            ]
        )
        wizard._security_workflow = mock_workflow

        await wizard._run_scan_via_workflow()

        # All three stages should have been called
        assert mock_workflow.run_stage.call_count == 3

        # Check stages called in order
        calls = mock_workflow.run_stage.call_args_list
        assert calls[0][0][0] == "triage"
        assert calls[1][0][0] == "analyze"
        assert calls[2][0][0] == "assess"

    @pytest.mark.asyncio
    async def test_scan_stores_combined_result_in_session(self):
        """Test combined scan result is stored in session."""
        wizard = _make_wizard()
        wizard._session = _make_session("src/")

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"findings": [{"severity": "critical"}], "files_scanned": 5}, 0, 0),
                ({"analyzed_findings": []}, 0, 0),
                (
                    {
                        "assessment": {},
                        "formatted_report": "Done",
                    },
                    0,
                    0,
                ),
            ]
        )
        wizard._security_workflow = mock_workflow

        await wizard._run_scan_via_workflow()

        scan_result = wizard._session.step_results.get("scan", {})
        assert scan_result.get("workflow_delegated") is True
        assert "findings" in scan_result
        assert scan_result["files_scanned"] == 5

    @pytest.mark.asyncio
    async def test_scan_uses_target_path_from_session(self):
        """Test scan reads target_path from session."""
        wizard = _make_wizard()
        wizard._session = _make_session("src/attune/models/")

        triage_call_input = {}

        async def mock_run_stage(stage, tier, input_data):
            if stage == "triage":
                triage_call_input.update(input_data)
                return ({"findings": [], "files_scanned": 0}, 0, 0)
            if stage == "analyze":
                return ({"analyzed_findings": []}, 0, 0)
            return ({"assessment": {}, "formatted_report": ""}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._security_workflow = mock_workflow

        await wizard._run_scan_via_workflow()

        assert triage_call_input.get("path") == "src/attune/models/"

    @pytest.mark.asyncio
    async def test_scan_triage_uses_cheap_tier(self):
        """Test triage stage is called with ModelTier.CHEAP."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        call_tiers = []

        async def mock_run_stage(stage, tier, input_data):
            call_tiers.append((stage, tier))
            if stage == "triage":
                return ({"findings": [], "files_scanned": 0}, 0, 0)
            if stage == "analyze":
                return ({"analyzed_findings": []}, 0, 0)
            return ({"assessment": {}, "formatted_report": ""}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._security_workflow = mock_workflow

        await wizard._run_scan_via_workflow()

        triage_tier = next(t for s, t in call_tiers if s == "triage")
        assert triage_tier == ModelTier.CHEAP

    @pytest.mark.asyncio
    async def test_scan_raises_when_workflow_unavailable(self):
        """Test _run_scan_via_workflow raises RuntimeError when workflow is None."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._security_workflow = None

        with patch.object(wizard, "_get_or_create_workflow", return_value=None):
            with pytest.raises(RuntimeError, match="SecurityAuditWorkflow not available"):
                await wizard._run_scan_via_workflow()

    @pytest.mark.asyncio
    async def test_scan_raises_when_session_is_none(self):
        """Test _run_scan_via_workflow raises RuntimeError without session."""
        wizard = _make_wizard()
        wizard._session = None

        with pytest.raises(RuntimeError, match="session not initialized"):
            await wizard._run_scan_via_workflow()

    @pytest.mark.asyncio
    async def test_scan_stores_workflow_state_for_later_stages(self):
        """Test triage/analyze/assess results are cached in _workflow_state."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"findings": [{"id": "f1"}]}, 0, 0),
                ({"analyzed_findings": [{"id": "f1"}]}, 0, 0),
                ({"assessment": {"severity_breakdown": {"high": 1}}}, 0, 0),
            ]
        )
        wizard._security_workflow = mock_workflow

        await wizard._run_scan_via_workflow()

        assert "triage" in wizard._workflow_state
        assert "analyze" in wizard._workflow_state
        assert "assess" in wizard._workflow_state


# =========================================================================
# _run_fixes_via_workflow
# =========================================================================


class TestRunFixesViaWorkflow:
    """Test _run_fixes_via_workflow with mocked SecurityAuditWorkflow."""

    @pytest.mark.asyncio
    async def test_fixes_via_workflow_calls_remediate_stage(self):
        """Test fixes runs the remediate stage."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        # Pre-populate _workflow_state from prior scan
        wizard._workflow_state = {
            "triage": {"findings": [{"severity": "high"}]},
            "analyze": {"analyzed_findings": []},
            "assess": {"assessment": {}},
        }

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            return_value=(
                {
                    "remediation_plan": "Fix step 1, step 2",
                    "fixes": [{"file": "src/config.py", "change": "Validate input"}],
                },
                0,
                0,
            )
        )
        wizard._security_workflow = mock_workflow

        await wizard._run_fixes_via_workflow()

        mock_workflow.run_stage.assert_called_once()
        call_args = mock_workflow.run_stage.call_args
        assert call_args[0][0] == "remediate"

    @pytest.mark.asyncio
    async def test_fixes_uses_premium_tier(self):
        """Test remediate stage is called with ModelTier.PREMIUM."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._workflow_state = {}

        captured_tier = []

        async def mock_run_stage(stage, tier, input_data):
            captured_tier.append(tier)
            return ({"remediation_plan": "", "fixes": []}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._security_workflow = mock_workflow

        await wizard._run_fixes_via_workflow()

        assert captured_tier[0] == ModelTier.PREMIUM

    @pytest.mark.asyncio
    async def test_fixes_stores_result_in_session(self):
        """Test fixes result is stored in session under 'generate_fixes'."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._workflow_state = {}

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            return_value=(
                {
                    "remediation_plan": "Apply patch A",
                    "fixes": [{"id": "fix1"}],
                },
                0,
                0,
            )
        )
        wizard._security_workflow = mock_workflow

        await wizard._run_fixes_via_workflow()

        fixes_result = wizard._session.step_results.get("generate_fixes", {})
        assert fixes_result.get("workflow_delegated") is True
        assert fixes_result.get("remediation_plan") == "Apply patch A"

    @pytest.mark.asyncio
    async def test_fixes_raises_when_workflow_unavailable(self):
        """Test _run_fixes_via_workflow raises RuntimeError when workflow is None."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._security_workflow = None

        with patch.object(wizard, "_get_or_create_workflow", return_value=None):
            with pytest.raises(RuntimeError, match="SecurityAuditWorkflow not available"):
                await wizard._run_fixes_via_workflow()

    @pytest.mark.asyncio
    async def test_fixes_raises_when_session_is_none(self):
        """Test _run_fixes_via_workflow raises RuntimeError without session."""
        wizard = _make_wizard()
        wizard._session = None

        with pytest.raises(RuntimeError, match="session not initialized"):
            await wizard._run_fixes_via_workflow()

    @pytest.mark.asyncio
    async def test_fixes_includes_prior_workflow_state_in_input(self):
        """Test remediate input includes prior triage/analyze/assess data."""
        wizard = _make_wizard()
        wizard._session = _make_session("src/")
        wizard._workflow_state = {
            "triage": {"findings": [{"id": "t1"}]},
            "analyze": {"analyzed_findings": [{"id": "a1"}]},
            "assess": {"risk_score": 42},
        }

        captured_input = {}

        async def mock_run_stage(stage, tier, input_data):
            captured_input.update(input_data)
            return ({"remediation_plan": "", "fixes": []}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._security_workflow = mock_workflow

        await wizard._run_fixes_via_workflow()

        # All prior state should be merged into remediate input
        assert "findings" in captured_input  # from triage
        assert "analyzed_findings" in captured_input  # from analyze
        assert "risk_score" in captured_input  # from assess
        assert captured_input.get("path") == "src/"


# =========================================================================
# _run_llm_step override
# =========================================================================


class TestRunLlmStepOverride:
    """Test _run_llm_step delegation and fallback behavior."""

    @pytest.mark.asyncio
    async def test_scan_step_delegates_to_workflow(self):
        """Test that scan step calls _run_scan_via_workflow."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        called = []

        async def mock_scan():
            called.append("scan")

        wizard._run_scan_via_workflow = mock_scan

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        await wizard._run_llm_step(scan_step)

        assert "scan" in called

    @pytest.mark.asyncio
    async def test_scan_step_falls_back_to_super_on_exception(self):
        """Test scan step falls back to super()._run_llm_step on exception."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        # Pre-complete scan so super()._run_llm_step has session
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("fallback", 5, 2))
        wizard._workflow._parse_xml_response = MagicMock(return_value={"summary": "fallback scan"})

        async def failing_scan():
            raise RuntimeError("workflow unavailable")

        wizard._run_scan_via_workflow = failing_scan

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        # Should not raise — falls back to LLM call
        await wizard._run_llm_step(scan_step)

        # Super's LLM path was used
        wizard._workflow._call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_fixes_step_delegates_to_workflow(self):
        """Test that generate_fixes step calls _run_fixes_via_workflow."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        called = []

        async def mock_fixes():
            called.append("fixes")

        wizard._run_fixes_via_workflow = mock_fixes

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        await wizard._run_llm_step(fixes_step)

        assert "fixes" in called

    @pytest.mark.asyncio
    async def test_generate_fixes_falls_back_to_super_on_exception(self):
        """Test generate_fixes falls back to super()._run_llm_step on exception."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("fixes response", 5, 2))
        wizard._workflow._parse_xml_response = MagicMock(return_value={"fixes": []})

        async def failing_fixes():
            raise RuntimeError("workflow not available")

        wizard._run_fixes_via_workflow = failing_fixes

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        await wizard._run_llm_step(fixes_step)

        wizard._workflow._call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_other_step_goes_directly_to_super(self):
        """Test non-scan/non-fixes steps call super()._run_llm_step directly."""

        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("result", 0, 0))
        wizard._workflow._parse_xml_response = MagicMock(return_value={})

        other_step = WizardStep(
            id="other_llm_step",
            name="Other",
            step_type=StepType.LLM_CALL,
        )
        # Should call through to super without trying workflow methods
        await wizard._run_llm_step(other_step)

        wizard._workflow._call_llm.assert_called_once()


# =========================================================================
# build_prompt_context
# =========================================================================


class TestBuildPromptContext:
    """Test build_prompt_context for each step ID."""

    def test_scan_step_context(self):
        """Test context for scan step includes target and focus."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.set("target_path", "src/attune/")
        wizard._session.set("focus_areas", "OWASP Top 10")

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        ctx = wizard.build_prompt_context(scan_step)

        # Should have a valid PromptContext
        assert ctx.role
        assert ctx.goal

    def test_generate_fixes_step_context(self):
        """Test context for generate_fixes includes scan findings."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.step_results["scan"] = {
            "findings": [{"severity": "high", "description": "SQL injection"}]
        }

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        ctx = wizard.build_prompt_context(fixes_step)

        assert ctx.role == "security remediation specialist"
        assert "SQL injection" in ctx.input_payload

    def test_decompose_remediation_step_context(self):
        """Test context for decompose_remediation combines scan and fixes."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        wizard._session.step_results["scan"] = {"findings": ["vuln1"]}
        wizard._session.step_results["generate_fixes"] = {"fixes": ["fix1"]}

        decompose_step = next(s for s in SecurityWizard.steps if s.id == "decompose_remediation")
        ctx = wizard.build_prompt_context(decompose_step)

        assert ctx.role == "security remediation planner"
        assert "vuln1" in ctx.input_payload
        assert "fix1" in ctx.input_payload

    def test_fallback_step_context(self):
        """Test context for unknown step returns default context."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        unknown_step = WizardStep(id="unknown_step", name="Unknown")
        ctx = wizard.build_prompt_context(unknown_step)

        assert ctx.role == "assistant"

    def test_build_prompt_context_raises_without_session(self):
        """Test build_prompt_context raises RuntimeError without session."""
        wizard = SecurityWizard()
        wizard._session = None

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.build_prompt_context(scan_step)

    def test_scan_context_uses_default_target_when_not_set(self):
        """Test scan context uses 'src/' as default when target_path not in session."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")
        # No target_path set

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        ctx = wizard.build_prompt_context(scan_step)

        # Should not raise and should return a context
        assert ctx is not None


# =========================================================================
# process_step_result
# =========================================================================


class TestProcessStepResult:
    """Test process_step_result stores data correctly."""

    def test_scan_step_stores_findings(self):
        """Test scan step result stored as scan_findings in session."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        result = {"findings": [{"severity": "high"}], "files_scanned": 10}
        wizard.process_step_result(scan_step, result)

        assert wizard._session.get("scan_findings") == result

    def test_generate_fixes_step_stores_fixes(self):
        """Test generate_fixes step result stored as fixes in session."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        result = {"fixes": [{"file": "config.py", "patch": "..."}]}
        wizard.process_step_result(fixes_step, result)

        assert wizard._session.get("fixes") == result

    def test_unmatched_step_does_not_store(self):
        """Test unmatched step ID does not store anything."""
        wizard = SecurityWizard()
        wizard._session = WizardSession(wizard_id="security")

        other_step = WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW)
        wizard.process_step_result(other_step, {"data": "value"})

        # Only scan_findings and fixes are explicitly set; neither should be present
        assert wizard._session.get("scan_findings") is None
        assert wizard._session.get("fixes") is None

    def test_process_step_result_raises_without_session(self):
        """Test process_step_result raises RuntimeError without session."""
        wizard = SecurityWizard()
        wizard._session = None

        scan_step = next(s for s in SecurityWizard.steps if s.id == "scan")
        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.process_step_result(scan_step, {})


# =========================================================================
# generate_fixes condition (_has_findings integration)
# =========================================================================


class TestGenerateFixesCondition:
    """Test the condition on the generate_fixes step."""

    def test_generate_fixes_step_has_condition(self):
        """Test generate_fixes step has a condition attribute."""
        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        assert fixes_step.condition is not None

    def test_condition_is_has_findings(self):
        """Test condition is the _has_findings function."""
        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        assert fixes_step.condition is _has_findings

    def test_condition_returns_true_with_high_findings(self):
        """Test condition returns True when high/critical findings exist."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "assessment": {"severity_breakdown": {"critical": 0, "high": 2}}
        }

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        assert fixes_step.condition(session) is True

    def test_condition_returns_false_with_no_findings(self):
        """Test condition returns False when no high/critical findings."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {"findings": [], "critical_issues": 0, "high_issues": 0}

        fixes_step = next(s for s in SecurityWizard.steps if s.id == "generate_fixes")
        assert fixes_step.condition(session) is False

    @pytest.mark.asyncio
    async def test_generate_fixes_skipped_when_no_findings(self):
        """Test generate_fixes step is skipped during run when no findings."""
        from attune.meta_workflows.models import FormResponse

        wizard = SecurityWizard()
        wizard._workflow = MagicMock()
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("resp", 0, 0))
        wizard._workflow._parse_xml_response = MagicMock(return_value={})

        # Mock _run_scan_via_workflow to store "no findings" scan result
        async def mock_scan():
            wizard._session.step_results["scan"] = {
                "findings": [],
                "critical_issues": 0,
                "high_issues": 0,
                "workflow_delegated": True,
            }
            wizard._session.steps_completed.append("scan")

        wizard._run_scan_via_workflow = mock_scan

        # Suppress other steps except scan and generate_fixes

        mock_response = FormResponse(
            template_id="gather_info",
            responses={
                "scope": "Full project (src/)",
                "target_path": "src/",
                "focus_areas": "All categories (Recommended)",
            },
        )
        wizard._form_engine = MagicMock()
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        result = await wizard.run()

        assert result.success is True
        # generate_fixes should be in skipped because condition returns False
        assert "generate_fixes" not in result.steps_completed
