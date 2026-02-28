"""API Endpoint Helpers for Socratic Web UI

Provides standard API response formatting and helper functions
for creating responses from sessions, forms, and blueprints.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .blueprint import WorkflowBlueprint
from .forms import Form
from .react_schemas import ReactBlueprintSchema, ReactFormSchema, ReactSessionSchema
from .session import SocraticSession


@dataclass
class APIResponse:
    """Standard API response format."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    next_action: str | None = None  # "continue", "generate", "complete"

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), indent=2)


def create_form_response(
    session: SocraticSession,
    form: Form | None,
    builder: Any,  # SocraticWorkflowBuilder
) -> APIResponse:
    """Create API response for form request.

    Args:
        session: Current session
        form: Form to display (or None if ready to generate)
        builder: SocraticWorkflowBuilder instance

    Returns:
        APIResponse with form data or generation prompt

    """
    session_schema = ReactSessionSchema.from_session(session)

    if form:
        form_schema = ReactFormSchema.from_form(form)
        return APIResponse(
            success=True,
            data={
                "session": asdict(session_schema),
                "form": asdict(form_schema),
            },
            next_action="continue",
        )
    if builder.is_ready_to_generate(session):
        return APIResponse(
            success=True,
            data={
                "session": asdict(session_schema),
                "message": "Ready to generate workflow",
            },
            next_action="generate",
        )
    return APIResponse(
        success=False,
        error="Unable to determine next step",
    )


def create_blueprint_response(
    blueprint: WorkflowBlueprint,
    session: SocraticSession,
) -> APIResponse:
    """Create API response for generated blueprint.

    Args:
        blueprint: Generated blueprint
        session: Source session

    Returns:
        APIResponse with blueprint data

    """
    blueprint_schema = ReactBlueprintSchema.from_blueprint(blueprint)
    session_schema = ReactSessionSchema.from_session(session)

    return APIResponse(
        success=True,
        data={
            "session": asdict(session_schema),
            "blueprint": asdict(blueprint_schema),
        },
        next_action="complete",
    )
