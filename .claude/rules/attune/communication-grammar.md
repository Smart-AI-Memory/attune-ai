---
paths:
  - "src/attune/elicitation/**"
  - "src/attune/meta_workflows/**"
  - "plugin/skills/elicit/**"
  - ".agents/skills/elicit/**"
---

# Communication Grammar

**Created:** 2026-06-29
**Spec:** [docs/specs/elicitation-form-surface/](../../../docs/specs/elicitation-form-surface/)
(V3 — decisions.md D14, v3-requirements.md)

---

## What this is

A small, growing **family of conversational constructs** the agent
composes to communicate with the user — structured shapes instead of
freeform prose. Each construct is a member of one declarative-form
substrate (`attune.meta_workflows.models.FormSchema`), so the same
artifact renders on every surface and validates the same way.

The grammar is **agent-to-user expression** (how the agent structures
what it offers). It is not user-to-agent command syntax, and it does not
replace the terse reply vocab (`y` / `go` / `1`) — those are the
*answers* to a construct.

Constructs fire **reactively**, in the live conversation — never on a
schedule. When a construct fires (e.g. the decision construct on a
non-trivial choice) is governed by
[decision-routine.md](decision-routine.md), not here; this file is the
*shape*, not the *when*.

---

## The substrate (shared by every construct)

- **One artifact** — a `FormSchema` of `FormQuestion`s, built from plain
  data via `attune.elicitation.form_from_dict` (D3).
- **Renderers** — `form_to_widget_html` (the widget surface, the rich
  one that renders on Claude Code, D10/D11); the `AskUserQuestion`
  fallback (`form_to_askuserquestion`); native MCP elicitation
  (`form_to_elicitation_schema`, currently non-rendering on CC).
- **One validator** — `collect_form_response` (R4): never silently
  accept malformed input; re-ask only the offending fields.

A construct adds **meaning and presentation** on top of this substrate;
it almost never adds a new round-trip or validator.

---

## Members

### intake-form (v1 / v2 — shipped)

Gather the independent dimensions of one decision as a single
(multi-select-capable) form. Driven by the `elicit` skill; adopted into
`/spec`, `/attune`, `/planning` (D13). Question types: `single_select`,
`multi_select`, `boolean`, `text_input`, `number`, `date`, `textarea`.

### decision / opening-shape (v3)

The agent offers a **recommended** option with a **rationale** and
per-option **tradeoffs**; the user picks one. A `QuestionType.DECISION`
is a presentation-enriched single-select — the answer is one option,
validated exactly as a single-select. Extra `FormQuestion` slots:
`recommended`, `rationale`, `option_notes`. Renders as cards (badge +
tradeoffs + rationale) on the widget surface; falls back to a
recommendation-first single-select on `AskUserQuestion`.

### pushback (v4)

The agent **disagrees** with the user's stated approach and offers a
concrete alternative + a disagreement rationale; the user picks one
(overrule = keep their approach, or switch). A `QuestionType.PUSHBACK`
is — like `decision` — a presentation-enriched single-select; the
answer is one option, validated exactly as a single-select. It adds one
optional slot, `user_position` (the option that is the user's stated
approach), and reuses `recommended` (= the agent's alternative),
`rationale`, and `option_notes`. The dissent framing is what
distinguishes it from `decision`: the `user_position` card is tagged
"your approach", the `recommended` card is badged "I'd suggest instead"
(not "Recommended") and ordered first, and the rationale callout is
headed "Why I'd push back". Falls back to a recommendation-first
single-select on `AskUserQuestion`. When the pushback construct fires is
governed by [decision-routine.md](decision-routine.md)'s pushback
discipline — this is the shape, not the when.

### progress (v5)

The agent **reports** a set of items by status — `done` / `in_flight` /
`blocked` — and surfaces the **blocked** items as a single-select picker
("which blocker do you want to tackle?"); the user picks one. It is the
first member that is a *report* rather than a fork. A
`QuestionType.PROGRESS` is — like `decision` / `pushback` — a
presentation-enriched single-select whose answer is one blocked option,
validated exactly as a single-select. It adds one optional slot,
`progress_items` (the reported items as `{label, status, detail?}` dicts;
the `blocked` subset's labels must equal `options`), and reuses
`recommended` (= the blocked item to tackle first, badged "suggested
next"), `rationale` (= a "Summary" callout), and `option_notes`. The
widget renders three buckets: `done`/`in_flight` items as static rows,
`blocked` items as the radiogroup picker. When **nothing is blocked**
(`options` empty) it degrades to a pure status display with no answer —
so "pure display" is a sub-state of one construct, not a separate member,
and the substrate stays answer-validated whenever there is something
actionable. Falls back to a recommendation-first single-select over the
blocked items on `AskUserQuestion` (the done/in_flight summary folds into
the question text). First consumer: the `/spec` execute gate (done =
completed tasks, in_flight = current task, blocked = quality-gate
failures; the picker = "which blocked task to fix/retry").

---

## How to add the next construct (#5)

Keep it additive and substrate-reusing. The decision (v3), pushback
(v4), and progress (v5) constructs are the worked examples to copy.

1. **Decide the shape.** Does it compose existing question types, or
   need a new `QuestionType`? Prefer composing. A new type is justified
   only when rendering or answer-meaning genuinely differs.
2. **Extend the model additively** (`meta_workflows/models.py`). Add the
   `QuestionType` member and any *optional* `FormQuestion` fields
   (defaults `None`), so every existing form is unaffected.
3. **Reuse the answer path.** Map the new type's answer validation to an
   existing validator in `bridge.py::_validate_answer` if the answer is
   shaped like one already (a decision validates as a single-select).
   Only add validation logic for a genuinely new answer shape.
4. **Render it.** Add a branch to `widget.py::_control_html` (and the
   submit-script reader if the control isn't a plain input), plus any
   styles. Keep the `sendPrompt` guard so it degrades to a readable
   static card.
5. **Definition validation.** Extend `bridge.py::form_from_dict` to
   parse and validate the new fields (e.g. a referenced option must
   exist).
6. **Surfaces.** Widen the rich enum in `mcp/tool_schemas.py` (update
   the count guard in `tests/unit/mcp/test_tool_schemas.py`), map it in
   `elicitation_schema.py` if native elicitation should carry it, and
   document the construct + its `AskUserQuestion` fallback in the
   `elicit` skill (both `plugin/` and `.agents/` copies).
7. **Prove it.** Add a test module under `tests/unit/elicitation/`
   (model + definition validation + render + round-trip + fallback) and
   **dogfood the live widget round-trip** — render a real form, submit,
   and validate the postback (the receipt). The widget path makes no
   Anthropic API call, so this is provable without credits.

---

## Cross-references

- [decision-routine.md](decision-routine.md) — when the decision
  construct fires (the trigger discipline; this file is the shape).
- `plugin/skills/elicit/SKILL.md` — the live skill that drives the
  substrate and carries the per-surface mapping rules.
- [docs/specs/elicitation-form-surface/](../../../docs/specs/elicitation-form-surface/)
  — the full decision log (D1–D14) and phase requirements.
