---
type: note
name: socratic-interaction-rule
tags: [philosophy, ux]
source: .claude/CLAUDE.md
---

# Note: Socratic Interaction Rule

## Context

Core UX principle: always guide users with questions before executing actions.

## Content

**Ask the material unknowns first, then execute — and when you ask,
ask once.** This rule is Anthropic's default for Claude plus Attune's
deltas (host-surface-parity D16, chair-ruled 2026-09-07). The baseline
is the host's: on a routine call, assume the sensible reading, state
the assumption, and proceed. Escalate to an ask only when the answer
would change the work.

### Ask when ANY of these holds

- The choice changes scope, architecture, files, external state, or
  acceptance criteria — or is hard to reverse.
- Two or more readings of the request are genuinely valid and lead to
  materially different work. Never guess on a genuine ambiguity.
- Three or more alternatives, or two with tradeoffs worth stating
  (the `decision` shape).
- You are recommending against something the user named (the
  `pushback` shape).
- The answer is a number, a date, or free text longer than a phrase.

When none holds, do not ask: assume, disclose the assumption in your
report, and keep going. Ceremony is the failure mode this rule is most
likely to cause.

### One batched ask, on the host's native control

When you do ask, gather every open dimension of the decision into ONE
`AskUserQuestion` call, never N sequential turns: 1–4 questions, 2–4
options each, the recommendation ordered first with " (Recommended)"
— except a `confirm` gate, which carries no recommended pick by
construction — free text through the built-in "Other" (do not add an
Other option), and `metadata.source` set to `"elicit-form"` for a
batch of more than one question or `"confirm-gate"` for that
two-option confirm (the format guard's two opt-ins; added 2026-09-11 —
the guard predated D16). Beyond four open dimensions,
split into successive calls of at most four, most consequential first,
and drop none; when the overflow is in options rather than questions,
use a two-tier picker (category, then item). No `FormSchema` is needed
on this path. Validate the returned answers against the questions you
asked, retain partial answers, correct only the affected answer, and
treat an interrupted or dismissed call as cancellation; an errored call
is a tool failure, so say so and ask conversationally. The `elicit`
skill's **Claude** host default is the full contract.

The native control carries the decision-shaped constructs too:

- `decision` / `pushback` — alternative or recommendation first,
  tradeoffs in each option's `description`, the rationale as the
  question's lead-in, richer notes in `preview`.
- `progress` / `deliberation` — the summary in the question text, the
  pickable items as options (two-tier picker beyond four).
- `confirm` — exactly two options and **no recommended option**: a
  pre-badged approval is what the construct exists to forbid.
- `assumption_review` — one question per assumption (up to four per
  call), accept / reject as options, edit through "Other".

### Constructs the native control cannot express

`ranking` (no ordering control), `triage` over four items, the
`number` / `date` / `textarea` fields, and a library-routed
`assumption_review` (its edit lane is a text question; an agent-composed
card with accept / reject and one edit through "Other" stays legal) have
no honest `AskUserQuestion` shape. For these, and only these, build the
`FormSchema` via `attune.elicitation.form_from_dict` and render
`form_to_widget_html(form)` through `show_widget` on a widget-capable
session (D17; desktop acceptance observed 2026-09-07). Where no widget
exists, or the user is in keyboard mode: one typed question for a single
`number` / `date` / `textarea`; the `form_to_markdown` skeleton with a
deterministic parse for a ranking, triage, assumption review, or any
multi-field form. Never silently drop a field. Otherwise the widget and
Attune forms are experimental in this repository too: use them only when
the user asks for a form or a trial.

### Two grammars, two directions — not a ranking

They are not competing methods and neither is "primary". They serve
opposite directions of the same exchange:

| Direction | Grammar | When |
|---|---|---|
| I ask | a batched ask | something genuinely needs settling |
| You answer | terse vocab (`y` / `go` / `1` / `→ X`) | it is already settled |

A bare confirm is **not an ask** — it is you closing a loop I opened.
Putting an ask in front of `go` adds friction to the highest-frequency
interaction in the loop. Do not do it.

The failure mode this rule guards is not "used terse vocab where a
batched ask belonged." It is **mis-classifying a multi-dimension ask as
a bare confirm** because prose is faster to write.

### Examples

- "run tests" → routine; run them.
- "audit src/ for secrets" → scope given; run it and disclose the depth
  you chose.
- "security audit" with nothing else → path + focus + depth → ONE
  batched ask, three questions.
- "commit" → files + change kind, when either is open → ONE batched
  ask.
- "retry 3x?" when backoff is better → `pushback` on the native
  control.

**Do NOT:**

- Assume the user wants the broadest possible execution
- Ask N sequential button-turns for what is one batched ask
- Re-ask a dimension the user already stated
- Pad an ask with questions you don't need
- Badge a recommended option on a confirm gate

This rule applies to ALL workflow interactions, not just `/attune`.

---

## Related Topics

_No related topics yet._
