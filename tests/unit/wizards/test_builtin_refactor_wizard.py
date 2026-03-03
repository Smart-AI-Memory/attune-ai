"""Unit tests for RefactorWizard workflow delegation paths.

Tests cover:
- _run_analysis_via_workflow: mock RefactorPlanWorkflow scan/analyze/prioritize/plan pipeline
- build_prompt_context for analyze, decompose_steps, and fallback
- process_step_result storing analysis data
- _run_llm_step override: delegation and fallback behavior
- _get_or_create_workflow: caching, ImportError fallback
- Error handling when workflow raises

Created: 2026-03-02
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.wizards.base import StepType, WizardStep
from attune.wizards.builtin.refactor_wizard import RefactorWizard
from attune.wizards.session import WizardSession
from attune.workflows.compat import ModelTier

# =========================================================================
# Helpers
# =========================================================================


def _make_wizard() -> RefactorWizard:
    """Return a RefactorWizard with mocked internal workflow."""
    wizard = RefactorWizard()
    wizard._workflow = MagicMock()
    wizard._workflow._render_xml_prompt = MagicMock(return_value="<prompt/>")
    wizard._workflow._call_llm = AsyncMock(return_value=("response", 10, 5))
    wizard._workflow._parse_xml_response = MagicMock(return_value={"summary": "analysis done"})
    return wizard


def _make_session(
    target_file: str = "src/main.py",
    refactor_type: str = "Reduce complexity",
    goal: str = "Improve readability",
) -> WizardSession:
    """Return a WizardSession with refactoring info set."""
    session = WizardSession(wizard_id="refactor")
    session.set("target_file", target_file)
    session.set("refactor_type", refactor_type)
    session.set("goal", goal)
    return session


# =========================================================================
# _get_or_create_workflow
# =========================================================================


class TestGetOrCreateWorkflow:
    """Test lazy workflow instantiation and caching."""

    def test_returns_cached_workflow_on_second_call(self):
        """Test workflow is instantiated once and cached."""
        wizard = RefactorWizard()
        mock_wf = MagicMock()
        wizard._refactor_workflow = mock_wf

        result = wizard._get_or_create_workflow()

        assert result is mock_wf

    def test_import_error_returns_none(self):
        """Test ImportError from workflow import returns None."""
        wizard = RefactorWizard()
        wizard._refactor_workflow = None

        with patch.dict("sys.modules", {"attune.workflows.refactor_plan": None}):
            result = wizard._get_or_create_workflow()
            assert result is None

    def test_patched_get_or_create_returns_none(self):
        """Test that _get_or_create_workflow can be patched to return None."""
        wizard = RefactorWizard()

        with patch.object(wizard, "_get_or_create_workflow", return_value=None):
            result = wizard._get_or_create_workflow()
            assert result is None


# =========================================================================
# _run_analysis_via_workflow
# =========================================================================


class TestRunAnalysisViaWorkflow:
    """Test _run_analysis_via_workflow with mocked RefactorPlanWorkflow."""

    @pytest.mark.asyncio
    async def test_analysis_runs_all_four_stages(self):
        """Test analysis runs scan, analyze, prioritize, and plan stages."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"debt_items": [{"id": "d1"}]}, 0, 0),  # scan
                ({"analysis": {"complexity": "high"}}, 0, 0),  # analyze
                ({"priorities": [{"id": "d1", "score": 8}]}, 0, 0),  # prioritize
                (
                    {
                        "refactoring_plan": "Step-by-step plan",
                        "summary": "Summary",
                        "formatted_report": "Report",
                    },
                    0,
                    0,
                ),  # plan
            ]
        )
        wizard._refactor_workflow = mock_workflow

        await wizard._run_analysis_via_workflow()

        assert mock_workflow.run_stage.call_count == 4
        stage_names = [call[0][0] for call in mock_workflow.run_stage.call_args_list]
        assert stage_names == ["scan", "analyze", "prioritize", "plan"]

    @pytest.mark.asyncio
    async def test_analysis_scan_uses_cheap_tier(self):
        """Test scan stage is called with ModelTier.CHEAP."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        call_tiers = []

        async def mock_run_stage(stage, tier, input_data):
            call_tiers.append((stage, tier))
            if stage == "scan":
                return ({"debt_items": []}, 0, 0)
            if stage == "analyze":
                return ({"analysis": {}}, 0, 0)
            if stage == "prioritize":
                return ({"priorities": []}, 0, 0)
            return ({"refactoring_plan": "", "summary": "", "formatted_report": ""}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._refactor_workflow = mock_workflow

        await wizard._run_analysis_via_workflow()

        scan_tier = next(t for s, t in call_tiers if s == "scan")
        assert scan_tier == ModelTier.CHEAP

    @pytest.mark.asyncio
    async def test_analysis_plan_uses_premium_tier(self):
        """Test plan stage is called with ModelTier.PREMIUM."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        call_tiers = []

        async def mock_run_stage(stage, tier, input_data):
            call_tiers.append((stage, tier))
            if stage == "scan":
                return ({"debt_items": []}, 0, 0)
            if stage == "analyze":
                return ({"analysis": {}}, 0, 0)
            if stage == "prioritize":
                return ({"priorities": []}, 0, 0)
            return ({"refactoring_plan": "", "summary": "", "formatted_report": ""}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._refactor_workflow = mock_workflow

        await wizard._run_analysis_via_workflow()

        plan_tier = next(t for s, t in call_tiers if s == "plan")
        assert plan_tier == ModelTier.PREMIUM

    @pytest.mark.asyncio
    async def test_analysis_uses_session_values(self):
        """Test analysis reads target_file, refactor_type, goal from session."""
        wizard = _make_wizard()
        wizard._session = _make_session(
            target_file="src/attune/models/auth.py",
            refactor_type="Extract method/function",
            goal="Separate concerns",
        )

        captured_input = {}

        async def mock_run_stage(stage, tier, input_data):
            if stage == "scan":
                captured_input.update(input_data)
                return ({"debt_items": []}, 0, 0)
            if stage == "analyze":
                return ({"analysis": {}}, 0, 0)
            if stage == "prioritize":
                return ({"priorities": []}, 0, 0)
            return ({"refactoring_plan": "", "summary": "", "formatted_report": ""}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._refactor_workflow = mock_workflow

        await wizard._run_analysis_via_workflow()

        assert captured_input.get("path") == "src/attune/models/auth.py"
        assert captured_input.get("refactor_type") == "Extract method/function"
        assert captured_input.get("goal") == "Separate concerns"

    @pytest.mark.asyncio
    async def test_analysis_stores_combined_result_in_session(self):
        """Test combined analysis result is stored in session."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        mock_workflow = MagicMock()
        mock_workflow.run_stage = AsyncMock(
            side_effect=[
                ({"debt_items": [{"id": "d1"}]}, 0, 0),
                ({"analysis": {"items": 5}}, 0, 0),
                ({"priorities": [{"rank": 1}]}, 0, 0),
                (
                    {
                        "refactoring_plan": "The plan",
                        "summary": "Summary text",
                        "formatted_report": "Report",
                    },
                    0,
                    0,
                ),
            ]
        )
        wizard._refactor_workflow = mock_workflow

        await wizard._run_analysis_via_workflow()

        analyze_result = wizard._session.step_results.get("analyze", {})
        assert analyze_result.get("workflow_delegated") is True
        assert analyze_result.get("refactoring_plan") == "The plan"
        assert analyze_result.get("summary") == "Summary text"

    @pytest.mark.asyncio
    async def test_analysis_raises_when_workflow_unavailable(self):
        """Test _run_analysis_via_workflow raises RuntimeError when workflow is None."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._refactor_workflow = None

        with patch.object(wizard, "_get_or_create_workflow", return_value=None):
            with pytest.raises(RuntimeError, match="RefactorPlanWorkflow not available"):
                await wizard._run_analysis_via_workflow()

    @pytest.mark.asyncio
    async def test_analysis_raises_when_session_is_none(self):
        """Test _run_analysis_via_workflow raises RuntimeError without session."""
        wizard = _make_wizard()
        wizard._session = None

        with pytest.raises(RuntimeError, match="session not initialized"):
            await wizard._run_analysis_via_workflow()

    @pytest.mark.asyncio
    async def test_analysis_propagates_data_between_stages(self):
        """Test each stage receives merged input from prior stages."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        stage_inputs = {}

        async def mock_run_stage(stage, tier, input_data):
            stage_inputs[stage] = dict(input_data)
            if stage == "scan":
                return ({"scan_marker": True}, 0, 0)
            if stage == "analyze":
                return ({"analyze_marker": True}, 0, 0)
            if stage == "prioritize":
                return ({"prioritize_marker": True}, 0, 0)
            return ({"refactoring_plan": "", "summary": "", "formatted_report": ""}, 0, 0)

        mock_workflow = MagicMock()
        mock_workflow.run_stage = mock_run_stage
        wizard._refactor_workflow = mock_workflow

        await wizard._run_analysis_via_workflow()

        # analyze stage should include scan result (scan_marker)
        assert stage_inputs["analyze"].get("scan_marker") is True
        # prioritize stage should include analyze result (analyze_marker)
        assert stage_inputs["prioritize"].get("analyze_marker") is True
        # plan stage should include prioritize result (prioritize_marker)
        assert stage_inputs["plan"].get("prioritize_marker") is True


# =========================================================================
# _run_llm_step override
# =========================================================================


class TestRunLlmStepOverride:
    """Test _run_llm_step delegation and fallback behavior."""

    @pytest.mark.asyncio
    async def test_analyze_step_delegates_to_workflow(self):
        """Test that analyze step calls _run_analysis_via_workflow."""
        wizard = _make_wizard()
        wizard._session = _make_session()

        called = []

        async def mock_analysis():
            called.append("analysis")

        wizard._run_analysis_via_workflow = mock_analysis

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        await wizard._run_llm_step(analyze_step)

        assert "analysis" in called

    @pytest.mark.asyncio
    async def test_analyze_falls_back_to_super_on_exception(self):
        """Test analyze falls back to super()._run_llm_step on exception."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("fallback response", 5, 2))
        wizard._workflow._parse_xml_response = MagicMock(
            return_value={"summary": "fallback analysis"}
        )

        async def failing_analysis():
            raise RuntimeError("workflow broke")

        wizard._run_analysis_via_workflow = failing_analysis

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        # Should not raise — falls back to LLM call
        await wizard._run_llm_step(analyze_step)

        wizard._workflow._call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_other_step_goes_directly_to_super(self):
        """Test non-analyze steps call super()._run_llm_step directly."""
        wizard = _make_wizard()
        wizard._session = _make_session()
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("result", 0, 0))
        wizard._workflow._parse_xml_response = MagicMock(return_value={})

        other_step = WizardStep(
            id="some_other_step",
            name="Other",
            step_type=StepType.LLM_CALL,
        )
        await wizard._run_llm_step(other_step)

        wizard._workflow._call_llm.assert_called_once()


# =========================================================================
# build_prompt_context
# =========================================================================


class TestBuildPromptContext:
    """Test build_prompt_context for each step ID."""

    def test_analyze_step_context_includes_target(self):
        """Test analyze context includes target_file, refactor_type, goal."""
        wizard = RefactorWizard()
        wizard._session = _make_session("src/auth.py", "Split large file", "Reduce size")

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        ctx = wizard.build_prompt_context(analyze_step)

        assert ctx.role == "senior software architect"
        assert "src/auth.py" in ctx.goal or "src/auth.py" in ctx.input_payload
        assert "Split large file" in ctx.goal or "Split large file" in ctx.input_payload

    def test_analyze_step_context_has_instructions(self):
        """Test analyze context has non-empty instructions."""
        wizard = RefactorWizard()
        wizard._session = _make_session()

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        ctx = wizard.build_prompt_context(analyze_step)

        assert len(ctx.instructions) > 0

    def test_analyze_step_context_has_constraints(self):
        """Test analyze context has non-empty constraints."""
        wizard = RefactorWizard()
        wizard._session = _make_session()

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        ctx = wizard.build_prompt_context(analyze_step)

        assert len(ctx.constraints) > 0

    def test_decompose_steps_context(self):
        """Test context for decompose_steps includes analysis result."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        wizard._session.step_results["analyze"] = {
            "summary": "Found 3 code smells",
            "priorities": ["p1", "p2"],
        }

        decompose_step = next(s for s in RefactorWizard.steps if s.id == "decompose_steps")
        ctx = wizard.build_prompt_context(decompose_step)

        assert ctx.role == "refactoring planner"
        assert "Found 3 code smells" in ctx.input_payload

    def test_fallback_step_context(self):
        """Test context for unknown step returns default context."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")

        unknown_step = WizardStep(id="unknown_xyz", name="Unknown")
        ctx = wizard.build_prompt_context(unknown_step)

        assert ctx.role == "assistant"

    def test_build_prompt_context_raises_without_session(self):
        """Test build_prompt_context raises RuntimeError without session."""
        wizard = RefactorWizard()
        wizard._session = None

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.build_prompt_context(analyze_step)

    def test_analyze_context_uses_defaults_when_session_empty(self):
        """Test analyze context uses defaults when session vars not set."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        # No values set in session

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        ctx = wizard.build_prompt_context(analyze_step)

        # Should not raise; defaults should be used
        assert ctx.role == "senior software architect"

    def test_decompose_steps_context_with_empty_analysis(self):
        """Test decompose_steps context when no analysis result in session."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        # No analyze result stored

        decompose_step = next(s for s in RefactorWizard.steps if s.id == "decompose_steps")
        ctx = wizard.build_prompt_context(decompose_step)

        assert ctx.role == "refactoring planner"
        # Input payload should be str representation of empty dict
        assert "{}" in ctx.input_payload


# =========================================================================
# process_step_result
# =========================================================================


class TestProcessStepResult:
    """Test process_step_result stores data correctly."""

    def test_analyze_step_stores_refactor_analysis(self):
        """Test analyze step result stored as refactor_analysis in session."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        result = {
            "debt_items": [{"id": "d1"}],
            "refactoring_plan": "Do this then that",
            "summary": "Three issues found",
        }
        wizard.process_step_result(analyze_step, result)

        stored = wizard._session.get("refactor_analysis")
        assert stored == result

    def test_unmatched_step_does_not_store(self):
        """Test unmatched step ID does not store refactor_analysis."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")

        other_step = WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW)
        wizard.process_step_result(other_step, {"data": "value"})

        assert wizard._session.get("refactor_analysis") is None

    def test_process_step_result_raises_without_session(self):
        """Test process_step_result raises RuntimeError without session."""
        wizard = RefactorWizard()
        wizard._session = None

        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.process_step_result(analyze_step, {})


# =========================================================================
# Wizard structure
# =========================================================================


class TestRefactorWizardStructure:
    """Test RefactorWizard step definitions."""

    def test_steps_order(self):
        """Test step sequence."""
        step_ids = [s.id for s in RefactorWizard.steps]
        assert step_ids == [
            "gather_info",
            "analyze",
            "decompose_steps",
            "preview",
            "confirm",
        ]

    def test_step_types(self):
        """Test step types are correct."""
        types = {s.id: s.step_type for s in RefactorWizard.steps}
        assert types["gather_info"] == StepType.QUESTION
        assert types["analyze"] == StepType.LLM_CALL
        assert types["decompose_steps"] == StepType.TASK_DECOMPOSE
        assert types["preview"] == StepType.PREVIEW
        assert types["confirm"] == StepType.CONFIRM

    def test_gather_info_has_questions(self):
        """Test gather_info step has the expected questions."""
        gather = RefactorWizard.steps[0]
        assert gather.questions is not None
        q_ids = [q.id for q in gather.questions]
        assert "refactor_type" in q_ids
        assert "target_file" in q_ids
        assert "goal" in q_ids

    def test_analyze_step_tier(self):
        """Test analyze step uses capable tier."""
        analyze_step = next(s for s in RefactorWizard.steps if s.id == "analyze")
        assert analyze_step.tier == "capable"

    def test_confirm_step_has_no_condition(self):
        """Test confirm step has no condition (always runs)."""
        confirm_step = next(s for s in RefactorWizard.steps if s.id == "confirm")
        assert confirm_step.condition is None
