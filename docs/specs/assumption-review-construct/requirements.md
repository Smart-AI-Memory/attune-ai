# Assumption-Review Construct — requirements

**Status:** approved (chair, 2026-08-15 — intake "proceed with your
recommendation for 0.6.0"; D2 forks ratified on the recommended
options via one batched form). Task ladder queued after ranking.
**Slug:** `assumption-review-construct` · **Repo:** attune-forms (spec
home here by the confirm-construct precedent, D1.3) · **Target:**
0.6.0, sequenced after `ranking`.
**Provenance:** round table `q-forms-grammar-expansion-001` — the codex
seat proposed "clarification with assumptions: present inferred
assumptions as individually accept/edit/reject instead of repeatedly
asking isolated questions"; moderator read: "the inference-first
discipline made a construct"; chair ruled BACKLOG (receipt
`resp-20260814-211025`) and on 2026-08-15 picked it for 0.6.0.

## Outcome

attune-forms gains an `assumption_review` construct — grammar member
#8: the agent lists the assumptions it inferred from context and the
user rules each one **accept / edit / reject**, supplying replacement
text for an edit. Today "infer first" (SKILL.md) is a discipline with
no artifact: inferred assumptions are either silently acted on or
re-asked cold. The construct makes them visible and individually
answerable — one round trip instead of N clarifying questions.

## Done when

`assumption_review` construct merged to attune-forms main with CI
green: definition validation, all four surfaces, answer validation
through `collect_form_response` including the flat-surface fold and
the edit-text lane, typed-reply ingestion, drift guards extended,
SKILL.md section (reconciled with "Infer first"), CHANGELOG entry, one
live human-validated receipt.

## Ruled constraints (D1 — the intake)

- In scope for 0.6.0, after ranking.
- Shares the triage machinery by construction: `triage_item_key`,
  dotted flat expansion, fold-back in `collect_form_response`.

## Requirements

- **R1 — model + definition validation.** `QuestionType.ASSUMPTION_REVIEW`.
  `assumptions`: non-empty list of `{id?, label, detail?, source?}`
  (the `triage_items` shape plus an optional `source` — where the
  agent inferred it from, e.g. "README §Install", "your message at
  10:02"); labels unique non-empty; ids unique non-empty when given
  (`triage_item_key` rule: id wins, label is the fallback). The
  disposition vocabulary is **fixed** (ratified D2-a):
  `accept` / `edit` / `reject` — the construct's meaning *is* the
  vocabulary, so it is not author-renameable (unlike triage). Optional
  `suggested` (`{item: "accept"}` only — ratified D2-b) renders visibly as the
  agent's proposal, never as the answer. `default` not permitted.
- **R2 — answer shape + validation (ratified D2-c).** The answer
  is `{item key: ruling}` where ruling is `"accept"`, `"reject"`, or
  `{"edit": "<replacement text>"}` (non-empty string). Required board:
  every item ruled; `required: false` allows partial. Problems name
  the item: unknown key, unknown ruling, `edit` without text, empty
  text.
- **R3 — widget render.** Rows like triage (label, detail, `source`
  in muted text), a three-way control per row; choosing `edit` reveals
  an inline text field pre-filled with the label so the user edits
  rather than retypes; `suggested: accept` pre-marks visibly. Postback
  is the R2 mapping. CSS family `.ae-assume-*`, reusing the triage row
  family where possible (budget per ranking D2-a).
- **R4 — flat surfaces.** `to_ask_user_formats`: per-item expansion
  like triage — a single-select `"<field id>.<item>"` over
  `accept / edit / reject`, and, because a host question tool can't
  branch, a paired optional text question `"<field id>.<item>.text"`
  ("Replacement text if editing"); the fold combines them and the R2
  validator requires text iff the ruling is `edit`. Elicitation
  schema: object with per-item enum + optional text properties.
  Markdown surface: numbered items with `source`; skeleton value
  `{item: null}`; typed shorthand `field.item: accept`,
  `field.item: reject`, `field.item: edit: <text>` (everything after
  the second colon is the text, trimmed).
- **R5 — skill reconciliation.** SKILL.md's "Infer first" says a
  settled dimension is omitted or prefilled, never re-asked. The
  construct does not reopen settled dimensions; it surfaces *inferred*
  ones the agent is about to act on. The skill section must draw that
  line (like confirm's R5a) — otherwise the failure mode is an agent
  that turns every inference into a review row. Guidance: use it when
  ≥ 2 inferences carry real consequences if wrong; a single safe
  inference is stated in prose and acted on.
- **R6 — drift guards.** Reference form + `EXAMPLE_ANSWERS` gain an
  assumption-review field (with one `edit` ruling so the text lane is
  exercised); needs-widget, CSS-family, widget round-trip, markdown
  conformance, ingestion tests extend; MCP field schema documents the
  type.

## Out of scope

- Free-form "add an assumption I missed" row (a textarea alongside
  the board covers it in v1).
- Confidence scores per assumption (could be a `tag` today).
- Any auto-wiring into attune-ai's scoping forms — consumers adopt by
  their own rulings.

## Acceptance criteria

- **AC-1** Definition validation: empty `assumptions`, duplicate keys,
  a `default`, or a `suggested` value other than `accept` each raise
  `FormValidationError` naming the field.
- **AC-2** Answer validation: unknown key, unknown ruling, `edit`
  without text, and missing item on a required board each produce a
  named problem; a mixed accept/edit/reject mapping validates.
- **AC-3** All four surfaces render the reference field; the widget
  round-trip, the flat expansion + text pairing fold, and the three
  markdown shorthand forms validate through `collect_form_response`.
- **AC-4** One live human-validated receipt.
- **AC-5** Full suite + lint green on CI; theme size recorded.

## Tasks

1. **Model + validation** (R1, R2, AC-1, AC-2): enum member, fields,
   `_parse_assumption_extras`, `_validate_assumption_review`, unit
   tests.
2. **Widget surface** (R3): renderer + inline edit field + CSS under
   the ratified budget; submit-script branch; round-trip simulator.
3. **Flat surfaces + ingestion** (R4): expansion with paired text
   question, fold, elicitation schema, markdown render/skeleton,
   `edit:` shorthand, per-surface tests.
4. **Guards + docs + receipt** (R5, R6, AC-3..5): reference form,
   drift guards, SKILL.md section incl. the Infer-first boundary,
   MCP schema text, CHANGELOG, live receipt, PR.
