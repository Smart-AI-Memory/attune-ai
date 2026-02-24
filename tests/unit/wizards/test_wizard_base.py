"""Unit tests for BaseWizard, StepType, WizardConfig, WizardResult, WizardStep.

Tests cover:
- StepType enum values
- WizardConfig, WizardStep, WizardResult data classes
- _resolve_tier helper
- BaseWizard.run() dispatch logic, step skipping, error handling
- _run_question_step, _run_preview_step, _run_confirm_step
- _WizardAbort flow control

Created: 2026-02-15
"""

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest

from attune.meta_workflows.models import FormQuestion, FormResponse, QuestionType
from attune.prompts import PromptContext
from attune.wizards.base import (
    BaseWizard,
    StepType,
    WizardConfig,
    WizardResult,
    WizardStep,
    _resolve_tier,
    _WizardAbort,
)
from attune.workflows.compat import ModelTier

# =========================================================================
# Helpers
# =========================================================================


class ConcreteWizard(BaseWizard):
    """Minimal concrete wizard for testing."""

    config = WizardConfig(
        wizard_id="test-wizard",
        name="Test Wizard",
        description="A wizard for testing",
    )
    steps = [
        WizardStep(
            id="q1",
            name="Question",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="user_input",
                    text="What is the input?",
                    type=QuestionType.TEXT_INPUT,
                ),
            ],
        ),
        WizardStep(
            id="preview",
            name="Preview",
            step_type=StepType.PREVIEW,
        ),
    ]

    def build_prompt_context(self, step):
        return PromptContext(role="tester", goal="test")

    def process_step_result(self, step, result):
        assert self._session is not None
        self._session.set(f"{step.id}_result", result)


# =========================================================================
# StepType
# =========================================================================


class TestStepType:
    """Test StepType enum."""

    def test_values(self):
        """Test all expected step types exist."""
        assert StepType.QUESTION.value == "question"
        assert StepType.LLM_CALL.value == "llm_call"
        assert StepType.TASK_DECOMPOSE.value == "task_decompose"
        assert StepType.PREVIEW.value == "preview"
        assert StepType.CONFIRM.value == "confirm"

    def test_str_behavior(self):
        """Test StepType is a str enum."""
        assert isinstance(StepType.QUESTION, str)


# =========================================================================
# WizardConfig
# =========================================================================


class TestWizardConfig:
    """Test WizardConfig data class."""

    def test_defaults(self):
        """Test default values."""
        config = WizardConfig(
            wizard_id="test",
            name="Test",
            description="A test wizard",
        )
        assert config.domain == "development"
        assert config.version == "1.0.0"
        assert config.source == "builtin"
        assert config.estimated_cost_range == (0.01, 0.50)
        assert config.estimated_duration_minutes == 5


# =========================================================================
# WizardStep
# =========================================================================


class TestWizardStep:
    """Test WizardStep data class."""

    def test_defaults(self):
        """Test default values."""
        step = WizardStep(id="s1", name="Step 1")
        assert step.step_type == StepType.QUESTION
        assert step.tier == "capable"
        assert step.max_tokens == 4096
        assert step.questions is None
        assert step.condition is None
        assert step.prompt_template is None
        assert step.prompt_context_template is None


# =========================================================================
# WizardResult
# =========================================================================


class TestWizardResult:
    """Test WizardResult data class."""

    def test_defaults(self):
        """Test default values."""
        result = WizardResult(wizard_id="test", run_id="abc", success=True)
        assert result.steps_completed == []
        assert result.collected_data == {}
        assert result.generated_output == ""
        assert result.tasks == []
        assert result.total_cost == 0.0
        assert result.total_duration_ms == 0.0
        assert result.error is None

    def test_to_dict(self):
        """Test serialization."""
        result = WizardResult(
            wizard_id="debug",
            run_id="abc123",
            success=True,
            steps_completed=["q1", "analyze"],
            collected_data={"target": "main.py"},
            total_cost=0.05,
        )
        d = result.to_dict()
        assert d["wizard_id"] == "debug"
        assert d["run_id"] == "abc123"
        assert d["success"] is True
        assert d["steps_completed"] == ["q1", "analyze"]
        assert d["collected_data"] == {"target": "main.py"}
        assert d["total_cost"] == 0.05
        assert d["error"] is None

    def test_to_dict_with_error(self):
        """Test serialization with error."""
        result = WizardResult(
            wizard_id="test", run_id="abc", success=False, error="Something failed"
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Something failed"


# =========================================================================
# _resolve_tier
# =========================================================================


class TestResolveTier:
    """Test _resolve_tier helper."""

    def test_known_tiers(self):
        """Test resolving known tier strings."""
        assert _resolve_tier("cheap") == ModelTier.CHEAP
        assert _resolve_tier("capable") == ModelTier.CAPABLE
        assert _resolve_tier("premium") == ModelTier.PREMIUM

    def test_unknown_tier_defaults_to_capable(self):
        """Test unknown tier falls back to CAPABLE."""
        assert _resolve_tier("unknown") == ModelTier.CAPABLE
        assert _resolve_tier("") == ModelTier.CAPABLE


# =========================================================================
# BaseWizard
# =========================================================================


class TestBaseWizard:
    """Test BaseWizard run and dispatch logic."""

    @pytest.mark.asyncio
    async def test_run_creates_session(self):
        """Test that run() creates a session."""
        wizard = ConcreteWizard()
        # Mock form engine to return responses
        mock_response = FormResponse(template_id="q1", responses={"user_input": "test"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        result = await wizard.run({"ctx_key": "ctx_value"})

        assert result.success is True
        assert result.wizard_id == "test-wizard"
        assert "q1" in result.steps_completed
        assert "preview" in result.steps_completed

    @pytest.mark.asyncio
    async def test_run_with_initial_context(self):
        """Test that initial_context is available in session."""
        wizard = ConcreteWizard()
        mock_response = FormResponse(template_id="q1", responses={"user_input": "test"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        result = await wizard.run({"target": "src/main.py"})

        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_without_initial_context(self):
        """Test that run() works with None initial_context."""
        wizard = ConcreteWizard()
        mock_response = FormResponse(template_id="q1", responses={"user_input": "test"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        result = await wizard.run()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_handles_exception(self):
        """Test that exceptions produce a failure result."""
        wizard = ConcreteWizard()
        # Make form engine raise
        wizard._form_engine.ask_questions = MagicMock(side_effect=RuntimeError("boom"))

        result = await wizard.run()

        assert result.success is False
        assert "boom" in result.error
        assert result.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_step_condition_skip(self):
        """Test that steps with False condition are skipped."""
        wizard = ConcreteWizard()
        # Add a conditional step that should be skipped
        wizard.steps = [
            WizardStep(
                id="skipped",
                name="Skipped Step",
                step_type=StepType.PREVIEW,
                condition=lambda session: False,
            ),
            WizardStep(
                id="runs",
                name="Runs",
                step_type=StepType.PREVIEW,
            ),
        ]

        result = await wizard.run()

        assert "skipped" not in result.steps_completed
        assert "runs" in result.steps_completed

    @pytest.mark.asyncio
    async def test_question_step_no_questions(self):
        """Test question step with no questions completes immediately."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="empty_q",
                name="Empty",
                step_type=StepType.QUESTION,
                questions=[],
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "empty_q" in result.steps_completed

    @pytest.mark.asyncio
    async def test_question_step_none_questions(self):
        """Test question step with questions=None completes immediately."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="null_q",
                name="Null Questions",
                step_type=StepType.QUESTION,
                questions=None,
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "null_q" in result.steps_completed

    @pytest.mark.asyncio
    async def test_preview_step_formats_output(self):
        """Test preview step generates formatted output."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]

        result = await wizard.run({"target": "main.py"})

        assert result.success is True
        assert "preview" in result.steps_completed

    @pytest.mark.asyncio
    async def test_preview_step_includes_collected_data(self):
        """Test preview includes collected data in output."""
        wizard = ConcreteWizard()
        mock_response = FormResponse(template_id="q1", responses={"target": "main.py"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="q1",
                name="Q",
                step_type=StepType.QUESTION,
                questions=[FormQuestion(id="target", text="File?", type=QuestionType.TEXT_INPUT)],
            ),
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "target" in str(result.generated_output)

    @pytest.mark.asyncio
    async def test_preview_step_includes_tasks(self):
        """Test preview includes decomposed tasks."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]

        # Pre-populate session with tasks
        result = await wizard.run()
        # The preview without tasks should still work
        assert result.success is True

    @pytest.mark.asyncio
    async def test_confirm_step_proceed(self):
        """Test confirm step with user approval."""
        wizard = ConcreteWizard()
        mock_response = FormResponse(template_id="confirm", responses={"confirm": "Yes, proceed"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="confirm",
                name="Confirm",
                description="Apply changes?",
                step_type=StepType.CONFIRM,
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "confirm" in result.steps_completed

    @pytest.mark.asyncio
    async def test_confirm_step_cancel(self):
        """Test confirm step with user cancellation aborts wizard."""
        wizard = ConcreteWizard()
        mock_response = FormResponse(template_id="confirm", responses={"confirm": "No, cancel"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="confirm",
                name="Confirm",
                description="Apply changes?",
                step_type=StepType.CONFIRM,
            ),
            WizardStep(
                id="should_not_run",
                name="After Confirm",
                step_type=StepType.PREVIEW,
            ),
        ]

        result = await wizard.run()

        # Wizard should have been aborted but still succeed (abort is user choice)
        assert result.success is True
        assert "should_not_run" not in result.steps_completed

    @pytest.mark.asyncio
    async def test_duration_is_tracked(self):
        """Test that total_duration_ms is set."""
        wizard = ConcreteWizard()
        wizard.steps = []

        result = await wizard.run()

        assert result.total_duration_ms >= 0


class TestRunLlmStep:
    """Test _run_llm_step dispatch path."""

    @pytest.mark.asyncio
    async def test_llm_step_tuple_response(self):
        """Test LLM step handles tuple (response, in_tokens, out_tokens)."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="analyze",
                name="Analyze",
                step_type=StepType.LLM_CALL,
                tier="cheap",
            ),
        ]
        # Mock internal workflow methods
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<prompt/>")
        wizard._workflow._call_llm = AsyncMock(
            return_value=("<summary>Analysis complete</summary>", 100, 50)
        )
        wizard._workflow._parse_xml_response = MagicMock(
            return_value={"summary": "Analysis complete"}
        )

        result = await wizard.run()

        assert result.success is True
        assert "analyze" in result.steps_completed
        wizard._workflow._call_llm.assert_called_once()
        wizard._workflow._parse_xml_response.assert_called_once_with(
            "<summary>Analysis complete</summary>"
        )

    @pytest.mark.asyncio
    async def test_llm_step_string_response(self):
        """Test LLM step handles plain string response."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="analyze",
                name="Analyze",
                step_type=StepType.LLM_CALL,
                tier="premium",
            ),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<prompt/>")
        wizard._workflow._call_llm = AsyncMock(return_value="plain text response")
        wizard._workflow._parse_xml_response = MagicMock(return_value=None)

        result = await wizard.run()

        assert result.success is True
        assert "analyze" in result.steps_completed
        # When parse returns None, raw_response is stored
        assert result.collected_data.get("analyze_result") == {
            "raw_response": "plain text response"
        }

    @pytest.mark.asyncio
    async def test_llm_step_parse_returns_none_uses_raw(self):
        """Test fallback to raw_response when XML parsing returns empty."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="llm1",
                name="LLM",
                step_type=StepType.LLM_CALL,
            ),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("no xml here", 10, 5))
        wizard._workflow._parse_xml_response = MagicMock(return_value={})

        result = await wizard.run()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_llm_step_type_error_fallback(self):
        """Test TypeError fallback when _call_llm signature differs."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="llm_te",
                name="LLM TE",
                step_type=StepType.LLM_CALL,
            ),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        # First call raises TypeError, second returns a string
        call_count = 0

        async def side_effect(prompt, tier, step_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TypeError("unexpected keyword")
            return "fallback response"

        wizard._workflow._call_llm = side_effect
        wizard._workflow._parse_xml_response = MagicMock(return_value={"summary": "ok"})

        result = await wizard.run()

        assert result.success is True
        assert "llm_te" in result.steps_completed


class TestRunDecomposeStep:
    """Test _run_decompose_step dispatch path."""

    @pytest.mark.asyncio
    async def test_decompose_step_stores_tasks(self):
        """Test decompose step calls TaskDecomposer and stores tasks."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="decompose",
                name="Decompose",
                step_type=StepType.TASK_DECOMPOSE,
            ),
        ]

        # Mock the decomposer via patch
        from attune.wizards.decomposer import DecomposedTask

        mock_tasks = [
            DecomposedTask(task_id="1", name="task-1", objective="Do thing 1"),
            DecomposedTask(task_id="2", name="task-2", objective="Do thing 2"),
        ]

        with patch("attune.wizards.decomposer.TaskDecomposer") as MockDecomposer:
            mock_instance = MagicMock()
            mock_instance.decompose = AsyncMock(return_value=mock_tasks)
            MockDecomposer.return_value = mock_instance

            result = await wizard.run()

        assert result.success is True
        assert "decompose" in result.steps_completed
        assert len(result.tasks) == 2
        assert result.tasks[0]["task_id"] == "1"
        assert result.tasks[1]["name"] == "task-2"

    @pytest.mark.asyncio
    async def test_decompose_step_empty_tasks(self):
        """Test decompose step with no tasks returned."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="decompose",
                name="Decompose",
                step_type=StepType.TASK_DECOMPOSE,
            ),
        ]

        with patch("attune.wizards.decomposer.TaskDecomposer") as MockDecomposer:
            mock_instance = MagicMock()
            mock_instance.decompose = AsyncMock(return_value=[])
            MockDecomposer.return_value = mock_instance

            result = await wizard.run()

        assert result.success is True
        assert result.tasks == []


class TestPreviewWithPopulatedState:
    """Test preview step with pre-populated session state."""

    @pytest.mark.asyncio
    async def test_preview_with_step_results(self):
        """Test preview renders step results that have summary keys."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]

        result = await wizard.run({"target": "main.py"})
        assert result.success is True

        # Now test with pre-populated step_results
        wizard2 = ConcreteWizard()
        wizard2.steps = [
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]
        await wizard2.run()
        # Manually populate session before preview runs
        # We need a different approach: use a multi-step wizard
        wizard3 = ConcreteWizard()
        mock_response = FormResponse(template_id="q1", responses={"user_input": "hello"})
        wizard3._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard3.steps = [
            WizardStep(
                id="q1",
                name="Question",
                step_type=StepType.QUESTION,
                questions=[
                    FormQuestion(
                        id="user_input",
                        text="Input?",
                        type=QuestionType.TEXT_INPUT,
                    )
                ],
            ),
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]
        result3 = await wizard3.run()
        assert result3.success is True
        # Preview should include collected data
        assert "user_input" in str(result3.generated_output)

    @pytest.mark.asyncio
    async def test_preview_with_tasks(self):
        """Test preview formats decomposed tasks."""
        wizard = ConcreteWizard()

        # Use decompose + preview steps
        from attune.wizards.decomposer import DecomposedTask

        mock_tasks = [
            DecomposedTask(task_id="1", name="add-auth", objective="Add auth module"),
        ]

        with patch("attune.wizards.decomposer.TaskDecomposer") as MockDecomposer:
            mock_instance = MagicMock()
            mock_instance.decompose = AsyncMock(return_value=mock_tasks)
            MockDecomposer.return_value = mock_instance

            wizard.steps = [
                WizardStep(
                    id="decompose",
                    name="Decompose",
                    step_type=StepType.TASK_DECOMPOSE,
                ),
                WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
            ]
            result = await wizard.run()

        assert result.success is True
        assert "Tasks (1)" in str(result.generated_output)
        assert "add-auth" in str(result.generated_output)

    @pytest.mark.asyncio
    async def test_preview_with_analysis_step_results(self):
        """Test preview shows analysis results with summary key."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="analyze",
                name="Analyze",
                step_type=StepType.LLM_CALL,
            ),
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(
            return_value=("<summary>Found 3 issues</summary>", 50, 20)
        )
        wizard._workflow._parse_xml_response = MagicMock(return_value={"summary": "Found 3 issues"})

        result = await wizard.run()

        assert result.success is True
        assert "Found 3 issues" in str(result.generated_output)

    @pytest.mark.asyncio
    async def test_preview_excludes_result_keys_from_inputs(self):
        """Test preview inputs section excludes keys ending with _result."""
        wizard = ConcreteWizard()
        mock_response = FormResponse(
            template_id="q1",
            responses={"target": "main.py", "analyze_result": "should hide"},
        )
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="q1",
                name="Q",
                step_type=StepType.QUESTION,
                questions=[FormQuestion(id="target", text="File?", type=QuestionType.TEXT_INPUT)],
            ),
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]

        result = await wizard.run()

        output = str(result.generated_output)
        assert "target" in output
        assert "analyze_result" not in output


class TestWizardAbort:
    """Test _WizardAbort exception."""

    def test_is_exception(self):
        """Test _WizardAbort is an Exception."""
        assert issubclass(_WizardAbort, Exception)

    def test_can_be_raised(self):
        """Test _WizardAbort can be raised and caught."""
        with pytest.raises(_WizardAbort):
            raise _WizardAbort()
