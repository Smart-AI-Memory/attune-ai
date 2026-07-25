---
type: faq
name: elicitation-forms-faq
feature: elicitation-forms
depth: faq
generated_at: 2026-07-25T05:58:04.934219+00:00
source_hash: 9670395c7ce23f96b61ec57648f0a6c01aad19746a4f965901b5f07a5f070d2c
status: generated
---

# Elicitation Forms FAQ

## What are elicitation forms?

Structured, interactive turns the agent uses instead of
freeform prose: a multi-part question becomes one clickable form, a
recommendation arrives as weighable cards, a disagreement renders
side-by-side. Every form is one declarative artifact — a
`FormSchema` of `FormQuestion`s built from plain data via
`attune.elicitation.form_from_dict` — rendered per surface and
validated the same way everywhere.

## What constructs does the communication grammar have?

Four, all members of the one form model: **intake** (several
independent decisions as one multi-select-capable form),
**decision** (a recommended option with rationale and per-option
tradeoffs), **pushback** (the agent disagrees and offers a concrete
alternative), and **progress** (a done/in_flight/blocked report
whose blocked items are a picker). `decision`, `pushback`, and
`progress` are presentation-enriched single-selects — the answer is
always one option, validated by membership like any
`single_select`.

## Which MCP tools expose this?

Four: `elicitation_render_form` (validate a form, return
batched AskUserQuestion payloads), `elicitation_collect_response`
(validate answers into `{field_id: value}`), `elicitation_ask`
(native MCP elicitation dialog, one call in-and-out), and
`elicitation_render_widget` (inline HTML for `show_widget`).

## Which tool should I use on which surface?

Widget-capable clients (Cowork / claude.ai):
`elicitation_render_widget` — it renders all controls richly and is
the surface where the `decision` / `pushback` / `progress` framing
shows. Clients with native MCP elicitation: `elicitation_ask`
(returns `{success: false, action: "unsupported"}` if the client
can't elicit — it does not render on Claude Code today). Everywhere
else: `elicitation_render_form` + the real `AskUserQuestion` tool,
where constructs collapse to a recommendation-first single-select.

## What field types are supported?

The v1 AskUserQuestion path takes four: `text_input`,
`single_select`, `multi_select`, `boolean`. The rich surfaces
(`elicitation_ask`, `elicitation_render_widget`) add `textarea`,
`number` (with `minimum`/`maximum`), `date` (YYYY-MM-DD), and the
construct types `decision`, `pushback`, `progress`.

## What happens when the user's answers are malformed?

Validation is never skipped (R4).
`elicitation_collect_response` enforces required fields and option
membership; on failure it returns `{success: false, problems}`
naming exactly the offending fields, so you re-ask only those —
malformed input is never silently accepted.

## How do widget answers get back to the agent?

The rendered form posts answers via `sendPrompt` as a
sentinel-marked JSON block (`__elicitation_response__`). Parse that
block and validate it with `elicitation_collect_response`. The
widget round-trip makes no Anthropic API call.

## When should a construct fire?

The grammar defines the *shape*; the *when* lives in the
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

## Why did a simple question render as a full form?

The widget is the default now. If you'd rather have buttons,
run `attune config set keyboard_mode true` — it persists for this
project. `ATTUNE_KEYBOARD_MODE=1` overrides it for one shell.

## Doesn't defaulting to the widget cost an extra round-trip?

Yes, and that is deliberate. Latency was the old routing axis
and it made the agent quietly downgrade forms that communicated
better; if a question is worth asking, it is worth asking legibly.
Trivial one-off choices still go to buttons.

## Do forms cost API credits?

No. Rendering and validation are pure local transforms — no
model call on any surface.

## Why didn't my rich form render?

The client isn't widget-capable; it fell back to the
`AskUserQuestion` menu. That's expected.

## Is `progress` / `decision` / `pushback` a different answer shape?

No — each answer is one selected option, validated like a
single-select.
