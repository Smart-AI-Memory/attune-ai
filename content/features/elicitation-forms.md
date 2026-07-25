---
feature: elicitation-forms
summary: Dynamic forms and the agent-to-user communication grammar
tags: [elicitation, forms, communication, ux]
source_globs:
  - src/attune/elicitation/**
  - src/attune/meta_workflows/models.py
nav:
  help: elicitation-forms
  mkdocs:
    how-to: how-to/elicitation-forms
    architecture: architecture/elicitation-forms
    reference: reference/elicitation-forms
---

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

This feature owns the form model, the renderers, the validator, and the
MCP tools that expose them. *When* a construct fires in a conversation is
a judgment call governed by the agent's decision routine, not by this
subsystem.

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
It persists **per project** as `keyboard_mode` in `./attune.config.json`:

```json
{ "keyboard_mode": true }
```

`ATTUNE_KEYBOARD_MODE=1` (or `0`) overrides it for one shell in either
direction. The terse reply vocabulary (`y` / `go` / `1`) answers any
construct on any surface regardless — a form never blocks a keyboard-only
user.

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

## Quickstart

Build a form from plain data, render it to the widget surface, and
validate the answer that posts back:

```python
from attune.elicitation import (
    form_from_dict,
    form_to_widget_html,
    collect_form_response,
)

form = form_from_dict({
    "title": "Release plan",
    "fields": [{
        "id": "bump",
        "text": "Which version bump?",
        "type": "decision",
        "options": ["patch", "minor", "major"],
        "recommended": "minor",
        "rationale": "Three additive features since the last tag.",
        "option_notes": {"minor": "new API, backward-compatible"},
    }],
})

html = form_to_widget_html(form)          # pass straight to show_widget
# … the user picks an option; the widget posts {"bump": "minor"} back …
response = collect_form_response(form, {"bump": "minor"})
assert response.responses["bump"] == "minor"
```

## Tasks

### Render a decision

A recommended option with a rationale and per-option tradeoffs, rendered
as cards (recommended badged and ordered first):

```python
form = form_from_dict({
    "title": "Approval",
    "fields": [{
        "id": "gate", "text": "High-severity gate failed — proceed?",
        "type": "decision",
        "options": ["Fix and retry", "Approve and continue"],
        "recommended": "Fix and retry",
        "rationale": "Two findings are unverified.",
    }],
})
```

### Render a pushback

Disagreement framed as dissent — the user's approach beside the agent's
alternative, under a "why I'd push back" rationale:

```python
form = form_from_dict({
    "title": "Approach",
    "fields": [{
        "id": "call", "text": "Build it how?",
        "type": "pushback",
        "options": ["Hand-roll a parser", "Reuse the existing one"],
        "user_position": "Hand-roll a parser",
        "recommended": "Reuse the existing one",
        "rationale": "The existing parser already handles every case here.",
    }],
})
```

### Render a progress report with a blocked-item picker

`progress_items` carries every item by status; the blocked subset must
equal `options` (the picker). When nothing is blocked, the construct
degrades to a pure status display with no answer:

```python
form = form_from_dict({
    "title": "Where we are",
    "fields": [{
        "id": "next", "text": "Which blocker first?",
        "type": "progress",
        "options": ["Fix the failing lane"],
        "recommended": "Fix the failing lane",
        "progress_items": [
            {"label": "Spec drafted", "status": "done"},
            {"label": "Tests written", "status": "in_flight"},
            {"label": "Fix the failing lane", "status": "blocked"},
        ],
    }],
})
```

### Render a select as a numbered list

```python
form = form_from_dict({
    "title": "Delivery",
    "fields": [{
        "id": "fmt", "text": "Pick a format:",
        "type": "single_select",
        "options": ["Bulleted brief", "Numbered steps", "Markdown table"],
        "list_style": "ordered",
    }],
})
```

## Reference

### Public API — `attune.elicitation`

| Symbol | Purpose |
|--------|---------|
| `form_from_dict(data)` | Build and validate a `FormSchema` from plain data; raises `FormValidationError` on a malformed definition. |
| `form_to_widget_html(form, message="")` | Render the rich inline HTML form for `show_widget`. |
| `form_to_askuserquestion(form, batch_size=4)` | Render batched `AskUserQuestion` payloads (the fallback surface). |
| `form_to_elicitation_schema(form)` | Render a native MCP elicitation JSON schema. |
| `select_form_surface(form, widget_capable=True, keyboard_mode=False)` | Choose the surface: `"widget"` (the default) or `"ask"`. |
| `is_trivial_form(form)` | True when a form is small enough that buttons lose nothing: one select/boolean, ≤3 options, no label >120 chars. |
| `keyboard_mode_enabled(project_root=None)` | Read the per-project opt-out (`keyboard_mode` in `./attune.config.json`; `ATTUNE_KEYBOARD_MODE` overrides). |
| `form_response_summary(form, response)` | Collapse an answered form to a compact markdown summary. |
| `needs_widget(form)` | Low-level controls check — True if `AskUserQuestion` would lose fidelity. Does not own the surface decision. |
| `collect_form_response(form, raw_answers, template_id="")` | Validate answers (R4) and return a `FormResponse`; raises `FormValidationError`. |
| `WIDGET_RESPONSE_MARKER` | The sentinel key the widget posts back under. |
| `FormValidationError` | Raised for a malformed definition or answer; lists every problem. |

### `QuestionType` values

`text_input`, `textarea`, `single_select`, `multi_select`, `boolean`,
`number` (with `minimum` / `maximum`), `date` (`YYYY-MM-DD`), and the
three construct types `decision`, `pushback`, `progress` — ten in all.

### Construct-specific `FormQuestion` fields

| Field | Used by | Meaning |
|-------|---------|---------|
| `recommended` | decision / pushback / progress | option to badge and order first; must be in `options` |
| `rationale` | decision / pushback / progress | the "why" callout |
| `option_notes` | decision / pushback | `{option: one-line tradeoff}` |
| `user_position` | pushback | the option that is the user's stated approach |
| `progress_items` | progress | `{label, status, detail?}` items; blocked subset must equal `options` |
| `list_style` | single_select / multi_select | `"ordered"` or `"unordered"` list render |

### MCP tools

`elicitation_render_form`, `elicitation_render_widget`,
`elicitation_collect_response`, and `elicitation_ask` — the same model,
exposed for agents that drive forms through the MCP server.

## Comparison

A form is the right tool when the exchange is genuinely a *choice* the
user makes. It is the wrong tool for an expository list ("here are three
reasons") — that expects no answer and is cheapest as plain markdown.
Reach for a construct when there is a fork, a recommendation, a
disagreement, or a status report to act on; reach for prose otherwise.

## Failure modes

### Rendering on a surface that has none

If a form is rendered to the widget surface but the client cannot post
back (`sendPrompt` unavailable), the submit button reports it and the
caller should fall back to `form_to_askuserquestion`. A rich widget needs
a widget-capable client; a plain terminal degrades to the menu fallback
by design.

### "Registered ≠ working until the server reboots"

A newly added construct or field reaches the live MCP server only after
the server restarts on the new version — the tool schema is loaded at
startup. Verify the live `elicitation_render_widget` schema actually
carries a new enum value before asserting the construct works end-to-end.

### A `progress` form whose blocked items disagree with its options

The bridge enforces `set(blocked labels) == set(options)`; a mismatch
raises `FormValidationError`. The picker can never offer a non-existent
blocker or omit a real one.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What are elicitation forms?
  **A:** Structured, interactive turns the agent uses instead of
  freeform prose: a multi-part question becomes one clickable form, a
  recommendation arrives as weighable cards, a disagreement renders
  side-by-side. Every form is one declarative artifact — a
  `FormSchema` of `FormQuestion`s built from plain data via
  `attune.elicitation.form_from_dict` — rendered per surface and
  validated the same way everywhere.
- **Q:** What constructs does the communication grammar have?
  **A:** Four, all members of the one form model: **intake** (several
  independent decisions as one multi-select-capable form),
  **decision** (a recommended option with rationale and per-option
  tradeoffs), **pushback** (the agent disagrees and offers a concrete
  alternative), and **progress** (a done/in_flight/blocked report
  whose blocked items are a picker). `decision`, `pushback`, and
  `progress` are presentation-enriched single-selects — the answer is
  always one option, validated by membership like any
  `single_select`.
- **Q:** Which MCP tools expose this?
  **A:** Four: `elicitation_render_form` (validate a form, return
  batched AskUserQuestion payloads), `elicitation_collect_response`
  (validate answers into `{field_id: value}`), `elicitation_ask`
  (native MCP elicitation dialog, one call in-and-out), and
  `elicitation_render_widget` (inline HTML for `show_widget`).
- **Q:** Which tool should I use on which surface?
  **A:** Widget-capable clients (Cowork / claude.ai):
  `elicitation_render_widget` — it renders all controls richly and is
  the surface where the `decision` / `pushback` / `progress` framing
  shows. Clients with native MCP elicitation: `elicitation_ask`
  (returns `{success: false, action: "unsupported"}` if the client
  can't elicit — it does not render on Claude Code today). Everywhere
  else: `elicitation_render_form` + the real `AskUserQuestion` tool,
  where constructs collapse to a recommendation-first single-select.
- **Q:** What field types are supported?
  **A:** The v1 AskUserQuestion path takes four: `text_input`,
  `single_select`, `multi_select`, `boolean`. The rich surfaces
  (`elicitation_ask`, `elicitation_render_widget`) add `textarea`,
  `number` (with `minimum`/`maximum`), `date` (YYYY-MM-DD), and the
  construct types `decision`, `pushback`, `progress`.
- **Q:** What happens when the user's answers are malformed?
  **A:** Validation is never skipped (R4).
  `elicitation_collect_response` enforces required fields and option
  membership; on failure it returns `{success: false, problems}`
  naming exactly the offending fields, so you re-ask only those —
  malformed input is never silently accepted.
- **Q:** How do widget answers get back to the agent?
  **A:** The rendered form posts answers via `sendPrompt` as a
  sentinel-marked JSON block (`__elicitation_response__`). Parse that
  block and validate it with `elicitation_collect_response`. The
  widget round-trip makes no Anthropic API call.
- **Q:** When should a construct fire?
  **A:** The grammar defines the *shape*; the *when* lives in the
  agent's Socratic rule and decision routine
  (`.claude/rules/attune/decision-routine.md`). The short version:
  build a form when two or more independent dimensions need settling
  (batch them into ONE form, never N sequential turns), when there are
  three or more alternatives or two with real tradeoffs, when you are
  disagreeing with the user, or when the answer is a number, date, or
  more than a phrase of text. A raw button-turn is right only for a
  single low-stakes choice among a few options. And a form never blocks
  a keyboard-only user: the terse reply vocabulary (`y` / `go` / `1`)
  answers any construct on any surface.
- **Q:** Why did a simple question render as a full form?
  **A:** The widget is the default now. If you'd rather have buttons,
  turn on keyboard mode — `{"keyboard_mode": true}` in the project's
  `./attune.config.json`, or `ATTUNE_KEYBOARD_MODE=1` for one shell.
- **Q:** Doesn't defaulting to the widget cost an extra round-trip?
  **A:** Yes, and that is deliberate. Latency was the old routing axis
  and it made the agent quietly downgrade forms that communicated
  better; if a question is worth asking, it is worth asking legibly.
  Trivial one-off choices still go to buttons.
- **Q:** Do forms cost API credits?
  **A:** No. Rendering and validation are pure local transforms — no
  model call on any surface.
- **Q:** Why didn't my rich form render?
  **A:** The client isn't widget-capable; it fell back to the
  `AskUserQuestion` menu. That's expected.
- **Q:** Is `progress` / `decision` / `pushback` a different answer shape?
  **A:** No — each answer is one selected option, validated like a
  single-select.

## Notes & tips

- Infer before you ask. If the answer is already in the conversation,
  skip the form and proceed — a one-question form beats five where four
  are already answerable.
- Use `recommended` to lead with a stated preference; the fallback surface
  orders it first.
- Keep option labels short. For richer options, the widget surface shows
  `option_notes` under each card.

## Design & extension

### The grammar's extension gate

A new construct is justified **only when rendering or answer-meaning
genuinely differs**. If the answer is shaped like an existing one (a
single-select pick), prefer reusing that answer path and adding a
`QuestionType` plus optional fields — not a parallel validator. If only
the *look* differs, it is a render variant of an existing type, not a new
member. The `list_style` list render is the worked example: it ships the
"intro + selectable list" shape as an option on the select types rather
than as a fifth construct.

### Adding a construct — the touch points

Even a construct that reuses the single-select answer path must register
its `QuestionType` at each enumeration site: the model, the definition
validator, the widget submit-script reader, the native-schema mapper, the
MCP tool schema (and its count guard), and the driving skill's docs. A
per-type "rejects out-of-option" test is the cheap guard that catches a
missed validation site. Prove it with a non-mocked round-trip — render,
submit, collect — not just unit tests.
