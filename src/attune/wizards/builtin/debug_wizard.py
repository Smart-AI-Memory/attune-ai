"""Debugging Wizard.

Guided flow: describe error -> analyze -> decompose fix -> preview -> confirm.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext

from ..base import BaseWizard, StepType, WizardConfig, WizardStep


class DebugWizard(BaseWizard):
    """Guided debugging wizard.

    Steps:
        1. Gather error details (QUESTION)
        2. Analyze root cause (LLM_CALL with bug-analysis template)
        3. Decompose fix into tasks (TASK_DECOMPOSE)
        4. Preview analysis and fix plan (PREVIEW)
        5. Confirm execution (CONFIRM)
    """

    config = WizardConfig(
        wizard_id="debug",
        name="Debugging Wizard",
        description="Guided error investigation and fix planning",
        domain="development",
        estimated_cost_range=(0.02, 0.30),
        estimated_duration_minutes=5,
    )

    steps = [
        WizardStep(
            id="gather_info",
            name="Describe the Problem",
            description="Collect error details and context",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="error_description",
                    text="What error or unexpected behavior are you seeing?",
                    type=QuestionType.TEXT_INPUT,
                    help_text="Include the error message, stack trace, or describe the behavior",
                ),
                FormQuestion(
                    id="target_file",
                    text="Which file(s) are involved?",
                    type=QuestionType.TEXT_INPUT,
                    default="",
                    help_text="e.g. src/main.py, or leave blank if unsure",
                ),
                FormQuestion(
                    id="has_stack_trace",
                    text="Do you have a stack trace or error log?",
                    type=QuestionType.BOOLEAN,
                    default="No",
                ),
            ],
        ),
        WizardStep(
            id="analyze",
            name="Analyze Root Cause",
            description="Use LLM to identify likely root causes",
            step_type=StepType.LLM_CALL,
            prompt_template="bug-analysis",
            tier="capable",
        ),
        WizardStep(
            id="decompose_fix",
            name="Plan the Fix",
            description="Break the fix into actionable tasks",
            step_type=StepType.TASK_DECOMPOSE,
            tier="capable",
        ),
        WizardStep(
            id="preview",
            name="Review Plan",
            description="Review the analysis and fix plan",
            step_type=StepType.PREVIEW,
        ),
        WizardStep(
            id="confirm",
            name="Confirm",
            description="Apply these fixes?",
            step_type=StepType.CONFIRM,
        ),
    ]

    def build_prompt_context(self, step: WizardStep) -> PromptContext:
        """Build prompt context from session state.

        Args:
            step: The current step.

        Returns:
            PromptContext for the LLM call.

        """
        assert self._session is not None

        if step.id == "analyze":
            error_desc = self._session.get("error_description", "Unknown error")
            target_file = self._session.get("target_file", "")
            has_trace = self._session.get("has_stack_trace", "No")

            input_text = f"Error: {error_desc}"
            if target_file:
                input_text += f"\nFile(s): {target_file}"
            if str(has_trace).lower() in ("yes", "true"):
                input_text += "\n(Stack trace available)"

            return PromptContext(
                role="senior debugging specialist",
                goal="Identify the root cause of this error and suggest a fix",
                instructions=[
                    "Analyze the error description for likely root causes",
                    "Consider common patterns: type mismatches, missing imports, logic errors",
                    "Suggest specific file and line locations if possible",
                    "Provide a concrete remediation approach",
                ],
                constraints=[
                    "Be specific and actionable",
                    "Prioritize the most likely root cause",
                    "Include code examples for the fix",
                ],
                input_type="error_report",
                input_payload=input_text,
            )

        if step.id == "decompose_fix":
            analysis = self._session.step_results.get("analyze", {})
            summary = analysis.get("summary", analysis.get("raw_response", ""))
            return PromptContext(
                role="implementation planner",
                goal=f"Plan the fix: {summary}",
                instructions=["Break the fix into small, testable tasks"],
                constraints=["Each task should touch 1-3 files"],
                input_type="analysis",
                input_payload=str(analysis),
            )

        return PromptContext(role="assistant", goal="Help debug the issue")

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Store analysis results in session.

        Args:
            step: The step that produced this result.
            result: Parsed LLM response.

        """
        assert self._session is not None
        if step.id == "analyze":
            self._session.set("analysis", result)
