# Run-Record Corpus — Decisions

## 2026-07-19 — Chair rulings on the three open questions (Patrick)

**D1 — Fork: Option B (canonicalize the existing telemetry
stream).** The seam, schema, writer, and five months of plumbing
already exist (`TelemetryMixin._emit_workflow_telemetry` →
`FileTelemetryBackend.log_workflow` → `workflow_runs.jsonl`); fix
its four defects (test isolation, worktree fragmentation, missing
provenance field, missing project field) rather than build a
second writer into `~/.attune/ops/runs/`. The ops dashboard store
stays exactly as designed. Investigation 1's Option-A
recommendation predated the corpus discovery and is superseded.

**D2 — RR-4 amendment path: chair-ruled edit.** The
pipeline-learner RR-4 source pin ("v1 mines exactly one source:
`~/.attune/ops/runs/**/*.json`") moves to the canonical telemetry
stream via a direct chair-ruled edit citing this spec — no
round-table re-entry required. The amendment lands in the same PR
as the RC-5 change, per RC-5's own text.

**D3 — Historical backfill: START CLEAN.** The 5-month archive is
not mined. Evidence (measured 2026-07-19, this session):

- 89% of the 3,849 real-named records sit inside test-like bursts
  (≥5 records starting within a rolling 60s window) — and bursts
  are not mere noise: back-to-back pytest executions manufacture
  exactly the high-support A→B pairs the miner scores, so the
  first chair-facing proposals would be learned from pytest
  execution order.
- The burst-free remainder is 408 records, 404 of them from
  Feb–Mar 2026 and ZERO in the last two months — near-weightless
  under RR-3's recency decay, and describing the Feb-era
  (API-execution) product.
- No filter is verifiable: no provenance field, null session ids,
  tests emit realistic names/costs/durations, and the burst
  heuristic's failure direction discards dense human sessions
  while passing slow SDK-backed tests. Unverifiable purity would
  poison RR-1's readiness numbers.
- Clean-start is cheap and reversible: RR-1's viability bar is
  reachable in a few weeks of normal dogfooding once RC-2 lands;
  archives stay on disk untouched (RC-1), so backfill can be
  revisited later against a known-clean comparison stream —
  validation that does not exist today.

Requirements header flipped DRAFT → chair-ruled in the same
commit. Execution is NOT yet armed — next step is the chair
queueing/authorizing implementation per the per-spec-arming
cadence ruling (roundtable-producing-team decisions).
