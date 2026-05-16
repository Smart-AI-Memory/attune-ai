# Requirements — Agent Surface Parallelism Evaluation

**Status:** draft (2026-05-16)
**Pairs with:** [`agent-surface-rebalance`](../agent-surface-rebalance/) (retired 2026-05-12)

---

## Problem

Today, the plugin surfaces 15 skills under `plugin/skills/` and exactly one subagent (`setup-guide`) under `plugin/agents/`. A user running multiple analytical workflows in a session (e.g. `/security`, `/deep-review`, `/code-quality`) runs them sequentially through MCP tool invocations. Each tool runs in its own isolated SDK session (verified by the retired `agent-surface-rebalance` Phase 0 measurement, 2026-05-12), so context bleed is not the concern — but wall-clock latency is.

A 4-subagent fan-out architecture would let the main agent spawn analytical subagents in parallel and synthesize their results, in principle reducing the wall-clock for a "review my changes" session from `sum(durations)` to `max(durations)`. Whether this materially helps depends on:

1. How often users actually invoke multiple analytical workflows in one session.
2. Whether the wall-clock saving compensates for the per-subagent overhead (system prompt, tool inventory, model warmup).
3. Whether the synthesis step adds enough value vs. the user reading three separate reports.

## Non-goals

- **Not a context-byte-savings spec.** That premise was measured and retired in `agent-surface-rebalance/decisions.md` D2. Subagent isolation prevents byte bleed; MCP already isolates equivalently.
- **Not a wholesale skill → subagent migration.** The 15-skill surface is the right shape for single-workflow invocation. The question is whether a *parallel orchestrator subagent* belongs alongside it.
- **Not in scope: fix-test, smart-test, or remediation loops.** Those have a different shape (sequential dependence on test results) and would earn their own spec.

## Success criteria

A measurable Phase 0 result that routes a clear decision:

- **PROCEED** if measured wall-clock savings on a real multi-workflow session ≥ 30% AND user-readable synthesis is qualitatively better than three separate reports.
- **DEFER** if either bar is missed.
- **RETIRE** if Phase 0 shows the multi-workflow pattern is rare enough that the wall-clock saving applies to <5% of sessions (i.e. solving a nonexistent problem).

The decision matrix lives in `decisions.md` and is committed BEFORE Phase 0 runs, per the existing CLAUDE.md lesson on pre-committed decision matrices.

## Measurement plan (Phase 0)

1. **Telemetry pass**: query `~/.attune/telemetry/usage.jsonl` for the last 90 days. Count sessions that invoked ≥2 analytical workflows (`security_audit`, `code_review`, `deep_review`, `bug_predict`, `dependency_check`, `performance_audit`). Compute the percentage of all sessions.
2. **Synthetic A/B**: pick one realistic target (e.g. `src/attune/ops/`, ~30 files). Run sequentially: `/security` + `/deep-review` + `/code-quality`. Record wall-clock, total cost, total tokens. Then implement a throwaway orchestrator subagent that fans out the same three analyses in parallel; record the same metrics.
3. **Qualitative**: capture all three reports side-by-side and the synthesized output. Hand-eval whether the synthesis adds meaningful signal or just paraphrases.

## Open questions

- **DECIDE-1**: Which target codebase region for the A/B measurement? Should be representative — not the easiest, not the hardest. Candidate: `src/attune/ops/` (29 files, ~5k LOC).
- **DECIDE-2**: How many analytical workflows in the parallel fan-out? Three is the smallest interesting number; four hits Anthropic's typical concurrency budget; six approaches the cost-cap edge.
- **DECIDE-3**: If PROCEED, what's the surface? A new `/review-all` skill that delegates to the orchestrator subagent? A new MCP tool? A new agent template that users register?

## Out-of-band

Whether this spec proceeds depends entirely on Phase 0. The risk profile (cheap measurement, well-defined decision matrix) means writing the spec is itself cheap. Implementation cost only attaches if measurement endorses it.
