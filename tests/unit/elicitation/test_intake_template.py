"""Intake template layer (workflow-intake-forms Phase 2a): the
structural-equality migration gate, ruled build-time boundaries,
and the template-less demand fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from attune.elicitation import fix_intake, spec_intake
from attune.elicitation.bridge import form_from_dict
from attune.elicitation.intake_template import (
    PROVIDERS,
    TEMPLATES,
    FieldSlot,
    FormTemplate,
    ProviderContext,
    TemplateError,
    build_form,
    intake_form,
    validate_template,
)

_CTX = ProviderContext(repo_root=Path("/nonexistent"))


# ---------------------------------------------------------------
# The migration gate: template output == the SHIPPED hand shapes
# (goldens below are copied verbatim from the deleted hand
# construction; structural equality, providers stubbed — D2).
# ---------------------------------------------------------------


def _hand_fix_form(scopes: list[str], probes: list[str]):
    fields = [
        {
            "id": "request",
            "text": "What should be fixed, in your words?",
            "type": "textarea",
            "required": True,
            "help_text": "Passed verbatim as the fix goal — no inference.",
        }
    ]
    if scopes:
        fields.append(
            {
                "id": "scope",
                "text": "Where must the diff stay confined (--scope)?",
                "type": "text_input",
                "required": True,
                "path_kind": "either",
                "path_options": scopes,
                "help_text": "Changed paths first — a fix usually lands where the change is.",
            }
        )
    else:
        fields.append(
            {
                "id": "scope",
                "text": "Where must the diff stay confined (--scope)?",
                "type": "text_input",
                "required": True,
                "path_kind": "either",
                "path_options": [],
                "help_text": "Changed paths first — a fix usually lands where the change is.",
            }
        )
    if probes:
        fields.append(
            {
                "id": "probes",
                "text": "How do we verify the fix (--probe)?",
                "type": "multi_select",
                "options": probes,
                "help_text": "Each probe is verified independently in the receipt.",
            }
        )
    else:
        fields.append(
            {
                "id": "probes",
                "text": "How do we verify the fix? (one command, e.g. pytest tests/x.py)",
                "type": "text_input",
                "required": True,
            }
        )
    return form_from_dict(
        {
            "title": "Fix intake",
            "description": "Compose an outcome-first fix: goal, scope, verification.",
            "fields": fields,
        }
    )


@pytest.mark.parametrize(
    ("scopes", "probes"),
    [
        (["src/pkg/mod.py", "src/pkg"], ["pytest tests/test_mod.py"]),
        ([], []),
        (["src/pkg"], []),
    ],
)
def test_fix_template_matches_shipped_hand_shape(scopes, probes) -> None:
    assert fix_intake.build_fix_intake_form(scopes, probes) == _hand_fix_form(scopes, probes)


def _hand_spec_form(areas: list[str]):
    fields = [
        {
            "id": "outcome",
            "text": "What should exist when this spec is done?",
            "type": "textarea",
            "required": True,
            "help_text": "One or two sentences — becomes the spec's outcome statement.",
        },
        {
            "id": "done_when",
            "text": "Done when? (acceptance criteria)",
            "type": "textarea",
            "required": True,
            "help_text": (
                "Cheap to write, expensive to skip — e.g. "
                "'PR merged green, regression test landed'."
            ),
        },
    ]
    if areas:
        fields.append(
            {
                "id": "area",
                "text": "Primary code area?",
                "type": "single_select",
                "options": [*areas, spec_intake.OTHER],
                "help_text": "Where most of the change lands — bounds the design conversation.",
            }
        )
    else:
        fields.append(
            {
                "id": "area",
                "text": "Primary code area? (path or name)",
                "type": "text_input",
                "required": True,
            }
        )
    fields.append(
        {
            "id": "slug",
            "text": "Spec slug (optional — leave blank to derive one)",
            "type": "text_input",
            "required": False,
            "help_text": "kebab-case directory name under docs/specs/.",
        }
    )
    return form_from_dict(
        {
            "title": "New spec intake",
            "description": "Frame the spec before brainstorming: outcome, acceptance, area.",
            "fields": fields,
        }
    )


@pytest.mark.parametrize("areas", [["src/attune/agents", "src/attune/ops"], []])
def test_spec_template_matches_shipped_hand_shape(areas) -> None:
    assert spec_intake.build_spec_intake_form(areas) == _hand_spec_form(areas)


# ---------------------------------------------------------------
# Ruled build-time boundaries
# ---------------------------------------------------------------


def test_unknown_provider_rejected() -> None:
    t = FormTemplate("T", "d", [FieldSlot(key="x", text="x?", provider="nope")])
    with pytest.raises(TemplateError, match="unknown provider"):
        validate_template(t)


def test_other_or_fallback_without_provider_rejected() -> None:
    t = FormTemplate("T", "d", [FieldSlot(key="x", text="x?", other="other")])
    with pytest.raises(TemplateError, match="require a provider"):
        validate_template(t)


@dataclass
class _FakeSchema:
    required_fields: dict
    optional_fields: dict


class _FakeWorkflow:
    input_schema = _FakeSchema(
        required_fields={"goal": str},
        optional_fields={"paths": list},
    )


def test_bound_template_tighten_only_and_list_rules(monkeypatch) -> None:
    import attune.workflows as workflows_pkg

    monkeypatch.setattr(workflows_pkg, "get_workflow", lambda name: _FakeWorkflow)
    loosened = FormTemplate(
        "T", "d", [FieldSlot(key="goal", text="g?", required=False)], workflow="fake"
    )
    with pytest.raises(TemplateError, match="tighten-only"):
        validate_template(loosened)
    unprovided_list = FormTemplate("T", "d", [FieldSlot(key="paths", text="p?")], workflow="fake")
    with pytest.raises(TemplateError, match="no provider"):
        validate_template(unprovided_list)
    tightened = FormTemplate(
        "T",
        "d",
        [FieldSlot(key="goal", text="g?", required=True)],
        workflow="fake",
    )
    validate_template(tightened)


# ---------------------------------------------------------------
# Overrides, prefill, and the template-less demand fallback
# ---------------------------------------------------------------


def test_override_bypasses_provider_and_provider_runs_otherwise() -> None:
    calls: list[str] = []

    def _prov(ctx: ProviderContext) -> list[str]:
        calls.append("ran")
        return ["a", "b"]

    PROVIDERS["_test_prov"] = _prov
    try:
        t = FormTemplate("T", "d", [FieldSlot(key="x", text="x?", provider="_test_prov")])
        overridden = build_form(t, _CTX, candidates_override={"x": ["z"]})
        assert overridden.questions[0].options == ["z"]
        assert calls == []
        live = build_form(t, _CTX)
        assert live.questions[0].options == ["a", "b"]
        assert calls == ["ran"]
    finally:
        del PROVIDERS["_test_prov"]


def test_prefill_is_exact_key_match_only() -> None:
    t = FormTemplate("T", "d", [FieldSlot(key="goal", text="g?")])
    ctx = ProviderContext(repo_root=Path("/nonexistent"), answered={"goal": "fix the boundary"})
    form = build_form(t, ctx)
    assert form.questions[0].default == "fix the boundary"
    unrelated = ProviderContext(repo_root=Path("/nonexistent"), answered={"goal_hint": "not this"})
    assert build_form(t, unrelated).questions[0].default is None


def test_template_less_intake_returns_none_and_marks_demand() -> None:
    assert "no-such-intake" not in TEMPLATES
    assert intake_form("no-such-intake", invocation_text="do a thing") is None


def test_cold_import_resolves_builtin_templates(tmp_path: Path) -> None:
    """Regression (2026-08-01): a process importing ONLY
    intake_template must still resolve 'fix' — registration is an
    import side effect of the intake modules, lazily ensured."""
    import subprocess
    import sys

    code = (
        "from attune.elicitation.intake_template import intake_form\n"
        "from pathlib import Path\n"
        "form = intake_form('fix', repo_root=Path('.'))\n"
        "assert form is not None, 'cold import lost builtin templates'\n"
        "print('cold-ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "cold-ok" in proc.stdout


def test_registered_intakes_resolve_via_intake_form(tmp_path: Path) -> None:
    form = intake_form("fix", repo_root=tmp_path)
    assert form is not None
    assert [q.id for q in form.questions] == ["request", "scope", "probes"]
    spec_form = intake_form("spec-intake", repo_root=tmp_path)
    assert spec_form is not None
    assert [q.id for q in spec_form.questions][0] == "outcome"
