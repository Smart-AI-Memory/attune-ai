# docs-outbox — decisions

## D1 — ACTIVATED: the outbox is the ruled fix for lessons-append conflicts

**Date:** 2026-08-06 · **Status:** ACTIVATED (chair: Patrick, via
decision form; validated receipt `resp-20260806-073002`)

The chair activated this parked candidate as the fix for the
slow-PR lessons-append conflict class, choosing it OVER the lead's
recommendation ("re-commit to EOD batching + a `merge=union`
seatbelt") and over a lessons-fragments restructure. Both rejected
options and the lead's rationale (discipline hadn't failed while
followed) are preserved per the pushback-shape record; the chair
weighed the growing multi-session pattern — parallel worktrees,
chip sessions, multiple same-day writers — and picked the
mechanism that removes in-session docs PRs entirely.

**Fresh motivating evidence (2026-08-06):** two lessons.md DIRTY
cycles in one session — #1963's lessons append conflicted #1964
(cut minutes earlier), then a second append re-conflicted it after
its own rebase window. Both were bundling violations of the
EOD-batch rule, and the day ALSO had a parallel chip session
(#1966) — the multi-writer condition the outbox is designed for.

**Effect:** the requirements interview (the four questions in
`requirements.md`) proceeds now; the candidate design (C1–C4)
remains the input hypothesis, not the contract. Build follows
ratified requirements, per the spec lifecycle. Until the outbox
ships, the EOD-batch rule stays binding for lessons appends.

## D2 — Interview answered; Phase-1 requirements RATIFIED

**Date:** 2026-08-06 · **Status:** approved (chair: Patrick, via
the four-question interview form; validated receipt
`resp-20260806-073859` — all four lead recommendations accepted)

- **Sweep cadence:** end-of-workday launchd + on-demand skill;
  stale-outbox warning at 2 days.
- **Pending-recall layer (C3): DEFERRED to Phase 2** — earns in on
  demonstrated need (reopen trigger: a session demonstrably missing
  a same-day lesson). The phasing concern was raised by the lead at
  activation (D1 discussion) and adopted by the chair here.
- **Write discipline:** per-artifact files, flat directory,
  timestamped names — concurrent writers conflict-free by
  construction.
- **Digest approval:** chip — one click spawns the
  approve-and-PR session; the ops inbox row is monitoring only.

`requirements.md` rewritten from candidate (C1–C4 hypotheses) to
Phase-1 ratified form (R1–R5, AC-1–AC-4, build tasks). Build may
proceed from the ratified requirements in a fresh session.

## D3 — Phase 1 BUILT; receipts AC-1/AC-3/AC-4 recorded, AC-2 pending chip

**Date:** 2026-08-06 · **Status:** built (lead: Claude; dogfooded
live against the real `~/.attune/docs-outbox/`)

Shipped (one PR): `attune.docs_outbox` package (store R1, routing
R2, sweep+digest R3, CLI), Stop-hook lessons reminder rerouted to
the outbox writer (drift-guarded in
`tests/unit/test_coverage_batch12.py`), `/docs-outbox` plugin
skill (+ `.agents/` sync), launchd TEMPLATE at
`scripts/launchd/com.smartaimemory.attune.docs-outbox-sweep.plist`
(daily 17:30, digest-compose only — NOT installed; chair's
machine, chair installs), ops Collaboration inbox "N docs pending,
oldest Nd" row (monitoring-only; stale is the only state that
counts toward the action badge). 56 new tests; package coverage
92% (worktree-coverage workaround). R5 not built (deferred, D2).

Build interpretations worth naming:

- **Memory lint** runs best-effort via
  `~/.claude/hooks/memory_lint.py` ONLY for artifacts targeting a
  `/memory/` directory (no Phase-1 kind does by default); absence
  or failure of the home linter degrades silently. In-repo there is
  no memory linter to call (verified).
- **Chip mechanics:** the sweep composes the digest; the chip is
  spawned by the in-session skill flow via `spawn_task` (a launchd
  run composes the digest and the next session's skill run spawns
  the chip). Surfaces without `spawn_task` fall back to asking
  directly — same approval contract.
- **Dedupe** is mechanical: exact-body duplicates dropped (keep
  earliest), same-slug kin flagged `related-slug` for the chair;
  no LLM judgment in the sweep.

**Receipts:**

- **AC-4 (no-rot) — PASS, live:** backdated artifact
  (`20260803-0900-lesson-ac4-stale-probe.md`, 3.0d) →
  `status` printed `1 pending, oldest 3.0d  STALE — sweep overdue`
  and the live collab provider returned
  `OutboxRow(count=1, oldest_days=3.0, stale=True)`. Probe removed
  after the receipt (synthetic backdate — a real 2-day wait is not
  dogfoodable same-day; the trigger math is also unit-tested).
- **AC-1 (conflict-class) — conflict-free half PASS, live:** two
  real lessons from this session written by two separate CLI
  processes in the same minute
  (`20260806-0958-lesson-website-skill-count-guard.md`,
  `20260806-0958-lesson-hermetic-home-reads.md`) — two distinct
  files, zero conflict by construction (no branch, no armed PR
  exists to go DIRTY), one digest listing both. The
  lands-in-one-PR half completes when the chip-spawned session
  applies and opens the swept PR (bundled with AC-2 by design —
  one approval, one PR).
- **AC-3 (routing) — PASS, live:** THIS D3 ruling was written the
  same day and ships merge-now in the feature PR, not via the
  outbox — R2's split exercised for real; the outbox CLI also
  refuses `--kind decision` outright (unit-tested).
- **AC-2 (sweep round-trip) — PENDING the chair:** digest composed
  and chip spawned; completes when Patrick clicks it and the
  spawned session lands the swept PR (then recallable after the
  next hydration). Record the close-out here when it lands.
