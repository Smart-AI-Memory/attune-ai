---
type: faq
name: elicitation-forms-faq
feature: elicitation-forms
depth: faq
status: manual
---

# Elicitation Forms FAQ

## What are elicitation forms?

Structured, interactive turns the agent uses instead of freeform
prose: a multi-part question becomes one clickable form, a
recommendation arrives as weighable cards, a disagreement renders
side-by-side. Every form is one declarative artifact — a `FormSchema`
of `FormQuestion`s built from plain data via
`attune.elicitation.form_from_dict` — rendered per surface and
validated the same way everywhere.

## What constructs does the communication grammar have?

Four, all members of the one form model: **intake** (several
independent decisions as one multi-select-capable form), **decision**
(a recommended option with rationale and per-option tradeoffs),
**pushback** (the agent disagrees and offers a concrete alternative),
and **progress** (a done/in_flight/blocked report whose blocked items
are a picker). `decision`, `pushback`, and `progress` are
presentation-enriched single-selects — the answer is always one
option, validated by membership like any `single_select`.

## Which MCP tools expose this?

Four: `elicitation_render_form` (validate a form, return batched
AskUserQuestion payloads), `elicitation_collect_response` (validate
answers into `{field_id: value}`), `elicitation_ask` (native MCP
elicitation dialog, one call in-and-out), and
`elicitation_render_widget` (inline HTML for `show_widget`).

## Which tool should I use on which surface?

Widget-capable clients (Cowork / claude.ai): `elicitation_render_widget`
— it renders all controls richly and is the surface where the
`decision` / `pushback` / `progress` framing shows. Clients with
native MCP elicitation: `elicitation_ask` (returns
`{success: false, action: "unsupported"}` if the client can't elicit
— it does not render on Claude Code today). Everywhere else:
`elicitation_render_form` + the real `AskUserQuestion` tool, where
constructs collapse to a recommendation-first single-select.

## What field types are supported?

The v1 AskUserQuestion path takes four: `text_input`,
`single_select`, `multi_select`, `boolean`. The rich surfaces
(`elicitation_ask`, `elicitation_render_widget`) add `textarea`,
`number` (with `minimum`/`maximum`), `date` (YYYY-MM-DD), and the
construct types `decision`, `pushback`, `progress`.

## What happens when the user's answers are malformed?

Validation is never skipped (R4). `elicitation_collect_response`
enforces required fields and option membership; on failure it
returns `{success: false, problems}` naming exactly the offending
fields, so you re-ask only those — malformed input is never
silently accepted.

## How do widget answers get back to the agent?

The rendered form posts answers via `sendPrompt` as a
sentinel-marked JSON block (`__elicitation_response__`). Parse that
block and validate it with `elicitation_collect_response`. The
widget round-trip makes no Anthropic API call.

## When should a construct fire?

That is a judgment call governed by the agent's decision routine
(`.claude/rules/attune/decision-routine.md`), not by this
subsystem — the grammar defines the *shape*, not the *when*. And a
form never blocks a keyboard-only user: the terse reply vocabulary
(`y` / `go` / `1`) answers any construct on any surface.

**Tags:** `elicitation`, `forms`, `communication`, `ux`, `widget`
