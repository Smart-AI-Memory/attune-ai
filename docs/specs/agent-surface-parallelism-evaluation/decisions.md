# Decisions — Agent Surface Parallelism Evaluation

**Status:** draft (2026-05-16) — no decisions resolved yet

---

## Pre-committed decision matrix (Phase 0 → action)

This matrix is recorded BEFORE Phase 0 runs, per the existing CLAUDE.md lesson "Pre-committed decision matrices survive contact with data." The commit timestamp of this file is the arbiter; we do not move the goalposts after seeing the numbers.

| Phase 0 result | Action |
|---|---|
| Multi-workflow sessions ≥ 10% of sessions AND wall-clock savings ≥ 30% AND synthesis adds qualitative signal | **PROCEED** to Phase 1 (design + small implementation behind a feature flag) |
| Multi-workflow sessions ≥ 10% AND wall-clock savings 15–30% | **DEFER** — write a decision doc with the measurements, revisit in 3 months |
| Multi-workflow sessions < 5% (rare pattern) | **RETIRE** — solving a nonexistent problem, no further work |
| Multi-workflow sessions 5–10% AND wall-clock savings ≥ 30% | **DEFER** — small audience, real benefit; revisit when telemetry has more data |
| Synthesis qualitatively NO BETTER than three separate reports | **RETIRE** — orchestrator adds latency without value |
| Wall-clock savings < 15% regardless of frequency | **RETIRE** — the architectural premise of parallelism didn't pan out |

---

## DECIDE callouts

### D1 — Target codebase region for the A/B

**Status:** open

**Options:**
- (a) `src/attune/ops/` — 29 files, ~5k LOC. Mid-size. Representative of dashboard work.
- (b) `src/attune/workflows/` — 60+ files, ~15k LOC. Larger; tests the cost-cap edge.
- (c) `src/attune/memory/` — 40+ files. Tests on a domain the analytical workflows have less prior context for.

**Recommendation pending Phase 0 design**: (a) for the first pass — large enough to be realistic, small enough to be cheap.

### D2 — Concurrency in the parallel fan-out

**Status:** open

**Options:**
- 3 workflows (`security`, `code-quality`, `deep-review`) — smallest interesting number.
- 4 workflows (add `bug-predict`).
- 5+ — approaches Anthropic concurrency limits and cost-cap edges.

**Recommendation pending Phase 0 design**: 3 for the first pass.

### D3 — Surface for PROCEED case

**Status:** open

If Phase 0 endorses, what's the user-facing surface?

**Options:**
- (a) New `/review-all` skill that delegates to an orchestrator subagent. Lowest discovery cost (a skill is what users look for).
- (b) New `/analyze` skill with a `--parallel` flag. Backward-compatible; same surface for single-workflow use.
- (c) MCP tool `analyze_parallel` that any skill can call. Most reusable; least discoverable.
- (d) Agent template registered as `parallel-analyst` that users invoke via `Task` tool. Maximum control; minimum hand-holding.

**Recommendation pending Phase 0 outcome**: defer until Phase 1.

### D4 — Where to host the synthesis step

**Status:** open

The orchestrator subagent that synthesizes the parallel results either (a) runs in the user's session (cheap, no new SDK session) or (b) launches as its own subagent with the three analytical results as context (clean separation, more cost).

**Recommendation pending Phase 0 outcome**: defer until Phase 1.

---

## Resolved decisions

(None yet — this is a draft.)
