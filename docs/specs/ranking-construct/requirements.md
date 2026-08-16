# Ranking Construct — requirements

**Status:** approved (chair, 2026-08-15 — intake "proceed with your
recommendation for 0.6.0"; D2 forks ratified on the recommended
options via one batched form). Task ladder executing.
**Slug:** `ranking-construct` · **Repo:** attune-forms (spec home here
by the confirm-construct precedent, D1.3) · **Target:** 0.6.0.
**Provenance:** round table `q-forms-grammar-expansion-001` — the codex
seat proposed "ranking/prioritization: ordered choices, optionally with
a top-N limit; appears constantly in planning and degrades to numbered
typed input"; moderator read recorded it as a backlog candidate; chair
ruled it BACKLOG (receipt `resp-20260814-211025`) and on 2026-08-15
picked it for 0.6.0 alongside `assumption-review` (content-plan session,
"let's proceed with your recommendation").

## Outcome

attune-forms gains a `ranking` construct — communication-grammar member
#7 (six today: decision, pushback, progress, deliberation, triage,
confirm): the user **orders** a set of options, optionally only the top
N. Today an ordering is improvised as a `multi_select` (loses order) or
N single-selects (loses the "one decision" framing); the construct makes
order the answer.

## Done when

`ranking` construct merged to attune-forms main with CI green:
definition validation, all four surfaces (widget / AskUserQuestion /
elicitation schema / markdown), answer validation through
`collect_form_response` including the flat-surface fold, typed-reply
ingestion of an ordered list, reference-form + round-trip + CSS-family
+ markdown-conformance drift guards extended, SKILL.md section,
CHANGELOG entry, and one live human-validated receipt.

## Ruled constraints (D1 — the intake)

- In scope for 0.6.0 with `assumption-review`; ranking lands **first**
  (it exercises the ordered-list answer shape and the ordinal flat
  expansion that assumption-review's fold builds on).
- Theme budget: the widget CSS family will not fit under the current
  8 KB cap (8,158 B used) — a budget ratification is a 0.6.0
  precondition (decisions.md D2-a).

## Requirements

- **R1 — model + definition validation.** `QuestionType.RANKING`.
  `options` required, ≥ 2 unique non-empty strings. Optional
  `top_n: int` — when present, `1 <= top_n <= len(options)`; when
  absent, the answer is a full permutation. Optional `suggested`
  (ratified D2-c): a proposed order (list of options, distinct,
  length == expected answer length) rendered visibly as a proposal,
  like triage `suggested`; never treated as the answer. `default` is
  **not** permitted (a pre-filled order is `suggested`, not `default` —
  keeps the answer an explicit act, and keeps one word for one thing).
- **R2 — answer shape + validation.** The answer is a **list** of
  option labels: distinct, every entry in `options`, length ==
  `top_n` if set else `len(options)`. Missing/empty on a required
  ranking is a named problem; a wrong length, a duplicate, or an
  unknown label each name the offending entry.
- **R3 — widget render.** Options render as an ordered list with
  move-up / move-down controls (no drag dependency — the widget is
  self-contained, no JS libraries); with `top_n` set, a "ranked" zone
  of N slots and an "unranked" pool; `suggested` pre-arranges the list
  with a visible "proposed" badge and the submit still requires an
  explicit action. Postback value is the ordered list. New CSS family
  `.ae-rank-*` (budget-aware; see D2-a).
- **R4 — flat surfaces (ratified D2-b).**
  `to_ask_user_formats`: **ordinal expansion** — one single-select per
  slot (`"<field id>.1"`, `"<field id>.2"`, … up to the answer length),
  each titled "Rank #k", options = all options (the host can't remove
  already-picked ones); `collect_form_response` folds the dotted
  answers back into the list and the R2 validator catches duplicates
  — the same dotted-namespace guard triage uses. Elicitation schema:
  JSON array of enum strings with `minItems == maxItems == answer
  length`, `uniqueItems: true`. Markdown surface: numbered option list
  + skeleton value `[]`; typed shorthand `field: b, a, c` (comma list,
  order preserved — the existing multi-select splitter) and the
  dotted `field.1: b` slot form both parse.
- **R5 — skill + docs.** SKILL.md gains "The ranking list": when to
  use (a genuine ordering, not a multi-select in disguise), keys, the
  `top_n` rule, and the flat-surface caveat that a host may show N
  identical option lists. MCP field schema documents the type; tool
  names/result shapes unchanged.
- **R6 — drift guards.** Reference form + `EXAMPLE_ANSWERS` gain a
  ranking field; needs-widget partition, CSS-family exhaustive +
  uniqueness tests, widget round-trip DOM simulator, markdown
  conformance, and ingestion tests all extend.

## Out of scope

- Weighted / scored ranking (each option gets a score) — a different
  answer shape; would be its own construct or a `number` matrix.
- Pairwise comparison UI.
- Drag-and-drop in the widget (v1 uses buttons; drag can come later
  without changing the answer shape).

## Acceptance criteria

- **AC-1** Definition validation: `< 2` options, `top_n` out of range,
  `default` present, or a malformed `suggested` each raise
  `FormValidationError` naming the field.
- **AC-2** Answer validation: wrong length, duplicate, unknown label,
  and empty-required each produce a named problem; a valid full
  permutation and a valid top-N list both validate.
- **AC-3** All four surfaces render the reference ranking; the widget
  round-trip, the ordinal-expansion fold, and both markdown shorthand
  forms validate through `collect_form_response`.
- **AC-4** One live human-validated receipt (a real ranking rendered,
  answered, validated — same pattern as confirm's D3).
- **AC-5** Full suite + lint green on CI (3 OS × 2 Python legs); theme
  size recorded in the CHANGELOG against the ratified budget.

## Tasks

1. **Model + validation** (R1, R2, AC-1, AC-2): enum member, fields,
   `_parse_ranking_extras`, `_validate_ranking`, unit tests.
2. **Widget surface** (R3): renderer + move controls + `.ae-rank-*`
   CSS under the ratified budget; submit-script branch; round-trip
   simulator support.
3. **Flat surfaces + ingestion** (R4): ordinal expansion + fold,
   elicitation array schema, markdown render/skeleton, shorthand
   parsing (list + dotted), per-surface tests.
4. **Guards + docs + receipt** (R5, R6, AC-3..5): reference form,
   drift guards, SKILL.md section, MCP schema text, CHANGELOG, live
   receipt, PR.
