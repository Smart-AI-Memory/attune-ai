# Pipeline Learner — Decisions

## 2026-07-19 — RR-1 external dependency resolved; source pin amended (chair)

**The run-persistence diagnosis (RR-1's named external
dependency).** The chip investigation session confirmed
`src/attune/ops/runner.py` persists one JSON per run correctly —
the 15-dirs/1-file signature is design, not breakage: persistence
is wired only in the ops dashboard server, and a 30-day prune at
every dashboard startup unlinks aging files while leaving empty
workflow dirs. The ops store's ceiling ("dashboard-launched runs
from the last 30 days") can never satisfy RR-1's corpus premise.

**Owner and fix.** `docs/specs/run-record-corpus/` (chair-ruled
2026-07-19) owns the fix: the telemetry seam
(`TelemetryMixin._emit_workflow_telemetry`) already emits one
`WorkflowRunRecord` per workflow execution on every path (MCP,
CLI, dashboard subprocess); that stream is canonicalized
home-global at `~/.attune/telemetry/workflow_runs.jsonl` with
`trigger` + `project` fields, suite isolation, and no-delete
rotation. See its decisions.md (D1–D3) for the fork evidence.

**Amendment (D2, chair-ruled edit).** RR-4's source pin and the
RR-1/RR-2 source references in requirements.md are amended
in-place (marked "amended 2026-07-19") from
`~/.attune/ops/runs/**/*.json` to the canonical stream. The
table's other text stands; the amendment block at the top of
requirements.md carries the rationale.

**Start clean (D3).** Records predating the 2026-07-19 cutover
are ineligible for mining: the pre-cutover archive is
pytest-polluted (89% of real-named records inside test-like
bursts) with no verifiable purity filter. RR-1's viability bar
must be met by post-cutover accumulation — the readiness check
reports honestly until then.

## 2026-07-19 — RR-8 lifecycle: fixture-only components LAND NOW (chair)

The chair chose RR-8's first lifecycle option: the
fixture-buildable core lands now with production surfacing
disabled. Shipped as `src/attune/pipeline_learner/` — corpus
loader + RR-1 readiness gate (`corpus.py`, cutover pinned at
2026-07-19T17:41:26Z, fixture-name exclusion, per-drop counters),
RR-2 miner + RR-3 ranker (`mining.py`; stated formula
0.35·freq + 0.25·ratio + 0.25·recency(30d half-life) +
0.15·manual-fraction, injected `now`, support-then-lexical
tie-breaker), RR-6 ledger (`decisions.py`, reopen delta = 3), and
the RR-7 acceptance scaffold (`scaffold.py`, validates against
`_DEFAULT_WORKFLOW_NAMES`, never registers). `learn()` proposes
nothing over an unready corpus and produces zero writes. RR-5
(curator source) is explicitly NOT built — gated until RR-1's
readiness passes on the live corpus; when it passes, RR-5 is the
next execution unit.
