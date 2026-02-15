"""Release Preparation Wizard.

Guided flow: version info -> readiness check -> changelog -> decompose -> preview -> confirm.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext

from ..base import BaseWizard, StepType, WizardConfig, WizardStep
from ..session import WizardSession


def _wants_changelog(session: WizardSession) -> bool:
    """Check if the user wants a changelog entry generated.

    Args:
        session: Current wizard session.

    Returns:
        True if user selected changelog generation.
    """
    answer = session.get("generate_changelog", "Yes")
    return str(answer).lower() in ("yes", "true")


class ReleasePrepWizard(BaseWizard):
    """Guided release preparation wizard.

    Steps:
        1. Version and options (QUESTION)
        2. Release readiness check (LLM_CALL with release-prep template)
        3. Generate changelog (LLM_CALL, conditional on question)
        4. Decompose release tasks (TASK_DECOMPOSE)
        5. Preview release checklist (PREVIEW)
        6. Confirm release (CONFIRM)
    """

    config = WizardConfig(
        wizard_id="release-prep",
        name="Release Preparation Wizard",
        description="Guided release readiness check and preparation",
        domain="release",
        estimated_cost_range=(0.03, 0.40),
        estimated_duration_minutes=8,
    )

    steps = [
        WizardStep(
            id="gather_info",
            name="Release Details",
            description="Define the release parameters",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="version_type",
                    text="What type of version bump?",
                    type=QuestionType.SINGLE_SELECT,
                    options=[
                        "Patch (bug fixes)",
                        "Minor (new features)",
                        "Major (breaking changes)",
                    ],
                    default="Patch (bug fixes)",
                ),
                FormQuestion(
                    id="run_tests",
                    text="Run full test suite as part of readiness check?",
                    type=QuestionType.BOOLEAN,
                    default="Yes",
                ),
                FormQuestion(
                    id="generate_changelog",
                    text="Auto-generate changelog entry from recent commits?",
                    type=QuestionType.BOOLEAN,
                    default="Yes",
                ),
            ],
        ),
        WizardStep(
            id="readiness_check",
            name="Readiness Check",
            description="Assess release readiness (tests, coverage, quality, security)",
            step_type=StepType.LLM_CALL,
            prompt_template="release-prep",
            tier="capable",
        ),
        WizardStep(
            id="changelog",
            name="Generate Changelog",
            description="Draft changelog entry from recent commits",
            step_type=StepType.LLM_CALL,
            prompt_template="doc-gen",
            tier="capable",
            condition=_wants_changelog,
        ),
        WizardStep(
            id="decompose_release",
            name="Release Tasks",
            description="Create release task checklist",
            step_type=StepType.TASK_DECOMPOSE,
            tier="capable",
        ),
        WizardStep(
            id="preview",
            name="Review Checklist",
            description="Review the release readiness report and task list",
            step_type=StepType.PREVIEW,
        ),
        WizardStep(
            id="confirm",
            name="Confirm Release",
            description="Proceed with the release?",
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

        if step.id == "readiness_check":
            version_type = self._session.get("version_type", "Patch")
            run_tests = self._session.get("run_tests", "Yes")

            return PromptContext(
                role="release engineer",
                goal=f"Assess readiness for a {version_type.lower()} release",
                instructions=[
                    "Check test suite status and coverage",
                    "Review open security issues",
                    "Verify code quality (linting, type checking)",
                    "Check documentation currency",
                    "Assess changelog completeness",
                ],
                constraints=[
                    "Report blockers vs warnings",
                    "Include pass/fail for each check",
                    "Be conservative -- flag uncertain items as warnings",
                ],
                input_type="release_request",
                input_payload=f"Version type: {version_type}\nRun tests: {run_tests}",
            )

        if step.id == "changelog":
            return PromptContext(
                role="technical writer",
                goal="Draft a changelog entry from recent git commits",
                instructions=[
                    "Group changes by category: Added, Changed, Fixed, Removed",
                    "Use imperative mood (e.g. 'Add feature' not 'Added feature')",
                    "Include PR/issue references where available",
                    "Follow Keep a Changelog format",
                ],
                constraints=[
                    "Only include user-facing changes",
                    "Skip routine dependency updates unless security-related",
                ],
                input_type="changelog_request",
                input_payload="Generate changelog from recent commits",
            )

        if step.id == "decompose_release":
            readiness = self._session.step_results.get("readiness_check", {})
            version_type = self._session.get("version_type", "Patch")
            return PromptContext(
                role="release automation planner",
                goal=f"Create tasks for {version_type.lower()} release",
                instructions=[
                    "Include version bump task",
                    "Include changelog update task",
                    "Include git tag creation task",
                    "Include any blocker-fix tasks from readiness check",
                ],
                constraints=["Order by dependency"],
                input_type="readiness_report",
                input_payload=str(readiness),
            )

        return PromptContext(role="assistant", goal="Prepare release")

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Store readiness and changelog results in session.

        Args:
            step: The step that produced this result.
            result: Parsed LLM response.
        """
        assert self._session is not None
        if step.id == "readiness_check":
            self._session.set("readiness_report", result)
        elif step.id == "changelog":
            self._session.set("changelog_draft", result)
