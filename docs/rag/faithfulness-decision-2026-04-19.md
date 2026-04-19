## Faithfulness Decision (attune-rag v0.1.3)

**Date:** 2026-04-19
**Decision owner:** Patrick Roebuck.
**Context:** After Phase 2.5c closed out retrieval work
(P@1 73.3%, fastembed deferred), the remaining accuracy
gap was **faithfulness** — the LLM retrieves correct
passages but still drifts into prior knowledge.

**Pre-committed gate:** top prompt variant must reach
mean faithfulness ≥ 0.85 to ship as the new default.
Below that, escalate to experiment 3 (extract-then-answer
two-stage pipeline).

---

## Decision

**Ship `citation` as the default prompt variant in
attune-rag v0.1.3. Experiment 3 is unnecessary.**

Hallucination rate drops from **46.7% → 6.7%** vs
baseline with identical retrieval quality. Mean
faithfulness reaches **1.00** — the single residual
unsupported claim is one of sixteen inside an already-hard
query (`gq-013 "orchestrate documentation workflow"`).

---

## Experiment design (Experiments 1 + 2)

Built in attune-rag and run on 2026-04-19:

1. **Faithfulness judge** — `FaithfulnessJudge` at
   `src/attune_rag/eval/faithfulness.py`. LLM-as-judge
   using Anthropic forced tool-use for guaranteed-schema
   JSON output. Decomposes each answer into atomic
   factual claims, marks each supported / unsupported
   against the retrieved passages, returns a 0-1 score.
2. **Prompt surgery** — three variants alongside
   `baseline` in `src/attune_rag/prompts.py`:
   - `strict` — refuses to answer outside the context
   - `citation` — forces `[P1]` / `[P2]` markers per
     claim, passages numbered at render time
   - `anti_prior` — tells the model its training data on
     attune is stale and the context is authoritative
3. **A/B runner** — `attune_rag.eval.bench_prompts`
   sweeps all four variants × 15 golden queries,
   generates + judges each answer, prints a table. 120
   LLM calls total (~$2, ~12 min sequential).

---

## Results

| variant | P@1 | R@3 | **faith** | refusal | **hallu.** |
|---|---|---|---|---|---|
| baseline | 73.3% | 86.7% | 0.94 | 0.0% | **46.7%** |
| strict | 73.3% | 86.7% | 0.97 | 0.0% | 26.7% |
| **citation** | 73.3% | 86.7% | **1.00** | 0.0% | **6.7%** |
| anti_prior | 73.3% | 86.7% | 0.95 | 0.0% | 33.3% |

Full per-query detail:
[ab-report-2026-04-19.json](./ab-report-2026-04-19.json).

**Read:** `faith` = mean faithfulness score ∈ [0, 1];
`hallu` = share of answers containing ≥1 unsupported
claim; `refusal` = share of answers the judge parsed as
zero-claim. Retrieval metrics (P@1, R@3) are identical
across variants — as expected, retrieval is upstream of
the prompt.

---

## Why citation wins

Two mechanisms, both causally downstream of the forced
cite-per-claim requirement:

1. **No citation = no claim.** Unsupported sentences are
   structurally awkward to produce. The model can't paste
   a `[P1]` marker onto a claim it can't locate in the
   passages without contradicting the template's
   no-unsupported-cite rule — so it tends to drop the
   sentence instead.
2. **Citation acts as a self-check loop.** Rendering
   `[P1, P3]` forces the model to re-scan those specific
   passages before emitting the sentence. That
   re-verification catches drift at the point of
   generation rather than relying on post-hoc filtering.

`strict` and `anti_prior` address the same failure mode
(prior-knowledge drift) with softer instructions.
Neither creates the structural speed-bump that
`citation` does, which is why they clear the gate but
don't approach 1.00.

---

## Follow-up wiring in v0.1.3

- `RagPipeline.run(...)` and `run_and_generate(...)`
  default to `prompt_variant="citation"`.
- `python -m attune_rag.benchmark --with-faithfulness
  --min-faithfulness 0.85` adds an opt-in faithfulness
  gate to the existing retrieval benchmark. Default off
  (the retrieval benchmark stays free / offline).
- `attune_rag.eval` exposes `FaithfulnessJudge` and
  `FaithfulnessResult` for third-party callers.

---

## What we did NOT do (and why)

- **Experiment 3 (extract-then-answer two-stage
  pipeline).** Pre-committed gate was ≥ 0.85 mean
  faithfulness from the top variant. Citation cleared it
  at 1.00. Building a two-stage pipeline that doubles
  inference cost to fix a 6.7% hallucination rate would
  regress ROI.
- **Tuning prompts further.** The single failure is
  inside a difficulty-hard query that was already
  flagged in the golden set as a keyword collision. A
  fixture-level fix (disambiguate the expected targets)
  is cleaner than a prompt tweak that could regress
  other variants.
- **Adding a faithfulness CI gate to every `pytest`
  run.** Every run would spend API tokens. The gate
  lives on the opt-in benchmark command where the cost
  is explicit.

---

## Residuals worth tracking

- **Judge variance.** A single judge model (Sonnet 4.6)
  scoring itself as generator may systematically under-
  call its own hallucinations. Worth a sanity check with
  a second model (Opus or a non-Anthropic model) before
  tightening the gate past 0.95.
- **Fixture coverage.** 15 queries × 4 variants is
  enough to decide between variants but under-powered
  for detecting subtle regressions. Expand the golden
  set to ~40-50 queries before relying on the
  faithfulness gate as a sole CI signal.
- **Judge latency.** Every `--with-faithfulness` run
  spends ~2 min + ~$0.30 at the current 15-query set.
  If we grow the fixture or run the gate on every PR,
  this is the budget line to watch.

---

## Links

- attune-rag v0.1.3 CHANGELOG entry
- Judge: `src/attune_rag/eval/faithfulness.py`
- Variants + registry:
  `src/attune_rag/prompts.py` (`PROMPT_VARIANTS`)
- A/B runner:
  `src/attune_rag/eval/bench_prompts.py`
- Benchmark gate wiring:
  `src/attune_rag/benchmark.py` (`--with-faithfulness`)
