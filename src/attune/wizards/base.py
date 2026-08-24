"""Base wizard class for XML-enhanced interactive workflows.

Provides ``BaseWizard``, the abstract base class for all wizards.
Data types (``StepType``, ``WizardStep``, ``WizardConfig``,
``WizardResult``) live in ``_types.py``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from attune.meta_workflows.form_engine import AskUserQuestionCallback, SocraticFormEngine
from attune.meta_workflows.models import FormQuestion, FormSchema, QuestionType
from attune.prompts import PromptContext
from attune.workflows.compat import ModelTier

from ._types import StepType, WizardConfig, WizardResult, WizardStep
from .session import WizardSession

# Re-export types for backward compatibility
__all__ = [
    "BaseWizard",
    "StepType",
    "WizardConfig",
    "WizardResult",
    "WizardStep",
]

logger = logging.getLogger(__name__)


# =========================================================================
# Tier mapping helper
# =========================================================================

_TIER_MAP = {
    "cheap": ModelTier.CHEAP,
    "capable": ModelTier.CAPABLE,
    "premium": ModelTier.PREMIUM,
}


def _resolve_tier(tier_str: str) -> ModelTier:
    """Resolve a tier string to a ModelTier enum.

    Args:
        tier_str: One of ``"cheap"``, ``"capable"``, ``"premium"``.

    Returns:
        Corresponding ``ModelTier`` value.

    """
    return _TIER_MAP.get(tier_str, ModelTier.CAPABLE)


# =========================================================================
# BaseWizard
# =========================================================================


class BaseWizard(ABC):
    """Abstract base class for interactive, multi-step wizards.

    Subclasses must define:
        - ``config``: A ``WizardConfig`` instance.
        - ``steps``: An ordered list of ``WizardStep`` definitions.
        - ``build_prompt_context()``: Builds a ``PromptContext`` for LLM steps.
        - ``process_step_result()``: Stores/transforms LLM step results.

    Example:
        >>> class MyWizard(BaseWizard):
        ...     config = WizardConfig(wizard_id="mine", name="My Wizard", description="Demo")
        ...     steps = [...]
        ...     def build_prompt_context(self, step): ...
        ...     def process_step_result(self, step, result): ...
        >>> wizard = MyWizard()
        >>> result = await wizard.run({"target": "src/main.py"})

    """

    config: WizardConfig
    steps: list[WizardStep]

    def __init__(
        self,
        ask_user_callback: AskUserQuestionCallback | None = None,
        provider: str | None = None,
        **workflow_kwargs: Any,
    ) -> None:
        """Initialize the wizard.

        Args:
            ask_user_callback: Callback for AskUserQuestion tool invocations.
                When ``None``, question steps use default values.
            provider: Model provider string (e.g. ``"anthropic"``).
            **workflow_kwargs: Extra arguments forwarded to ``BaseWorkflow``.

        """
        from .internal_workflow import WizardInternalWorkflow

        self._workflow = WizardInternalWorkflow(provider=provider, **workflow_kwargs)
        self._form_engine = SocraticFormEngine(ask_user_callback=ask_user_callback)
        self._session: WizardSession | None = None

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    async def run(self, initial_context: dict[str, Any] | None = None) -> WizardResult:
        """Execute the wizard flow.

        Iterates through all steps, dispatching each by its ``StepType``.
        Steps with a ``condition`` that returns ``False`` are skipped.

        Args:
            initial_context: Optional starting context (e.g. file path, error message).

        Returns:
            ``WizardResult`` with collected data, generated output, and tasks.

        """
        start = time.time()
        self._session = WizardSession(
            wizard_id=self.config.wizard_id,
            initial_context=initial_context or {},
        )

        logger.info("Starting wizard %s (run=%s)", self.config.wizard_id, self._session.run_id)

        try:
            for step in self.steps:
                # Check skip condition
                if step.condition is not None and not step.condition(self._session):
                    logger.info("Skipping step %s (condition not met)", step.id)
                    self._session.skip_step(step.id)
                    continue

                logger.info("Running step %s (%s)", step.id, step.step_type.value)
                await self._dispatch_step(step)

        except _WizardAbort:
            logger.info("Wizard aborted by user at step confirmation")
        except Exception as e:  # noqa: BLE001
            logger.error("Wizard %s failed: %s", self.config.wizard_id, e)
            duration_ms = (time.time() - start) * 1000
            return WizardResult(
                wizard_id=self.config.wizard_id,
                run_id=self._session.run_id,
                success=False,
                steps_completed=self._session.steps_completed,
                collected_data=self._session.collected_data,
                total_cost=self._session.total_cost,
                total_duration_ms=duration_ms,
                error=str(e),
            )

        duration_ms = (time.time() - start) * 1000
        return WizardResult(
            wizard_id=self.config.wizard_id,
            run_id=self._session.run_id,
            success=True,
            steps_completed=self._session.steps_completed,
            collected_data=self._session.collected_data,
            generated_output=self._session.generated_output,
            tasks=self._session.tasks,
            total_cost=self._session.total_cost,
            total_duration_ms=duration_ms,
        )

    # -----------------------------------------------------------------
    # Step dispatch
    # -----------------------------------------------------------------

    async def _dispatch_step(self, step: WizardStep) -> None:
        """Route a step to the appropriate handler.

        Args:
            step: The step to execute.

        """
        handlers = {
            StepType.QUESTION: self._run_question_step,
            StepType.LLM_CALL: self._run_llm_step,
            StepType.TASK_DECOMPOSE: self._run_decompose_step,
            StepType.REVIEW: self._run_review_step,
            StepType.PREVIEW: self._run_preview_step,
            StepType.CONFIRM: self._run_confirm_step,
        }
        handler = handlers[step.step_type]
        await handler(step)

    # -----------------------------------------------------------------
    # QUESTION step
    # -----------------------------------------------------------------

    async def _run_question_step(self, step: WizardStep) -> None:
        """Collect user input via AskUserQuestion.

        Args:
            step: A step with ``step_type == StepType.QUESTION``.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        questions = step.questions or []
        if not questions:
            logger.warning("Question step %s has no questions", step.id)
            self._session.complete_step(step.id)
            return

        schema = FormSchema(
            title=step.name,
            description=step.description,
            questions=questions,
        )
        response = self._form_engine.ask_questions(schema, template_id=step.id)

        # Store each response in the session
        for key, value in response.responses.items():
            self._session.set(key, value)

        self._session.complete_step(step.id, result=response.responses)

    # -----------------------------------------------------------------
    # LLM_CALL step
    # -----------------------------------------------------------------

    async def _run_llm_step(self, step: WizardStep) -> None:
        """Call an LLM with an XML prompt and parse the response.

        Args:
            step: A step with ``step_type == StepType.LLM_CALL``.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        context = self.build_prompt_context(step)

        # Render XML prompt
        prompt = self._workflow._render_xml_prompt(
            role=context.role,
            goal=context.goal,
            instructions=context.instructions,
            constraints=context.constraints,
            input_type=context.input_type,
            input_payload=context.input_payload,
            extra=context.extra,
        )

        tier = _resolve_tier(step.tier)

        # Call LLM — _call_llm(tier, system, user_message, ...) returns
        # (text, input_tokens, output_tokens). The rendered XML prompt carries
        # the role/goal/instructions, so it is the user message.
        response_text, _input_tokens, _output_tokens = await self._workflow._call_llm(
            tier=tier,
            system="Follow the XML task specification precisely.",
            user_message=prompt,
            stage_name=step.id,
        )

        # Parse response
        parsed = self._workflow._parse_xml_response(response_text)
        if not parsed:
            parsed = {"raw_response": response_text}

        # Let subclass process the result
        self.process_step_result(step, parsed)
        self._session.complete_step(step.id, result=parsed)

    # -----------------------------------------------------------------
    # REVIEW step
    # -----------------------------------------------------------------

    async def _run_review_step(self, step: WizardStep) -> None:
        """Show intermediate results and ask user for feedback.

        Displays the output of a prior LLM step and asks
        "Does this look right?" If the user says no, the source
        LLM step is re-run and the review repeats (up to 2 retries).

        Args:
            step: A step with ``step_type == StepType.REVIEW``.
                Must have ``review_source_step_id`` pointing to a
                prior LLM_CALL step.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")

        source_id = step.review_source_step_id
        if not source_id:
            logger.warning("REVIEW step %s has no review_source_step_id", step.id)
            self._session.complete_step(step.id, result={"approved": True})
            return

        max_retries = 2
        for attempt in range(max_retries + 1):
            # Get the source step's result
            source_result = self._session.step_results.get(source_id, {})
            if isinstance(source_result, dict):
                summary = source_result.get(
                    "summary",
                    source_result.get("raw_response", str(source_result)),
                )
            else:
                summary = str(source_result)

            # Show the result and ask for approval
            review_question = FormQuestion(
                id="review_approval",
                text=(f"Here's what the analysis found:\n\n{summary}\n\n" "Does this look right?"),
                type=QuestionType.SINGLE_SELECT,
                options=["Yes, continue", "No, try again"],
                default="Yes, continue",
            )
            schema = FormSchema(
                title=step.name,
                description=step.description or "Review intermediate results",
                questions=[review_question],
            )
            response = self._form_engine.ask_questions(schema, template_id=step.id)
            answer = response.get("review_approval", "Yes, continue")

            if "yes" in str(answer).lower() or "continue" in str(answer).lower():
                self._session.complete_step(step.id, result={"approved": True})
                return

            # User said no — re-run the source LLM step if retries remain
            if attempt < max_retries:
                logger.info(
                    "User rejected review — re-running step %s (attempt %d/%d)",
                    source_id,
                    attempt + 2,
                    max_retries + 1,
                )
                source_step = self._find_step(source_id)
                if source_step:
                    await self._run_llm_step(source_step)

        # Exhausted retries — proceed with last result
        logger.info("Max retries reached for review step %s — proceeding", step.id)
        self._session.complete_step(step.id, result={"approved": False})

    def _find_step(self, step_id: str) -> WizardStep | None:
        """Find a step by ID.

        Args:
            step_id: Step identifier to look up.

        Returns:
            The matching ``WizardStep``, or ``None``.

        """
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def _required_step(self, step_id: str) -> WizardStep:
        """Find a step by ID, raising a clear error when absent.

        #2242: bare ``next(s for s in self.steps if s.id == ...)`` raised
        an opaque ``StopIteration`` when a wizard's step list drifted
        from the IDs its handlers expect.

        Args:
            step_id: Step identifier to look up.

        Returns:
            The matching ``WizardStep``.

        Raises:
            ValueError: If no step with ``step_id`` exists.
        """
        step = self._find_step(step_id)
        if step is None:
            raise ValueError(
                f"wizard '{type(self).__name__}' has no step {step_id!r} "
                f"(steps: {[s.id for s in self.steps]})"
            )
        return step

    # -----------------------------------------------------------------
    # TASK_DECOMPOSE step
    # -----------------------------------------------------------------

    async def _run_decompose_step(self, step: WizardStep) -> None:
        """Break the current problem into XML sub-tasks.

        Args:
            step: A step with ``step_type == StepType.TASK_DECOMPOSE``.

        """
        from .decomposer import TaskDecomposer

        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        decomposer = TaskDecomposer(self._workflow)

        # Build problem description from session state
        context = self.build_prompt_context(step)

        tasks = await decomposer.decompose(
            problem_description=context.goal,
            codebase_context=context.input_payload,
            constraints=context.constraints,
        )

        task_dicts = [t.to_dict() for t in tasks]
        self._session.tasks = task_dicts
        self._session.complete_step(step.id, result=task_dicts)

    # -----------------------------------------------------------------
    # PREVIEW step
    # -----------------------------------------------------------------

    async def _run_preview_step(self, step: WizardStep) -> None:
        """Show generated results for review.

        This step formats the session's current output and tasks into
        a preview string and stores it. In an interactive context, the
        calling code (CLI or Claude Code) would display this to the user.

        Args:
            step: A step with ``step_type == StepType.PREVIEW``.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")

        preview_parts = [f"## {self.config.name} - Preview\n"]

        # Show collected data summary
        if self._session.collected_data:
            preview_parts.append("### Inputs")
            for key, value in self._session.collected_data.items():
                if not key.endswith("_result"):
                    preview_parts.append(f"- **{key}**: {value}")
            preview_parts.append("")

        # Show analysis results
        for step_id, result in self._session.step_results.items():
            if isinstance(result, dict):
                summary = result.get("summary", result.get("raw_response", ""))
                if summary:
                    preview_parts.append(f"### {step_id}")
                    preview_parts.append(str(summary))
                    preview_parts.append("")

        # Show decomposed tasks
        if self._session.tasks:
            preview_parts.append(f"### Tasks ({len(self._session.tasks)})")
            for i, task in enumerate(self._session.tasks, 1):
                name = task.get("name", task.get("task_id", f"Task {i}"))
                objective = task.get("objective", "")
                preview_parts.append(f"{i}. **{name}** -- {objective}")
            preview_parts.append("")

        preview_text = "\n".join(preview_parts)
        self._session.generated_output = preview_text
        self._session.complete_step(step.id, result={"preview": preview_text})

    # -----------------------------------------------------------------
    # CONFIRM step
    # -----------------------------------------------------------------

    async def _run_confirm_step(self, step: WizardStep) -> None:
        """Ask user for final confirmation.

        If the user declines, raises ``_WizardAbort`` to stop the flow.

        Args:
            step: A step with ``step_type == StepType.CONFIRM``.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        confirm_question = FormQuestion(
            id="confirm",
            text=step.description or "Proceed with these changes?",
            type=QuestionType.SINGLE_SELECT,
            options=["Yes, proceed", "No, cancel"],
            default="Yes, proceed",
        )
        schema = FormSchema(
            title=step.name,
            description=step.description,
            questions=[confirm_question],
        )
        response = self._form_engine.ask_questions(schema, template_id=step.id)
        answer = response.get("confirm", "Yes, proceed")

        if "no" in str(answer).lower() or "cancel" in str(answer).lower():
            self._session.complete_step(step.id, result={"confirmed": False})
            raise _WizardAbort

        self._session.complete_step(step.id, result={"confirmed": True})

    # -----------------------------------------------------------------
    # Abstract methods for subclasses
    # -----------------------------------------------------------------

    @abstractmethod
    def build_prompt_context(self, step: WizardStep) -> PromptContext:
        """Build a ``PromptContext`` for a given step using session state.

        Called for ``LLM_CALL`` and ``TASK_DECOMPOSE`` steps.

        Args:
            step: The current step.

        Returns:
            A ``PromptContext`` with role, goal, instructions, input, etc.

        """

    @abstractmethod
    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Process and store the result of an LLM step.

        Called after ``_run_llm_step`` parses the LLM response.
        Subclasses should extract relevant fields and store them in
        ``self._session`` for use by later steps.

        Args:
            step: The step that produced this result.
            result: Parsed LLM response dict.

        """


# =========================================================================
# Internal exception for wizard flow control
# =========================================================================


class _WizardAbort(Exception):
    """Raised when the user declines a CONFIRM step."""
