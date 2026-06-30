# Elicitation Form Surface — V4 Requirements

## The pushback construct (communication grammar member #3)

V4 adds the **pushback** construct — the third member of this spec's
declarative-form family and the second non-intake one (after V3's
`decision`). Where a `decision` offers a *neutral* recommendation, a
pushback frames **dissent**: the agent disagrees with the user's stated
approach and presents a concrete alternative + rationale, and the user
chooses to overrule or switch.

Patrick chose this as construct #3 (2026-06-30) over a status/progress
construct, and chose **a new `QuestionType.PUSHBACK`** over composing
the existing `decision` type — because the whole value of pushback over
decision is the dissent framing; composing would be a doc note, not a
construct. Scope is **substrate + one consumer**.

## What already exists — reuse, do not rebuild

- `FormSchema` / `FormQuestion` / `QuestionType` / `FormResponse`
  (`meta_workflows/models.py`).
- The V3 `decision` machinery: `rationale` / `option_notes` /
  `recommended` fields (`models.py:95-97`), the card renderer
  (`widget.py:_control_html` DECISION branch, `:57-75`), the rationale
  callout (`widget.py:141-156`), and `form_from_dict` validation of the
  decision extras (`bridge.py:140-179`).
- `collect_form_response` validation (R4) and the live round-trip
  (`form_to_widget_html` → `show_widget` → `sendPrompt` sentinel →
  `collect_form_response`), proven for `decision` in D15.
- The `elicit` skill surface-mapping + AskUserQuestion fallback (D7).

## The gap — confirmed against models.py + widget.py + bridge.py

A pushback is a presentation-enriched `SINGLE_SELECT` like `decision`,
but the substrate cannot express the dissent framing:

- which option is **the user's stated approach** (the status-quo card),
  vs the agent's preferred alternative;
- the dissent labels — a "your approach" tag on the user's option, an
  "I'd suggest instead" badge on the alternative (not "Recommended"),
  and a "Why I'd push back" rationale header (not "Why").

`decision` renders all alternatives as peers with one neutral
"Recommended" badge — it cannot show *which* option the user already
chose, so it reads as advice, not disagreement.

## Key insight — the answer path is unchanged

A pushback's answer is exactly one selected option (overrule = the
user's approach; switch = the alternative), which `SINGLE_SELECT`
already validates by membership. The round-trip (sentinel JSON →
`collect_form_response`) and validation are reused **untouched**. V4 is
the dissent presentation plus a thin, additive model extension —
exactly the V3 shape.

This surface makes **no Anthropic API call**, so V4 is fully buildable
and dogfoodable with no API credits (same as V3).

## Requirements

- RV4.1 — Add `QuestionType.PUSHBACK` (an enriched single-select with
  dissent framing).
- RV4.2 — One additive optional `FormQuestion` field: `user_position`
  (`str | None`, must be one of `options` when set) — the option that
  is the user's stated approach. Reuse `recommended` (= the agent's
  alternative), `rationale` (= the disagreement rationale), and
  `option_notes` (= per-option tradeoffs) unchanged. All optional;
  existing forms unaffected.
- RV4.3 — `widget.py` renders `PUSHBACK` as cards: the `user_position`
  card tagged "your approach", the `recommended` card badged "I'd
  suggest instead" and ordered first, a "Why I'd push back" rationale
  callout. The answer posts as the selected option (same payload
  shape; reuse the decision JS reader).
- RV4.4 — AskUserQuestion fallback (`elicit` skill): `PUSHBACK` maps to
  a `single_select`, agent's alternative first (recommendation-first,
  D7), the user's approach clearly labelled, rationale folded into the
  question text / option help.
- RV4.5 — Degrades to a readable static card where `sendPrompt` is
  absent (inherits the widget's behavior).
- RV4.6 — `form_from_dict` (`bridge.py`) validates the pushback fields:
  `user_position` and `recommended` must each be in `options`; reuse
  the decision validation for `rationale` / `option_notes`.
- RV4.7 — `collect_form_response` and the round-trip are unchanged;
  guarded by reusing the existing validation tests.
- RV4.8 — **Consumer (substrate + one consumer):** wire pushback into
  the `/spec` task-review gate — when the user rejects/edits a task in
  a way the agent assesses as weaker AND it can render the concrete
  alternative, present a `pushback` instead of prose (the
  decision-routine "pushback discipline"). `decision-routine.md` gains
  a pointer naming the pushback construct as THE concrete artifact its
  discipline requires. (Exact gate confirmed at task review — see T6.)
- RV4.9 — Surfaces: widen the rich enum in `mcp/tool_schemas.py` to
  include `pushback` and update the count guard in
  `tests/unit/mcp/test_tool_schemas.py`; map it in
  `elicitation_schema.py` if native elicitation should carry it; keep
  `.agents/` skill mirrors synced (`scripts/sync_agents_skills.py`).

## Acceptance criteria

- AC1 — `PUSHBACK` type + `user_position` field added; existing form
  tests stay green (additive, backward-compatible).
- AC2 — A real pushback renders as the dissent card layout ("your
  approach" tag + "I'd suggest instead" badge + "Why I'd push back"
  rationale) AND as the AskUserQuestion fallback, from one
  `FormSchema`.
- AC3 — Round-trip proven live: `elicitation_render_widget` →
  `show_widget` → pick → `sendPrompt` sentinel →
  `elicitation_collect_response` success (the receipt; mirrors D15).
- AC4 — Static fallback verified (`sendPrompt` undefined → readable).
- AC5 — Keyboard accessible (radiogroup / Enter + Space) on the cards.
- AC6 — The consumer fires: the `/spec` task-review gate renders a
  pushback when the agent disagrees, and `decision-routine.md` points
  to the construct.
- AC7 — `communication-grammar.md` lists pushback as member #3 and the
  "how to add the next construct" worked example still holds.

## Out of scope

- New surfaces — native MCP elicitation stays a non-renderer on CC
  (D10); only the enum/mapping is touched for forward-compat.
- `slider` / `color` controls (still deferred).
- The trigger discipline (WHEN to push back) lives in
  `decision-routine.md`; V4 supplies the artifact + one wired gate, not
  a rewrite of the discipline.
- A status/progress construct (the option not chosen) — future #4.

## Tasks (for review)

- T1 — model: `QuestionType.PUSHBACK` + `user_position` field +
  `to_askuserquestion` fallback (recommendation-first, like decision).
- T2 — `bridge.py`: `form_from_dict` validates `PUSHBACK`
  (`user_position` ∈ options; reuse decision extras validation).
- T3 — `widget.py`: `_control_html` `PUSHBACK` cards (your-approach tag
  + "I'd suggest instead" badge + "Why I'd push back" callout) + CSS +
  accessibility; reuse the decision JS reader.
- T4 — `elicit` skill: `PUSHBACK` → AskUserQuestion fallback mapping
  (+ `.agents/` mirror via `sync_agents_skills.py`).
- T5 — surfaces: `mcp/tool_schemas.py` enum + `test_tool_schemas.py`
  count guard; `elicitation_schema.py` map (forward-compat).
- T6 — consumer: wire pushback into the `/spec` task-review gate +
  `decision-routine.md` pointer (RV4.8; confirm exact gate here).
- T7 — `communication-grammar.md`: add pushback as member #3.
- T8 — tests: model (additive) + bridge validation + widget render
  (dissent structure) + round-trip reuse; plus the live dogfood
  receipt (AC3).
