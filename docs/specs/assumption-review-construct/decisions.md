# Assumption-Review Construct — decisions

Decision log for [requirements.md](requirements.md). Append-only;
newest at the bottom.

## D1 — Intake ruling (chair, 2026-08-15)

**Date:** 2026-08-15 · **Status:** decided (Patrick, content-plan
session: "let's proceed with your recommendation for 0.6.0").

Provenance chain: round table `q-forms-grammar-expansion-001` (codex
seat proposed assumption-review; chair ruled BACKLOG, receipt
`resp-20260814-211025`). Lead's 2026-08-15 assessment recommended it
for 0.6.0 with ranking (≈1.5 confirm-units: triage-shaped plus an edit
lane; immediate consumer = every scoping form via "Infer first"). Chair
accepted.

1. **In scope for 0.6.0**, sequenced after ranking.
2. **Slug = `assumption-review-construct`**, spec home attune-ai
   `docs/specs/` (confirm-construct D1.3 precedent).
3. **Done-when** recorded in requirements.

## D2 — Lead-proposed rules flagged for ratification (2026-08-15)

**Date:** 2026-08-15 · **Status:** RATIFIED — chair ruled via the batched
form shared with ranking's D2, each on the recommended option: D2-a
fixed vocabulary + D2-c edit lane ("Edit lane + fixed vocab"); D2-b
`suggested: accept` allowed visibly, `default` forbidden ("Both,
visibly, no default"). Theme budget 8 → 10 KB ratified under ranking
D2-a and applies here.

- **D2-a — Fixed vocabulary** `accept / edit / reject` (not
  author-renameable). Rationale: the vocabulary is the construct's
  meaning; renameable labels would let it drift into a triage clone.
  Alternative: author-nameable like triage (then the construct is
  triage + an edit lane, and its skill guidance is the only thing
  distinguishing it).
- **D2-b — `suggested` may pre-mark `accept` only,** visibly, never
  as the answer; `default` forbidden. Rationale: pre-marking accept is
  the natural ergonomics of "here's what I inferred — object if
  wrong", but it must stay a visible proposal (the confirm D2 logic,
  softened: assumptions are cheap to accept, approvals are not).
  Alternative: no `suggested` at all (every row starts unmarked).
- **D2-c — Edit lane in v1,** answer value `{"edit": "<text>"}` beside
  the `"accept"` / `"reject"` strings; flat surfaces pair each item's
  single-select with an optional text question and the fold enforces
  "text iff edit". Alternative: v1 = accept/reject only, edits typed
  into a companion textarea. Lead recommends the edit lane: without
  it the construct is `triage` with `dispositions: ["accept",
  "reject"]`, which already works today with zero code — the edit
  lane is the only reason to build it.

Rulings recorded above; the "no edit lane" alternative was explicitly
rejected with the note that it is expressible as triage today.

## D3 — Execution notes + review deviations (lead, 2026-08-15)

**Date:** 2026-08-15 · **Status:** recorded (execution complete; PR
attune-forms #25, stacked on #24 → #21).

- **R4 "numbered items" → bullets, deliberately.** The markdown
  shorthand's `N: value` form means *field* number; numbering the
  assumption rows would invite `2: accept` ambiguity. Rows render as
  bullets with `source` in italics — the substantive R4 requirements
  (source shown, `{item: null}` skeleton, the three shorthands) hold.
- **R1 label uniqueness enforced** in addition to key uniqueness
  (triage's precedent is keys only); two identical rows are
  indistinguishable to the user whatever their ids.
- **Review outcome** (five-lens adversarial workflow, two skeptics per
  finding; the skeptic pool hit a usage limit part-way, so four
  candidates were verified by the lead by reproduction): confirmed —
  single-quoted vocabulary hint made `problems_to_markdown` re-ask a
  sibling field named `edit`; verified — blank-edit widget gate,
  duplicate labels, `edit: <text>` accepted on the JSON reply path (the
  rule line teaches that form), inline edit text beats the text lane on
  both paths; not a defect — `{"edit": null}` is named by the
  validator. All fixed with pinned regressions
  (`TestReviewFindings`). `problems_to_markdown` now attributes by the
  leading quoted id only (a hardening beyond this construct).
- **AC-4** live receipt: pending the chair (reference form
  `inferred_scope`).
