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
commit.

## 2026-07-19 — Execution armed and implemented (chair: option 1)

Chair armed execution the same day. Implementation (branch
`feat/run-record-corpus`): RC-1 canonical stream routing in
`TelemetryStore` (explicit `storage_dir` still keeps every file
local — test isolation unchanged); RC-3 `trigger`/`project` fields
+ `run_context.py` resolvers wired into BOTH emit paths
(`TelemetryMixin` and `TelemetryService`); RC-4 store singleton
reset added to the existing `_isolate_attune_home` autouse fixture
+ drift-guard test; RC-5 no-delete 50 MB rotation into
`telemetry/archive/` + ops-prune non-interference test; RR-4
amendment landed in pipeline-learner (see its decisions.md).

**RC-2 audit result — the SDK-era dry pipe had a second cause.**
Live-fire probing found the modern SDK-native workflows
(code-review, security-audit, etc. — 17 files) override
`execute()` wholesale and never reach `ExecutionMixin.execute`'s
telemetry epilogue: they logged per-stage usage but NO run record.
That, not only worktree fragmentation, is why the corpus has
near-zero real records in the June–July SDK era. Closed at one
seam: `BaseWorkflow.__init_subclass__` wraps any subclass-defined
async `execute` to emit best-effort after completion, with an
idempotence marker on the result object (guarded `is True` so
MagicMock results can't fake it). A run that raises without
producing a result emits nothing — not a run. Receipts: live-fire
`CodeReviewWorkflow.execute()` from this worktree against a
scratch `ATTUNE_HOME` landed records on both the validation-error
and keyless-SDK-failure paths with `trigger=manual`,
`project=attune-ai` (worktree resolved to parent repo); full unit
suite 17,719 passed; new module serial-clean.

**Audit gap (named follow-up, out of this PR):** agent-team
workflows that bypass `BaseWorkflow` entirely (observed:
`health-check`, `agents_executed=3`, ran green, emitted nothing)
need their own emission seam. Low corpus impact — the volume is in
the SDK workflows — but RC-2's "every path" is not fully closed
until it lands.

**Named follow-up (RC-3, not in this PR):** the dashboard
rec-click attribution stamp — threading a `trigger` field through
`POST /workflows/{name}/run` → `RunnerService.execute` →
`ATTUNE_RUN_TRIGGER` in the subprocess env, plus the client-side
send on next-workflow recommendation clicks. Until it lands,
dashboard runs record as `manual` (correct for workflow-button
clicks, conservative for rec clicks per `resolve_run_trigger`'s
stated bias).

## 2026-07-19 — RC-2 follow-up closed: report-shaped results emit

**Root-cause correction.** The named follow-up ("agent-team
workflows that bypass `BaseWorkflow` entirely") was mis-attributed:
`OrchestratedHealthCheckWorkflow`, `DocumentationOrchestrator`, and
`SecureReleasePipeline` all subclass `BaseWorkflow` and ARE wrapped
by the RC-2 `__init_subclass__` seam. What they bypass is the
`WorkflowResult` SHAPE: their `execute` returns report objects
(`HealthCheckReport`, `OrchestratorResult`, `SecureReleaseResult`)
without `stages`/`cost_report`/timestamps, so
`_emit_workflow_telemetry` died on `result.stages`
(`AttributeError`), was swallowed by the wrapper's best-effort
catch, and recorded nothing — reproduced by probe before the fix.

**Fix.** Emission is now shape-tolerant in BOTH emit paths
(`TelemetryMixin._emit_workflow_telemetry` and
`TelemetryService.emit_workflow_record`): a report-shaped result
gets a degraded record — identity, `trigger`/`project` provenance,
wall-clock timing captured by the execute-wrapper, success/error —
with stage detail and cost totals honestly zero, not guessed. The
service path also gained the idempotence marker it lacked (double
emission was possible when ctx-based workflows chain
`super().execute()`).

**Receipts.** Repro probe (report-shaped result → 0 files,
AttributeError in debug log) then post-fix probe (1 record,
idempotent on re-emit); live-fire keyless
`OrchestratedHealthCheckWorkflow(mode="daily").execute(path=".")`
from this worktree against a scratch `ATTUNE_HOME` landed
`workflow_name=orchestrated-health-check`, `trigger=manual`,
`project=attune-ai`, `success=False` (one agent failed keyless —
honest), `total_duration_ms=116339`. Serial suite:
`tests/unit/telemetry/test_run_record_corpus.py` 22 passed (6 new
in `TestReportShapedEmission`); breadth:
`tests/unit/workflows tests/unit/telemetry` 3324 passed.

**Still open (unchanged).** The dashboard rec-click attribution
stamp (RC-3 follow-up) — dashboard runs still record as `manual`.

## 2026-07-19 — RC-3 follow-up closed: rec-click attribution stamp

The dashboard now stamps recommendation-launched runs end-to-end:
the three rec surfaces in `run_view.js` (chain pills, rec cards,
suggestion chips) send `{"trigger": "attune-rec"}` in the run POST;
`POST /workflows/{name}/run` validates the field (unknown values
400 at the API edge, though the child-side resolver stays
junk-tolerant); `RunnerService.start` threads it onto the `Run`
(persisted in the ops record via `to_dict`/`from_record`, additive
— pre-RC-3 records load as `None`); and `_execute` exports
`ATTUNE_RUN_TRIGGER` into the subprocess env so the workflow's own
canonical run record carries the attribution via
`resolve_run_trigger`. The manual Run button (`runner.js`) sends no
trigger and keeps resolving to `manual` — `resolve_run_trigger`'s
conservative bias is now only the fallback, not the steady state.

Receipts: `tests/unit/ops/test_run_trigger_attribution.py` (9
tests, serial) — including a REAL subprocess round-trip through
`_execute` observing `ENV_TRIGGER=attune-rec` in the child, the
400-on-junk contract, record round-trip, and source-level guards
that all three rec surfaces stamp while the manual button doesn't;
`tests/unit/ops` breadth 1463 passed. Browser-click verification
deferred deliberately: a live dashboard click launches a real
billable workflow; the subprocess seam test exercises the same
boundary keylessly.
