"""Intake templates — generated forms from declarative slots (Phase 2).

workflow-intake-forms Phase 2a, chair-ruled 2026-07-31 (spec
decisions.md D2, roundtable `q-intake-forms-phase2-design-001`):
one declarative :class:`FormTemplate` per intake replaces the
hand-written form-building modules. The template layer OWNS form
construction; candidate derivation stays in plain provider
callables; rendering and validation stay in the substrate
(`form_from_dict`, `select_form_surface`) unchanged.

Ruled boundaries (do not drift):

- **Tighten-only:** a slot may require a schema-optional field;
  a schema-REQUIRED field rendered optional rejects at build time.
- **`list` without a provider rejects at build time** — nothing
  guesses candidates.
- **Prefill is exact-match only** (a value already present in
  ``ProviderContext.answered`` under the slot's key) — never
  heuristic, never an LLM.
- **Template-less workflows get NO generated form** in v1:
  :func:`intake_form` returns ``None`` (caller falls back to a
  free-text ask) and emits the demand-telemetry marker — the
  chair-ruled merge of the table's 2-1 split.
- **Cache-free v1**: providers run inline every time; caching
  arrives only with a Phase 3 measured budget miss.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from attune.elicitation.bridge import form_from_dict
from attune.meta_workflows.models import FormSchema

logger = structlog.get_logger(__name__)

#: Candidate providers by name: plain callables, no entry points,
#: no plugins (H3-no-parallel-framework).
PROVIDERS: dict[str, Callable[[ProviderContext], list[str]]] = {}


@dataclass
class ProviderContext:
    """What a candidate provider may read — nothing else.

    ``answered`` carries already-collected fields (exact-match
    prefill and future inter-field candidates); ``invocation_text``
    is the user's raw ask.
    """

    repo_root: Path
    invocation_text: str = ""
    answered: dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldSlot:
    """One form field, declaratively.

    ``provider`` names a :data:`PROVIDERS` entry whose candidates
    become the options; with no candidates the slot degrades to a
    required free-text input (``fallback_text`` or ``text``, help
    dropped) — the always-buildable rule the hand modules pinned.
    ``options`` is for static choice lists; ``other`` appends a
    free-text sentinel after provider candidates.
    """

    key: str
    text: str
    control: str | None = None
    provider: str | None = None
    options: list[str] | None = None
    other: str | None = None
    fallback_text: str | None = None
    help_text: str | None = None
    required: bool | None = None
    default: str | None = None


@dataclass
class FormTemplate:
    """A whole intake form, declaratively.

    ``workflow`` binds to a registry name for schema cross-checks;
    ``None`` is a standalone (skill) intake — the spec intake is
    one, so the binding is optional by design (recorded in the
    Phase 2 execution notes).
    """

    title: str
    description: str
    fields: list[FieldSlot]
    workflow: str | None = None


class TemplateError(ValueError):
    """A template violated a ruled build-time boundary."""


def validate_template(template: FormTemplate) -> None:
    """Build-time boundary checks (ruled; reject, never repair).

    Raises:
        TemplateError: tighten-only violated, a ``list``-typed
            schema field has no provider, an ``other`` sentinel or
            ``fallback_text`` appears without a provider, or a
            named provider is unregistered.
    """
    for slot in template.fields:
        if slot.provider is not None and slot.provider not in PROVIDERS:
            raise TemplateError(f"slot {slot.key!r}: unknown provider {slot.provider!r}")
        if slot.provider is None and (slot.other or slot.fallback_text):
            raise TemplateError(f"slot {slot.key!r}: 'other'/'fallback_text' require a provider")
    if template.workflow is None:
        return
    from attune.workflows import get_workflow

    workflow_cls = get_workflow(template.workflow)
    schema = getattr(workflow_cls, "input_schema", None)
    if schema is None:
        raise TemplateError(f"workflow {template.workflow!r} declares no input_schema")
    slot_by_key = {slot.key: slot for slot in template.fields}
    for key in schema.required_fields:
        slot = slot_by_key.get(key)
        if slot is not None and slot.required is False:
            raise TemplateError(
                f"slot {key!r}: schema-required field rendered optional (tighten-only)"
            )
    for key, py_type in {**schema.required_fields, **schema.optional_fields}.items():
        slot = slot_by_key.get(key)
        if slot is not None and py_type is list and slot.provider is None:
            raise TemplateError(
                f"slot {key!r}: list-typed field has no provider — rejected, not guessed"
            )


def _slot_field(
    slot: FieldSlot,
    ctx: ProviderContext,
    overrides: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Render one slot to a ``form_from_dict`` field dict.

    ``overrides`` supplies pre-derived candidates per slot key —
    the seam the hand-module delegations and the equality gate's
    stubbed-provider tests use (providers are NOT called for an
    overridden slot).
    """
    prefilled = ctx.answered.get(slot.key)
    base: dict[str, Any] = {"id": slot.key, "text": slot.text}
    if slot.help_text is not None:
        base["help_text"] = slot.help_text
    if slot.required is not None:
        base["required"] = slot.required
    if slot.default is not None:
        base["default"] = slot.default
    if prefilled is not None:
        base["default"] = str(prefilled)

    if slot.provider is not None:
        if overrides is not None and slot.key in overrides:
            candidates = overrides[slot.key]
        else:
            candidates = PROVIDERS[slot.provider](ctx)
        if candidates:
            base["type"] = slot.control or "single_select"
            base["options"] = [*candidates, slot.other] if slot.other else list(candidates)
            return base
        fallback = {
            "id": slot.key,
            "text": slot.fallback_text or slot.text,
            "type": "text_input",
            "required": True,
        }
        if slot.default is not None or prefilled is not None:
            fallback["default"] = base.get("default")
        return fallback

    if slot.options is not None:
        base["type"] = slot.control or "single_select"
        base["options"] = list(slot.options)
        return base

    base["type"] = slot.control or "text_input"
    return base


def build_form(
    template: FormTemplate,
    ctx: ProviderContext,
    candidates_override: dict[str, list[str]] | None = None,
) -> FormSchema:
    """Build the validated :class:`FormSchema` for a template."""
    validate_template(template)
    return form_from_dict(
        {
            "title": template.title,
            "description": template.description,
            "fields": [_slot_field(slot, ctx, candidates_override) for slot in template.fields],
        }
    )


#: In-tree templates by intake name (registry workflow names and
#: standalone skill-intake names share this namespace).
TEMPLATES: dict[str, FormTemplate] = {}


def intake_form(
    name: str,
    invocation_text: str = "",
    repo_root: Path | None = None,
    answered: dict[str, Any] | None = None,
) -> FormSchema | None:
    """Generate the intake form for ``name``, or ``None`` (ruled).

    ``None`` means no template exists: the caller falls back to a
    free-text ask — never an auto-derived form (chair merge ruling)
    — and the demand marker below is the telemetry that makes slot
    authoring demand-driven.
    """
    template = TEMPLATES.get(name)
    if template is None:
        logger.info(
            "intake_form.template_missing",
            intake=name,
            invocation_present=bool(invocation_text),
        )
        return None
    ctx = ProviderContext(
        repo_root=repo_root or Path.cwd(),
        invocation_text=invocation_text,
        answered=answered or {},
    )
    return build_form(template, ctx)
