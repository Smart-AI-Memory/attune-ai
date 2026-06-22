# Tasks — Agent Surface Parallelism Evaluation
**Status:** RETIRED (2026-05-29) — orchestrator already ships in `deep_review.py`; see requirements.md / decisions.md
| Phase | Status | Owner | Notes |
|---|---|---|---|
| Phase 0 — Telemetry + A/B measurement | in progress | | 0.1 done 2026-05-16, see `phase0-findings.md` |
| Phase 1 — Design + flagged implementation | gated on Phase 0 | | Only if matrix says PROCEED |
| Phase 2 — Rollout decision | gated on Phase 1 | | |

---

## Phase 0 — Measurement (cheap, ~$10–20)

**Goal:** route the decision in `decisions.md` with real numbers, not hypotheses.

- [x] **0.1** Telemetry pull. Query `~/.attune/telemetry/usage.jsonl` for the last 90 days. Output: `phase0-data/multi-workflow-sessions.csv` with one row per session showing workflows invoked + count. Compute `% of sessions with ≥2 analytical workflows`. **Done 2026-05-16 — 45.7% multi-analytical sessions, frequency gate clears. See `phase0-findings.md`.**
- [ ] **0.2** Resolve `decisions.md` D1 (target codebase region) and D2 (fan-out concurrency) based on Phase 0 design notes. Commit the resolution.
- [ ] **0.3** Sequential baseline. Pick target region (per D1). Run `/security`, `/code-quality`, `/deep-review` sequentially in a fresh session. Capture wall-clock, total cost, total tokens for each. Save reports to `phase0-data/sequential-baseline/`.
- [ ] **0.4** Parallel arm. Build a throwaway orchestrator (no need to be production-ready) that uses the Task tool / SDK subagents to fan out the same three analyses. Capture same metrics + the synthesized output. Save to `phase0-data/parallel-arm/`.
- [ ] **0.5** Qualitative comparison. Side-by-side read of the three sequential reports vs. the synthesized parallel output. Hand-evaluate (a) signal preserved (b) novel insight from synthesis (c) readability.
- [ ] **0.6** Phase 0 report. Write `phase0-findings.md` consolidating: telemetry %, wall-clock delta, cost delta, qualitative call. Apply the pre-committed matrix to route the decision. If RETIRE, mark this spec retired in its `decisions.md` and close.

**Budget cap:** $20. If Phase 0 measurement exceeds $20, stop and re-scope before continuing.

---

## Phase 1 — Design + flagged implementation (only if Phase 0 says PROCEED)

- [ ] **1.1** Resolve `decisions.md` D3 (surface) and D4 (synthesis hosting) based on Phase 0 qualitative findings.
- [ ] **1.2** Design doc covering: orchestrator subagent system prompt, tool inventory, synthesis prompt, failure modes (one of N subagents fails, partial results), cost-cap behavior.
- [ ] **1.3** Implementation behind feature flag `ATTUNE_PARALLEL_REVIEW=1`. No default rollout.
- [ ] **1.4** Real-user dogfood for 1 week. Telemetry on flag usage and outcomes.

---

## Phase 2 — Rollout decision (gated on Phase 1 dogfood)

- [ ] **2.1** Aggregate Phase 1 dogfood telemetry. Compare against Phase 0 hypothesis.
- [ ] **2.2** Decision: graduate flag to default-on, keep flag-only, or revert. Document in `decisions.md` D5.

---

## Retirement criteria

This spec auto-retires if any of the following:

- Phase 0 routes to RETIRE per the matrix in `decisions.md`.
- 90 days pass without Phase 0 being started (signals deprioritization).
- A different spec (e.g. session-level parallelism, workflow-level concurrency) ships and obviates the need.

Retirement note goes in `decisions.md` with a one-line summary.
