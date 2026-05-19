# Decisions — Agent Surface Parallelism Evaluation

**Status:** in progress (2026-05-19) — Phase 0.1 complete (telemetry), refined baseline + D2 resolved; D1 provisional; D3+D4 still gated on Phase 0 outcome

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

**Status:** RESOLVED 2026-05-19 — see "Resolved decisions" below. Chosen: 3 workflows = `bug-predict + code-review + security-audit` (the modal triplet from Phase 0.1).

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

### Refined baseline for Phase 0.3–0.5 (2026-05-19)

**Decision:** Phase 0.3 (sequential) and 0.4 (parallel) compare against `/deep-review` as the baseline, NOT three workflows run serially via shell as the original spec proposed.

**Rationale:** Phase 0.1 findings (2026-05-16) showed that 27 of 48 multi-analytical sessions hit exactly the `bug-predict + code-review + security-audit` triplet — which is what `/deep-review` already spawns as Claude Agent SDK subagents (`src/attune/workflows/deep_review.py:268-291`). The proposed orchestrator substantially duplicates `/deep-review`'s pipeline. Measuring against three-workflows-serial would inflate the wall-clock-savings number relative to reality, and the qualitative-synthesis gate has to clear "better than `/deep-review`" — not "better than no synthesis at all" — to justify a new surface.

**Concrete change to tasks:**
- **0.3 (Sequential baseline)**: run `/security`, `/code-review`, `/bug-predict` sequentially against the target region. Capture wall-clock, cost, tokens. This is the worst-case latency upper bound.
- **0.3b (New)**: run `/deep-review` once against the same target. Capture the same metrics plus a trace of whether the orchestrator dispatched subagents in one assistant turn (parallel) or three (serial). This is the *real* baseline.
- **0.4 (Parallel arm)**: build a throwaway orchestrator that fans out the same three analyses in parallel. Capture same metrics.
- **0.5 (Qualitative)**: hand-eval the parallel arm's synthesis vs both (a) the three sequential reports and (b) `/deep-review`'s synthesized output.

**Gates (refined per Phase 0.1 recommendation):**

| Original gate | Refined gate |
|---|---|
| Wall-clock savings vs 3-workflows-serial | Wall-clock savings vs `/deep-review` pipeline |
| Synthesis adds qualitative signal | Synthesis adds signal *beyond what /deep-review already produces* |

The pre-committed matrix in this file still routes the decision; only the comparison baseline changed.

### Probe before measurement (2026-05-19)

**Decision:** Phase 0.3 instruments the `/deep-review` run to determine whether its subagents currently dispatch in parallel or serially.

**Rationale:** The orchestrator system prompt (`deep_review.py:121-126`) and task template (`deep_review.py:128-148`) say "each subagent focuses on a specific domain and will report findings independently" — a parallel hint, but not a guarantee. The Claude Agent SDK's dispatch behavior depends on whether the orchestrator issues multiple Task tool calls in one assistant turn. If it does (parallel), the spec retires because the proposed work is already shipping. If it doesn't (serial), the right fix is a one-line orchestrator-prompt tweak to deep-review, not a new orchestrator skill. Either way, this probe costs nothing extra — same `/deep-review` run that's already in 0.3b.

**Probe output:** record in `phase0-data/deep-review-trace.md`: the sequence of assistant turns and which Task tool calls fire in each. One-line conclusion: "parallel" or "serial" or "mixed."

### D1 — Target codebase region: (a) `src/attune/ops/` (provisional)

**Status:** provisional — confirm at Phase 0.3 kickoff that `ops/` is still ~29 files / ~5k LOC. Has grown substantially since 2026-05-16; may now be ~40 files. Verify with `find src/attune/ops -name "*.py" | wc -l` before running measurement.

**Rationale:** Mid-size representative codebase. Pattern matches what users actually invoke `/deep-review` on. Cheaper than `src/attune/workflows/` (15k LOC) but more realistic than a single file.

### D2 — Concurrency in parallel fan-out: 3 workflows

**Status:** RESOLVED.

**Choice:** `bug-predict + code-review + security-audit` — the modal triplet from Phase 0.1 telemetry (27 of 48 multi-analytical sessions). Matches what users actually run. Avoids spec-original `code-quality + deep-review` which was partially redundant with `/deep-review` itself.

**Rationale:** Three is the smallest interesting number per the original spec. Using the telemetry-derived modal triplet means the measurement directly addresses the dominant real-world usage pattern. Four+ workflows are out of scope for Phase 0 — revisit if Phase 0 routes to PROCEED.

### Single-operator skew — acknowledged limitation (2026-05-19)

**Acknowledgment:** Phase 0.1's 45.7% multi-analytical-sessions figure is heavily Patrick-weighted (13,318 of 19,014 events from one user_id). All Phase 0 measurement decisions inherit this skew. Even with rigorous A/B, the outcome reflects "what's right for Patrick's workflow pattern," not external users. This is a known limitation and not a blocker — but any PROCEED/DEFER/RETIRE decision must be honest about the sample size.

**Mitigation:** if Phase 0 routes to PROCEED, Phase 1 dogfood (gated on feature flag) becomes the multi-user telemetry pass. If it routes to RETIRE or DEFER, the single-operator caveat is documented and we trust that real users hitting a different pattern would surface a different spec.
