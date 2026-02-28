"""Test Generation Wizard.

Guided flow: select target -> analyze -> decompose tests -> preview -> confirm.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext

from ..base import BaseWizard, StepType, WizardConfig, WizardStep


class TestGenWizard(BaseWizard):
    """Guided test generation wizard.

    Steps:
        1. Select target and test style (QUESTION)
        2. Analyze code for untested paths (LLM_CALL with test-gen template)
        3. Decompose into test file tasks (TASK_DECOMPOSE)
        4. Preview generated tests (PREVIEW)
        5. Confirm file creation (CONFIRM)
    """

    config = WizardConfig(
        wizard_id="test-gen",
        name="Test Generation Wizard",
        description="Generate behavioral tests for a module or file",
        domain="testing",
        estimated_cost_range=(0.02, 0.40),
        estimated_duration_minutes=5,
    )

    steps = [
        WizardStep(
            id="gather_info",
            name="Select Target",
            description="Choose what to generate tests for",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="target_path",
                    text="Which file or directory should tests be generated for?",
                    type=QuestionType.TEXT_INPUT,
                    help_text="e.g. src/attune/config.py or src/attune/workflows/",
                ),
                FormQuestion(
                    id="test_style",
                    text="What kind of tests?",
                    type=QuestionType.SINGLE_SELECT,
                    options=[
                        "Unit tests",
                        "Integration tests",
                        "Edge case tests",
                        "All of the above",
                    ],
                    default="Unit tests",
                ),
                FormQuestion(
                    id="framework",
                    text="Test framework?",
                    type=QuestionType.SINGLE_SELECT,
                    options=["pytest (Recommended)", "unittest"],
                    default="pytest (Recommended)",
                ),
            ],
        ),
        WizardStep(
            id="analyze",
            name="Analyze Code",
            description="Identify untested paths and coverage gaps",
            step_type=StepType.LLM_CALL,
            prompt_template="test-gen",
            tier="capable",
        ),
        WizardStep(
            id="decompose_tests",
            name="Generate Test Plan",
            description="Create individual test file tasks",
            step_type=StepType.TASK_DECOMPOSE,
            tier="capable",
        ),
        WizardStep(
            id="preview",
            name="Review Tests",
            description="Review the generated test plan",
            step_type=StepType.PREVIEW,
        ),
        WizardStep(
            id="confirm",
            name="Confirm",
            description="Write these test files?",
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
            target = self._session.get("target_path", "src/")
            test_style = self._session.get("test_style", "Unit tests")
            framework = self._session.get("framework", "pytest")

            return PromptContext(
                role="senior test engineer",
                goal=f"Analyze {target} and identify untested code paths for {test_style.lower()}",
                instructions=[
                    f"Analyze the target: {target}",
                    f"Focus on generating {test_style.lower()}",
                    "Identify functions and branches without test coverage",
                    "Suggest specific test cases for each untested path",
                    f"Use {framework} conventions",
                ],
                constraints=[
                    "Follow existing test patterns in the codebase",
                    "Include edge cases and error handling tests",
                    "Use descriptive test names: test_{function}_{scenario}_{expected}",
                ],
                input_type="code_path",
                input_payload=target,
                extra={"test_style": test_style, "framework": framework},
            )

        if step.id == "decompose_tests":
            analysis = self._session.step_results.get("analyze", {})
            target = self._session.get("target_path", "src/")
            return PromptContext(
                role="test generation planner",
                goal=f"Create test files for {target}",
                instructions=["Create one task per test file"],
                constraints=["Each test file should be self-contained"],
                input_type="analysis",
                input_payload=str(analysis),
            )

        return PromptContext(role="assistant", goal="Generate tests")

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Store analysis results in session.

        Args:
            step: The step that produced this result.
            result: Parsed LLM response.

        """
        assert self._session is not None
        if step.id == "analyze":
            self._session.set("test_analysis", result)
