"""Declarative form → AskUserQuestion bridge (elicitation v1).

The load-bearing core of the ``elicitation-form-surface`` spec (Option
B): it runs the salvaged, surface-agnostic ``FormSchema`` model
(:mod:`attune.meta_workflows.models`) against the live
``AskUserQuestion`` tool. These are pure transforms — no agent/tool
dependency — so they are fully testable, and they are the same seam a
future richer (v2) renderer plugs into.

Public surface:

- :func:`form_from_dict` — build the declarative artifact (D3) from
  plain serializable data.
- :func:`form_to_askuserquestion` — batched ``AskUserQuestion`` payloads
  (≤4 questions per call).
- :func:`collect_form_response` — validate raw answers (required +
  option membership) and map them into a ``FormResponse`` (R4 — never
  silently accept malformed input).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from attune.elicitation.bridge import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_askuserquestion,
)
from attune.elicitation.elicitation_schema import form_to_elicitation_schema
from attune.elicitation.reference_form import EXAMPLE_ANSWERS, REFERENCE_FORM
from attune.elicitation.widget import WIDGET_RESPONSE_MARKER, form_to_widget_html

__all__ = [
    "EXAMPLE_ANSWERS",
    "REFERENCE_FORM",
    "WIDGET_RESPONSE_MARKER",
    "FormValidationError",
    "collect_form_response",
    "form_from_dict",
    "form_to_askuserquestion",
    "form_to_elicitation_schema",
    "form_to_widget_html",
]
