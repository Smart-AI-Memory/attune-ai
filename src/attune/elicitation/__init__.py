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
- :func:`select_form_surface` — the surface router (D21): the widget is
  the default; ``AskUserQuestion`` is the explicit fallback, taken only
  for a non-widget client, keyboard mode, or a trivial form.
- :func:`is_trivial_form` — the narrow, mechanical triviality test the
  router uses.
- :func:`is_fully_inferred` / :func:`inferred_field_count` — inference
  state. A fully-inferred form renders as a one-tap confirmation rather
  than a question, and is never silently skipped.
- :func:`keyboard_mode_enabled` — the user's terse/keyboard opt-out
  (D17), persisted per project in ``attune.config.json`` with
  ``ATTUNE_KEYBOARD_MODE`` as a session override.
- :func:`set_keyboard_mode` — persist that preference (what
  ``attune config set keyboard_mode`` calls).
- :func:`needs_widget` — low-level *controls* check: True iff a form
  loses fidelity on ``AskUserQuestion``. No longer owns the surface
  decision — prefer :func:`select_form_surface`.
- :func:`form_response_summary` — collapse an answered form to a
  compact markdown summary, so a long session accumulates a few lines
  per ask instead of a screenful of markup.
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
    form_response_summary,
    form_to_askuserquestion,
    inferred_field_count,
    is_fully_inferred,
    is_trivial_form,
    keyboard_mode_enabled,
    needs_widget,
    select_form_surface,
    set_keyboard_mode,
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
    "form_response_summary",
    "form_to_askuserquestion",
    "form_to_elicitation_schema",
    "form_to_widget_html",
    "inferred_field_count",
    "is_fully_inferred",
    "is_trivial_form",
    "keyboard_mode_enabled",
    "needs_widget",
    "select_form_surface",
    "set_keyboard_mode",
]
