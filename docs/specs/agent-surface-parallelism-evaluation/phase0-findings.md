# Phase 0 Findings — Agent Surface Parallelism Evaluation

**Status:** partial — Task 0.1 (telemetry pull) complete; Tasks 0.2–0.6
still gated on Patrick's go-ahead for cost-spending arms.
**Date:** 2026-05-16

---

## TL;DR

- **Frequency gate: PASS with caveat.** 45.7% of inferred sessions
  invoke ≥2 analytical workflows — well above the matrix's 10% gate.
- **Caveat — single-operator data.** All 19,014 telemetry events come
  from 3 user_ids dominated by one (13,318 events). The "% of
  sessions" is essentially "% of Patrick's sessions," not external
  user behavior.
- **Premise concern.** 27 of the 48 multi-analytical sessions use
  exactly `bug-predict + code-review + security-audit` — the workflow
  trio `/deep-review` already bundles via Claude Agent SDK subagents.
  The spec's proposed implementation may be ~50% pre-existing.
- **Routing.** Frequency gate clears, but the matrix has two more
  gates (wall-clock savings ≥30% AND qualitative synthesis value)
  that need 0.3–0.5 to measure. The deep-review overlap means those
  comparisons may show smaller-than-expected wins.

---

## Method

- **Input.** `~/.attune/telemetry/usage.jsonl` (v1.0 schema,
  2026-02-16 → 2026-05-09, 19,014 events).
- **Filtered out.** Test-fixture workflows (`stub-workflow`,
  `test-tier-fallback`, `test-workflow`, `success-workflow`,
  `failing-stub`). Left 5,820 real events.
- **Session inference.** Time-gap heuristic per `user_id`: any gap
  >30 minutes between consecutive events starts a new session. Yields
  105 inferred sessions.
- **Analytical workflows.** `security-audit`, `code-review`,
  `bug-predict`, `deep-review`, `refactor-plan`, `perf-audit`,
  `test-audit`, `doc-audit`. The user-facing review/audit family the
  spec proposes to fan out.
- **Reproduction.** `python3 phase0-data/analyze_telemetry.py` from
  repo root regenerates the CSV and `summary.txt`. The script is
  intentionally short and stdlib-only.

---

## Headline metrics

| Metric | Sessions | % |
|---|---:|---:|
| Total inferred sessions | 105 | 100.0 |
| Sessions with ≥2 distinct workflows (any kind) | 101 | 96.2 |
| Sessions with ≥1 analytical workflow | 82 | 78.1 |
| **Sessions with ≥2 analytical workflows** | **48** | **45.7** |
| Sessions with ≥3 analytical workflows | 37 | 35.2 |
| Sessions with ≥4 analytical workflows | 8 | 7.6 |

Matrix gate per `decisions.md`: multi-analytical ≥10% → frequency gate
clears, downstream gates needed.

---

## Distribution by analytical-workflow count

| Analytical count | Sessions | % |
|---:|---:|---:|
| 0 | 23 | 21.9 |
| 1 | 34 | 32.4 |
| 2 | 11 | 10.5 |
| 3 | 29 | 27.6 |
| 4 | 2 | 1.9 |
| 5 | 6 | 5.7 |

The bimodal shape (1 or 3 analytical workflows dominant) is the
fingerprint of two distinct patterns: a single-workflow "drive-by"
mode (1 analytical) and a bundled review mode (3 analytical) — see
next section.

---

## Top multi-analytical combinations

| Count | Combination |
|---:|---|
| 27 | `bug-predict + code-review + security-audit` |
| 9 | `code-review + security-audit` |
| 6 | `bug-predict + doc-audit + perf-audit + refactor-plan + test-audit` |
| 2 | `bug-predict + code-review + perf-audit + security-audit` |
| 1 | `bug-predict + code-review` |
| 1 | `doc-audit + perf-audit + refactor-plan` |
| 1 | `doc-audit + refactor-plan + test-audit` |
| 1 | `refactor-plan + test-audit` |

**Observation: the modal multi-analytical combo IS `/deep-review`.**
27 of 48 multi-analytical sessions invoke exactly the
`bug-predict + code-review + security-audit` triplet. That trio is
the same one `/deep-review` already spawns as three Claude Agent SDK
subagents:

- `src/attune/workflows/deep_review.py` — defines subagents
  `security-reviewer`, `quality-reviewer`, `test-gap-reviewer` and a
  Task-tool-based orchestrator.
- The orchestrator prompt does not specify sequential execution; the
  SDK's default dispatch behavior is for parallel Task tool calls
  emitted in one assistant turn.

This means the spec's "novel value" question collapses to:

1. Are the 27 telemetry hits actually `/deep-review` invocations
   surfaced as their constituent workflow events (likely yes — the
   subagent dispatch records under the constituent workflow names)?
2. If yes, does the SDK already run them in parallel? (Needs measure.)
3. If parallel already, what is the proposed orchestrator adding over
   `/deep-review` aside from a fresh skill name?

These are exactly the questions Phase 0.3–0.5 was designed to answer.
The deep-review overlap makes the qualitative-value gate harder, not
easier, to clear.

---

## Data caveats

1. **Single-operator skew.** Three distinct `user_id` hashes; one
   accounts for 13,318 of 19,014 events. This is Patrick's dev/test
   activity — not external user behavior. The 45.7% number is
   directionally meaningful for one developer's workflow patterns but
   under-validated as a population metric.
2. **Automated-pipeline events not separable.** Several sessions
   (e.g. session #1, #2, #3, #5, #8, #9 in the CSV) show identical
   workflow sequences and short durations — characteristic of release
   prep or CI dogfooding, not interactive review. No `session_id`
   field exists to filter these out cleanly.
3. **30-minute gap heuristic.** Choice is conservative for
   interactive sessions; longer-running batched jobs may collapse
   together. Sensitivity testing not done — would not change the
   headline by more than a few percentage points based on visual
   spot-check of the CSV.

---

## Recommendation

Frequency gate clears. **Recommend running Phase 0.3 (sequential
baseline) and 0.4 (parallel arm) as designed** — but specifically
target the comparison against `/deep-review`'s subagent pipeline as a
control, not just the three workflows run serially in shell. This
rephrases the matrix's wall-clock and qualitative gates:

| Original gate | Refined gate |
|---|---|
| Wall-clock savings vs running 3 workflows serially | Wall-clock savings vs `/deep-review`'s current subagent pipeline |
| Synthesis adds qualitative signal | Synthesis adds qualitative signal _beyond what /deep-review already produces_ |

If the refined gates both clear, the spec's value is "make
`/deep-review`'s parallelism explicit and possibly extensible to other
workflow combos." If one or both fail, the spec retires because
`/deep-review` already covers the modal pattern.

**Budget impact:** unchanged. Phase 0.3–0.5 still fits under the $20
cap. The refined comparison costs the same — one extra
`/deep-review` run instead of three separate workflow runs.

---

## Pointer files

- `phase0-data/analyze_telemetry.py` — reproducible analysis script
- `phase0-data/multi-workflow-sessions.csv` — one row per inferred
  session
- `phase0-data/summary.txt` — raw output of the analysis script
