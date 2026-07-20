# Run-Record Corpus (RR-1 unblock) — Requirements

**Status:** shipped (2026-07-19) — implemented same day (#1472); chair-ruled: all three open questions
ruled (B; chair-ruled RR-4 edit; start clean — see
`decisions.md`). Drafted 2026-07-19 by the follow-up session
(direct draft; not a producing run). This is
the "separate spec" that pipeline-learner RR-1 names as its hard
external dependency: establish and verify that workflow run
records accumulate, so RR-1's readiness gate can ever pass.

## Evidence base (two investigations, one session apart)

**Investigation 1 — ops-runs persistence (chip session
`task_656149ab`, 2026-07-19).** Nothing is broken; the pipe is dry
by design. `_persist_run` has exactly one caller
(`RunnerService._finish_run`, `src/attune/ops/runner.py:686`) and
`persistence_dir` is wired only in the ops dashboard server
(`src/attune/ops/server.py:53`) — MCP- and CLI-launched workflow
runs never write an ops run record. `prune_old_runs`
(`src/attune/ops/runner.py:940`) runs at every dashboard startup
with `runs_retention_days=30` and unlinks files but not
directories — the observed 15-dirs/1-file signature. Both halves
reproduced by live probe. The ceiling of the current design is
"dashboard-launched runs from the last 30 days"; the miner's
"thousands of runs going back months" can never accumulate here
without widening.

**Investigation 2 — the telemetry seam (this session,
2026-07-19).** A run-record corpus ALREADY EXISTS and has been
accumulating for five months at a different seam.
`TelemetryMixin._emit_workflow_telemetry`
(`src/attune/workflows/telemetry_mixin.py:263`) builds a
`WorkflowRunRecord` (run_id, workflow_name, started_at/
completed_at, per-stage tiers/models/tokens, total_cost, success,
error) per workflow execution and appends it via
`FileTelemetryBackend.log_workflow` to
`<storage_dir>/workflow_runs.jsonl`. Measured at
`~/attune-ai/.attune/workflow_runs.jsonl`: **18,289 records,
2026-02-15 → 2026-07-19, 59 distinct days; 3,849 carry real
workflow names across 55 distinct days, 3,126 with cost > 0.**
But the stream has four defects that make it unusable as-is:

1. **Test pollution dominates.** ~14,400 records are pytest
   fixtures (`stub-workflow`, `test-tier-fallback`,
   `success-workflow`, `test-workflow`, `failing-*`), and the
   suite also emits realistic names — recent "real-named" records
   trace to test bursts (e.g. all of 2026-07-19's records landed
   in one second at 04:22). The suite writes to the REAL
   project-local `.attune/` because `FileTelemetryBackend`
   defaults to a cwd-relative `storage_dir=".attune"`.
2. **Worktree fragmentation.** The cwd-relative default scatters
   corpora across `.claude/worktrees/*/.attune/workflow_runs.jsonl`
   (observed: 25 and 75 records in two worktrees), so recent
   real usage never consolidates.
3. **No provenance field.** `WorkflowRunRecord` has no
   manual-vs-`ATTUNE_REC` attribution (pipeline-learner RR-3
   needs it; absent records weight as auto — acceptable, but the
   field must exist going forward).
4. **No project identifier.** Records carry `session_id`/`user_id`
   (both observed null) but no project field; single-project
   scope (RR-4) is currently only implied by file location.

`~/.attune/telemetry/usage.jsonl` (UsageTracker's home-global
stream) is per-stage call events, not run records, and is
test-polluted the same way — it is corroborating volume evidence,
not a corpus candidate.

## Decision fork (chair rules; drafter recommends B)

- **A. Widen the ops-runs write path** — persist from the shared
  execution seam into `~/.attune/ops/runs/**/*.json` (investigation
  1's original recommendation, made before the telemetry corpus
  was found). Builds a second writer parallel to one that already
  exists; also needs retention surgery so the dashboard's 30-day
  prune doesn't eat the miner's corpus.
- **B (recommended). Canonicalize the existing telemetry stream** —
  the seam, schema, writer, and five months of plumbing already
  exist; fix its four defects (isolation, fragmentation,
  provenance, project id) and point pipeline-learner RR-1 at it.
  No new writer; the ops dashboard store stays exactly as designed
  (a 30-day dashboard log viewer, per its own spec).
- Choosing B requires a pipeline-learner amendment: RR-4 pins "v1
  mines exactly one source: `~/.attune/ops/runs/**/*.json`" — the
  pin would move to the canonical telemetry stream. That amendment
  is named here so the chair rules on both together, not
  discovers the conflict later.

## Requirements (written for B; A noted where it diverges)

**RC-1 — One canonical, home-global run-record stream**
Run records consolidate to a single file regardless of which
checkout or worktree ran the workflow.

- Canonical location: `~/.attune/telemetry/workflow_runs.jsonl`
  (the existing home-global telemetry dir). `FileTelemetryBackend`
  resolves it via the same mechanism UsageTracker uses for
  `usage.jsonl`; the cwd-relative `.attune/` default stops
  receiving run records.
- Existing project-local corpora are left in place as historical
  archives (readable by the miner's backfill, RC-5); no migration
  writes.
- Under A, the analogous requirement is one `~/.attune/ops/runs/`
  tree fed from the shared seam; fragmentation cannot recur
  because the path is already home-global.

**RC-2 — Every real execution path emits exactly one record**
The seam is `_emit_workflow_telemetry`; paths that bypass it are
enumerated and closed, not assumed absent.

- An audit (part of this spec's execution) lists each workflow
  entry point — MCP tools, `attune` CLI, ops dashboard, meta
  workflows — and shows each reaches `log_workflow` exactly once
  per run. Dashboard-launched runs must not double-write (they
  already persist an ops record; that store is unchanged).
- Acceptance probe is a live-fire receipt, not a unit test: run
  one MCP workflow and one CLI workflow from a worktree, then show
  two new records in the canonical stream with correct
  `workflow_name`, parseable `started_at`, and cost/token totals.

**RC-3 — Provenance and project fields on the record**
`WorkflowRunRecord` gains two optional fields, populated going
forward; historical records without them count as
unknown-provenance / unknown-project (never guessed).

- `trigger`: `manual` | `attune-rec` | unset. Wired from the same
  attribution `ATTUNE_REC` recommendations carry today
  (`curator/sources/recommendations.py`, `ops/runner.py`).
- `project`: a stable identifier resolved from the repo root
  (worktrees resolve to their parent repo's identity, so
  `.claude/worktrees/*` runs tag as `attune-ai`).
- Both fields are additive and optional — `from_dict` on old
  records keeps working (asserted).

**RC-4 — Test isolation: the suite never writes production
telemetry again**
The pollution class is closed at the fixture layer, not by
convention.

- An autouse fixture (or env guard honored by the backend, e.g.
  `ATTUNE_TELEMETRY_DIR`) redirects ALL telemetry writes to
  `tmp_path` for the entire suite. A drift-guard test fails if a
  suite run leaves the canonical stream's mtime/size changed.
- The historical-purity rule for miners is stated once, here:
  records whose `workflow_name` matches the known fixture-name set
  OR that predate RC-3's fields are eligible only as
  unknown-provenance backfill, and fixture-named records are
  excluded outright.

**RC-5 — Retention compatible with mining; readiness re-pointed**
The corpus must be allowed to reach RR-1's viability bar and the
readiness check must measure the right stream.

- The canonical stream is NOT subject to the ops 30-day prune
  (telemetry files are already unpruned; this is asserted so a
  future "clean up telemetry" change trips a test, not the miner).
  A size guard (e.g. rotate past 50 MB into
  `~/.attune/telemetry/archive/`) keeps the file bounded without
  deleting history the miner can read.
- pipeline-learner RR-1's readiness check inspects the canonical
  stream (+ optional historical backfill per RC-4's purity rule)
  and reports the same four numbers (eligible records, distinct
  workflows, distinct active days, date span). The RR-4 source
  pin is amended in the same PR that lands this change, citing
  this spec.

## Non-goals

- Fixing or redesigning the ops dashboard run store — it works as
  designed; only the cosmetic empty-dir `rmdir` in
  `prune_old_runs` may ride along if trivial.
- Bulletin archive input (stays deferred per pipeline-learner
  RR-4).
- Cleaning or rewriting historical polluted records — purity is a
  read-time filter (RC-4), not a data migration.
- Cross-project mining semantics (RC-3 only makes the field
  exist).

## Acceptance (spec-level)

1. Live-fire: MCP + CLI runs from a worktree land in the canonical
   stream (RC-2 receipt).
2. Suite run leaves the canonical stream untouched (RC-4
   drift-guard green).
3. A full pytest pass followed by the readiness check reports zero
   NEW fixture-named records post-cutover.
4. pipeline-learner's readiness check, pointed at the canonical
   stream, reports honestly — including "insufficient corpus" if
   real usage hasn't yet crossed RR-1's viability bar. This spec
   makes accumulation possible; it does not fake the bar.

## Open questions — RULED 2026-07-19

All three ruled by the chair; rulings + evidence in
`decisions.md`:

1. A vs. B → **B** (canonicalize the telemetry stream).
2. RR-4 amendment path → **chair-ruled edit** citing this spec;
   lands with the RC-5 change.
3. Historical backfill → **start clean** (89% of real-named
   archive records sit in test-like bursts; the burst-free
   remainder is 408 records, none newer than two months; no
   verifiable purity filter exists). Archives stay on disk;
   revisit only against a known-clean post-cutover stream.
