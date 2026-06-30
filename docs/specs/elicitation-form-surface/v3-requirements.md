# Elicitation Form Surface — V3 Requirements

## The decision construct (communication grammar)

V3 adds the first **non-intake** member of this spec's declarative-form
family. V1/V2 built the substrate for *intake* (gather input across
dimensions) and proved the S1 widget round-trip live (D11), adopted into
`/spec`, `/attune`, `/planning` (D13). V3 adds a **decision** construct:
the agent offers a recommended choice with rationale and ranked
alternatives; the user picks one.

This is the "opening-shape" Patrick reacted to in session (2026-06-29).
Naming the family of constructs over the proven substrate is the
"communication grammar." Folded here from a standalone draft per D14.

## What already exists — reuse, do not rebuild

- `FormSchema` / `FormQuestion` / `QuestionType` / `FormResponse`
  (`meta_workflows/models.py`).
- `form_to_widget_html` (`elicitation/widget.py`) — the S1 renderer,
  live round-trip proven (D11).
- `collect_form_response` validation (R4).
- The `elicit` skill surface-mapping + AskUserQuestion fallback (D7).

## The gap — confirmed against widget.py + models.py

A decision is a presentation-enriched `SINGLE_SELECT`. The substrate
cannot today express:

- a recommended option (marker / badge),
- per-option one-line tradeoffs,
- a rationale / "why it matters" callout distinct from `help_text`.

`SINGLE_SELECT` renders a flat `<select>`: no card layout, no
recommendation, no rationale slot.

## Key insight — the answer path is unchanged

A decision's answer is exactly one selected option, which is what
`SINGLE_SELECT` already validates (membership). So the round-trip
(sentinel JSON → `collect_form_response`) and validation are reused
**untouched**. V3 is presentation plus a thin, additive model
extension only.

This surface makes **no Anthropic API call** (`form_to_widget_html` →
`show_widget` → `sendPrompt` → `collect_form_response` are all pure /
client-side), so V3 is fully buildable and dogfoodable with no API
credits.

## Requirements

- RV3.1 — Add `QuestionType.DECISION` (an enriched single-select).
- RV3.2 — Additive optional `FormQuestion` fields: `rationale`
  (`str | None`), `option_notes` (`dict[str, str] | None`, option →
  tradeoff), `recommended` (`str | None`, must be one of `options`).
  All optional; existing forms unaffected.
- RV3.3 — `widget.py` renders `DECISION` as cards: a badged
  recommended card first, ranked alternatives, a rationale callout;
  the answer posts as the selected option (same payload shape).
- RV3.4 — AskUserQuestion fallback (`elicit` skill): `DECISION` maps
  to a `single_select`, recommendation-first ordering (already the
  skill's convention, D7), tradeoffs folded into option help.
- RV3.5 — Degrades to a readable static card where `sendPrompt` is
  absent (inherits the widget's behavior).
- RV3.6 — A "communication grammar" doc names the construct family
  and how to add the next construct.
- RV3.7 — `collect_form_response` and the round-trip are unchanged;
  guarded by reusing the existing validation tests.

## Acceptance criteria

- AC1 — `DECISION` type + fields added; existing form tests stay green
  (additive, backward-compatible).
- AC2 — A real decision renders as the card layout (recommended badge
  + tradeoffs + rationale) AND as the AskUserQuestion fallback, from
  one `FormSchema`.
- AC3 — Round-trip proven: `form_to_widget_html` → `show_widget` →
  pick → `sendPrompt` sentinel → `collect_form_response` success (the
  receipt; mirrors D11). Function + `show_widget` level provable in
  session; the full MCP-tool path on next server boot (D9/D11
  pattern).
- AC4 — Static fallback verified (`sendPrompt` undefined → readable).
- AC5 — Keyboard accessible (role / tabindex / Enter + Space) on the
  option cards.
- AC6 — Grammar doc explains the family and how to add construct #3.

## Out of scope

- New surfaces — native MCP elicitation stays out (D10).
- `slider` / `color` controls (still deferred).
- The trigger discipline (when a decision fires) lives in
  `decision-routine.md`, unchanged. V3 is the rendering / artifact,
  not the when.

## Tasks (for review)

- T1 — model: `QuestionType.DECISION` + 3 optional fields +
  validation (`recommended` in `options`).
- T2 — `widget.py`: `_control_html` `DECISION` branch (cards + badge +
  rationale callout) + accessibility.
- T3 — `elicit` skill: `DECISION` → AskUserQuestion fallback mapping.
- T4 — communication-grammar doc (family + how to extend).
- T5 — tests: model (additive), widget render (structure), round-trip
  reuse; plus the live dogfood receipt (AC3).
