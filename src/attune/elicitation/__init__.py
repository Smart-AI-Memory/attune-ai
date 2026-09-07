"""Declarative form → AskUserQuestion bridge (elicitation v1).

The substrate now lives in the standalone ``attune-forms`` package
(extracted 2026-08-12; this repo is its first consumer). This module
does three things:

1. **Aliases the legacy module paths** — ``attune.elicitation.bridge``,
   ``.widget``, ``.theme``, ``.elicitation_schema``, ``.template_store``,
   ``.reference_form``, ``.intake_template`` are the SAME module objects
   as their ``attune_forms`` counterparts (the ``os.path`` aliasing
   pattern), so imports, monkeypatching, and class identity behave
   exactly as before the extraction.
2. **Registers the host seams** — the workflow-schema resolver (backed
   by the workflow registry) and the template loader that imports the
   attune-specific intakes (fix, spec, workflow templates).
3. **Re-exports the public API** unchanged.

Public surface (unchanged):

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

import sys

import attune_forms.bridge as _bridge
import attune_forms.elicitation_schema as _elicitation_schema
import attune_forms.intake_template as _intake_template
import attune_forms.reference_form as _reference_form
import attune_forms.template_store as _template_store
import attune_forms.theme as _theme
import attune_forms.widget as _widget

for _name, _mod in {
    "bridge": _bridge,
    "elicitation_schema": _elicitation_schema,
    "intake_template": _intake_template,
    "reference_form": _reference_form,
    "template_store": _template_store,
    "theme": _theme,
    "widget": _widget,
}.items():
    sys.modules[f"{__name__}.{_name}"] = _mod

# The full os.path pattern needs BOTH bindings: the sys.modules entry
# (for `import attune.elicitation.bridge`) and the package ATTRIBUTE
# (for `attune.elicitation.bridge` access after `import
# attune.elicitation`) — a cached sys.modules alias alone is never
# bound as a parent attribute (caught live on the 3.10 CI lanes).
bridge = _bridge
elicitation_schema = _elicitation_schema
intake_template = _intake_template
reference_form = _reference_form
template_store = _template_store
theme = _theme
widget = _widget


def _workflow_schema_resolver(name: str):
    """Resolve a registry workflow's input schema for template binding."""
    from attune.workflows import get_workflow

    return getattr(get_workflow(name), "input_schema", None)


def _load_builtin_templates() -> None:
    """Import the attune intake modules (registration is an import
    side effect; re-import is a no-op)."""
    import attune.elicitation.fix_intake  # noqa: F401
    import attune.elicitation.spec_intake  # noqa: F401
    import attune.elicitation.workflow_templates  # noqa: F401


if _intake_template.WORKFLOW_SCHEMA_RESOLVER is None:
    _intake_template.WORKFLOW_SCHEMA_RESOLVER = _workflow_schema_resolver
if _load_builtin_templates not in _intake_template.TEMPLATE_LOADERS:
    _intake_template.TEMPLATE_LOADERS.append(_load_builtin_templates)

from attune_forms.bridge import (  # noqa: E402
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
from attune_forms.elicitation_schema import form_to_elicitation_schema  # noqa: E402
from attune_forms.reference_form import EXAMPLE_ANSWERS, REFERENCE_FORM  # noqa: E402
from attune_forms.template_store import form_from_template, list_templates  # noqa: E402
from attune_forms.widget import WIDGET_RESPONSE_MARKER, form_to_widget_html  # noqa: E402

from attune.elicitation.ask_payload import form_to_ask_payload  # noqa: E402
from attune.elicitation.surface_policy import (  # noqa: E402
    CapabilitySnapshot,
    SurfaceBinding,
    SurfaceContextStore,
    select_surface,
)

__all__ = [
    "CapabilitySnapshot",
    "SurfaceBinding",
    "SurfaceContextStore",
    "select_surface",
    "EXAMPLE_ANSWERS",
    "REFERENCE_FORM",
    "WIDGET_RESPONSE_MARKER",
    "FormValidationError",
    "collect_form_response",
    "form_from_dict",
    "form_from_template",
    "form_response_summary",
    "form_to_ask_payload",
    "form_to_askuserquestion",
    "form_to_elicitation_schema",
    "form_to_widget_html",
    "inferred_field_count",
    "is_fully_inferred",
    "is_trivial_form",
    "keyboard_mode_enabled",
    "list_templates",
    "needs_widget",
    "select_form_surface",
    "set_keyboard_mode",
]
