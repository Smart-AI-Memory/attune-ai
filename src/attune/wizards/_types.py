"""Data types for the wizard framework.

Defines ``StepType``, ``WizardStep``, ``WizardConfig``, and
``WizardResult`` used by ``BaseWizard`` and its subclasses.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from attune.meta_workflows.models import FormQuestion

if TYPE_CHECKING:
    from .session import WizardSession


# =========================================================================
# Enums
# =========================================================================


class StepType(str, Enum):
    """Execution mode for a wizard step.

    Attributes:
        QUESTION: Interactive step that collects user input via AskUserQuestion.
        LLM_CALL: Calls an LLM with an XML prompt template.
        TASK_DECOMPOSE: Breaks a problem into structured XML sub-tasks.
        PREVIEW: Shows generated results and asks for approval.
        CONFIRM: Final yes/no gate before execution.
    """

    QUESTION = "question"
    LLM_CALL = "llm_call"
    TASK_DECOMPOSE = "task_decompose"
    PREVIEW = "preview"
    CONFIRM = "confirm"


# =========================================================================
# Data classes
# =========================================================================


@dataclass
class WizardStep:
    """Definition of a single wizard step.

    Args:
        id: Unique step identifier (e.g. ``"gather_context"``).
        name: Human-readable step name.
        description: What this step does.
        step_type: Determines how the step is executed.
        prompt_template: XML template name from the prompt registry,
            or ``None`` for question/preview/confirm steps.
        tier: Model tier for LLM steps (``"cheap"``, ``"capable"``, ``"premium"``).
        questions: ``FormQuestion`` list for ``QUESTION`` steps.
        condition: Optional callable; if it returns ``False`` the step is skipped.
        max_tokens: Maximum tokens for LLM response.
        prompt_context_template: Declarative prompt context for config-driven wizards.
            Keys: ``role``, ``goal``, ``instructions``, ``constraints``.
            Values may contain ``{session.var}`` placeholders.
    """

    id: str
    name: str
    description: str = ""
    step_type: StepType = StepType.QUESTION
    prompt_template: str | None = None
    tier: str = "capable"
    questions: list[FormQuestion] | None = None
    condition: Callable[[WizardSession], bool] | None = None
    max_tokens: int = 4096
    prompt_context_template: dict[str, Any] | None = None


@dataclass
class WizardConfig:
    """Metadata for a wizard.

    Args:
        wizard_id: Short identifier (e.g. ``"debug"``).
        name: Human-readable name (e.g. ``"Debugging Wizard"``).
        description: One-sentence description.
        domain: Category (e.g. ``"development"``).
        version: Semantic version.
        source: Origin of this wizard (``"builtin"`` or ``"custom"``).
        estimated_cost_range: Estimated USD cost range per run.
        estimated_duration_minutes: Estimated wall-clock minutes per run.
    """

    wizard_id: str
    name: str
    description: str
    domain: str = "development"
    version: str = "1.0.0"
    source: str = "builtin"
    estimated_cost_range: tuple[float, float] = (0.01, 0.50)
    estimated_duration_minutes: int = 5


@dataclass
class WizardResult:
    """Result from a completed wizard run.

    Args:
        wizard_id: Which wizard produced this result.
        run_id: Unique run identifier.
        success: Whether the wizard completed successfully.
        steps_completed: List of step IDs that ran.
        collected_data: All user-provided data from question steps.
        generated_output: Final output (text or structured dict).
        tasks: Decomposed XML tasks, if any.
        total_cost: Total LLM cost in USD.
        total_duration_ms: Wall-clock duration in milliseconds.
        error: Error message if ``success`` is ``False``.
    """

    wizard_id: str
    run_id: str
    success: bool
    steps_completed: list[str] = field(default_factory=list)
    collected_data: dict[str, Any] = field(default_factory=dict)
    generated_output: str | dict[str, Any] = ""
    tasks: list[dict[str, Any]] = field(default_factory=list)
    total_cost: float = 0.0
    total_duration_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict.

        Returns:
            Dict representation of this result.
        """
        return {
            "wizard_id": self.wizard_id,
            "run_id": self.run_id,
            "success": self.success,
            "steps_completed": self.steps_completed,
            "collected_data": self.collected_data,
            "generated_output": self.generated_output,
            "tasks": self.tasks,
            "total_cost": self.total_cost,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
        }
