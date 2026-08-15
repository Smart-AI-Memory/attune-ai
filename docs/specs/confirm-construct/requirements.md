# Confirm Construct — requirements

**Status:** approved (chair, 2026-08-14 — "requirements approved",
given after the lead's D2/R5a disclosure); task ladder under review.
Intake rulings in [decisions.md](decisions.md) D1; D2 ratified.
**Slug:** `confirm-construct` · **Repo:** attune-forms (spec home here
by the extraction-era precedent — attune-forms carries no specs tree).
**Provenance:** round table `q-forms-grammar-expansion-001` — the
claude and codex seats independently proposed a consequences-preview
approval gate; chair ruled it "spec next" (receipt
`resp-20260814-211025`). Intake accepted as prefilled
(receipt `resp-20260814-212130`).

## Outcome (from the intake)

attune-forms gains a `confirm` construct — communication-grammar
member #7: an **action preview with an explicit consequences list and
an approve/abort gate**. Today a side-effectful step (release, merge,
delete, spend) is improvised with a `boolean`, which loses the "here
is exactly what will happen" structure; the construct makes the
consequences first-class and the approval an explicit act.

## Done when (intake, verbatim)

confirm construct merged to attune-forms main with CI green:
definition validation, all four surfaces (widget / AskUserQuestion /
elicitation schema / markdown), answer validation through
`collect_form_response`, reference-form + round-trip drift guards
extended, and one live human-validated receipt recorded.

## Ruled constraints (D1 — re-open only by new ruling)

- **Two-way answer** (intake fork 1): the answer is exactly one of two
  author-nameable option labels, default `["Approve", "Abort"]` —
  always exactly two. No third lane, no typed-acknowledgment ceremony
  in v1.
- **Structured consequences** (intake fork 2): `consequences` is a
  non-empty list of `{label, severity?, detail?}` — the `triage_items`
  shape, so the grammar stays one family. `severity` is a free tag;
  the conventional vocabulary (`low` / `medium` / `high` /
  `irreversible`) is named in the skill doc, not enforced.
- **Degradation** (round-table ruling, both proposing seats): flat
  surfaces render a two-option single-select with the consequences
  folded compactly into the description/help text. Never a silent
  boolean that hides the receipt.
- **No pre-selected approval (LEAD-PROPOSED — chair ratification
  pending, flagged 2026-08-14):** R1 forbids `default`/`recommended`
  on a confirm. This rule was added by the lead beyond the intake
  forks; it stands only once the chair ratifies it (decisions.md D2
  records the disposition).

## Requirements

- **R1 — model + definition validation.** `QuestionType.CONFIRM` with
  `consequences` (required, non-empty, validated like `triage_items`
  minus ids) and exactly two `options` (defaulted to
  `["Approve", "Abort"]` when omitted; any other count is a definition
  error). **No `default` and no `recommended` are permitted on a
  confirm** — a pre-selected or pre-badged approval defeats the gate;
  the definition validator rejects them. Approving must be an explicit
  act on every surface.
- **R2 — widget render.** The question text is the action headline;
  consequences render as rows with their severity tag visibly badged
  (reusing the triage row/tag styling family where possible); the two
  options render as unchecked controls. Submit script reads it like
  the other construct radios; the CSS-family trimmer and the
  round-trip DOM simulator learn the type.
- **R3 — flat surfaces.** `to_ask_user_format`: single-select of the
  two labels, consequences folded into help text
  (`"Will: X (irreversible); Y — detail"` style, compact). Elicitation
  schema: string enum of the two labels (not JSON boolean — labels
  carry meaning). Markdown surface: consequences as bullets with
  severity tags, skeleton value `null` (never prefilled — R1's
  no-default rule projected to S4).
- **R4 — answer validation.** Membership over the two options via the
  existing `_validate_membership`; empty/missing answer on a required
  confirm is a named problem. No fold logic needed (scalar answer).
- **R5a — skill-rule reconciliation.** The shipped forms skill rules
  "a user's bare confirmation is never a form". The confirm construct
  inverts that for consequence-bearing actions, so the skill text MUST
  draw the boundary explicitly: bare re-confirmations ("go", "yes")
  stay conversational; the construct is reserved for actions whose
  consequences deserve enumeration (destructive, costly,
  outward-facing). Without this line the two rules contradict and the
  construct's failure mode is ceremony inflation.
- **R5 — drift guards.** Reference form + `EXAMPLE_ANSWERS` gain a
  confirm field; needs-widget partition, CSS-family exhaustive test,
  widget round-trip, and markdown conformance guards all extend; the
  MCP field schema documents the type (names/shapes unchanged, same
  boundary as PR #14).

## Out of scope

- Typed-acknowledgment friction for irreversible actions (named as a
  possible v2 in D1; needs its own ruling and a flat-surface answer).
- Any auto-wiring into attune-ai workflows (release-execute etc.) —
  consumers adopt in their own repos/rulings.
- Tolerant markdown ingestion (its own "spec next" thread).

## Acceptance criteria

- **AC-1** Definition validation: missing/empty `consequences`, a
  non-2 option count, or a `default`/`recommended` on a confirm each
  raise `FormValidationError` naming the field.
- **AC-2** All four surfaces render the reference confirm; the widget
  round-trip and markdown-skeleton round-trip validate through
  `collect_form_response`.
- **AC-3** One live human-validated receipt: a real confirm rendered,
  answered, validated (the D15/D16 receipt pattern — same as the
  deliberation/triage tranche's chair-ruling form).
- **AC-4** Full suite + lint green on CI (3 OS × 2 Python legs).

## Tasks

1. **Model + validation** (R1, R4, AC-1): enum member, fields, parser
   (`_parse_confirm_extras`), option-count/no-default/no-recommended
   rules, membership validation, unit tests.
2. **Widget surface** (R2): renderer + severity badges + CSS
   (budget-aware — stay under the 8 KB cap or raise with a ruling),
   submit-script branch, round-trip simulator support.
3. **Flat surfaces** (R3): ask-format fold, elicitation enum, markdown
   render + skeleton, per-surface tests.
4. **Guards + docs + receipt** (R5, AC-2..4): reference form, drift
   guards, skill doc section, CHANGELOG, live receipt, PR.
