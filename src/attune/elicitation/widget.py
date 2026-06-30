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

from html import escape

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
    if q.type == QuestionType.DECISION:
        notes = q.option_notes or {}
        ordered = list(q.options)
        if q.recommended and q.recommended in ordered:
            ordered = [q.recommended] + [o for o in ordered if o != q.recommended]
        cards = ""
        for opt in ordered:
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

    if q.type == QuestionType.PUSHBACK:
        # Dissent framing: the agent's alternative (``recommended``) is badged
        # "I'd suggest instead" and ordered first; the user's stated approach
        # (``user_position``) carries a muted "your approach" tag. Same radio
        # answer path as DECISION.
        notes = q.option_notes or {}
        ordered = list(q.options)
        if q.recommended and q.recommended in ordered:
            ordered = [q.recommended] + [o for o in ordered if o != q.recommended]
        cards = ""
        for opt in ordered:
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

    if q.type == QuestionType.PROGRESS:
        # A status report: done/in_flight items render as static rows; the
        # blocked items become the radiogroup picker (recommended first,
        # "suggested next" badge). With no blocked items the picker is
        # omitted and the control is a pure status display.
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
        ordered = list(q.options)
        if q.recommended and q.recommended in ordered:
            ordered = [q.recommended] + [o for o in ordered if o != q.recommended]
        detail_by_label = {it.get("label"): it.get("detail") for it in by_status["blocked"]}
        cards = ""
        for opt in ordered:
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

    if q.type == QuestionType.MULTI_SELECT:
        boxes = "".join(
            f'<label class="ae-check"><input type="checkbox" data-control '
            f'value="{_esc(opt)}"{_checked(q, opt)}> {_esc(opt)}</label>'
            for opt in q.options
        )
        return f'<div class="ae-checks">{boxes}</div>'

    if q.type == QuestionType.SINGLE_SELECT:
        opts = '<option value="">— choose —</option>' + "".join(
            f'<option value="{_esc(opt)}"{_selected(q, opt)}>{_esc(opt)}</option>'
            for opt in q.options
        )
        return f'<select data-control class="ae-input">{opts}</select>'

    if q.type == QuestionType.BOOLEAN:
        opts = '<option value="">—</option>' + "".join(
            f'<option value="{_esc(o)}"{_selected(q, o)}>{_esc(o)}</option>'
            for o in _BOOLEAN_OPTIONS
        )
        return f'<select data-control class="ae-input">{opts}</select>'

    if q.type == QuestionType.NUMBER:
        bounds = ""
        if q.minimum is not None:
            bounds += f' min="{_esc(q.minimum)}"'
        if q.maximum is not None:
            bounds += f' max="{_esc(q.maximum)}"'
        default = f' value="{_esc(q.default)}"' if q.default is not None else ""
        return (
            f'<input type="number" step="any" data-control class="ae-input"' f"{bounds}{default}>"
        )

    if q.type == QuestionType.DATE:
        default = f' value="{_esc(q.default)}"' if q.default is not None else ""
        return f'<input type="date" data-control class="ae-input"{default}>'

    if q.type == QuestionType.TEXTAREA:
        maxlen = f' maxlength="{_esc(q.max_length)}"' if q.max_length else ""
        default = _esc(q.default) if q.default is not None else ""
        return (
            f'<textarea data-control class="ae-input ae-textarea" rows="3"'
            f"{maxlen}>{default}</textarea>"
        )

    # TEXT_INPUT (default).
    maxlen = f' maxlength="{_esc(q.max_length)}"' if q.max_length else ""
    default = f' value="{_esc(q.default)}"' if q.default is not None else ""
    return f'<input type="text" data-control class="ae-input"{maxlen}{default}>'


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
    return (
        f'<div class="ae-field" data-fid="{_esc(q.id)}" '
        f'data-ftype="{_esc(q.type.value)}">'
        f'<label class="ae-label">{_esc(q.text)}{req}</label>'
        f"{help_html}{_control_html(q)}{rationale_html}</div>"
    )


def form_to_widget_html(form: FormSchema, message: str = "") -> str:
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

    Args:
        form: The validated form to render (build it with
            :func:`form_from_dict` first).
        message: Optional prompt shown above the form.

    Returns:
        An HTML string ready to pass straight to
        ``mcp__visualize__show_widget``.
    """
    intro = f'<p class="ae-msg">{_esc(message)}</p>' if message else ""
    desc = f'<p class="ae-desc">{_esc(form.description)}</p>' if form.description else ""
    fields = "".join(_field_html(q) for q in form.questions)

    return f"""<h2 class="sr-only">{_esc(form.title)} — interactive form</h2>
<form id="attune-elicit-form" data-form-title="{_esc(form.title)}">
<style>
#attune-elicit-form {{ display:block; width:100%; padding:1rem 0;
  color:var(--text-primary); line-height:1.5; }}
#attune-elicit-form .sr-only {{ position:absolute; width:1px; height:1px;
  overflow:hidden; clip:rect(0 0 0 0); }}
#attune-elicit-form h3 {{ font-size:18px; font-weight:500; margin:0 0 .25rem; }}
#attune-elicit-form .ae-msg {{ margin:0 0 .5rem; color:var(--text-secondary); }}
#attune-elicit-form .ae-desc {{ margin:0 0 1rem; color:var(--text-muted);
  font-size:15px; }}
#attune-elicit-form .ae-field {{ margin:0 0 1rem; }}
#attune-elicit-form .ae-label {{ display:block; font-weight:500;
  margin:0 0 .35rem; }}
#attune-elicit-form .ae-req {{ color:var(--text-accent); margin-left:2px; }}
#attune-elicit-form .ae-help {{ font-size:13px; color:var(--text-muted);
  margin:0 0 .35rem; }}
#attune-elicit-form .ae-input {{ width:100%; box-sizing:border-box;
  padding:.5rem .6rem; font-size:15px; color:var(--text-primary);
  background:var(--surface-1); border:1px solid var(--border);
  border-radius:var(--radius); }}
#attune-elicit-form .ae-textarea {{ resize:vertical; min-height:3.5rem; }}
#attune-elicit-form .ae-checks {{ display:flex; flex-direction:column;
  gap:.35rem; }}
#attune-elicit-form .ae-check {{ display:flex; align-items:center; gap:.5rem;
  font-weight:400; }}
#attune-elicit-form .ae-cards {{ display:flex; flex-direction:column; gap:.5rem; }}
#attune-elicit-form .ae-card {{ position:relative; display:flex;
  flex-direction:column; gap:.15rem; padding:.6rem 1.9rem .6rem .75rem;
  border:1px solid var(--border); border-radius:var(--radius); cursor:pointer; }}
#attune-elicit-form .ae-card:hover {{ border-color:var(--text-muted); }}
#attune-elicit-form .ae-card-rec {{ border-color:var(--border-accent); }}
#attune-elicit-form .ae-card input {{ position:absolute; top:.7rem; right:.6rem; }}
#attune-elicit-form .ae-card-title {{ font-weight:500; }}
#attune-elicit-form .ae-card-note {{ font-size:13px; color:var(--text-muted); }}
#attune-elicit-form .ae-rec-badge {{ font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:.03em; color:var(--text-accent); }}
#attune-elicit-form .ae-yours-tag {{ font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:.03em; color:var(--text-muted); }}
#attune-elicit-form .ae-rationale {{ margin:.6rem 0 0; padding:.4rem 0 .4rem .75rem;
  font-size:13px; color:var(--text-secondary);
  border-left:2px solid var(--border-accent); }}
#attune-elicit-form .ae-rationale-h {{ display:block; font-weight:600;
  font-size:11px; text-transform:uppercase; letter-spacing:.03em;
  color:var(--text-accent); margin-bottom:.15rem; }}
#attune-elicit-form .ae-progress {{ display:flex; flex-direction:column; gap:.5rem; }}
#attune-elicit-form .ae-prog-rows {{ display:flex; flex-direction:column; gap:.25rem; }}
#attune-elicit-form .ae-prog-row {{ display:flex; align-items:baseline; gap:.5rem;
  font-size:14px; color:var(--text-secondary); }}
#attune-elicit-form .ae-prog-icon {{ flex:none; font-weight:700; width:1.1em;
  text-align:center; }}
#attune-elicit-form .ae-prog-done .ae-prog-icon {{ color:var(--text-success,#3fb950); }}
#attune-elicit-form .ae-prog-in_flight .ae-prog-icon {{ color:var(--text-accent); }}
#attune-elicit-form .ae-prog-blocked {{ color:var(--text-accent); }}
#attune-elicit-form .ae-prog-detail {{ font-size:13px; color:var(--text-muted); }}
#attune-elicit-form .ae-prog-label {{ color:var(--text-primary); }}
#attune-elicit-form .ae-prog-done .ae-prog-label {{ text-decoration:line-through;
  color:var(--text-muted); }}
#attune-elicit-form .ae-prog-blocked-h {{ font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:.03em; color:var(--text-accent); }}
#attune-elicit-form .ae-card .ae-prog-icon {{ margin-right:.15rem; }}
#attune-elicit-form .ae-submit {{ margin-top:.5rem; padding:.55rem 1.1rem;
  font-size:15px; font-weight:500; cursor:pointer; color:var(--text-primary);
  background:var(--bg-accent); border:1px solid var(--border-accent);
  border-radius:var(--radius); }}
#attune-elicit-form .ae-submit:disabled {{ opacity:.6; cursor:default; }}
#attune-elicit-form .ae-error {{ margin-top:.5rem; font-size:14px;
  color:var(--text-accent); }}
</style>
<h3>{_esc(form.title)}</h3>
{intro}{desc}
{fields}
<button type="button" id="ae-submit" class="ae-submit">Submit</button>
<div id="ae-error" class="ae-error" role="alert"></div>
<script>
(function() {{
  var form = document.getElementById('attune-elicit-form');
  var btn = document.getElementById('ae-submit');
  var err = document.getElementById('ae-error');
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
        if (!el || el.value === '') return;
        answers[fid] = (ftype === 'number') ? Number(el.value) : el.value;
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
