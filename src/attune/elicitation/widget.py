"""Declarative-form → ``show_widget`` HTML renderer (elicitation v2 / S1).

The "escape hatch" surface from decision D8: render the SAME declarative
artifact (D3) as an inline HTML form for the ``mcp__visualize__show_widget``
tool. Unlike the AskUserQuestion bridge (v1) and native MCP elicitation
(v2 lead surface), this surface renders the v2.1 rich controls
(``number``/``date``/``textarea`` with real spinner/date-picker/multiline
widgets) and is the home for controls no other surface can express.

Return path (the S1-specific shape — D4/D8): the widget has no structured
callback, only the global ``sendPrompt(text)``. On submit it serializes the
answers to JSON inside a sentinel-marked message; the agent parses that and
re-uses the existing :func:`attune.elicitation.collect_form_response`
validation seam (R4). This module owns ONLY the pure
``FormSchema -> html`` transform — no agent or tool dependency — so it is
fully testable.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from html import escape

from attune.elicitation.bridge import is_fully_inferred
from attune.elicitation.theme import CSS_BASE as _CSS_BASE
from attune.elicitation.theme import CSS_FAMILIES as _CSS_FAMILIES
from attune.meta_workflows.models import FormQuestion, FormSchema, QuestionType

#: Sentinel key the submit payload carries so the agent can recognise a
#: form postback among ordinary chat messages and route it to
#: ``collect_form_response``. Kept in sync with the ``elicit`` skill.
WIDGET_RESPONSE_MARKER = "__elicitation_response__"

#: The Yes/No values a BOOLEAN control posts (``collect_form_response``
#: validates a boolean answer against exactly these).
_BOOLEAN_OPTIONS = ("Yes", "No")


def _esc(value: object) -> str:
    """HTML-escape a value for safe use in text or a quoted attribute."""
    return escape(str(value), quote=True)


def _list_html(q: FormQuestion, *, multi: bool) -> str:
    """Render select options as an ordered/unordered selectable list.

    A presentation variant of SINGLE_SELECT (radios) / MULTI_SELECT
    (checkboxes) used when ``q.list_style`` is set: the items render as
    ``<ol>``/``<ul>`` entries, each pickable by mouse or keyboard. The
    answer path is unchanged — the inputs still carry ``data-control`` and
    the submit script reads them the same way it reads any select.

    Args:
        q: The select question to render.
        multi: True for MULTI_SELECT (checkboxes), False for SINGLE_SELECT
            (radios).

    Returns:
        An HTML fragment for the list control.
    """
    tag = "ol" if q.list_style == "ordered" else "ul"
    input_type = "checkbox" if multi else "radio"
    name = "" if multi else f' name="{_esc(q.id)}"'
    role = "" if multi else ' role="radiogroup"'
    items = ""
    for opt in q.options:
        items += (
            f'<li class="ae-list-item"><label>'
            f'<input type="{input_type}"{name} data-control '
            f'value="{_esc(opt)}"{_checked(q, opt)}> '
            f"<span>{_esc(opt)}</span></label></li>"
        )
    return f'<{tag} class="ae-list"{role}>{items}</{tag}>'


def _ordered_options_recommended_first(q: FormQuestion) -> list[str]:
    """Return ``q.options`` with ``q.recommended`` moved to the front,
    when it names one of them. Shared by the three card-based renders
    (DECISION, PUSHBACK, PROGRESS report style).
    """
    ordered = list(q.options)
    if q.recommended and q.recommended in ordered:
        ordered = [q.recommended] + [o for o in ordered if o != q.recommended]
    return ordered


def _control_decision_html(q: FormQuestion) -> str:
    """Render a DECISION control: recommended-first cards with notes."""
    notes = q.option_notes or {}
    cards = ""
    for opt in _ordered_options_recommended_first(q):
        is_rec = opt == q.recommended
        badge = '<span class="ae-rec-badge">Recommended</span>' if is_rec else ""
        note = f'<span class="ae-card-note">{_esc(notes[opt])}</span>' if opt in notes else ""
        checked = " checked" if q.default == opt else ""
        cls = "ae-card ae-card-rec" if is_rec else "ae-card"
        cards += (
            f'<label class="{cls}">'
            f'<input type="radio" name="{_esc(q.id)}" data-control '
            f'value="{_esc(opt)}"{checked}>'
            f'{badge}<span class="ae-card-title">{_esc(opt)}</span>{note}</label>'
        )
    return f'<div class="ae-cards" role="radiogroup">{cards}</div>'


def _control_pushback_html(q: FormQuestion) -> str:
    """Render a PUSHBACK control.

    Dissent framing: the agent's alternative (``recommended``) is badged
    "I'd suggest instead" and ordered first; the user's stated approach
    (``user_position``) carries a muted "your approach" tag. Same radio
    answer path as DECISION.
    """
    notes = q.option_notes or {}
    cards = ""
    for opt in _ordered_options_recommended_first(q):
        is_rec = opt == q.recommended
        is_user = opt == q.user_position
        badge = '<span class="ae-rec-badge">I&#x27;d suggest instead</span>' if is_rec else ""
        tag = '<span class="ae-yours-tag">your approach</span>' if is_user else ""
        note = f'<span class="ae-card-note">{_esc(notes[opt])}</span>' if opt in notes else ""
        checked = " checked" if q.default == opt else ""
        cls = "ae-card ae-card-rec" if is_rec else "ae-card"
        cards += (
            f'<label class="{cls}">'
            f'<input type="radio" name="{_esc(q.id)}" data-control '
            f'value="{_esc(opt)}"{checked}>'
            f'{badge}{tag}<span class="ae-card-title">{_esc(opt)}</span>{note}</label>'
        )
    return f'<div class="ae-cards" role="radiogroup">{cards}</div>'


def _control_progress_report_html(q: FormQuestion) -> str:
    """Render PROGRESS in v5.1 "report" style: a neutral digest.

    Item status is a free-form category tag (no task semantics, no
    strikethrough); items named in options render as pickable "go
    deeper" cards, the rest as static tagged rows. Same radio answer
    path as the default style.
    """
    items = q.progress_items or []
    notes = q.option_notes or {}
    by_label = {it.get("label"): it for it in items}
    rows = ""
    for it in items:
        if it.get("label") in q.options:
            continue
        tag = f'<span class="ae-prog-tag">{_esc(it.get("status", ""))}</span>'
        detail = (
            f'<span class="ae-prog-detail">{_esc(it["detail"])}</span>' if it.get("detail") else ""
        )
        rows += (
            f'<div class="ae-prog-row ae-prog-report">'
            f'{tag}<span class="ae-prog-label">{_esc(it.get("label", ""))}</span>'
            f"{detail}</div>"
        )
    cards = ""
    for opt in _ordered_options_recommended_first(q):
        it = by_label.get(opt, {})
        is_rec = opt == q.recommended
        badge = '<span class="ae-rec-badge">suggested next</span>' if is_rec else ""
        tag = f'<span class="ae-prog-tag">{_esc(it.get("status", ""))}</span>'
        note_text = notes.get(opt) or it.get("detail")
        note = f'<span class="ae-card-note">{_esc(note_text)}</span>' if note_text else ""
        checked = " checked" if q.default == opt else ""
        cls = "ae-card ae-card-rec" if is_rec else "ae-card"
        cards += (
            f'<label class="{cls}">'
            f'<input type="radio" name="{_esc(q.id)}" data-control '
            f'value="{_esc(opt)}"{checked}>'
            f'{badge}{tag}<span class="ae-card-title">{_esc(opt)}</span>{note}</label>'
        )
    picker = (
        '<div class="ae-prog-blocked-h">Pick one to go deeper:</div>'
        f'<div class="ae-cards" role="radiogroup">{cards}</div>'
        if cards
        else ""
    )
    rows_html = f'<div class="ae-prog-rows">{rows}</div>' if rows else ""
    return f'<div class="ae-progress">{rows_html}{picker}</div>'


def _control_progress_html(q: FormQuestion) -> str:
    """Render PROGRESS in the default task style.

    Done/in_flight items render as static rows; the blocked items
    become the radiogroup picker (recommended first, "suggested next"
    badge). With no blocked items the picker is omitted and the
    control is a pure status display.
    """
    items = q.progress_items or []
    notes = q.option_notes or {}
    by_status: dict[str, list[dict[str, str]]] = {"done": [], "in_flight": [], "blocked": []}
    for it in items:
        st = it.get("status", "")
        if st in by_status:
            by_status[st].append(it)
    rows = ""
    for status_key, icon, sr in (("done", "✓", "done"), ("in_flight", "◐", "in progress")):
        for it in by_status[status_key]:
            detail = (
                f'<span class="ae-prog-detail">{_esc(it["detail"])}</span>'
                if it.get("detail")
                else ""
            )
            rows += (
                f'<div class="ae-prog-row ae-prog-{status_key}">'
                f'<span class="ae-prog-icon" aria-hidden="true">{icon}</span>'
                f'<span class="ae-prog-label">{_esc(it.get("label", ""))}</span>{detail}'
                f'<span class="sr-only"> ({sr})</span></div>'
            )
    detail_by_label = {it.get("label"): it.get("detail") for it in by_status["blocked"]}
    cards = ""
    for opt in _ordered_options_recommended_first(q):
        is_rec = opt == q.recommended
        badge = '<span class="ae-rec-badge">suggested next</span>' if is_rec else ""
        note_text = notes.get(opt) or detail_by_label.get(opt)
        note = f'<span class="ae-card-note">{_esc(note_text)}</span>' if note_text else ""
        checked = " checked" if q.default == opt else ""
        cls = "ae-card ae-card-rec" if is_rec else "ae-card"
        cards += (
            f'<label class="{cls}">'
            f'<input type="radio" name="{_esc(q.id)}" data-control '
            f'value="{_esc(opt)}"{checked}>'
            f'<span class="ae-prog-icon ae-prog-blocked" aria-hidden="true">✕</span>'
            f'{badge}<span class="ae-card-title">{_esc(opt)}</span>{note}</label>'
        )
    picker = (
        '<div class="ae-prog-blocked-h">Blocked — pick one to tackle:</div>'
        f'<div class="ae-cards" role="radiogroup">{cards}</div>'
        if cards
        else ""
    )
    rows_html = f'<div class="ae-prog-rows">{rows}</div>' if rows else ""
    return f'<div class="ae-progress">{rows_html}{picker}</div>'


def _control_multi_select_html(q: FormQuestion) -> str:
    """Render MULTI_SELECT: a list_style list, or plain checkboxes."""
    if q.list_style:
        return _list_html(q, multi=True)
    boxes = "".join(
        f'<label class="ae-check"><input type="checkbox" data-control '
        f'value="{_esc(opt)}"{_checked(q, opt)}> {_esc(opt)}</label>'
        for opt in q.options
    )
    return f'<div class="ae-checks">{boxes}</div>'


def _control_single_select_html(q: FormQuestion) -> str:
    """Render SINGLE_SELECT: a list_style list, or a native <select>."""
    if q.list_style:
        return _list_html(q, multi=False)
    opts = '<option value="">— choose —</option>' + "".join(
        f'<option value="{_esc(opt)}"{_selected(q, opt)}>{_esc(opt)}</option>' for opt in q.options
    )
    return f'<select data-control class="ae-input">{opts}</select>'


def _control_boolean_html(q: FormQuestion) -> str:
    """Render BOOLEAN as a Yes/No <select>."""
    opts = '<option value="">—</option>' + "".join(
        f'<option value="{_esc(o)}"{_selected(q, o)}>{_esc(o)}</option>' for o in _BOOLEAN_OPTIONS
    )
    return f'<select data-control class="ae-input">{opts}</select>'


def _control_number_html(q: FormQuestion) -> str:
    """Render NUMBER with min/max bounds mirrored onto native attrs."""
    bounds = ""
    if q.minimum is not None:
        bounds += f' min="{_esc(q.minimum)}"'
    if q.maximum is not None:
        bounds += f' max="{_esc(q.maximum)}"'
    default = f' value="{_esc(q.default)}"' if q.default is not None else ""
    return f'<input type="number" step="any" data-control class="ae-input"' f"{bounds}{default}>"


def _control_date_html(q: FormQuestion) -> str:
    """Render DATE as a native date input."""
    default = f' value="{_esc(q.default)}"' if q.default is not None else ""
    return f'<input type="date" data-control class="ae-input"{default}>'


def _control_textarea_html(q: FormQuestion) -> str:
    """Render TEXTAREA with max_length mirrored onto native attrs."""
    maxlen = f' maxlength="{_esc(q.max_length)}"' if q.max_length else ""
    default = _esc(q.default) if q.default is not None else ""
    return (
        f'<textarea data-control class="ae-input ae-textarea" rows="3"'
        f"{maxlen}>{default}</textarea>"
    )


def _control_text_input_html(q: FormQuestion) -> str:
    """Render TEXT_INPUT — also the fallback for any other type."""
    maxlen = f' maxlength="{_esc(q.max_length)}"' if q.max_length else ""
    default = f' value="{_esc(q.default)}"' if q.default is not None else ""
    return f'<input type="text" data-control class="ae-input"{maxlen}{default}>'


#: Per-type control renderers. PROGRESS is special-cased in
#: ``_control_html`` (it branches further on ``progress_style``); any
#: type not present here falls back to ``_control_text_input_html``,
#: matching the original's unconditional TEXT_INPUT tail.
_CONTROL_RENDERERS: dict[QuestionType, Callable[[FormQuestion], str]] = {
    QuestionType.DECISION: _control_decision_html,
    QuestionType.PUSHBACK: _control_pushback_html,
    QuestionType.MULTI_SELECT: _control_multi_select_html,
    QuestionType.SINGLE_SELECT: _control_single_select_html,
    QuestionType.BOOLEAN: _control_boolean_html,
    QuestionType.NUMBER: _control_number_html,
    QuestionType.DATE: _control_date_html,
    QuestionType.TEXTAREA: _control_textarea_html,
}


def _control_html(q: FormQuestion) -> str:
    """Render the input control for one question (no label/wrapper).

    Every control carries ``data-control`` so the submit script can find
    it generically; numeric/length bounds are mirrored onto the native
    attributes for in-widget feedback, but the authoritative check is
    still server-side ``collect_form_response`` (R4).

    Args:
        q: The question to render a control for.

    Returns:
        An HTML fragment for the control.
    """
    if q.type == QuestionType.PROGRESS:
        return (
            _control_progress_report_html(q)
            if q.progress_style == "report"
            else _control_progress_html(q)
        )
    return _CONTROL_RENDERERS.get(q.type, _control_text_input_html)(q)


def _checked(q: FormQuestion, opt: str) -> str:
    """Return ``checked`` if ``opt`` is the question's default selection."""
    return " checked" if q.default is not None and opt == q.default else ""


def _selected(q: FormQuestion, opt: str) -> str:
    """Return ``selected`` if ``opt`` is the question's default value."""
    return " selected" if q.default is not None and opt == q.default else ""


def _field_html(q: FormQuestion) -> str:
    """Render one labelled field (label + optional help + control).

    For a DECISION question a ``rationale`` callout ("why this
    recommendation") is rendered beneath the option cards; for a PUSHBACK
    the same callout is headed "Why I'd push back"; for a PROGRESS report
    it is headed "Summary".
    """
    req = '<span class="ae-req" title="required">*</span>' if q.required else ""
    help_html = f'<div class="ae-help">{_esc(q.help_text)}</div>' if q.help_text else ""
    rationale_headers = {
        QuestionType.PUSHBACK: "Why I&#x27;d push back",
        QuestionType.PROGRESS: "Summary",
    }
    rationale_h = rationale_headers.get(q.type, "Why")
    rationale_html = (
        f'<div class="ae-rationale"><span class="ae-rationale-h">{rationale_h}</span>'
        f"{_esc(q.rationale)}</div>"
        if q.rationale
        else ""
    )
    # An inferred value is the agent's GUESS. It must never read as a
    # settled fact — the badge is what makes a wrong inference catchable,
    # and is the difference between inference-first being a mechanism and
    # being a paragraph of guidance.
    inferred_html = (
        f'<div class="ae-inferred"><span class="ae-inferred-b">guessed</span>'
        f"{_esc(q.inferred_from)}</div>"
        if q.inferred_from
        else ""
    )
    inferred_attr = ' data-inferred="1"' if q.inferred_from else ""
    return (
        f'<div class="ae-field" data-fid="{_esc(q.id)}" '
        f'data-ftype="{_esc(q.type.value)}"{inferred_attr}>'
        f'<label class="ae-label">{_esc(q.text)}{req}</label>'
        f"{help_html}{inferred_html}{_control_html(q)}{rationale_html}</div>"
    )


#: The form CSS lives in :mod:`attune.elicitation.theme` — the ONE
#: tracked source (workflow-intake-forms Task 3), projected here as
#: inline injection and to the ops dashboard as /static/form-theme.css.
#: ``_CSS_BASE``/``_CSS_FAMILIES`` are imported aliases; the per-form
#: family selection below is unchanged: every form emits BASE, each
#: field pulls in only the family its control renders with, so a form
#: never ships styles for controls it lacks. See :func:`_needed_css`.


def _families_for(question: FormQuestion) -> set[str]:
    """Return the CSS families one question's control renders with."""
    qtype = question.type
    if qtype == QuestionType.PROGRESS:
        return {"CARDS", "PROGRESS"}  # blocked picker reuses the cards
    if qtype in (QuestionType.DECISION, QuestionType.PUSHBACK):
        return {"CARDS"}
    if qtype == QuestionType.MULTI_SELECT:
        return {"LIST"} if question.list_style else {"CHECKS"}
    if qtype == QuestionType.SINGLE_SELECT:
        return {"LIST"} if question.list_style else {"INPUT"}
    return {"INPUT"}  # boolean, number, date, textarea, text_input, fallback


def _needed_css(form: FormSchema) -> str:
    """Return BASE plus only the family CSS the form's controls use."""
    used: set[str] = set()
    for question in form.questions:
        used |= _families_for(question)
    return _CSS_BASE + "".join(css for name, css in _CSS_FAMILIES if name in used)


def form_to_widget_html(
    form: FormSchema,
    message: str = "",
    instance_id: str | None = None,
) -> str:
    """Render a declarative form as an inline ``show_widget`` HTML form.

    The S1 surface (D8). The returned HTML is self-contained (scoped
    styles + a submit script) and theme-native (Claude Design System CSS
    variables, transparent background, no ``position: fixed``). On submit
    it posts a sentinel-marked JSON payload via the global
    ``sendPrompt`` so the agent can validate it through
    :func:`collect_form_response`.

    All form-supplied text is HTML-escaped, and no form data is
    interpolated into executable script — the submit handler reads the
    DOM generically by ``data-*`` attributes — so a malicious label or
    option cannot inject markup or script.

    Element ids are suffixed per render so two forms shown on the same
    page (e.g. a demo's basic + advanced beats) never collide in the
    DOM — a duplicate id would make the second form's submit script
    read the first form's fields.

    Args:
        form: The validated form to render (build it with
            :func:`form_from_dict` first).
        message: Optional prompt shown above the form.
        instance_id: Optional alphanumeric suffix for the element ids;
            defaults to a fresh random one per call. Pass a fixed value
            only when a deterministic render is needed (tests, golden
            output).

    Returns:
        An HTML string ready to pass straight to
        ``mcp__visualize__show_widget``.
    """
    sfx = "".join(c for c in (instance_id or "") if c.isalnum()) or uuid.uuid4().hex[:8]
    form_id = f"attune-elicit-form-{sfx}"
    intro = f'<p class="ae-msg">{_esc(message)}</p>' if message else ""
    desc = f'<p class="ae-desc">{_esc(form.description)}</p>' if form.description else ""
    fields = "".join(_field_html(q) for q in form.questions)
    css = _needed_css(form).replace("#attune-elicit-form", f"#{form_id}")

    # Fully-inferred forms are confirmations, not questions: the agent
    # believes it knows every answer already. Chair-ruled 2026-07-25 to
    # RENDER rather than skip — a silent correct-looking guess is the one
    # failure a form cannot recover from. The banner and button label are
    # what tell the user this is a review, not an interrogation.
    confirm = is_fully_inferred(form)
    confirm_html = (
        '<p class="ae-confirm">Everything below was filled in from '
        "context. Change anything that&#x27;s wrong, then confirm.</p>"
        if confirm
        else ""
    )
    submit_label = "Confirm" if confirm else "Submit"

    return f"""<h2 class="sr-only">{_esc(form.title)} — interactive form</h2>
<form id="{form_id}" data-form-title="{_esc(form.title)}">
<style>
{css}</style>
<h3>{_esc(form.title)}</h3>
{intro}{desc}{confirm_html}
{fields}
<button type="button" id="ae-submit-{sfx}" class="ae-submit">{submit_label}</button>
<div id="ae-error-{sfx}" class="ae-error" role="alert"></div>
<script>
(function() {{
  var form = document.getElementById('{form_id}');
  var btn = document.getElementById('ae-submit-{sfx}');
  var err = document.getElementById('ae-error-{sfx}');
  if (!form || !btn) return;
  btn.addEventListener('click', function() {{
    var answers = {{}};
    form.querySelectorAll('.ae-field').forEach(function(f) {{
      var fid = f.getAttribute('data-fid');
      var ftype = f.getAttribute('data-ftype');
      if (ftype === 'multi_select') {{
        var vals = [];
        f.querySelectorAll('[data-control]:checked').forEach(function(c) {{
          vals.push(c.value);
        }});
        answers[fid] = vals;
      }} else if (ftype === 'decision' || ftype === 'pushback' || ftype === 'progress') {{
        // progress: the answer is the selected blocked item; when nothing
        // is blocked there is no radio and no answer is posted (display-only).
        var picked = f.querySelector('[data-control]:checked');
        if (picked) answers[fid] = picked.value;
      }} else {{
        var el = f.querySelector('[data-control]');
        if (!el) return;
        if (el.type === 'radio') {{
          // single_select rendered as a list (list_style) — read the
          // checked radio, not the first control.
          var picked = f.querySelector('[data-control]:checked');
          if (picked) answers[fid] = picked.value;
        }} else if (el.value !== '') {{
          answers[fid] = (ftype === 'number') ? Number(el.value) : el.value;
        }}
      }}
    }});
    var payload = {{ {WIDGET_RESPONSE_MARKER!r}: true,
      title: form.getAttribute('data-form-title'), answers: answers }};
    if (typeof sendPrompt === 'function') {{
      sendPrompt('Elicitation form submitted — parse and validate this '
        + 'response:\\n```json\\n' + JSON.stringify(payload) + '\\n```');
      btn.disabled = true; btn.textContent = 'Submitted \\u2713';
    }} else {{
      err.textContent = 'This surface cannot post back (sendPrompt '
        + 'unavailable). Use the AskUserQuestion fallback.';
    }}
  }});
}})();
</script>
</form>"""
