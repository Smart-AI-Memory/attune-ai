"""Declarative form → MCP elicitation ``requestedSchema``.

The v2 lead surface (decision D8) is MCP native elicitation: the server
sends an ``elicitation/create`` request whose ``requestedSchema`` is a
flat object of primitive properties, and the client returns a structured,
keyed response that drops straight into
:func:`attune.elicitation.collect_form_response`.

This module holds the pure transform — the artifact's
:class:`~attune.meta_workflows.models.FormSchema` to that schema dict.
The live emit (``session.elicit_form``) lives in the MCP server; keeping
the transform here makes it fully unit-testable and surface-agnostic.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.meta_workflows.models import FormQuestion, FormSchema, QuestionType


def _property_for(question: FormQuestion) -> dict[str, Any]:
    """Build the elicitation schema property for one question.

    Maps each :class:`QuestionType` to the matching MCP elicitation
    primitive (flat object, primitives only — spec 2025-11-25).
    """
    prop: dict[str, Any] = {"title": question.text}

    if question.type in (
        QuestionType.SINGLE_SELECT,
        QuestionType.DECISION,
        QuestionType.PUSHBACK,
    ):
        prop.update(type="string", enum=list(question.options))
    elif question.type == QuestionType.MULTI_SELECT:
        prop.update(type="array", items={"type": "string", "enum": list(question.options)})
        if question.required:
            prop["minItems"] = 1
    elif question.type == QuestionType.BOOLEAN:
        prop["type"] = "boolean"
    elif question.type == QuestionType.NUMBER:
        prop["type"] = "number"
        if question.minimum is not None:
            prop["minimum"] = question.minimum
        if question.maximum is not None:
            prop["maximum"] = question.maximum
    elif question.type == QuestionType.DATE:
        prop.update(type="string", format="date")
    else:  # TEXT_INPUT, TEXTAREA
        prop["type"] = "string"
        if question.max_length is not None:
            prop["maxLength"] = question.max_length

    if question.help_text:
        prop["description"] = question.help_text
    if question.default is not None:
        prop["default"] = question.default
    return prop


def form_to_elicitation_schema(form: FormSchema) -> dict[str, Any]:
    """Map a :class:`FormSchema` to an MCP elicitation ``requestedSchema``.

    The result is a JSON-Schema object: ``{"type": "object",
    "properties": {field_id: <property>, ...}, "required": [...]}``, ready
    to pass to ``ServerSession.elicit_form``. The client's keyed
    ``content`` response maps straight back through
    :func:`collect_form_response` (the v1 validation seam).

    Args:
        form: The declarative form to render.

    Returns:
        The elicitation ``requestedSchema`` dict.
    """
    properties = {q.id: _property_for(q) for q in form.questions}
    required = [q.id for q in form.questions if q.required]
    return {"type": "object", "properties": properties, "required": required}
