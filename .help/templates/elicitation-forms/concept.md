---
type: concept
name: elicitation-forms-concept
feature: elicitation-forms
depth: concept
generated_at: 2026-09-06T00:35:04.869548+00:00
source_hash: 9162a67905eb555cfdd3b260da2b35f34972ceed46c693d35319d40e7370db18
status: generated
---

# Dynamic forms and the agent-to-user communication grammar

## Overview

Elicitation forms let the agent shape an exchange to fit the moment:
instead of a wall of prose, it renders an interactive form whenever a
structured turn communicates better than text. A multi-part question
becomes one form you answer with a click; a recommendation arrives as
weighable cards; a disagreement is shown side-by-side so you can
overrule it in one tap. The goal is plainly to **improve human/AI
communication** — make the back-and-forth faster, clearer, and less
ambiguous.

Every form is one declarative artifact — a `FormSchema` of
`FormQuestion`s — built from plain data with `form_from_dict`, validated
once with `collect_form_response`, and rendered by surface-specific
renderers. The same artifact renders richly on a widget-capable client
and degrades gracefully everywhere else; the answer is validated the
same way regardless of surface.

### Forms are input grammar; workspaces are task projections

A form is best for one bounded input turn. A command workspace is the
larger protocol for a task that persists across turns: intake, preview,
execution, and receipt are versioned views over host-owned state. The
view document is still declarative data and still renders to widget or
Markdown, but it is disposable — it never becomes execution authority.

Fix is the first live workspace. `fix_workspace_preview` rebuilds its
validated CLI contract, stores canonical state in the MCP session, and
binds the rendered actions to the workspace id, revision, one-time nonce,
and SHA-256 hash of the exact future argv. `fix_workspace_collect_action`
rebuilds that contract again before accepting `edit_contract` or
`run_fix`; it consumes the nonce and returns the approved argv but does
not execute it. This separates three things that should not be conflated:

1. the form records intent;
2. the workspace explains the exact consequence;
3. the existing Fix CLI remains the executor and receipt boundary.

On top of that shared substrate sits a small, growing **communication
grammar** — a family of constructs, each a member of the one form model:

- **intake** — gather several independent decisions as one
  (multi-select-capable) form;
- **decision** — offer a recommended option with a rationale and
  per-option tradeoffs;
- **pushback** — disagree with a stated approach and offer a concrete
  alternative;
- **progress** — report a set of items by status and surface the blocked
  ones as a picker.

The substrate itself — the `FormSchema` models, the bridge, the
surface renderers, the theme, the intake template engine, and the
`form_events` telemetry — lives in the standalone
[attune-forms](https://github.com/Smart-AI-Memory/attune-forms)
package (PyPI: `attune-forms`), which attune-ai depends on. The
`attune.elicitation` import paths used throughout these docs remain
fully supported: they alias the same module objects, so imports,
monkeypatching, and class identity behave exactly as before the
extraction. What lives in this repo is the attune-side integration —
the host seams, the attune-specific intake templates, and the MCP
tools that expose the forms. *When* a construct fires in a
conversation is a judgment call governed by the agent's decision
routine, not by this subsystem.

Two of these forms run **live** on the website — rendered by the
production `form_from_dict` → `form_to_widget_html` pipeline, not
mockups: a five-control audit-scoping decision form at
[smartaimemory.com/forms-demo/audit.html](https://smartaimemory.com/forms-demo/audit.html)
and a session-retro triage form at
[smartaimemory.com/forms-demo/retro.html](https://smartaimemory.com/forms-demo/retro.html)
(both embedded on
[how-it-works](https://smartaimemory.com/how-it-works/)). They are
regenerated from `scripts/render_demo_forms.py`, so the demos cannot
drift from the API these docs describe.

## Concepts

### One substrate, many constructs

A construct is not a parallel system — it is meaning and presentation
layered on the single form model. Adding a construct almost never adds a
new round-trip or a new validator; it adds a `QuestionType` and a few
optional `FormQuestion` fields, and reuses the existing answer path.

| Construct | `QuestionType` | Answer | Extra fields |
|-----------|----------------|--------|--------------|
| intake | `single_select` / `multi_select` / … | the picked value(s) | — |
| decision | `decision` | one option | `rationale`, `option_notes`, `recommended` |
| pushback | `pushback` | one option | `user_position` (+ reuses `recommended`, `rationale`, `option_notes`) |
| progress | `progress` | one blocked item | `progress_items` (+ reuses `recommended`, `rationale`) |

`decision`, `pushback`, and `progress` are all **presentation-enriched
single-selects**: the answer is one option, validated by membership
exactly like a plain `single_select`. What differs is the rendering and
the framing.

### Validation is never skipped (R4)

`collect_form_response` is the one validator. A missing required field
with no default, or a value outside a select's options, raises
`FormValidationError` naming every offending field so the caller can
re-ask just those — it never silently accepts malformed input. This holds
for every construct, because every construct's answer is a select answer
underneath.

### Surfaces, and graceful degradation

A form renders three ways, in order of richness:

- **Widget** (`form_to_widget_html` → `show_widget`) — **the default**:
  cards, badges, the three-bucket progress board, dissent framing. Renders
  on widget-capable clients (claude.ai / Cowork). Answers post back through
  a sentinel-marked JSON block which you validate with
  `collect_form_response`.
- **AskUserQuestion** (`form_to_askuserquestion`) — the fallback: batched
  payloads (≤4 questions each), recommendation-first. The constructs
  collapse to a recommendation-ordered single-select here. Works in a
  plain terminal.
- **Native MCP elicitation** (`form_to_elicitation_schema`) — a JSON-schema
  form for clients with native elicitation. It does not render on Claude
  Code today and lacks multi-select, so it is not the default.

### Choosing a surface

`select_form_surface(form, widget_capable=…, keyboard_mode=…)` decides,
and the rich widget is what it decides by default. The axis is **how much
of the option space the reader can see at once**, not how many tool calls
it costs — folding three options and their tradeoffs into prose above a
single-select turns a scan into a serial read.

Precedence, highest first:

1. **Client can't render widgets** → `AskUserQuestion`. A constraint.
2. **A `number` / `date` / `textarea` field** → widget, always. No
   `AskUserQuestion` control exists, so this outranks the opt-out and a
   field can never be silently dropped.
3. **Keyboard mode on** → `AskUserQuestion`.
4. **Trivial form** → `AskUserQuestion`. Trivial is narrow and mechanical:
   one `single_select`/`boolean`, ≤3 options, no option label over 120
   characters. A long label means a tradeoff was folded into the text —
   that form wanted a card.
5. **Otherwise** → widget.

Latency is not an input. `needs_widget` still exists as the low-level
"does this lose fidelity on `AskUserQuestion`" check, but it no longer
owns the decision.

### Keyboard mode

Keyboard mode is the opt-out for people who would rather type than click.
Turn it on with the CLI:

```bash
attune config set keyboard_mode true
```

It persists **per project** as `keyboard_mode` in `./attune.config.json`,
so it survives restarts and stays scoped to the repo you set it in.
`attune config show` reports the current value.
`ATTUNE_KEYBOARD_MODE=1` (or `0`) overrides it for one shell in either
direction.

Nobody has to know the setting exists to find it: after ten answered
forms, the next submission surfaces a one-time hint pointing at the
command (D17's usage-triggered discovery — it reaches people who have
felt the friction, and never fires for someone already opted in). The terse reply vocabulary (`y` / `go` / `1`) answers any
construct on any surface regardless — a form never blocks a keyboard-only
user.

### Inference-first — don't ask what you can already answer

Ceremony isn't caused by forms being rich. It's caused by being asked
things you already answered. So fill in what the conversation already
told you, and let the form confirm rather than interrogate.

A field carries `inferred_from` alongside its `default` — the value plus
why you guessed it:

```json
{
  "id": "scope",
  "type": "single_select",
  "text": "Which path?",
  "options": ["src", "tests"],
  "default": "src",
  "inferred_from": "you have been editing src/attune/elicitation/"
}
```

An inference without a value is a definition error, so a "guessed" badge
can never appear over an empty control.

**A guess must look like a guess.** The widget badges every inferred
field and shows the provenance under the label; the `AskUserQuestion`
fallback folds it into help text (`Guessed: src — you have been editing
src/`). Neither surface presents an inferred value as settled, which is
what makes a wrong guess catchable instead of silently accepted.

**When every field is inferred, the form still renders** — as a one-tap
confirmation with a "Confirm" button, not a skipped step. Skipping would
be faster, and it is the one thing that must not happen: a correct-
looking wrong guess the user never got to see is the only failure a form
cannot recover from. Fields stay editable, so confirming is a review.

`is_fully_inferred(form)` drives that mode; `inferred_field_count(form)`
reports how much a form inferred. `attune.telemetry.form_events`
records both per routing decision, and `inference_rate()` reads them
back — inference-first is authoring discipline, so counting it is the
only way to know it is being followed rather than merely documented.

### Collapsing an answered form

Once a form is submitted, the rendered markup has done its job and only
the question/answer pairs still carry meaning.
`form_response_summary(form, response)` returns a title line plus one
bullet per answer, so a long session accumulates summaries instead of
screenfuls of HTML.

### The list render variant (`list_style`)

A `single_select` or `multi_select` can set `list_style: "ordered"`
(numbered) or `"unordered"` (bulleted) to render its options as a familiar
intro-sentence-plus-list shape — each item pickable by mouse or the
`1` / `2` / `3` vocabulary — instead of a dropdown or checkboxes. This is
presentation only: the answer and its validation are unchanged. It is a
render option on the select types, **not** a separate construct.

### Template-bound forms — sculpt once, cast per fork

A recurring ask (the session contract, a release gate, a review choice)
should not be re-composed as a fresh dict every time. A **stored
template** is exactly the dict `form_from_dict` accepts plus a top-level
`slots` list naming its `{placeholder}` substitution points and an
`example_slots` mapping with one representative value per slot. Casting
a template fills the slots and validates the *result* through the same
seam as a hand-built dict — every problem listed, never a partial form.

Two properties make templates load-bearing rather than a convenience:

- **The fused server path.** Every form-taking MCP tool accepts
  `template` + `slots` in place of `form`. The server loads, casts,
  validates, and renders in one call, so neither the form definition
  nor its HTML transits the agent's context. Answers collected from a
  template-cast form carry the template name as `template_id`, which
  makes responses joinable across sessions.
- **The cast-every-template gate.** Because every stored template
  carries `example_slots`, a drift test casts each one and validates the
  form the substitution actually produces. Validating an uncast template
  proves nothing about what the placeholders become; the gate checks the
  thing users see.

`form_from_dict` stamps every build with a `source` (`dict` by default,
`template:<name>` for a cast), so template adoption is measured from the
form telemetry rather than asserted. Preview casts (the authoring preview, `python -m attune_forms.preview`)
suppress that telemetry so authoring never inflates the meter.
