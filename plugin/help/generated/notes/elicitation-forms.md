---
name: elicitation-forms
source: content/features/elicitation-forms.md
tags:
- elicitation
- forms
- communication
- ux
- widget
type: note
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

## Notes & tips

- Infer before you ask. If the answer is already in the conversation,
  skip the form and proceed — a one-question form beats five where four
  are already answerable.
- Use `recommended` to lead with a stated preference; the fallback surface
  orders it first.
- Keep option labels short. For richer options, the widget surface shows
  `option_notes` under each card.
