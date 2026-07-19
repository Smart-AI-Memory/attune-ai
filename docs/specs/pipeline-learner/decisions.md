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
