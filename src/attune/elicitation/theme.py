"""Shared form theme — the ONE tracked CSS source for intake forms.

workflow-intake-forms Task 3 (design.md "The shared look"): every
form surface renders from this module's CSS, projected — never
hand-copied:

- **Widgets** (claude.ai): ``form_to_widget_html`` injects the
  needed family blocks inline (the widget sandbox's CSP forbids
  external stylesheet fetches, so shared means shared-by-SOURCE).
- **Ops dashboard**: the full ``FORM_THEME_CSS`` string is served
  as ``/static/form-theme.css`` from a projected file that a drift
  test keeps byte-equal to the constant.

Every ``var()`` reference carries a literal fallback, so one
stylesheet renders native on claude.ai (host tokens win,
light/dark follows the host) and standalone (fallbacks win).

Budget: ``FORM_THEME_CSS`` is capped at 6 KB raw by
``test_form_theme_budget`` (amended from 4 KB by chair ruling
2026-07-31 — the original figure predated the mandated fallback
literals; measured full sheet = 5,574 B) — no fonts, no icon
fonts, no images, no @import; growth past the cap is a design
decision, not a drift.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

#: Base rules every form emits (scoped under ``#attune-elicit-form``;
#: the widget renderer rewrites the id per instance).
CSS_BASE = """#attune-elicit-form { display:block; width:100%; padding:1rem 0;
  color:var(--text-primary,#2c2c2a); line-height:1.5; }
#attune-elicit-form .sr-only { position:absolute; width:1px; height:1px;
  overflow:hidden; clip:rect(0 0 0 0); }
#attune-elicit-form h3 { font-size:18px; font-weight:500; margin:0 0 .25rem; }
#attune-elicit-form .ae-msg { margin:0 0 .5rem; color:var(--text-secondary,#5f5e59); }
#attune-elicit-form .ae-desc { margin:0 0 1rem; color:var(--text-muted,#8a887f);
  font-size:15px; }
#attune-elicit-form .ae-field { margin:0 0 1rem; }
#attune-elicit-form .ae-label { display:block; font-weight:500;
  margin:0 0 .35rem; }
#attune-elicit-form .ae-req { color:var(--text-accent,#a1571c); margin-left:2px; }
#attune-elicit-form .ae-confirm { font-size:14px; color:var(--text-secondary,#5f5e59);
  border-left:3px solid var(--border-accent,#d8b89a); border-radius:0;
  padding:.35rem .6rem; margin:0 0 1rem; }
#attune-elicit-form .ae-inferred { font-size:13px; color:var(--text-muted,#8a887f);
  margin:0 0 .35rem; }
#attune-elicit-form .ae-inferred-b { display:inline-block; font-size:11px;
  font-weight:500; text-transform:uppercase; letter-spacing:.04em;
  color:var(--text-accent,#a1571c); background:var(--bg-accent,#f3ece4);
  border:1px solid var(--border-accent,#d8b89a); border-radius:var(--radius,8px);
  padding:0 .35rem; margin-right:.4rem; }
#attune-elicit-form .ae-help { font-size:13px; color:var(--text-muted,#8a887f);
  margin:0 0 .35rem; }
#attune-elicit-form .ae-submit { margin-top:.5rem; padding:.55rem 1.1rem;
  font-size:15px; font-weight:500; cursor:pointer; color:var(--text-primary,#2c2c2a);
  background:var(--bg-accent,#f3ece4); border:1px solid var(--border-accent,#d8b89a);
  border-radius:var(--radius,8px); }
#attune-elicit-form .ae-submit:disabled { opacity:.6; cursor:default; }
#attune-elicit-form .ae-error { margin-top:.5rem; font-size:14px;
  color:var(--text-accent,#a1571c); }
#attune-elicit-form .ae-field-missing { border-left:3px solid
  var(--text-accent,#a1571c); padding-left:.6rem; }
"""

#: INPUT — text_input, textarea, number, date, boolean, non-list single_select.
CSS_INPUT = """#attune-elicit-form .ae-input { width:100%; box-sizing:border-box;
  padding:.5rem .6rem; font-size:15px; color:var(--text-primary,#2c2c2a);
  background:var(--surface-1,#f7f6f3); border:1px solid var(--border,#e3e1dc);
  border-radius:var(--radius,8px); }
#attune-elicit-form .ae-textarea { resize:vertical; min-height:3.5rem; }
"""

#: CHECKS — non-list multi_select (checkbox rows).
CSS_CHECKS = """#attune-elicit-form .ae-checks { display:flex; flex-direction:column;
  gap:.35rem; }
#attune-elicit-form .ae-check { display:flex; align-items:center; gap:.5rem;
  font-weight:400; }
"""

#: LIST — any select rendered with ``list_style``.
CSS_LIST = """#attune-elicit-form .ae-list { margin:0; padding-left:1.6rem;
  display:flex; flex-direction:column; gap:.3rem; }
#attune-elicit-form .ae-list-item label { display:inline-flex;
  align-items:baseline; gap:.45rem; cursor:pointer; font-weight:400; }
"""

#: CARDS — decision / pushback option cards + the rationale callout (also
#: reused by the progress blocked-picker).
CSS_CARDS = """#attune-elicit-form .ae-cards { display:flex; flex-direction:column; gap:.5rem; }
#attune-elicit-form .ae-card { position:relative; display:flex;
  flex-direction:column; gap:.15rem; padding:.6rem 1.9rem .6rem .75rem;
  border:1px solid var(--border,#e3e1dc); border-radius:var(--radius,8px);
  cursor:pointer; }
#attune-elicit-form .ae-card:hover { border-color:var(--text-muted,#8a887f); }
#attune-elicit-form .ae-card-rec { border-color:var(--border-accent,#d8b89a); }
#attune-elicit-form .ae-card input { position:absolute; top:.7rem; right:.6rem; }
#attune-elicit-form .ae-card-title { font-weight:500; }
#attune-elicit-form .ae-card-note { font-size:13px; color:var(--text-muted,#8a887f); }
#attune-elicit-form .ae-rec-badge { font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:.03em; color:var(--text-accent,#a1571c); }
#attune-elicit-form .ae-yours-tag { font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:.03em; color:var(--text-muted,#8a887f); }
#attune-elicit-form .ae-rationale { margin:.6rem 0 0; padding:.4rem 0 .4rem .75rem;
  font-size:13px; color:var(--text-secondary,#5f5e59);
  border-left:2px solid var(--border-accent,#d8b89a); }
#attune-elicit-form .ae-rationale-h { display:block; font-weight:600;
  font-size:11px; text-transform:uppercase; letter-spacing:.03em;
  color:var(--text-accent,#a1571c); margin-bottom:.15rem; }
"""

#: PROGRESS — the done/in_flight/blocked status rows (pulls CARDS too).
CSS_PROGRESS = """#attune-elicit-form .ae-progress { display:flex; flex-direction:column; gap:.5rem; }
#attune-elicit-form .ae-prog-rows { display:flex; flex-direction:column; gap:.25rem; }
#attune-elicit-form .ae-prog-row { display:flex; align-items:baseline; gap:.5rem;
  font-size:14px; color:var(--text-secondary,#5f5e59); }
#attune-elicit-form .ae-prog-icon { flex:none; font-weight:700; width:1.1em;
  text-align:center; }
#attune-elicit-form .ae-prog-done .ae-prog-icon { color:var(--text-success,#3fb950); }
#attune-elicit-form .ae-prog-in_flight .ae-prog-icon { color:var(--text-accent,#a1571c); }
#attune-elicit-form .ae-prog-blocked { color:var(--text-accent,#a1571c); }
#attune-elicit-form .ae-prog-detail { font-size:13px; color:var(--text-muted,#8a887f); }
#attune-elicit-form .ae-prog-label { color:var(--text-primary,#2c2c2a); }
#attune-elicit-form .ae-prog-done .ae-prog-label { text-decoration:line-through;
  color:var(--text-muted,#8a887f); }
#attune-elicit-form .ae-prog-blocked-h { font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:.03em; color:var(--text-accent,#a1571c); }
#attune-elicit-form .ae-prog-tag { flex:none; font-size:10px; font-weight:600;
  text-transform:uppercase; letter-spacing:.04em; color:var(--text-muted,#8a887f);
  border:1px solid var(--border,#e3e1dc); border-radius:3px; padding:0 .3em; }
#attune-elicit-form .ae-card .ae-prog-tag { align-self:flex-start; }
#attune-elicit-form .ae-card .ae-prog-icon { margin-right:.15rem; }
"""

#: Named family blocks in cascade-emission order (BASE is always first).
CSS_FAMILIES: list[tuple[str, str]] = [
    ("INPUT", CSS_INPUT),
    ("CHECKS", CSS_CHECKS),
    ("LIST", CSS_LIST),
    ("CARDS", CSS_CARDS),
    ("PROGRESS", CSS_PROGRESS),
]

#: The full theme: base + every family, in cascade order. This exact
#: string is what the ops dashboard serves at ``/static/form-theme.css``
#: (byte-equal by drift test) and what the 4 KB budget test measures.
FORM_THEME_CSS = CSS_BASE + "".join(css for _name, css in CSS_FAMILIES)
