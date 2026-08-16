"""Tests for per-control CSS family emission in ``form_to_widget_html``.

The widget ships CSS only for the control families a form actually uses
(``_needed_css``). The load-bearing invariant is **coverage**: every
class a control renders must have a matching selector in the emitted
``<style>``. ``test_every_control_types_classes_are_styled`` renders each
control branch and asserts no class is left unstyled — so a new control
(or a family-mapping slip) that drops a needed rule fails CI instead of
shipping an unstyled form.
"""

from __future__ import annotations

import re

import pytest

from attune.elicitation import form_from_dict, form_to_widget_html
from attune.elicitation.widget import _CSS_FAMILIES, _families_for
from attune.meta_workflows.models import QuestionType

_CLASS_RE = re.compile(r'class="([^"]*)"')

#: One minimal valid form per render branch (keyed by a readable label).
_FORMS: dict[str, dict] = {
    "text_input": {"id": "t", "type": "text_input", "text": "t"},
    "textarea": {"id": "t", "type": "textarea", "text": "t"},
    "number": {"id": "n", "type": "number", "text": "n", "minimum": 0},
    "date": {"id": "d", "type": "date", "text": "d"},
    "boolean": {"id": "b", "type": "boolean", "text": "b"},
    "single_select": {"id": "s", "type": "single_select", "text": "s", "options": ["a", "b"]},
    "single_select_list": {
        "id": "s",
        "type": "single_select",
        "text": "s",
        "options": ["a", "b"],
        "list_style": "unordered",
    },
    "multi_select": {"id": "m", "type": "multi_select", "text": "m", "options": ["a", "b"]},
    "multi_select_list": {
        "id": "m",
        "type": "multi_select",
        "text": "m",
        "options": ["a", "b"],
        "list_style": "ordered",
    },
    "decision": {
        "id": "x",
        "type": "decision",
        "text": "x",
        "options": ["a", "b"],
        "recommended": "a",
        "rationale": "why",
    },
    "pushback": {
        "id": "x",
        "type": "pushback",
        "text": "x",
        "options": ["a", "b"],
        "user_position": "a",
        "recommended": "b",
    },
    "progress": {
        "id": "p",
        "type": "progress",
        "text": "p",
        "options": ["X"],
        "progress_items": [{"label": "D", "status": "done"}, {"label": "X", "status": "blocked"}],
    },
    "progress_report": {
        "id": "p",
        "type": "progress",
        "text": "p",
        "progress_style": "report",
        "options": ["A"],
        "progress_items": [{"label": "A", "status": "note"}],
    },
    "deliberation": {
        "id": "d",
        "type": "deliberation",
        "text": "d",
        "options": ["a", "b"],
        "endorsements": {"a": ["claude", "codex"], "b": ["antigravity"]},
        "recommended": "a",
        "rationale": "why",
    },
    "triage": {
        "id": "g",
        "type": "triage",
        "text": "g",
        "triage_items": [
            {"id": "i1", "label": "Item one", "tag": "high", "detail": "ctx"},
            {"label": "Item two"},
        ],
        "dispositions": ["keep", "drop"],
        "suggested": {"i1": "keep"},
    },
    "confirm": {
        "id": "c",
        "type": "confirm",
        "text": "c",
        "consequences": [
            {"label": "Tag pushed", "severity": "irreversible", "detail": "v1"},
            {"label": "Docs promote"},
        ],
    },
    "ranking": {
        "id": "r",
        "type": "ranking",
        "text": "r",
        "options": ["a", "b", "c"],
        "top_n": 2,
        "suggested": ["b", "a"],
    },
    "assumption_review": {
        "id": "ar",
        "type": "assumption_review",
        "text": "ar",
        "assumptions": [
            {"id": "a1", "label": "Assumed one", "source": "README", "detail": "ctx"},
            {"label": "Assumed two"},
        ],
        "suggested": {"a1": "accept"},
    },
}


def _split(html: str) -> tuple[str, str]:
    """Return ``(style_block, body)`` — body is between </style> and <script>."""
    style = html.split("<style>")[1].split("</style>")[0]
    body = html.split("</style>")[1].split("<script>")[0]
    return style, body


def _emitted_classes(body: str) -> set[str]:
    classes: set[str] = set()
    for match in _CLASS_RE.finditer(body):
        classes.update(match.group(1).split())
    return {c for c in classes if c.startswith("ae-") or c == "sr-only"}


def _is_styled(style: str, cls: str) -> bool:
    return any(token in style for token in (f".{cls} ", f".{cls}{{", f".{cls}:"))


@pytest.mark.parametrize("label", sorted(_FORMS))
def test_every_control_types_classes_are_styled(label: str) -> None:
    """No control may emit a class the trimmed CSS doesn't define."""
    html = form_to_widget_html(form_from_dict({"title": "t", "fields": [_FORMS[label]]}))
    style, body = _split(html)
    unstyled = [c for c in _emitted_classes(body) if not _is_styled(style, c)]
    assert not unstyled, f"{label}: classes with no CSS: {unstyled}"


def test_base_shell_classes_always_present() -> None:
    """Shell classes render for every form, whatever its controls."""
    html = form_to_widget_html(
        form_from_dict({"title": "t", "fields": [_FORMS["text_input"]]}), message="hi"
    )
    style, _ = _split(html)
    for cls in ("sr-only", "ae-field", "ae-label", "ae-submit", "ae-error", "ae-msg"):
        assert _is_styled(style, cls)


def test_trimming_actually_drops_families() -> None:
    """A plain form must ship less CSS than one using cards + progress."""
    plain = form_to_widget_html(form_from_dict({"title": "t", "fields": [_FORMS["number"]]}))
    rich = form_to_widget_html(form_from_dict({"title": "t", "fields": [_FORMS["progress"]]}))
    assert len(_split(plain)[0]) < len(_split(rich)[0])
    # The plain form carries no card or progress rules.
    plain_style = _split(plain)[0]
    assert "ae-card" not in plain_style
    assert "ae-prog" not in plain_style


def test_families_for_returns_known_names() -> None:
    """Every QuestionType maps only to declared family names (drift guard).

    A new control routed to a mistyped or missing family fails here before
    it can ship an unstyled control.
    """
    known = {name for name, _ in _CSS_FAMILIES}
    for qtype in QuestionType:
        fields = {"id": "q", "type": qtype.value, "text": "q"}
        # Give constructs/selects the extra keys form_from_dict requires.
        if qtype in (QuestionType.SINGLE_SELECT, QuestionType.MULTI_SELECT):
            fields["options"] = ["a", "b"]
        elif qtype in (QuestionType.DECISION, QuestionType.PUSHBACK):
            fields.update(options=["a", "b"], recommended="a")
        elif qtype == QuestionType.PROGRESS:
            fields.update(options=["X"], progress_items=[{"label": "X", "status": "blocked"}])
        elif qtype == QuestionType.DELIBERATION:
            fields.update(options=["a", "b"], endorsements={"a": ["claude"]})
        elif qtype == QuestionType.TRIAGE:
            fields.update(triage_items=[{"label": "X"}], dispositions=["keep", "drop"])
        elif qtype == QuestionType.CONFIRM:
            fields.update(consequences=[{"label": "X"}])
        elif qtype == QuestionType.RANKING:
            fields.update(options=["a", "b"])
        elif qtype == QuestionType.ASSUMPTION_REVIEW:
            fields.update(assumptions=[{"label": "X"}])
        form = form_from_dict({"title": "t", "fields": [fields]})
        families = _families_for(form.questions[0])
        assert families, f"{qtype.value} maps to no family"
        assert families <= known, f"{qtype.value} maps to unknown family: {families - known}"
