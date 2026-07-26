"""Tests for inference-first forms — prefilled values marked as guesses.

The premise: ceremony isn't caused by forms being rich, it's caused by
being asked things you already answered. A form that arrives with fields
filled in from context turns a three-dimension ask into a confirmation.

The risk that creates is the opposite one — a wrong guess accepted
because it looked settled. So the guarantees under test are:

1. An inferred value is always VISIBLY a guess, on every surface.
2. A fully-inferred form is still RENDERED (as a confirmation), never
   silently skipped — chair-ruled 2026-07-25.
3. An inference without a value is a definition error, so a "guessed"
   badge can never appear over an empty control.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    FormValidationError,
    form_from_dict,
    form_to_askuserquestion,
    form_to_widget_html,
    inferred_field_count,
    is_fully_inferred,
)

_INFERRED = {
    "id": "scope",
    "type": "single_select",
    "text": "Which path?",
    "options": ["src", "tests"],
    "default": "src",
    "inferred_from": "you have been editing src/",
}
_PLAIN = {"id": "depth", "type": "single_select", "text": "Depth?", "options": ["quick", "deep"]}
_INFERRED_2 = {**_PLAIN, "default": "deep", "inferred_from": "you asked for a thorough pass"}


def _form(fields: list[dict]) -> object:
    return form_from_dict({"title": "Scope this work", "fields": fields})


@pytest.fixture(autouse=True)
def _isolate_telemetry(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))


# --------------------------------------------------------------------
# definition validation
# --------------------------------------------------------------------


def test_inferred_from_parses() -> None:
    form = _form([_INFERRED])
    assert form.questions[0].inferred_from == "you have been editing src/"


def test_inference_without_a_value_is_rejected() -> None:
    """A guess with no value can't be rendered honestly — reject it."""
    with pytest.raises(FormValidationError, match="requires 'default'"):
        _form([{"id": "a", "type": "boolean", "text": "Proceed?", "inferred_from": "vibes"}])


@pytest.mark.parametrize("bad", ["", "   ", 42, []])
def test_inferred_from_must_be_a_non_empty_string(bad: object) -> None:
    with pytest.raises(FormValidationError, match="non-empty string"):
        _form([{**_INFERRED, "inferred_from": bad}])


def test_plain_default_is_not_an_inference() -> None:
    """A static suggestion is not a guess and must not be badged as one."""
    form = _form([{**_PLAIN, "default": "quick"}])
    assert form.questions[0].inferred_from is None
    assert inferred_field_count(form) == 0


# --------------------------------------------------------------------
# is_fully_inferred — what drives confirmation mode
# --------------------------------------------------------------------


def test_fully_inferred_only_when_every_field_is() -> None:
    assert is_fully_inferred(_form([_INFERRED, _INFERRED_2])) is True
    assert is_fully_inferred(_form([_INFERRED, _PLAIN])) is False
    assert is_fully_inferred(_form([_PLAIN])) is False


def test_empty_form_is_not_fully_inferred() -> None:
    """Nothing to confirm is not the same as everything confirmed.

    `form_from_dict` rejects an empty field list, so this state is only
    reachable by direct construction — but `all([])` is True, so without
    the guard an empty form would claim to be fully inferred and render
    a confirmation with nothing in it.
    """
    from attune.meta_workflows.models import FormSchema

    assert is_fully_inferred(FormSchema(title="T", description="", questions=[])) is False


def test_inferred_field_count() -> None:
    assert inferred_field_count(_form([_INFERRED, _PLAIN])) == 1
    assert inferred_field_count(_form([_INFERRED, _INFERRED_2])) == 2


# --------------------------------------------------------------------
# the widget — a guess must LOOK like a guess
# --------------------------------------------------------------------


def test_inferred_field_is_visibly_badged() -> None:
    html = form_to_widget_html(_form([_INFERRED, _PLAIN]))
    assert "ae-inferred-b" in html  # the badge
    assert "you have been editing src/" in html  # the provenance, shown
    assert html.count('data-inferred="1"') == 1  # only the inferred field


def test_uninferred_form_carries_no_badge() -> None:
    html = form_to_widget_html(_form([_PLAIN]))
    assert 'data-inferred="1"' not in html
    assert "you have been editing" not in html


def test_fully_inferred_renders_as_a_confirmation() -> None:
    """Chair-ruled: render, don't skip. The framing must say so."""
    html = form_to_widget_html(_form([_INFERRED, _INFERRED_2]))
    assert "filled in from" in html  # the confirmation banner
    assert ">Confirm</button>" in html
    assert ">Submit</button>" not in html


def test_partially_inferred_is_still_a_question() -> None:
    html = form_to_widget_html(_form([_INFERRED, _PLAIN]))
    assert "filled in from" not in html
    assert ">Submit</button>" in html


def test_fully_inferred_fields_remain_editable() -> None:
    """A confirmation the user cannot correct is just a silent guess."""
    html = form_to_widget_html(_form([_INFERRED, _INFERRED_2]))
    assert html.count("data-control") >= 2


# --------------------------------------------------------------------
# the fallback surface must not lose the signal
# --------------------------------------------------------------------


def test_askuserquestion_fallback_carries_the_guess() -> None:
    payloads = [q for batch in form_to_askuserquestion(_form([_INFERRED])) for q in batch]
    assert "Guessed: src" in payloads[0]["help_text"]
    assert "you have been editing src/" in payloads[0]["help_text"]


def test_fallback_preserves_existing_help_text() -> None:
    form = _form([{**_INFERRED, "help_text": "Pick a module."}])
    payload = form_to_askuserquestion(form)[0][0]
    assert payload["help_text"].startswith("Pick a module.")
    assert "Guessed: src" in payload["help_text"]


def test_fallback_help_text_untouched_without_inference() -> None:
    form = _form([{**_PLAIN, "help_text": "Pick a depth."}])
    assert form_to_askuserquestion(form)[0][0]["help_text"] == "Pick a depth."


# --------------------------------------------------------------------
# the decay guard
# --------------------------------------------------------------------


def test_inference_rate_measures_what_actually_happened() -> None:
    """Inference-first is prompt discipline; this is how we know it fired."""
    from attune.elicitation import select_form_surface
    from attune.telemetry.form_events import inference_rate

    select_form_surface(_form([_INFERRED, _PLAIN]))  # 1 of 2
    select_form_surface(_form([_INFERRED, _INFERRED_2]))  # 2 of 2, fully
    select_form_surface(_form([_PLAIN]))  # 0 of 1

    rate = inference_rate()
    assert rate["forms"] == 3
    assert rate["fields"] == 5
    assert rate["fields_inferred"] == 3
    assert rate["fully_inferred"] == 1
    assert rate["inferred_share"] == 0.6


def test_inference_rate_is_zero_not_an_error_when_nothing_logged() -> None:
    from attune.telemetry.form_events import inference_rate

    assert inference_rate()["forms"] == 0
    assert inference_rate()["inferred_share"] == 0.0
