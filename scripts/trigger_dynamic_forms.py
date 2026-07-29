"""Trigger the dynamic forms (elicitation) feature end-to-end — offline, no API credits.

Exercises the full pipeline the agent uses live:
  dict -> form_from_dict -> select_form_surface -> form_to_widget_html
       -> collect_form_response (validate) -> form_response_summary

Run from the repo:
    PYTHONPATH=src python scripts/trigger_dynamic_forms.py
The rendered widget HTML is written to dynamic_form_demo.html in the
current directory; open it in a browser to see the form (submit needs a
sendPrompt-capable surface, but every control renders).
"""

from __future__ import annotations

from pathlib import Path

from attune.elicitation import (
    EXAMPLE_ANSWERS,
    REFERENCE_FORM,
    collect_form_response,
    form_from_dict,
    form_response_summary,
    form_to_askuserquestion,
    form_to_widget_html,
    select_form_surface,
)

# 1. Build the declarative artifact (D3) — the canonical reference form
#    has exactly one field per control type (text, select, multi,
#    boolean, number, date, textarea, decision, pushback, progress).
form = form_from_dict(REFERENCE_FORM)
print(f"form: {form.title!r} — {len(form.questions)} fields")

# 2. Route the surface (D21): widget by default, AskUserQuestion fallback.
surface = select_form_surface(form, widget_capable=True)
print(f"surface router picked: {surface}")

# 3. Render the widget HTML (what elicitation_render_widget returns).
html = form_to_widget_html(form, message="Triggered by trigger_dynamic_forms.py")
out = Path.cwd() / "dynamic_form_demo.html"
out.write_text(html, encoding="utf-8")
print(f"widget HTML written: {out} ({len(html)} bytes) — open in a browser")

# 4. Show the AskUserQuestion fallback payloads (batched <=4 questions/call).
batches = form_to_askuserquestion(form)
print(f"AskUserQuestion fallback: {len(batches)} batched call(s)")

# 5. Round-trip: validate a full set of answers (R4 — never silently
#    accept malformed input).
response = collect_form_response(form, EXAMPLE_ANSWERS)
print("validated answers:")
for field_id, value in response.responses.items():
    print(f"  {field_id}: {value}")

# 6. Compact summary — what the agent echoes back into the session.
print()
print(form_response_summary(form, response))
