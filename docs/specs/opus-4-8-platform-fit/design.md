# Design — Opus 4.8 Platform Fit (Phase 0 harness)

**Status:** superseded (2026-07-10) — by fable-premium-tier (premium tier opus-4-8 → claude-fable-5, approved 2026-07-10); Phase-0 harness never built or run (#674 was the mechanical prerequisite, not this scope)
**Phase 1:** [requirements.md](./requirements.md) — approved 2026-06-08 (#679)

Realizes Phase 0 (measure-first). Authoring is decoupled from
running: everything here is buildable with zero API spend; the
measurement run itself is gated on the API billing block clearing
and a ratified budget (OQ-3 answer below).

## Instrumentation: env-gated stream dump in the adapter

One additive change to `agent_sdk_adapter.collect_agent_output()` —
the single funnel every SDK workflow's message loop passes through:

- When `ATTUNE_SDK_STREAM_DUMP=<dir>` is set, append one JSON line
  per SDK message to `<dir>/<workflow>-<ts>.jsonl`: message type,
  per-block records (`kind`, `chars` for TextBlocks, `tool_name` for
  ToolUseBlocks, `parent_tool_use_id`), and the full ResultMessage
  metadata (cost, usage, turns, duration).
- Off by default; zero behavior change when unset (drift-guarded by
  a test asserting no dump file appears without the env var).
- Post-run, the harness also calls `collect_subagent_transcripts()`
  for per-subagent volume.

Rationale: every Phase-0 axis is derivable from this one dump —
narration volume (TextBlock chars between ToolUseBlocks; wrap-up =
trailing TextBlock run), subagent spawn count (Task/Agent tool-use
blocks), tool mix (tool_name histogram), ask-rate (AskUserQuestion
tool uses + interrogative terminal TextBlocks), effort fit + cost
(ResultMessage usage/duration/cost). No per-workflow changes.

## Harness: `scripts/phase0/opus48_behavior.py`

- **Corpus (OQ-1 answer): frozen in-tree snapshots.** Copy two
  bounded targets into `scripts/phase0/corpus/` at authoring time
  (`gates/` ~150 LOC — the proven bug-predict target — and
  `voice/report_renderer.py` + tests ~600 LOC). Live `src/` paths
  drift between runs; frozen copies make every re-run measure the
  same input forever.
- **Run matrix (9 runs):**
  - 3 workflows (`security-audit`, `code-review`, `deep-review`) ×
    1 corpus target × 2 models (4.8 premium map vs 4.6 pin) = 6 —
    the A/B for narration / subagents / tools / ask-rate / cost.
  - `security-audit` × 3 efforts (`medium`/`high`/`xhigh`) on 4.8
    = 3 — the effort-fit curve.
- **Baseline (OQ-2 answer): one-off Opus-4.6 A/B**, not telemetry —
  `usage.jsonl` lacks per-run subagent/tool counts; 4.6 is still an
  active model so a clean same-harness A/B is cheap and like-for-like.
- Each run: real API, `ATTUNE_MAX_BUDGET_USD=10` per run, dumps to
  `scripts/phase0/phase0-data/` (gitignored raw, committed
  `phase0-findings.md` summary). The harness computes the per-axis
  metrics table and emits it as markdown.
- Model pinning: a `--model-override` env passed through the premium
  tier map for the 4.6 leg (mechanism verified at implementation
  time against `adaptive_routing` — introspect, don't assume).

## Budget (OQ-3 answer — needs Patrick's ratification)

9 runs × multi-subagent on premium ≈ $3–8/run → **ceiling $90,
expected ~$50**. Hard per-run cap $10; the harness aborts the matrix
when cumulative spend crosses $90. Not running until the org billing
block clears.

## Decision flow

`decisions.md` carries the pre-committed per-axis matrix (committed
BEFORE any run — same PR as this design). After the run:
`phase0-findings.md` routes each axis TUNE/LEAVE strictly per the
matrix; all-LEAVE retires the spec with the artifact (a valid
outcome, per requirements).
