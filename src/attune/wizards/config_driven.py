"""Config-driven wizard loaded from YAML definitions.

Allows users to create custom wizards without writing Python.
Wizard definitions are stored as YAML files in ``.attune/wizards/``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext
from attune.security.path_validation import _validate_file_path

from .base import BaseWizard, StepType, WizardConfig, WizardStep
from .session import WizardSession

logger = logging.getLogger(__name__)

# =========================================================================
# YAML schema version
# =========================================================================

SCHEMA_VERSION = "1.0"

# Valid step type strings → StepType enum
_STEP_TYPE_MAP = {
    "question": StepType.QUESTION,
    "llm_call": StepType.LLM_CALL,
    "task_decompose": StepType.TASK_DECOMPOSE,
    "review": StepType.REVIEW,
    "preview": StepType.PREVIEW,
    "confirm": StepType.CONFIRM,
}

# Valid question type strings → QuestionType enum
_QUESTION_TYPE_MAP = {
    "text_input": QuestionType.TEXT_INPUT,
    "single_select": QuestionType.SINGLE_SELECT,
    "boolean": QuestionType.BOOLEAN,
}


# =========================================================================
# Session variable interpolation
# =========================================================================

_SESSION_VAR_PATTERN = re.compile(r"\{session\.([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _interpolate_session_vars(text: str, session: WizardSession) -> str:
    """Replace ``{session.var_name}`` placeholders with session values.

    Only does key lookups on ``session.get()`` — never evaluates
    arbitrary expressions.

    Args:
        text: Template string with ``{session.xxx}`` placeholders.
        session: Current wizard session.

    Returns:
        String with placeholders replaced by session values.

    """

    def _replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        value = session.get(var_name, f"<{var_name}>")
        return str(value)

    return _SESSION_VAR_PATTERN.sub(_replacer, text)


def _interpolate_dict(data: dict[str, Any], session: WizardSession) -> dict[str, Any]:
    """Recursively interpolate session variables in a dict.

    Args:
        data: Dict with possible ``{session.xxx}`` placeholders in string values.
        session: Current wizard session.

    Returns:
        New dict with all string values interpolated.

    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _interpolate_session_vars(value, session)
        elif isinstance(value, list):
            result[key] = [
                _interpolate_session_vars(item, session) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, dict):
            result[key] = _interpolate_dict(value, session)
        else:
            result[key] = value
    return result


# =========================================================================
# ConfigDrivenWizard
# =========================================================================


class ConfigDrivenWizard(BaseWizard):
    """A wizard loaded from a YAML definition file.

    Custom wizards define their steps, questions, and prompt contexts
    declaratively in YAML. Session variable interpolation (``{session.xxx}``)
    allows dynamic prompt construction.

    Example YAML:

    .. code-block:: yaml

        schema_version: "1.0"
        wizard_id: "code-migration"
        name: "Code Migration Wizard"
        description: "Guide through migrating code between frameworks"
        domain: "development"

        steps:
          - id: "gather_info"
            name: "Migration Scope"
            step_type: "question"
            questions:
              - id: "source"
                text: "Migrating FROM which framework?"
                type: "text_input"
          - id: "analyze"
            step_type: "llm_call"
            tier: "capable"
            prompt_context:
              role: "migration specialist"
              goal: "Plan migration from {session.source}"
    """

    def __init__(self, config: WizardConfig, steps: list[WizardStep], **kwargs: Any) -> None:
        """Initialize a config-driven wizard.

        Args:
            config: Wizard metadata.
            steps: Step definitions (already parsed from YAML).
            **kwargs: Forwarded to ``BaseWizard.__init__``.

        """
        self.config = config
        self.steps = steps
        super().__init__(**kwargs)

    # -----------------------------------------------------------------
    # Factory: from YAML
    # -----------------------------------------------------------------

    @classmethod
    def from_yaml(cls, yaml_path: str, **kwargs: Any) -> ConfigDrivenWizard:
        """Load a wizard definition from a YAML file.

        Args:
            yaml_path: Path to the YAML definition file.
            **kwargs: Forwarded to ``__init__``.

        Returns:
            A ``ConfigDrivenWizard`` instance ready to run.

        Raises:
            ValueError: If the YAML is invalid or missing required fields.
            FileNotFoundError: If the file does not exist.

        """
        from attune.security.path_validation import _validate_file_path

        path = _validate_file_path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Wizard definition not found: {yaml_path}")

        with path.open() as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid wizard YAML: expected a mapping, got {type(data).__name__}")

        return cls._from_dict(data, **kwargs)

    @classmethod
    def _from_dict(cls, data: dict[str, Any], **kwargs: Any) -> ConfigDrivenWizard:
        """Build a wizard from a parsed YAML dict.

        Args:
            data: Parsed YAML data.
            **kwargs: Forwarded to ``__init__``.

        Returns:
            A ``ConfigDrivenWizard`` instance.

        Raises:
            ValueError: If required fields are missing or step types are invalid.

        """
        _validate_schema(data)

        config = WizardConfig(
            wizard_id=data["wizard_id"],
            name=data["name"],
            description=data.get("description", ""),
            domain=data.get("domain", "development"),
            version=data.get("version", "1.0.0"),
            source="custom",
            estimated_cost_range=tuple(data.get("estimated_cost_range", [0.01, 0.50])),
            estimated_duration_minutes=data.get("estimated_duration_minutes", 5),
        )

        steps = _parse_steps(data.get("steps", []))
        return cls(config=config, steps=steps, **kwargs)

    # -----------------------------------------------------------------
    # Serialization: to YAML
    # -----------------------------------------------------------------

    def to_yaml(self, output_path: str) -> Path:
        """Serialize this wizard's definition to a YAML file.

        Args:
            output_path: File path to write.

        Returns:
            Validated path where the file was written.

        Raises:
            ValueError: If the path is invalid or targets a system directory.

        """
        validated = _validate_file_path(output_path)

        data = self._to_dict()
        try:
            with validated.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        except PermissionError as e:
            logger.error("Permission denied writing wizard to %s: %s", validated, e)
            raise
        except OSError as e:
            logger.error("OS error writing wizard to %s: %s", validated, e)
            raise ValueError(f"Cannot write wizard YAML: {e}") from e

        return validated

    def _to_dict(self) -> dict[str, Any]:
        """Serialize wizard to a YAML-safe dict.

        Returns:
            Dict suitable for ``yaml.safe_dump()``.

        """
        steps_data = []
        for step in self.steps:
            step_dict: dict[str, Any] = {
                "id": step.id,
                "name": step.name,
                "step_type": step.step_type.value,
            }
            if step.description:
                step_dict["description"] = step.description
            if step.tier != "capable":
                step_dict["tier"] = step.tier
            if step.questions:
                step_dict["questions"] = [_question_to_dict(q) for q in step.questions]
            if step.prompt_context_template:
                step_dict["prompt_context"] = step.prompt_context_template
            steps_data.append(step_dict)

        return {
            "schema_version": SCHEMA_VERSION,
            "wizard_id": self.config.wizard_id,
            "name": self.config.name,
            "description": self.config.description,
            "domain": self.config.domain,
            "version": self.config.version,
            "estimated_cost_range": list(self.config.estimated_cost_range),
            "estimated_duration_minutes": self.config.estimated_duration_minutes,
            "steps": steps_data,
        }

    # -----------------------------------------------------------------
    # Abstract method implementations
    # -----------------------------------------------------------------

    def build_prompt_context(self, step: WizardStep) -> PromptContext:
        """Build prompt context from the step's declarative template.

        Interpolates ``{session.xxx}`` placeholders with current session values.

        Args:
            step: The current step.

        Returns:
            ``PromptContext`` for the LLM call.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")

        template = step.prompt_context_template
        if not template:
            return PromptContext(
                role="assistant",
                goal=f"Execute step: {step.name}",
            )

        interpolated = _interpolate_dict(template, self._session)

        return PromptContext(
            role=interpolated.get("role", "assistant"),
            goal=interpolated.get("goal", step.name),
            instructions=interpolated.get("instructions", []),
            constraints=interpolated.get("constraints", []),
            input_type=interpolated.get("input_type", ""),
            input_payload=interpolated.get("input_payload", ""),
        )

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Store results generically under the step ID.

        Args:
            step: The step that produced this result.
            result: Parsed LLM response.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        self._session.set(f"{step.id}_result", result)


# =========================================================================
# Schema validation
# =========================================================================


def _validate_schema(data: dict[str, Any]) -> None:
    """Validate a wizard YAML schema.

    Args:
        data: Parsed YAML data.

    Raises:
        ValueError: If required fields are missing or invalid.

    """
    required_fields = ["wizard_id", "name", "steps"]
    for field_name in required_fields:
        if field_name not in data:
            raise ValueError(f"Wizard YAML missing required field: '{field_name}'")

    if not isinstance(data["steps"], list) or not data["steps"]:
        raise ValueError("Wizard YAML 'steps' must be a non-empty list")

    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i} must be a mapping")
        if "id" not in step:
            raise ValueError(f"Step {i} missing required field: 'id'")
        step_type_str = step.get("step_type", "question")
        if step_type_str not in _STEP_TYPE_MAP:
            raise ValueError(
                f"Step '{step['id']}' has invalid step_type '{step_type_str}'. "
                f"Valid types: {list(_STEP_TYPE_MAP.keys())}",
            )


# =========================================================================
# Parsing helpers
# =========================================================================


def _parse_steps(steps_data: list[dict[str, Any]]) -> list[WizardStep]:
    """Parse step dicts from YAML into ``WizardStep`` objects.

    Args:
        steps_data: List of step dicts from YAML.

    Returns:
        List of ``WizardStep`` instances.

    """
    steps: list[WizardStep] = []
    for step_data in steps_data:
        step_type = _STEP_TYPE_MAP[step_data.get("step_type", "question")]

        questions = None
        if step_type == StepType.QUESTION and "questions" in step_data:
            questions = [_parse_question(q) for q in step_data["questions"]]

        prompt_context_template = step_data.get("prompt_context")

        steps.append(
            WizardStep(
                id=step_data["id"],
                name=step_data.get("name", step_data["id"]),
                description=step_data.get("description", ""),
                step_type=step_type,
                prompt_template=step_data.get("prompt_template"),
                tier=step_data.get("tier", "capable"),
                questions=questions,
                max_tokens=step_data.get("max_tokens", 4096),
                prompt_context_template=prompt_context_template,
                review_source_step_id=step_data.get("review_source_step_id"),
            ),
        )

    return steps


def _parse_question(q_data: dict[str, Any]) -> FormQuestion:
    """Parse a question dict from YAML into a ``FormQuestion``.

    Args:
        q_data: Question dict from YAML.

    Returns:
        ``FormQuestion`` instance.

    """
    q_type_str = q_data.get("type", "text_input")
    q_type = _QUESTION_TYPE_MAP.get(q_type_str, QuestionType.TEXT_INPUT)

    return FormQuestion(
        id=q_data["id"],
        text=q_data.get("text", ""),
        type=q_type,
        options=q_data.get("options"),
        default=q_data.get("default"),
        help_text=q_data.get("help_text"),
    )


def _question_to_dict(q: FormQuestion) -> dict[str, Any]:
    """Serialize a ``FormQuestion`` to a YAML-safe dict.

    Args:
        q: FormQuestion to serialize.

    Returns:
        Dict suitable for YAML output.

    """
    d: dict[str, Any] = {"id": q.id, "text": q.text, "type": q.type}
    if isinstance(q.type, QuestionType):
        d["type"] = q.type.value
    if q.options:
        d["options"] = q.options
    if q.default is not None:
        d["default"] = q.default
    if q.help_text:
        d["help_text"] = q.help_text
    return d
