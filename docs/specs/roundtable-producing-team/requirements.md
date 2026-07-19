# Round Table v2 — Producing Team: Requirements

**Status: requirements DRAFTED from thread `table-v2-001`
(2026-07-18)** — architecture converged by the table itself in one
round; initial settings chair-ratified same day (phase-1-minimal +
fixed-roles-first, moderator pushback accepted — see
[decisions.md](decisions.md)).

## Vision

Evolve the round table (v1: `agent-round-table`, P0–P3 shipped)
from a deliberating body into a **producing team**: capable of
authoring high-quality specs (requirements, design, tasks) and
generating working solutions (code, tests), under the same ratified
constraints — chair-only per-item promotion, members strictly
text-in/text-out, moderator owns all I/O, 3-round ceiling, output
routed through the contract's four artifact tiers.

Chair directive (2026-07-18): "Full implementation of a robust
team/roundtable that is powerful and able to create powerful specs
and generate ai solutions."

## Converged architecture (table-v2-001 — the end-state)

All three seats independently converged on:

1. **Moderator as sole materializer** — members emit diffs and
   spec fragments as text; the moderator materializes them in an
   ISOLATED scratch worktree, never a tracked path.
2. **Receipts before the chair** — tests, lint, and real-boundary
   probes run and attach before any candidate reaches chair
   review; green-with-receipts is the floor, not the pitch.
3. **Dissent as a first-class output** — a dissent register /
   decision-option matrix travels with every draft; 2-1 items
   carry the minority note; contested items surface as decision
   forms. Never synthetic unanimity.
4. **Per-item promotion scales up** — a spec draft is a list of
   promotable items (per-REQ), not a blob; v1's P2 gates extend
   unchanged.
5. **Roles per round** — drafter / adversarial critic / verifier.
   Rotation is the end-state (two seats independently demanded
   it); fixed roles first is the ratified starting setting.

Distinct contributions folded in: grounding pack + typed round
contracts + artifact compiler + cross-seat diff review (claude);
traceable proposal ledger + executable spec quality gates +
budget-aware recovery (codex); tier auto-classification +
apply-ready diff output contracts (antigravity).

## Phases

- **V2-P1 — minimal spec-authoring loop (ratified scope).**
  Exactly three settings live: (a) moderator-built **grounding
  pack** (source excerpts, greps for the targeted property,
  current test status, prior lessons/specs); (b) **typed round
  outputs** — Round 1 draft as numbered REQ-IDs with acceptance
  criteria; Round 2 critique with file:line citations required;
  Round 3 converge with per-item tags (agreed / 2-1 / contested);
  (c) **per-REQ chair promotion** through the existing gates.
  Dissent register as a simple section, not a system. Fixed
  roles: claude drafts, codex + antigravity critique. Deliverable:
  ONE real spec authored by the table, shipped end-to-end.
- **V2-P2 — artifact compiler + proposal ledger.** Deterministic
  assembly of member fragments into tier-shaped drafts; per-item
  IDs traceable end-to-end (evidence → objection → chair status →
  test). Built AFTER V2-P1's real spec teaches what they need.
- **V2-P3 — solution generation.** Members emit unified diffs;
  moderator materializes in a scratch worktree, pre-flights
  pinned formatters, runs named tests serially, captures
  exact-tail receipts; one bounded repair round; cross-seat
  review (different seat than author) before chair review.
- **V2-P4 — rotation + routine integration.** Role rotation
  switches on once the loop is baselined; producing-team runs
  become schedulable routines (v1 P3 machinery).

## Requirements

- **TR-1** No member performs I/O in any phase; the moderator is
  the only process that reads/writes files, Redis, or git (v1 R1
  carried forward, unchanged).
- **TR-2** Nothing reaches a tracked path without explicit
  per-item chair approval; scratch worktrees and board state are
  the only pre-approval homes for generated content (v1 R4).
- **TR-3** Every candidate presented to the chair carries
  verification receipts naming the commands actually run and
  their results; mocked and real-boundary evidence are labeled
  distinctly.
- **TR-4** Round outputs are typed and lintable: a Round-2
  critique claim about the code without a file:line citation from
  the grounding pack is rejected by the moderator before posting
  (extends the lesson-lint precedent).
- **TR-5** The dissent register is non-empty or explicitly
  attested empty in every chair presentation; a table that never
  disagrees is a defect signal, not a convergence signal.
- **TR-6** Candidates per session are capped at **7** (chair-ruled
  2026-07-19) so chair attention stays real; per-item invocation
  budgets kill stuck items cheaply.
- **TR-7** Spec drafts stage in untracked scratch or the board,
  structured per-REQ; chair rules item-by-item; only approved
  REQs are written to the spec file.
- **TR-8** (V2-P3) Member-proposed code is validated in an
  isolated scratch worktree before chair review; a failing
  candidate gets at most one repair round within the 3-round
  ceiling; rejection discards the scratch worktree.
- **TR-9** Success is measured by chair-approved artifacts that
  survive real execution and boundary tests — never by agreement
  rate, document completeness, or process volume (codex's risk,
  adopted as a requirement).

## Acceptance criteria

- **TAC-1** V2-P1 ships one real spec authored by the table:
  grounding pack built, three typed rounds run (or early halt),
  per-REQ chair ruling recorded, approved REQs in a tracked
  `requirements.md` whose provenance names the thread id.
- **TAC-2** A Round-2 critique lacking citations is demonstrably
  rejected before posting (TR-4 receipt).
- **TAC-3** A 2-1 item reaches the chair carrying the minority
  position verbatim (TR-5 receipt).
- **TAC-4** (V2-P3) A member-proposed diff that fails its tests
  is shown to get its repair round and, still failing, is
  presented as failed-with-receipts or withheld — never silently
  dropped or laundered green.

## Out of scope

- Code generation in V2-P1 (ratified: spec authoring first).
- Any member-side file/Redis/git access (structural, carried).
- Auto-promotion of any kind, in any phase.
- Roster changes (fixed three seats; revisit with field evidence).
