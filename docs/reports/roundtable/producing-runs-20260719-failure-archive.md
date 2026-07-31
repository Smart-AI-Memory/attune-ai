# Producing runs 2026-07-19 — failure archive (chair-promoted 2026-07-22)

**Chair ruling:** archive + queue re-runs. All four V2-P4 producing
runs of 2026-07-19 FAILED before staging (`staged: 0` — TR-6 staging
never occurred, R8 honored; no unruled content ever reached the
chair). Promoted before TTL expiry to preserve the only copies of
the seat draft documents and the failure receipts.

**Why each failed — and why re-runs should succeed now:**

- `spec-lifecycle-gates-…-1` — LINT_DIRTY: codex critique carried an
  uncited item after its one repair round. The citation contract has
  since been taught by worked example (the format-contract lesson).
- `spec-lifecycle-gates-…-2` — INPUT_INVALID: the grounding pack
  path pointed into a since-deleted worktree. Re-arm with a pack at
  a stable tracked path.
- `pipeline-learner-v1` — SEAT_ABSENT ×2: the claude seat's revoked
  OAuth token era; the seat now runs the API-key path (backlog (c)
  ruling, verified in the 07-22 dry-run rehearsal).
- `usage-signals-refresh` — LINT_DIRTY: the antigravity final draft
  omitted convergence tags on every item; the tag contract now ships
  a worked example in the brief.

**Re-run queue (chair-ruled):** re-arm all three subjects post-lift
with stable grounding packs; tracked in the re-run issue referenced
by the session starter.

The salvage value below: complete seat documents (drafts/critiques
— e.g. an 8-item RR draft for pipeline-learner, a 5-item draft for
usage-signals) that future runs or spec sessions can mine.

---

## Chair rulings already made (constraints on the draft)

See `decisions.md` in this directory — verdict-ledger location,
flaky-live-fire override path, and fixed-vs-dynamic gate policy are
ruled; the draft must conform, not re-litigate.

## PACK-2 — SHIPPED since approval (docs/specs/usage-signals/decisions.md, live probes 2026-07-19)

- D1 Phase 0 baseline COMPLETE (2026-06-11) with per-package
  pypistats tables and mirror-split addendum.
- D2 zero-instrumentation verdict recorded; D4 ping ruled BUILD.
- D3 R4 snapshot script shipped: `scripts/reach_snapshot.py`;
  `docs/specs/usage-signals/snapshots/` holds dated JSONs current
  through 2026-07-18.
- D5–D8 Phase 2 opt-in ping shipped END-TO-END and verified live
  (2026-06-20): `src/attune/telemetry/usage_ping.py` (default OFF;
  `DO_NOT_TRACK` and `ATTUNE_USAGE_PING` overrides; payload
  enumerated), website ingest chain with validate + rate-limit libs
  (`website/lib/usage/{validate,rate-limit}.ts`).
- D9/D11/D12 default stays OFF; first-run consent prompt shipped
  (8.6.1) on CLI and plugin/MCP channels as the opt-in lever.
- D13 R6 spend alarm SHIPPED (2026-06-20).
- D11 (second use — the decisions ledger has a duplicate D11
  number, a small hygiene defect worth a candidate noting):
  attune-rag download figure declared uninterpreted noise
  (2026-07-12).
- DEC-7 amendment (2026-07-17): 10.5.0 tagged mid-window as a
  deliberate probe; read scheduled with tag-date + external
  responses on 2026-07-27.

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/producing-runs-20260719-failure-archive.md` and is
not distributed with the repository.*
