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
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
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
        # Windows Python < 3.13 has coarse perf_counter resolution; the
        # exception path can complete under one tick and record 0.0ms.
        # Mirror the pattern used in test_duration_is_tracked: >= 0.
        assert result.total_duration_ms >= 0

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
    async def test_llm_step_type_error_propagates(self):
        """Test that TypeError from _call_llm propagates as a failure."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="llm_te",
                name="LLM TE",
                step_type=StepType.LLM_CALL,
            ),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")

        async def side_effect(prompt, tier, step_id):
            raise TypeError("unexpected keyword")

        wizard._workflow._call_llm = side_effect

        result = await wizard.run()

        assert result.success is False
        assert "unexpected keyword" in result.error


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


class TestRunReviewStep:
    """Test _run_review_step dispatch path with retry logic."""

    @pytest.mark.asyncio
    async def test_review_step_approve_on_first_try(self):
        """Test review step completes when user approves immediately."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="llm_step",
                name="LLM",
                step_type=StepType.LLM_CALL,
            ),
            WizardStep(
                id="review",
                name="Review",
                step_type=StepType.REVIEW,
                review_source_step_id="llm_step",
            ),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("analysis", 10, 20))
        wizard._workflow._parse_xml_response = MagicMock(
            return_value={"summary": "Root cause found"}
        )

        # User approves on first try
        wizard._form_engine.ask_questions = MagicMock(
            return_value=FormResponse(
                responses={"review_approval": "Yes, continue"},
                template_id="review",
            )
        )

        result = await wizard.run()

        assert result.success is True
        assert "review" in result.steps_completed
        review_result = wizard._session.step_results.get("review")
        assert review_result == {"approved": True}

    @pytest.mark.asyncio
    async def test_review_step_reject_then_approve(self):
        """Test review step re-runs source LLM step on rejection then approves."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="llm_step",
                name="LLM",
                step_type=StepType.LLM_CALL,
            ),
            WizardStep(
                id="review",
                name="Review",
                step_type=StepType.REVIEW,
                review_source_step_id="llm_step",
            ),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("analysis v2", 10, 20))
        wizard._workflow._parse_xml_response = MagicMock(
            return_value={"summary": "Better analysis"}
        )

        # First call: reject. Second call: approve.
        call_count = 0

        def mock_ask(schema, template_id=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FormResponse(
                    responses={"review_approval": "No, try again"},
                    template_id=template_id or "",
                )
            return FormResponse(
                responses={"review_approval": "Yes, continue"},
                template_id=template_id or "",
            )

        wizard._form_engine.ask_questions = mock_ask

        result = await wizard.run()

        assert result.success is True
        assert "review" in result.steps_completed
        # LLM was called for initial step + 1 retry = 2 total from review
        # plus the initial dispatch = at least 2 calls
        assert wizard._workflow._call_llm.call_count >= 2

    @pytest.mark.asyncio
    async def test_review_step_exhaust_retries(self):
        """Test review step proceeds after exhausting max retries."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="llm_step",
                name="LLM",
                step_type=StepType.LLM_CALL,
            ),
            WizardStep(
                id="review",
                name="Review",
                step_type=StepType.REVIEW,
                review_source_step_id="llm_step",
            ),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("analysis", 10, 20))
        wizard._workflow._parse_xml_response = MagicMock(return_value={"summary": "Same analysis"})

        # Always reject
        wizard._form_engine.ask_questions = MagicMock(
            return_value=FormResponse(
                responses={"review_approval": "No, try again"},
                template_id="review",
            )
        )

        result = await wizard.run()

        assert result.success is True
        assert "review" in result.steps_completed
        review_result = wizard._session.step_results.get("review")
        assert review_result == {"approved": False}

    @pytest.mark.asyncio
    async def test_review_step_no_source_id_auto_approves(self):
        """Test review step auto-approves when review_source_step_id is None."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="review",
                name="Review",
                step_type=StepType.REVIEW,
                # No review_source_step_id set
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "review" in result.steps_completed
        review_result = wizard._session.step_results.get("review")
        assert review_result == {"approved": True}

    @pytest.mark.asyncio
    async def test_find_step_returns_none_for_unknown_id(self):
        """Test _find_step returns None for a non-existent step ID."""
        wizard = ConcreteWizard()
        wizard._session = None  # Not needed for this test
        assert wizard._find_step("nonexistent") is None

    @pytest.mark.asyncio
    async def test_find_step_returns_matching_step(self):
        """Test _find_step returns the correct step by ID."""
        wizard = ConcreteWizard()
        found = wizard._find_step("q1")
        assert found is not None
        assert found.id == "q1"


class TestSessionNotInitialized:
    """Test RuntimeError when session is None."""

    @pytest.mark.asyncio
    async def test_question_step_raises_without_session(self):
        """Test _run_question_step raises RuntimeError without session."""
        wizard = ConcreteWizard()
        wizard._session = None
        step = WizardStep(
            id="q",
            name="Q",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(id="x", text="?", type=QuestionType.TEXT_INPUT),
            ],
        )
        with pytest.raises(RuntimeError, match="session not initialized"):
            await wizard._run_question_step(step)

    @pytest.mark.asyncio
    async def test_llm_step_raises_without_session(self):
        """Test _run_llm_step raises RuntimeError without session."""
        wizard = ConcreteWizard()
        wizard._session = None
        step = WizardStep(id="l", name="L", step_type=StepType.LLM_CALL)
        with pytest.raises(RuntimeError, match="session not initialized"):
            await wizard._run_llm_step(step)

    @pytest.mark.asyncio
    async def test_confirm_step_raises_without_session(self):
        """Test _run_confirm_step raises RuntimeError without session."""
        wizard = ConcreteWizard()
        wizard._session = None
        step = WizardStep(id="c", name="C", step_type=StepType.CONFIRM)
        with pytest.raises(RuntimeError, match="session not initialized"):
            await wizard._run_confirm_step(step)


class TestWizardAbort:
    """Test _WizardAbort exception."""

    def test_is_exception(self):
        """Test _WizardAbort is an Exception."""
        assert issubclass(_WizardAbort, Exception)

    def test_can_be_raised(self):
        """Test _WizardAbort can be raised and caught."""
        with pytest.raises(_WizardAbort):
            raise _WizardAbort()


# =========================================================================
# Additional uncovered paths
# =========================================================================


class TestQuestionStepEdgeCases:
    """Test _run_question_step with various question types and response shapes."""

    @pytest.mark.asyncio
    async def test_question_step_stores_all_responses(self):
        """Test that all response keys from form engine are stored in session."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="gather",
                name="Gather",
                step_type=StepType.QUESTION,
                questions=[
                    FormQuestion(id="name", text="Name?", type=QuestionType.TEXT_INPUT),
                    FormQuestion(
                        id="mode",
                        text="Mode?",
                        type=QuestionType.SINGLE_SELECT,
                        options=["fast", "slow"],
                        default="fast",
                    ),
                ],
            ),
        ]
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(
            template_id="gather",
            responses={"name": "Alice", "mode": "fast"},
        )
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        result = await wizard.run()

        assert result.success is True
        assert result.collected_data.get("name") == "Alice"
        assert result.collected_data.get("mode") == "fast"

    @pytest.mark.asyncio
    async def test_question_step_completes_with_empty_responses(self):
        """Test question step completes even when form returns empty responses."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="q_empty",
                name="Empty Responses",
                step_type=StepType.QUESTION,
                questions=[
                    FormQuestion(id="optional", text="Optional?", type=QuestionType.TEXT_INPUT),
                ],
            ),
        ]
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(template_id="q_empty", responses={})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        result = await wizard.run()

        assert result.success is True
        assert "q_empty" in result.steps_completed

    @pytest.mark.asyncio
    async def test_question_step_calls_form_engine_with_template_id(self):
        """Test question step passes step ID as template_id to form engine."""
        wizard = ConcreteWizard()
        step_id = "my_specific_step"
        wizard.steps = [
            WizardStep(
                id=step_id,
                name="My Step",
                step_type=StepType.QUESTION,
                questions=[
                    FormQuestion(id="x", text="X?", type=QuestionType.TEXT_INPUT),
                ],
            ),
        ]
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(template_id=step_id, responses={"x": "val"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        await wizard.run()

        call_kwargs = wizard._form_engine.ask_questions.call_args
        assert call_kwargs[1].get("template_id") == step_id or (
            len(call_kwargs[0]) > 1 and call_kwargs[0][1] == step_id
        )


class TestConfirmStepEdgeCases:
    """Test _run_confirm_step rejection and step abort behavior."""

    @pytest.mark.asyncio
    async def test_confirm_step_reject_with_no_word(self):
        """Test that 'no' in answer triggers abort."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(template_id="confirm", responses={"confirm": "No, cancel"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="confirm",
                name="Confirm",
                description="Proceed?",
                step_type=StepType.CONFIRM,
            ),
            WizardStep(
                id="after_confirm",
                name="After",
                step_type=StepType.PREVIEW,
            ),
        ]

        result = await wizard.run()

        # Wizard aborts but still succeeds (abort is graceful)
        assert result.success is True
        assert "after_confirm" not in result.steps_completed
        assert "confirm" in result.steps_completed

    @pytest.mark.asyncio
    async def test_confirm_step_reject_with_cancel_word(self):
        """Test that 'cancel' in answer triggers abort."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(template_id="confirm", responses={"confirm": "cancel"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="confirm_step",
                name="Confirm",
                step_type=StepType.CONFIRM,
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        confirmed_result = wizard._session.step_results.get("confirm_step")
        assert confirmed_result == {"confirmed": False}

    @pytest.mark.asyncio
    async def test_confirm_step_proceed_yes(self):
        """Test that 'yes' in answer does not abort."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(template_id="confirm", responses={"confirm": "Yes, proceed"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="conf2",
                name="Confirm",
                step_type=StepType.CONFIRM,
            ),
        ]

        await wizard.run()

        confirmed_result = wizard._session.step_results.get("conf2")
        assert confirmed_result == {"confirmed": True}

    @pytest.mark.asyncio
    async def test_confirm_step_stores_confirmed_false_before_abort(self):
        """Test confirm step stores confirmed=False before raising _WizardAbort."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(template_id="confirm", responses={"confirm": "No"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="final_confirm",
                name="Final",
                description="Last chance",
                step_type=StepType.CONFIRM,
            ),
        ]

        result = await wizard.run()

        # Session step result should reflect user cancellation
        assert wizard._session.step_results["final_confirm"]["confirmed"] is False
        assert result.success is True  # Abort is not an error


class TestPreviewStepEdgeCases:
    """Test _run_preview_step with various session states."""

    @pytest.mark.asyncio
    async def test_preview_empty_state_produces_minimal_output(self):
        """Test preview with completely empty session produces a heading."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]

        result = await wizard.run()

        assert result.success is True
        # Should at least contain the wizard name in the preview
        assert wizard.config.name in result.generated_output

    @pytest.mark.asyncio
    async def test_preview_excludes_result_suffixed_keys(self):
        """Test preview skips collected_data keys ending with _result."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(
            template_id="q1",
            responses={
                "target": "src/main.py",
                "analyze_result": "internal data - should not appear",
            },
        )
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="q1",
                name="Q",
                step_type=StepType.QUESTION,
                questions=[FormQuestion(id="target", text="Target?", type=QuestionType.TEXT_INPUT)],
            ),
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]

        result = await wizard.run()

        output = result.generated_output
        assert "target" in output
        assert "analyze_result" not in output

    @pytest.mark.asyncio
    async def test_preview_includes_step_results_with_raw_response(self):
        """Test preview shows raw_response when summary is absent."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="llm_step",
                name="LLM Step",
                step_type=StepType.LLM_CALL,
            ),
            WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        ]
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("raw output here", 10, 5))
        wizard._workflow._parse_xml_response = MagicMock(
            return_value={"raw_response": "raw output here"}
        )

        result = await wizard.run()

        assert "raw output here" in result.generated_output

    @pytest.mark.asyncio
    async def test_preview_step_raises_without_session(self):
        """Test _run_preview_step raises RuntimeError without session."""
        wizard = ConcreteWizard()
        wizard._session = None
        step = WizardStep(id="p", name="P", step_type=StepType.PREVIEW)
        with pytest.raises(RuntimeError, match="session not initialized"):
            await wizard._run_preview_step(step)


class TestConditionEvaluationWithSessionState:
    """Test step condition callbacks that examine session state."""

    @pytest.mark.asyncio
    async def test_condition_receives_session_with_prior_data(self):
        """Test that condition callback receives populated session state."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        captured_sessions = []

        def condition_capture(session):
            captured_sessions.append(dict(session.collected_data))
            return False  # Skip this step

        mock_response = FormResponse(template_id="q1", responses={"user_input": "hello"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="q1",
                name="Q",
                step_type=StepType.QUESTION,
                questions=[
                    FormQuestion(id="user_input", text="Input?", type=QuestionType.TEXT_INPUT)
                ],
            ),
            WizardStep(
                id="conditional",
                name="Conditional Step",
                step_type=StepType.PREVIEW,
                condition=condition_capture,
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "conditional" not in result.steps_completed
        # Condition was called with session that has the prior q1 data
        assert len(captured_sessions) == 1
        assert captured_sessions[0].get("user_input") == "hello"

    @pytest.mark.asyncio
    async def test_condition_true_does_not_skip(self):
        """Test that condition returning True runs the step normally."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="always_run",
                name="Always Run",
                step_type=StepType.PREVIEW,
                condition=lambda session: True,
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "always_run" in result.steps_completed

    @pytest.mark.asyncio
    async def test_multiple_conditions_some_skipped(self):
        """Test mix of skipped and non-skipped conditional steps."""
        wizard = ConcreteWizard()
        wizard.steps = [
            WizardStep(
                id="step_skip",
                name="Skip Me",
                step_type=StepType.PREVIEW,
                condition=lambda s: False,
            ),
            WizardStep(
                id="step_run",
                name="Run Me",
                step_type=StepType.PREVIEW,
                condition=lambda s: True,
            ),
            WizardStep(
                id="step_skip2",
                name="Skip Me Too",
                step_type=StepType.PREVIEW,
                condition=lambda s: False,
            ),
        ]

        result = await wizard.run()

        assert result.success is True
        assert "step_skip" not in result.steps_completed
        assert "step_run" in result.steps_completed
        assert "step_skip2" not in result.steps_completed
        assert len(wizard._session.steps_skipped) == 2


class TestDispatchStep:
    """Test _dispatch_step routes correctly to each handler."""

    @pytest.mark.asyncio
    async def test_dispatch_question_step(self):
        """Test QUESTION step dispatch calls _run_question_step."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        mock_response = FormResponse(template_id="q", responses={"k": "v"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        # Initialize session manually
        from attune.wizards.session import WizardSession

        wizard._session = WizardSession(wizard_id="test-wizard")

        step = WizardStep(
            id="q",
            name="Q",
            step_type=StepType.QUESTION,
            questions=[FormQuestion(id="k", text="K?", type=QuestionType.TEXT_INPUT)],
        )
        await wizard._dispatch_step(step)

        assert "q" in wizard._session.steps_completed

    @pytest.mark.asyncio
    async def test_dispatch_preview_step(self):
        """Test PREVIEW step dispatch calls _run_preview_step."""
        wizard = ConcreteWizard()
        from attune.wizards.session import WizardSession

        wizard._session = WizardSession(wizard_id="test-wizard")

        step = WizardStep(id="prev", name="Prev", step_type=StepType.PREVIEW)
        await wizard._dispatch_step(step)

        assert "prev" in wizard._session.steps_completed

    @pytest.mark.asyncio
    async def test_dispatch_confirm_step(self):
        """Test CONFIRM step dispatch calls _run_confirm_step."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse
        from attune.wizards.session import WizardSession

        mock_response = FormResponse(template_id="conf", responses={"confirm": "Yes, proceed"})
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard._session = WizardSession(wizard_id="test-wizard")

        step = WizardStep(id="conf", name="Conf", step_type=StepType.CONFIRM)
        await wizard._dispatch_step(step)

        assert "conf" in wizard._session.steps_completed

    @pytest.mark.asyncio
    async def test_dispatch_llm_step(self):
        """Test LLM_CALL step dispatch calls _run_llm_step."""
        wizard = ConcreteWizard()
        wizard._workflow._render_xml_prompt = MagicMock(return_value="<p/>")
        wizard._workflow._call_llm = AsyncMock(return_value=("result", 10, 5))
        wizard._workflow._parse_xml_response = MagicMock(return_value={"key": "val"})

        from attune.wizards.session import WizardSession

        wizard._session = WizardSession(wizard_id="test-wizard")

        step = WizardStep(id="llm", name="LLM", step_type=StepType.LLM_CALL)
        await wizard._dispatch_step(step)

        assert "llm" in wizard._session.steps_completed

    @pytest.mark.asyncio
    async def test_dispatch_decompose_step(self):
        """Test TASK_DECOMPOSE step dispatch calls _run_decompose_step."""
        from attune.wizards.decomposer import DecomposedTask
        from attune.wizards.session import WizardSession

        wizard = ConcreteWizard()
        wizard._session = WizardSession(wizard_id="test-wizard")

        mock_tasks = [DecomposedTask(task_id="1", name="t1", objective="Do it")]

        with patch("attune.wizards.decomposer.TaskDecomposer") as MockDecomposer:
            mock_instance = MagicMock()
            mock_instance.decompose = AsyncMock(return_value=mock_tasks)
            MockDecomposer.return_value = mock_instance

            step = WizardStep(id="decomp", name="Decomp", step_type=StepType.TASK_DECOMPOSE)
            await wizard._dispatch_step(step)

        assert "decomp" in wizard._session.steps_completed

    @pytest.mark.asyncio
    async def test_dispatch_review_step(self):
        """Test REVIEW step dispatch calls _run_review_step."""
        from attune.meta_workflows.models import FormResponse
        from attune.wizards.session import WizardSession

        wizard = ConcreteWizard()
        wizard._session = WizardSession(wizard_id="test-wizard")
        # Pre-populate source step result
        wizard._session.step_results["source_step"] = {"summary": "Analysis done"}

        mock_response = FormResponse(
            template_id="review", responses={"review_approval": "Yes, continue"}
        )
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)

        step = WizardStep(
            id="review",
            name="Review",
            step_type=StepType.REVIEW,
            review_source_step_id="source_step",
        )
        await wizard._dispatch_step(step)

        assert "review" in wizard._session.steps_completed


class TestRunWithInitialContext:
    """Test run() with initial_context parameter."""

    @pytest.mark.asyncio
    async def test_initial_context_available_in_session(self):
        """Test initial_context values are accessible via session.get()."""
        wizard = ConcreteWizard()
        wizard.steps = []  # No steps needed

        result = await wizard.run(initial_context={"file": "auth.py", "mode": "strict"})

        assert result.success is True
        # Session should have captured initial context
        assert wizard._session.initial_context.get("file") == "auth.py"
        assert wizard._session.initial_context.get("mode") == "strict"

    @pytest.mark.asyncio
    async def test_run_none_initial_context_is_empty_dict(self):
        """Test run() with None initial_context results in empty initial_context."""
        wizard = ConcreteWizard()
        wizard.steps = []

        await wizard.run(initial_context=None)

        assert wizard._session.initial_context == {}

    @pytest.mark.asyncio
    async def test_run_initial_context_does_not_override_collected_data(self):
        """Test that session.set() overrides initial_context values."""
        wizard = ConcreteWizard()
        from attune.meta_workflows.models import FormResponse

        # Form engine will return "new_value" for "key"
        mock_response = FormResponse(
            template_id="q1",
            responses={"user_input": "from_form"},
        )
        wizard._form_engine.ask_questions = MagicMock(return_value=mock_response)
        wizard.steps = [
            WizardStep(
                id="q1",
                name="Q",
                step_type=StepType.QUESTION,
                questions=[
                    FormQuestion(id="user_input", text="Input?", type=QuestionType.TEXT_INPUT)
                ],
            ),
        ]

        # Initial context has "user_input" = "from_context"
        await wizard.run(initial_context={"user_input": "from_context"})

        # collected_data should have the form value
        assert wizard._session.collected_data.get("user_input") == "from_form"
        # But initial_context is unchanged
        assert wizard._session.initial_context.get("user_input") == "from_context"
        # Session.get() prefers collected_data
        assert wizard._session.get("user_input") == "from_form"
