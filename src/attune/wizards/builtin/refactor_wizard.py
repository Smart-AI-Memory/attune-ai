"""Refactoring Wizard.

Guided flow: describe goal -> analyze -> decompose steps -> preview -> confirm.

Delegates the analysis step to ``RefactorPlanWorkflow`` for mature
multi-stage scanning (scan → analyze → prioritize → plan) while
preserving the wizard-guided UX.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext
from attune.workflows.compat import ModelTier

if TYPE_CHECKING:
    from attune.workflows.base import BaseWorkflow

from ..base import BaseWizard, StepType, WizardConfig, WizardStep

logger = logging.getLogger(__name__)


class RefactorWizard(BaseWizard):
    """Guided refactoring wizard.

    Delegates the analysis step to ``RefactorPlanWorkflow`` for mature
    multi-stage code analysis. Falls back to independent LLM calls if
    the workflow is unavailable.

    Steps:
        1. Describe refactoring goal and target (QUESTION)
        2. Analyze code structure via RefactorPlanWorkflow (LLM_CALL)
        3. Decompose into incremental steps (TASK_DECOMPOSE)
        4. Preview before/after plan (PREVIEW)
        5. Confirm execution (CONFIRM)
    """

    config = WizardConfig(
        wizard_id="refactor",
        name="Refactoring Wizard",
        description="Plan safe, incremental code refactoring",
        domain="development",
        estimated_cost_range=(0.02, 0.35),
        estimated_duration_minutes=5,
    )

    steps = [
        WizardStep(
            id="gather_info",
            name="Describe Refactoring",
            description="What do you want to improve?",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="refactor_type",
                    text="What kind of refactoring?",
                    type=QuestionType.SINGLE_SELECT,
                    options=[
                        "Extract method/function",
                        "Split large file",
                        "Reduce complexity",
                        "Rename and reorganize",
                        "Other",
                    ],
                    default="Reduce complexity",
                ),
                FormQuestion(
                    id="target_file",
                    text="Which file or module to refactor?",
                    type=QuestionType.TEXT_INPUT,
                    help_text="e.g. src/attune/workflows/base.py",
                ),
                FormQuestion(
                    id="goal",
                    text="What's the goal of this refactoring?",
                    type=QuestionType.TEXT_INPUT,
                    default="Improve readability and maintainability",
                ),
            ],
        ),
        WizardStep(
            id="analyze",
            name="Analyze Structure",
            description="Analyze current code structure and identify improvements",
            step_type=StepType.LLM_CALL,
            prompt_template="refactor-plan",
            tier="capable",
        ),
        WizardStep(
            id="decompose_steps",
            name="Plan Steps",
            description="Break refactoring into safe, incremental tasks",
            step_type=StepType.TASK_DECOMPOSE,
            tier="capable",
        ),
        WizardStep(
            id="preview",
            name="Review Plan",
            description="Review the refactoring plan",
            step_type=StepType.PREVIEW,
        ),
        WizardStep(
            id="confirm",
            name="Confirm",
            description="Apply this refactoring?",
            step_type=StepType.CONFIRM,
        ),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize refactoring wizard.

        Args:
            **kwargs: Forwarded to ``BaseWizard.__init__``.

        """
        super().__init__(**kwargs)
        self._refactor_workflow: BaseWorkflow | None = None

    # -----------------------------------------------------------------
    # Workflow delegation
    # -----------------------------------------------------------------

    def _get_or_create_workflow(self) -> Any:
        """Lazily instantiate and cache RefactorPlanWorkflow.

        Returns:
            RefactorPlanWorkflow instance, or None if unavailable.

        """
        if self._refactor_workflow is not None:
            return self._refactor_workflow

        try:
            from attune.workflows.refactor_plan import RefactorPlanWorkflow

            self._refactor_workflow = RefactorPlanWorkflow(
                use_crew_for_analysis=False,
            )
            return self._refactor_workflow
        except ImportError:
            logger.warning("RefactorPlanWorkflow not available, using LLM fallback")
            return None
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Workflow is optional enhancement, not required
            logger.exception("Failed to initialize RefactorPlanWorkflow")
            return None

    async def _run_llm_step(self, step: WizardStep) -> None:
        """Override to delegate analysis to RefactorPlanWorkflow.

        Falls back to the base LLM call if the workflow is unavailable
        or encounters an error.

        Args:
            step: A step with ``step_type == StepType.LLM_CALL``.

        """
        if step.id == "analyze":
            try:
                await self._run_analysis_via_workflow()
                return
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback to independent LLM call
                logger.exception("Workflow analysis failed, falling back to LLM")

        # Fall back to base LLM call
        await super()._run_llm_step(step)

    async def _run_analysis_via_workflow(self) -> None:
        """Run scan + analyze + prioritize + plan via RefactorPlanWorkflow.

        Builds input from wizard session, runs all four stages,
        and stores the combined result in the wizard session.

        Raises:
            RuntimeError: If the workflow is not available.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        workflow = self._get_or_create_workflow()
        if workflow is None:
            raise RuntimeError("RefactorPlanWorkflow not available")

        target = self._session.get("target_file", ".")
        refactor_type = self._session.get("refactor_type", "Reduce complexity")
        goal = self._session.get("goal", "Improve readability")

        input_data: dict[str, Any] = {
            "path": target,
            "refactor_type": refactor_type,
            "goal": goal,
        }

        # Stage 1: Scan — find TODO/FIXME/HACK markers
        scan_result, s_in, s_out = await workflow.run_stage(
            "scan",
            ModelTier.CHEAP,
            input_data,
        )

        # Stage 2: Analyze — debt trajectory analysis
        analyze_input = {**input_data, **scan_result}
        analyze_result, a_in, a_out = await workflow.run_stage(
            "analyze",
            ModelTier.CAPABLE,
            analyze_input,
        )

        # Stage 3: Prioritize — score by impact/effort/risk
        prioritize_input = {**analyze_input, **analyze_result}
        prioritize_result, p_in, p_out = await workflow.run_stage(
            "prioritize",
            ModelTier.CAPABLE,
            prioritize_input,
        )

        # Stage 4: Plan — generate refactoring roadmap
        plan_input = {**prioritize_input, **prioritize_result}
        plan_result, pl_in, pl_out = await workflow.run_stage(
            "plan",
            ModelTier.PREMIUM,
            plan_input,
        )

        # Combine results for session storage
        combined: dict[str, Any] = {
            "debt_items": scan_result.get("debt_items", []),
            "analysis": analyze_result.get("analysis", {}),
            "priorities": prioritize_result.get("priorities", []),
            "refactoring_plan": plan_result.get("refactoring_plan", ""),
            "summary": plan_result.get("summary", ""),
            "formatted_report": plan_result.get("formatted_report", ""),
            "workflow_delegated": True,
        }

        self.process_step_result(
            self._required_step("analyze"),
            combined,
        )
        self._session.complete_step("analyze", result=combined)

    # -----------------------------------------------------------------
    # Abstract method implementations
    # -----------------------------------------------------------------

    def build_prompt_context(self, step: WizardStep) -> PromptContext:
        """Build prompt context from session state.

        Used as fallback when workflow delegation is not available.

        Args:
            step: The current step.

        Returns:
            PromptContext for the LLM call.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")

        if step.id == "analyze":
            refactor_type = self._session.get("refactor_type", "Reduce complexity")
            target = self._session.get("target_file", "")
            goal = self._session.get("goal", "Improve readability")

            return PromptContext(
                role="senior software architect",
                goal=f"{refactor_type} in {target}: {goal}",
                instructions=[
                    f"Analyze the structure of {target}",
                    f"Focus on: {refactor_type}",
                    "Identify specific code smells and improvement opportunities",
                    "Propose incremental changes that preserve behavior",
                    "Estimate effort and risk for each change",
                ],
                constraints=[
                    "Changes must be backward-compatible",
                    "Each step should leave the code in a working state",
                    "Preserve existing tests",
                    "Keep changes small and reviewable",
                ],
                input_type="refactoring_request",
                input_payload=f"Target: {target}\nType: {refactor_type}\nGoal: {goal}",
            )

        if step.id == "decompose_steps":
            analysis = self._session.step_results.get("analyze", {})
            return PromptContext(
                role="refactoring planner",
                goal="Break refactoring into safe incremental steps",
                instructions=["Each step should be a single, atomic change"],
                constraints=["Tests must pass after each step"],
                input_type="analysis",
                input_payload=str(analysis),
            )

        return PromptContext(role="assistant", goal="Plan refactoring")

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Store analysis results in session.

        Args:
            step: The step that produced this result.
            result: Parsed LLM response or workflow output.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        if step.id == "analyze":
            self._session.set("refactor_analysis", result)
