# Elicitation Form Surface — V5 Requirements

## The progress construct (communication grammar member #4)

V5 adds the **progress** construct — the fourth member of this spec's
declarative-form family and the first that is a *report* rather than a
fork. Where `intake` (#1), `decision` (#2), and `pushback` (#3) each ask
the user to choose, a progress construct **reports** the state of a set
of items — done / in-flight / blocked — agent→user, and surfaces the
**blocked** items as a single-select picker ("which blocker do you want
to tackle?").

Patrick chose this as construct #4 (2026-06-30) over stopping the
grammar, chose the **report + blocked-item picker** answer path over a
pure display or a bare acknowledge, and chose the **`/spec` execute
gate** as the first consumer. Scope is **substrate + one consumer**.

## Why it still fits the substrate

The substrate (`FormSchema` of `FormQuestion`s + `collect_form_response`
validation, R4) is built around *questions with answers*. A pure status
display would never run the validator — markdown-in-a-form, the weakest
fit. The chosen shape keeps the construct answer-validated: the report's
**blocked** items become the `options` of a `SINGLE_SELECT`, so the
answer is exactly one selected blocker — validated by membership,
**reusing the decision/pushback answer path untouched**.

When there are **zero blocked items**, `options` is empty and the
construct degrades to a pure status *display* (no radiogroup, no answer).
That makes "pure display" a natural sub-state of one construct, not a
separate member — the substrate stays answer-validated whenever there is
something actionable.

This surface makes **no Anthropic API call**, so V5 is fully buildable
and dogfoodable with no API credits (same as V3/V4).

## What already exists — reuse, do not rebuild

- `FormSchema` / `FormQuestion` / `QuestionType` / `FormResponse`
  (`meta_workflows/models.py`).
- The single-select answer path: `to_ask_user_format`
  (`models.py:119-131`, recommendation-first ordering) and
  `collect_form_response` membership validation (R4).
- The V3/V4 card machinery: `recommended` / `rationale` / `option_notes`
  fields (`models.py:106-109`), the card renderer and rationale callout
  (`widget.py:_control_html`), and `form_from_dict` validation of the
  decision/pushback extras (`bridge.py`).
- The live round-trip (`form_to_widget_html` → `show_widget` →
  `sendPrompt` sentinel → `collect_form_response`), proven for
  `decision` (D15) and `pushback` (D16).
- The `elicit` skill surface-mapping + AskUserQuestion fallback (D7).

## The gap — confirmed against models.py + widget.py + bridge.py

A progress report is a `SINGLE_SELECT` over its blocked items, but the
substrate cannot express the report itself:

- the **non-answerable** items — everything that is `done` or
  `in_flight` is reported but is NOT a pickable option;
- the per-item **status** (`done` / `in_flight` / `blocked`) that drives
  the three-bucket layout and the status badges.

`option_notes` carries per-option detail but only for items that ARE
options; there is no way to carry items that are reported-but-not-
answerable, nor their status. That is the one genuinely new piece of
data V5 adds.

## Naming

New enum member `QuestionType.PROGRESS = "progress"` (single word, like
`DECISION` / `PUSHBACK`). The grammar member is the "progress" /
"status-report" construct.

## Requirements

- RV5.1 — Add `QuestionType.PROGRESS` (a report that renders three
  status buckets and offers its blocked items as an enriched
  single-select picker).
- RV5.2 — One additive optional `FormQuestion` field: `progress_items`
  (`list[dict[str, str]] | None`), each item `{label, status, detail?}`
  with `status` ∈ {`done`, `in_flight`, `blocked`}. Reuse `recommended`
  (= the blocked item to suggest tackling first), `rationale` (= the
  report summary / "why this next" callout), and `option_notes` (=
  per-blocked-item detail) unchanged. All optional; existing forms
  unaffected.
- RV5.3 — Invariant: `options` MUST equal the set of `progress_items`
  whose `status == "blocked"` (the picker offers exactly the actionable
  items). `recommended`, when set, MUST be one of `options`.
- RV5.4 — `widget.py` renders `PROGRESS` as three buckets — Done (✓),
  In-flight (◐), Blocked (✕) — with status badges. `done`/`in_flight`
  items are **static rows** (not selectable); `blocked` items are the
  **selectable radiogroup cards** (the picker), `recommended` ordered
  first with a "suggested next" badge, optional `rationale` callout. The
  answer posts as the selected option (same payload shape; reuse the
  decision JS reader).
- RV5.5 — Empty-blocked degrade: when no item is `blocked` (`options`
  empty), render a pure status display — no radiogroup, no answer
  control — and the round-trip is a no-op (display only).
- RV5.6 — AskUserQuestion fallback (`elicit` skill): `PROGRESS` folds
  the done/in-flight/blocked summary into the question text and maps the
  blocked items to a `single_select` (suggested-first, D7). When there
  are no blocked items there is no AskUserQuestion to ask — the agent
  narrates the report.
- RV5.7 — Degrades to a readable static report where `sendPrompt` is
  absent (inherits the widget's behavior).
- RV5.8 — `form_from_dict` (`bridge.py`) validates the progress fields:
  each `progress_items` entry has a valid `status`; the blocked subset
  equals `options` (RV5.3); `recommended` ∈ `options`; reuse the
  decision validation for `rationale` / `option_notes`.
- RV5.9 — `collect_form_response` and the round-trip are unchanged (the
  answer is a single-select membership check); guarded by reusing the
  existing validation tests.
- RV5.10 — **Consumer (substrate + one consumer):** wire `progress`
  into the `/spec` execute gate — render a progress report at the
  execute loop's reporting point: `done` = completed tasks, `in_flight`
  = the current task, `blocked` = tasks that failed a quality gate
  (severity-gated). The blocked-item picker = "which blocked task to
  fix/retry", and selecting one routes to the fix-and-retry path. (Exact
  integration point confirmed at task review — see T6.)
- RV5.11 — Surfaces: widen the rich enum in `mcp/tool_schemas.py` to
  include `progress` (9→10) and add `progress_items`; update the count
  guard in `tests/unit/mcp/test_tool_schemas.py`; map it in
  `elicitation_schema.py` (forward-compat); keep `.agents/` skill
  mirrors synced (`scripts/sync_agents_skills.py`).

## Acceptance criteria

- AC1 — `PROGRESS` type + `progress_items` field added; existing form
  tests stay green (additive, backward-compatible).
- AC2 — A real progress report renders as the three-bucket layout
  (done/in-flight static rows + blocked radiogroup picker with
  "suggested next" badge) AND as the AskUserQuestion fallback, from one
  `FormSchema`.
- AC3 — Round-trip proven live: `elicitation_render_widget` →
  `show_widget` → pick a blocked item → `sendPrompt` sentinel →
  `elicitation_collect_response` success (the receipt; mirrors D15/D16).
- AC4 — Empty-blocked degrade verified: a report with no blocked items
  renders as a pure display (no picker) and is a round-trip no-op.
- AC5 — Static fallback verified (`sendPrompt` undefined → readable
  report).
- AC6 — Keyboard accessible (radiogroup / Enter + Space) on the blocked
  cards.
- AC7 — The consumer fires: the `/spec` execute gate renders a progress
  report with the blocked-task picker.
- AC8 — `communication-grammar.md` lists progress as member #4 and the
  "how to add the next construct" worked example still holds.

## Out of scope

- New surfaces — native MCP elicitation stays a non-renderer on CC
  (D10); only the enum/mapping is touched for forward-compat.
- `slider` / `color` controls (still deferred).
- Multi-select over blocked items (tackle several at once) — the picker
  is single-select to reuse the answer path untouched; batch-fix is a
  future refinement, not V5.
- Live/streaming progress updates — the construct is a point-in-time
  report rendered when the consumer reaches its reporting point, not a
  continuously-updating widget.

## Tasks (for review)

- T1 — model: `QuestionType.PROGRESS` + `progress_items` field +
  `to_ask_user_format` fallback (blocked items → single-select,
  suggested-first).
- T2 — `bridge.py`: `form_from_dict` validates `PROGRESS`
  (`progress_items` statuses; blocked subset == options; recommended ∈
  options; reuse decision extras validation).
- T3 — `widget.py`: `_control_html` `PROGRESS` three-bucket render
  (done/in-flight static rows + blocked radiogroup cards + "suggested
  next" badge + rationale callout) + CSS + accessibility + empty-blocked
  degrade; reuse the decision JS reader.
- T4 — `elicit` skill: `PROGRESS` → AskUserQuestion fallback mapping
  (+ `.agents/` mirror via `sync_agents_skills.py`).
- T5 — surfaces: `mcp/tool_schemas.py` enum (9→10) + `progress_items` +
  `test_tool_schemas.py` count guard; `elicitation_schema.py` map
  (forward-compat).
- T6 — consumer: wire progress into the `/spec` execute gate +
  confirm the exact reporting point (RV5.10).
- T7 — `communication-grammar.md`: add progress as member #4.
- T8 — tests: model (additive) + bridge validation + widget render
  (three-bucket + empty-blocked degrade) + round-trip reuse; plus the
  live dogfood receipt (AC3).
