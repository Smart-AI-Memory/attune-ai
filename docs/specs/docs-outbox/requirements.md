# Docs Outbox — Requirements (Phase 1 ratified)

**Status:** approved (2026-08-06 — interview answered by the chair,
receipt `resp-20260806-073859`; D2 in [decisions.md](decisions.md)).
Phase 1 = R1–R4 below; the pending-recall layer is DEFERRED (R5).
**Slug:** `docs-outbox`
**Provenance:** 2026-07-22 candidate (chair-captured, PR #1624);
ACTIVATED 2026-08-06 as the ruled fix for the lessons.md
both-append conflict class (D1). Companion memory:
`project_docs_outbox_idea`.

## Problem (motivating evidence)

Small docs artifacts — lessons appends, roundtable reports, process
drafts — each ship as their own auto-merge PR, and any PR carrying a
lessons.md append that doesn't merge quickly goes DIRTY when another
append lands first. Evidence: ~13 small-docs PRs on 2026-07-22; two
lessons.md DIRTY cycles plus a parallel chip session on 2026-08-06.
Naive batching has two logged failure modes (#942 armed-catch-all,
#1577 label-never-reclassifies), and a branch-parked lesson is
unavailable all day.

## Requirements (Phase 1 — ratified 2026-08-06)

- **R1 — outbox store.** Small docs land in `~/.attune/docs-outbox/`
  as **per-artifact files in a flat directory with timestamped
  names** (e.g. `20260806-1432-lesson-browser-pane-svg.md`).
  Concurrent writers are conflict-free by construction; the sweep
  concatenates in timestamp order. No long-lived branch, no armed-PR
  window.
- **R2 — mechanical routing by artifact type.** Lessons, roundtable
  reports/archives, process drafts, plan files → ALWAYS outbox.
  `decisions.md` rulings, spec status flips, starter-adjacent state
  → ALWAYS merge-now via the existing flow (parallel sessions act on
  them same-day). No per-case judgment; the Stop-hook lessons
  reminder points at the outbox.
- **R3 — curating sweep.** End-of-workday launchd job (US-5/
  clean-run pattern) **plus an on-demand skill**: dedupe related
  lessons, run the memory lint, flag core-worthy candidates, compose
  ONE auto-merge PR. Stale-outbox warning at **2 days**; the ops
  Collaboration inbox gains a "N docs pending, oldest Nd" row
  (monitoring only — approval is R4).
- **R4 — digest approval via chip.** The sweep presents a one-screen
  digest as a **chip**; one click spawns the approve-and-PR session.
  No auto-shipping: the chair (or their spawned session) approves
  the digest before the PR opens.
- **R5 — pending-recall layer DEFERRED to Phase 2.** Hydration does
  NOT read the outbox in Phase 1; artifacts become recallable at the
  nightly merge, same availability as today's EOD batching. Reopen
  trigger: a session demonstrably missing a lesson written earlier
  the same day. Any Phase-2 build must render the `pending`
  provenance tag honestly on every serving surface it reaches.

## Acceptance criteria — receipts, not registration

- **AC-1 — conflict-class receipt.** Two same-day writers (two
  sessions, or a session plus a chip) each outbox a lesson; the
  sweep lands both in one PR with zero DIRTY cycles.
- **AC-2 — sweep round-trip receipt.** A real outboxed lesson passes
  dedupe + memory lint, appears in the digest, is chair-approved via
  the chip, and lands on main in the swept PR — then is recallable
  after hydration.
- **AC-3 — routing receipt.** A decisions.md ruling written the same
  day ships merge-now (NOT via the outbox), demonstrating R2's
  split.
- **AC-4 — no-rot receipt.** An artifact left 2+ days triggers the
  stale warning on the ops inbox row.

## Out of scope (Phase 1)

- The pending-recall layer (R5 — deferred, trigger recorded).
- Migrating historical lessons.md content — the corpus stays as-is;
  only NEW small docs route through the outbox.
- Multi-machine outbox sync (machine-local until swept, accepted).

## Tasks (for build review)

1. Outbox writer helper + routing table + Stop-hook reminder update.
2. Sweep engine: concatenate, dedupe, lint, digest compose.
3. Chip integration (digest → spawn approve session → one PR).
4. launchd job + ops inbox pending row + stale warning.
5. Dogfood AC-1..AC-4 live; record receipts in decisions.md.
