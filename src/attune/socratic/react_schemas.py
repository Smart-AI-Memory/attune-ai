"""React Component Schemas for Socratic Web UI

Provides dataclass schemas for rendering Socratic forms, sessions,
and blueprints in React frontends.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .blueprint import WorkflowBlueprint
from .forms import FieldType, Form
from .session import SocraticSession


@dataclass
class ReactFormSchema:
    """Schema for rendering forms in React.

    Can be directly consumed by a React frontend to render
    the Socratic form with appropriate components.
    """

    form_id: str
    title: str
    description: str
    progress: float
    round_number: int
    is_final: bool
    fields: list[dict[str, Any]]
    categories: list[str]

    @classmethod
    def from_form(cls, form: Form) -> ReactFormSchema:
        """Create schema from a Form object."""
        fields = []

        for f in form.fields:
            field_schema = {
                "id": f.id,
                "type": _field_type_to_component(f.field_type),
                "label": f.label,
                "helpText": f.help_text,
                "placeholder": f.placeholder,
                "default": f.default,
                "category": f.category,
                "required": f.validation.required,
                "validation": {
                    "minLength": f.validation.min_length,
                    "maxLength": f.validation.max_length,
                    "minValue": f.validation.min_value,
                    "maxValue": f.validation.max_value,
                    "pattern": f.validation.pattern,
                },
                "showWhen": f.show_when,
                "options": (
                    [
                        {
                            "value": o.value,
                            "label": o.label,
                            "description": o.description,
                            "icon": o.icon,
                            "recommended": o.recommended,
                        }
                        for o in f.options
                    ]
                    if f.options
                    else None
                ),
            }
            fields.append(field_schema)

        return cls(
            form_id=form.id,
            title=form.title,
            description=form.description,
            progress=form.progress,
            round_number=form.round_number,
            is_final=form.is_final,
            fields=fields,
            categories=form.categories or list(dict.fromkeys(f.category for f in form.fields)),
        )

    def to_json(self) -> str:
        """Serialize to JSON for API response."""
        return json.dumps(asdict(self), indent=2)


def _field_type_to_component(field_type: FieldType) -> str:
    """Map FieldType to React component name."""
    mapping = {
        FieldType.SINGLE_SELECT: "RadioGroup",
        FieldType.MULTI_SELECT: "CheckboxGroup",
        FieldType.TEXT: "TextInput",
        FieldType.TEXT_AREA: "TextArea",
        FieldType.SLIDER: "Slider",
        FieldType.BOOLEAN: "Switch",
        FieldType.NUMBER: "NumberInput",
        FieldType.GROUP: "FieldGroup",
    }
    return mapping.get(field_type, "TextInput")


@dataclass
class ReactSessionSchema:
    """Schema for session state in React."""

    session_id: str
    state: str
    goal: str
    domain: str | None
    confidence: float
    current_round: int
    requirements_completeness: float
    ready_to_generate: bool
    ambiguities: list[str]
    assumptions: list[str]

    @classmethod
    def from_session(cls, session: SocraticSession) -> ReactSessionSchema:
        """Create schema from a SocraticSession."""
        return cls(
            session_id=session.session_id,
            state=session.state.value,
            goal=session.goal,
            domain=session.goal_analysis.domain if session.goal_analysis else None,
            confidence=session.goal_analysis.confidence if session.goal_analysis else 0,
            current_round=session.current_round,
            requirements_completeness=session.requirements.completeness_score(),
            ready_to_generate=session.can_generate(),
            ambiguities=session.goal_analysis.ambiguities if session.goal_analysis else [],
            assumptions=session.goal_analysis.assumptions if session.goal_analysis else [],
        )

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), indent=2)


@dataclass
class ReactBlueprintSchema:
    """Schema for blueprint display in React."""

    id: str
    name: str
    description: str
    domain: str
    languages: list[str]
    quality_focus: list[str]
    automation_level: str
    agents: list[dict[str, Any]]
    stages: list[dict[str, Any]]
    success_criteria: dict[str, Any] | None

    @classmethod
    def from_blueprint(cls, blueprint: WorkflowBlueprint) -> ReactBlueprintSchema:
        """Create schema from a WorkflowBlueprint."""
        agents = []
        for agent in blueprint.agents:
            agents.append(
                {
                    "id": agent.spec.id,
                    "name": agent.spec.name,
                    "role": agent.spec.role.value,
                    "goal": agent.spec.goal,
                    "backstory": (
                        agent.spec.backstory[:200] + "..."
                        if len(agent.spec.backstory) > 200
                        else agent.spec.backstory
                    ),
                    "modelTier": agent.spec.model_tier,
                    "tools": [t.name for t in agent.spec.tools],
                }
            )

        stages = []
        for stage in blueprint.stages:
            stages.append(
                {
                    "id": stage.id,
                    "name": stage.name,
                    "description": stage.description,
                    "agents": stage.agent_ids,
                    "parallel": stage.parallel,
                    "dependsOn": stage.depends_on,
                }
            )

        success_criteria = None
        if blueprint.success_criteria:
            success_criteria = blueprint.success_criteria.to_dict()

        return cls(
            id=blueprint.id,
            name=blueprint.name,
            description=blueprint.description,
            domain=blueprint.domain,
            languages=blueprint.supported_languages,
            quality_focus=blueprint.quality_focus,
            automation_level=blueprint.automation_level,
            agents=agents,
            stages=stages,
            success_criteria=success_criteria,
        )

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), indent=2)
