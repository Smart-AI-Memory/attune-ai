# Ranking Construct — decisions

Decision log for [requirements.md](requirements.md). Append-only;
newest at the bottom.

## D1 — Intake ruling (chair, 2026-08-15)

**Date:** 2026-08-15 · **Status:** decided (Patrick, content-plan
session: "let's proceed with your recommendation for 0.6.0").

Provenance chain: round table `q-forms-grammar-expansion-001` (codex
seat proposed ranking; chair ruled BACKLOG, receipt
`resp-20260814-211025`). On 2026-08-15 the lead assessed the four
backlog items against the confirm-construct cost unit (PR #15: 16
files / +558 lines / one day) and recommended **0.6.0 = ranking +
assumption-review + theme-budget ratification**, with `hunk_review`
deferred until a diff-review consumer commits and the
surface-capability contract split into its own spec (a router change,
not a construct). Chair accepted the recommendation as stated.

1. **In scope for 0.6.0**, sequenced first (before assumption-review).
2. **Slug = `ranking-construct`**, spec home attune-ai `docs/specs/`
   (confirm-construct D1.3 precedent).
3. **Done-when** recorded in requirements.

## D2 — Lead-proposed rules flagged for ratification (2026-08-15)

**Date:** 2026-08-15 · **Status:** RATIFIED — chair ruled all three via
one batched four-question form in the content-plan session (paired
with assumption-review's D2), each on the recommended option:
D2-a "Raise cap to 10 KB"; D2-b "Ordinal expansion"; D2-c "Both,
visibly, no default" (covers ranking `suggested` + assumption-review
`suggested: accept`). Per the confirm-construct D2 discipline, these were
added by the lead beyond the intake and stand only once ratified.

- **D2-a — Theme budget.** `FORM_THEME_CSS` is 8,158 B of the 8,192 B
  cap; the `.ae-rank-*` family cannot fit. Lead recommends **raise the
  cap 8 KB → 10 KB** (the 6 → 8 KB precedent, ratified with #14),
  recording the measured size at merge. Alternative: a CSS
  consolidation pass first (unknown yield; delays both constructs).
- **D2-b — Flat-surface degradation = ordinal expansion.** One
  single-select per rank slot (`field.k`, "Rank #k"), folded back into
  the list on collection, duplicates caught by the validator — the
  triage dotted-id pattern. Alternative under the strict-degradation
  rule: fail loudly on flat surfaces (`to_ask_user_format` raises, as
  triage does for its *unexpanded* form) and rely on markdown's typed
  list. Lead recommends expansion: each slot is a faithful
  single-select, and the fold is machinery that already exists.
- **D2-c — `suggested` order allowed, `default` forbidden.** A
  proposed order renders visibly as a proposal (triage `suggested`
  precedent); `default` is rejected so the answer stays an explicit
  act and one word keeps one meaning across constructs. Alternative:
  neither (no pre-arrangement at all).

Rulings: D2-a raise to 10 KB (record measured size at merge; a CSS
consolidation pass was offered and NOT chosen — do not treat the cap as
a ratchet without a new ruling). D2-b ordinal expansion + fold. D2-c
`suggested` allowed visibly, `default` rejected.

## D3 — Execution notes (lead, 2026-08-15)

**Date:** 2026-08-15 · **Status:** recorded (execution complete; PR
attune-forms #24, stacked on #21).

- Widget design: ranked `<ol>` (CSS-counter numbered — a flex `<li>`
  drops its marker, caught in the browser check) + unranked pool moved
  by add / up / down / remove buttons; an untouched form posts nothing,
  so the ordering is an explicit act (D2-c) even without `suggested`.
- Theme measured 9,808 B after RANK (10,064 B once assumption-review's
  ASSUME family landed) against the ratified 10 KB cap.
- **AC-4** live receipt: pending the chair (reference form
  `rollout_order`).

## D4 — AC-4 live receipt (chair, 2026-08-16)

**Date:** 2026-08-16 · **Status:** SATISFIED — receipt
`resp-20260816-021540`.

The construct's first human-validated round trip was the attune-forms
0.6.0 release intake itself (the confirm-construct D3 pattern): a live
`ranking` — "After the cut — order the top three follow-ups", five
options, `top_n: 3`, no `suggested` — rendered from `main` through
`form_to_widget_html`, answered by the chair in the widget (pool →
ranked list via the buttons), posted back, and validated through
`collect_form_response`. Answer, in order: attune-ai parity (bump the
attune-forms lock 0.1.0 → 0.6.0 + mirror tests) → project Article B →
project Article A (after its §7 flips to 0.6.0). Post 1 and the 0.5.0
cleanup batch were left unranked and wait. The ranking is the order
the lead works in after the cut.
