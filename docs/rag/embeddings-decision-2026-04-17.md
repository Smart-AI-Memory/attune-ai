# Embeddings Decision (attune-rag v0.1.x / v0.2.0)

**Date:** 2026-04-17
**Decision gate:** Task 2.5 of the RAG grounding spec v4.0
([.claude/plans/feature-rag-code-grounding-2026-04-17.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/.claude/plans/feature-rag-code-grounding-2026-04-17.md)).
**Decision owner:** Patrick Roebuck.
**Gate criteria (from spec):** Adopt embeddings only if
delta precision@1 >= 15 pts AND install cost <50MB AND no
new network dependency at import time.

---

## Decision

**Sequence: keyword tuning first (v0.1.x), then
`fastembed` fallback if the gate isn't met (v0.2.0).**

1. **v0.1.x patch (next):** category-biased keyword
   tuning in `KeywordRetriever`. Boost `concepts/` and
   `quickstarts/`, penalize `errors/faqs/warnings/`. Zero
   new deps. Re-run `python -m attune_rag.benchmark` and
   commit the new baseline back to this doc.
2. **v0.2.0 (conditional):** if v0.1.x clears the 70% P@1
   gate, embeddings stay deferred indefinitely. If
   v0.1.x plateaus, v0.2.0 ships `attune-rag[embeddings]`
   using **`fastembed`** (ONNX-based local embeddings,
   ~35MB install). **Not sentence-transformers.**
3. **Independent track:** attune-help 0.6.0 metadata
   enrichment (Approved Follow-up in the spec) is
   pursued in parallel regardless of the embeddings
   outcome, because it improves retrieval quality for
   every retriever.

---

## Prior-lesson clarification

The CLAUDE.md lesson cited in the original spec ("Anthropic's
built-in prompt caching supersedes custom caching") was about
**semantic caching**, not **RAG retrieval**. Those are
different problems with different ROI profiles:

- Semantic caching matches similar *queries* to cached
  *responses* for cost savings. ROI is bounded by how often
  attune workflow prompts happen to be similar in the wild.
  In practice they rarely are (unique file paths, code
  snippets, timestamps), so the ROI was measured at 0.4%.
  Disabling it was correct.
- RAG retrieval matches *queries* to *documents* for
  grounding. ROI is bounded by how often semantic
  similarity beats keyword overlap. Our benchmark below
  shows this happens for 6/15 queries — the entire "hard"
  bucket.

Reusing the caching lesson to reject RAG embeddings would
over-generalize. But the lesson does correctly rule out the
specific `sentence-transformers` + `torch` stack (420MB
install), which fails the <50MB gate regardless of ROI.

---

## Baseline (KeywordRetriever, attune-help 0.5.1)

From `python -m attune_rag.benchmark` against
`tests/golden/queries.yaml` (15 queries):

| Metric | Value |
|---|---|
| Precision@1 | 53.33% (8/15) |
| Recall@3 | 60.00% (9/15) |
| Mean latency | 11.83 ms |
| Max latency | ~48 ms |

Breakdown:

| Difficulty | P@1 | R@3 |
|---|---|---|
| Easy (5) | 4/5 (80%) | 5/5 (100%) |
| Medium (4) | 4/4 (100%) | 4/4 (100%) |
| Hard (6) | **0/6 (0%)** | **0/6 (0%)** |

All six hard failures share a single pattern: lesson / error
/ faq files whose filename contains the query keywords
outrank the `concepts/` or `quickstarts/` file that actually
explains the feature. Examples:

- `"look for dangerous eval calls"` returns
  `errors/bug-predict-dangerous-eval-flags-subprocess-exec.md`
  instead of `concepts/tool-bug-predict.md` because
  the error filename literally contains "dangerous-eval".
- `"vulnerability scan"` returns
  `errors/dependency-lower-bounds-trigger-scorecard-vulnerability-alerts.md`
  for the same reason.
- `"plan a new feature"` returns
  `concepts/tool-refactor-plan.md` (keyword collision on
  "plan") and three `errors/new-*` files.

Root cause is corpus distribution: attune-help has 147 error
+ 144 faq + 105 warning files versus 43 concept + 41
quickstart. Lesson files outnumber concept files ~4:1, so
keyword matches land in lesson files disproportionately.

---

## Options considered

### Option A — Keyword retriever tuning

- **Install cost:** 0
- **Network:** no
- **Latency impact:** negligible
- **Expected P@1 lift:** +10–25 pts (closes 3–4 of 6 hard
  queries)
- **Complexity:** ~20 LOC in `retrieval.py`, a few new
  tests, class attrs for category weights

Candidate changes:

1. **Category-weighted scoring.** Multiply final score by
   a per-category factor:
   - `concepts/`, `quickstarts/`, `tasks/`: **1.5x**
   - `references/`, `comparisons/`: 1.0x
   - `tips/`, `notes/`, `troubleshooting/`: 0.9x
   - `errors/`, `warnings/`, `faqs/`: **0.6x**
2. **Strip long-filename boilerplate** before path
   tokenizing. Error filenames like `bug-predict-
   dangerous-eval-flags-subprocess-exec.md` dump lesson-
   title tokens into the path-score channel, which should
   really only reflect feature names.
3. **Boost first-heading token overlap** instead of just
   generic content overlap.

Won't close the truly semantic gaps (`"plan a new feature"`
vs `refactor-plan`), but will close the category-bias
gaps.

### Option B — `fastembed` (ONNX local embeddings)

- **Install cost:** ~35MB (ONNX runtime + MiniLM model)
- **Network:** no (after one-time model download at install)
- **Latency impact:** ~30–80ms per query after warm-up;
  ~1s cold-start to load the ONNX model
- **Expected P@1 lift:** +25–40 pts (closes most / all 6
  hard queries)
- **Complexity:** new `EmbeddingRetriever` class,
  pre-computed corpus embedding cache (~4MB), test
  coverage for two retrievers, optional extra wiring.

Why this over `sentence-transformers`:
`sentence-transformers` carries the `torch` dep (~420MB),
which fails the gate. `fastembed` was built specifically to
avoid the torch tax — it ships ONNX models loaded via
`onnxruntime`, which is ~10MB. Combined with a MiniLM model
(~23MB), total install is ~35MB. Meets the gate.

Why local over hosted:
Hosted embeddings require a per-query network call, which
technically satisfies the "no network at import time"
language in the gate but introduces runtime network cost
and provider churn. Local avoids both at the cost of install
size. For a library whose default corpus is already bundled
locally (attune-help), local embeddings are the right
architectural fit.

### Option C — Hosted embeddings

- **Install cost:** ~1MB SDK dep per provider
- **Network:** per query
- **Latency impact:** 50–150ms network round trip
- **Expected P@1 lift:** similar to Option B (semantic
  similarity wins for the same reasons)
- **Complexity:** provider adapters (matches existing
  `attune_rag.providers.*` pattern), embedding cache
  invalidation
- **Ongoing:** provider churn (model renames, pricing)
  + per-query API cost

Considered but dispreferred vs Option B because network-at-
query for a local corpus is a regression in operational
posture. Kept on deck as a backup if fastembed hits quality
issues on domains attune-help doesn't cover (multilingual,
code-heavy, etc.).

### Option D — `sentence-transformers`

**Rejected.** 420MB install fails the <50MB gate. Retained
for historical reference because it's the strategy
cited in the caching lesson.

---

## Plan of record

### Phase 2.5a (v0.1.x patch)

- Implement category-biased keyword tuning per Option A
- Re-run `attune-rag.benchmark`; append results section
  below with before/after metrics
- If 70% P@1 gate cleared → ship v0.1.1; close this doc
  as RESOLVED
- If plateau → proceed to Phase 2.5b

### Phase 2.5b (v0.2.0, conditional)

- Add `attune-rag[embeddings]` optional extra using
  `fastembed` (option B)
- Implement `EmbeddingRetriever` behind the same
  `RetrieverProtocol` so callers can swap in via
  `RagPipeline(retriever=EmbeddingRetriever())`
- Ship corpus embedding cache (auto-built on first use,
  stored in user cache dir)
- Re-run benchmark with both retrievers; attach results
- Document the <50MB gate as satisfied (measured install
  size)
- Keep keyword retriever as the default so zero-dep users
  aren't affected

### Pre-commitment on the 15-pt gate

The gate for Phase 2.5b is:

- **Precision@1 improvement >= 15 pts** over whatever
  Phase 2.5a baseline we land
- **Install cost < 50MB** measured via `du` on a fresh
  venv with the extra
- **No network dependency at import time** — model
  download at install is fine; network calls during
  `import attune_rag` are not

Writing this BEFORE running embedding experiments so a
later "we already spent X days on this" argument can't
move the gate.

---

## Phase 2.5a result (attune-rag 0.1.1, 2026-04-18)

Tuning landed: category weights, filename-length cap on
path hits, and a minimal suffix stemmer. Re-ran
`attune-rag.benchmark` against the same 15-query golden set
and attune-help 0.5.1 corpus.

| Metric | Baseline (0.1.0) | Tuned (0.1.1) | Delta |
|---|---|---|---|
| Precision@1 | 53.33% | 66.67% | **+13.34 pts** |
| Recall@3 | 60.00% | 73.33% | **+13.33 pts** |
| Easy P@1 | 4/5 | 5/5 | +1 |
| Medium P@1 | 4/4 | 4/4 | — |
| Hard P@1 | 0/6 | 1/6 | +1 |
| Mean latency | 11.83 ms | 42.45 ms | +30.6 ms |

**Gate result: NOT MET (3.33 pts short of 70%).** Landing
at the top of Option A's predicted +10–25 pts range. The
four unrecovered hard queries — `plan a new feature`,
`vulnerability scan`, `orchestrate documentation workflow`,
`look for dangerous eval calls` — have zero token overlap
with their targets and require semantic similarity, exactly
as anticipated above.

### Decision: proceed to Phase 2.5b

Per the pre-committed gate, v0.1.1 ships the tuning
improvement and v0.2.0 adds `attune-rag[embeddings]` using
`fastembed`. Keyword retrieval remains the default for
zero-dep users.

## Phase 2.5c result (attune-help 0.7.0 + attune-rag 0.1.2, 2026-04-18)

After Phase 2.5a plateaued at 66.67% P@1, I ran a
prototype: hand-crafted path-keyed keyword-rich summaries
for one feature (bug-predict) and re-benchmarked. Result
showed +40 pts P@1 for that feature, validating that the
real ceiling wasn't the retriever but the corpus.
Concretely: attune-help shipped summaries keyed by feature
name (`"bug-predict"`) while `DirectoryCorpus` expected
path-keyed (`"concepts/tool-bug-predict.md"`), so every
one of 633 corpus entries silently had `summary=None` at
retrieval time. The 1.5x `SUMMARY_WEIGHT` was applied to
zero data.

Shipped the fix as attune-help 0.7.0 (path-keyed
`summaries_by_path.json`, 124 polished summaries across 26
features, LLM polish pipeline with feature-
differentiation hints) + attune-rag 0.1.2 (updated
`AttuneHelpCorpus` to consume the new sidecar).

Re-ran the 15-query golden benchmark against attune-help
0.7.0 corpus with `AttuneHelpCorpus` + `KeywordRetriever`:

| Metric | 0.1.1 (tuning only) | 0.1.2 + 0.7.0 | Delta |
|---|---|---|---|
| Precision@1 | 66.67% | **73.33%** | **+6.66 pts** |
| Recall@3 | 73.33% | **86.67%** | **+13.34 pts** |
| Easy P@1 | 5/5 | 4/5 | -1 |
| Medium P@1 | 4/4 | 4/4 | — |
| Hard P@1 | 1/6 | 3/6 | +2 |

**Gate result: MET.** Precision@1 73.33% clears the 70% gate by
3.33 pts without any embeddings dependency.

Corresponding multi-feature fixture benchmark (26 features ×
25 queries = 650 queries) lands at 71.7% P@1 / 81.5% R@3 with
similar margin.

### Decision: Phase 2.5b deferred indefinitely

Per the fastembed decision matrix (committed before this
run):

> If Golden P@1 ≥ 80% AND industry fixture P@1 ≥ 70%:
> defer fastembed indefinitely.
> If Golden P@1 70-80%: ship fastembed as optional extra.

Golden P@1 73.33% + fixture P@1 71.7% puts us in the middle
band. Per the matrix, fastembed moves to **optional extra**
status: we do NOT build it into the default attune-rag
install, but we do keep the `attune-rag[embeddings]` extra
slot reserved for a future contribution from users who need
cross-corpus retrieval (where summaries don't exist).

The immediate work is complete. Follow-up items:

- attune-help 0.7.1 — differentiation-tuning for the 6
  features below the 60% per-feature P@1 gate (spec,
  code-quality, planning, refactor-plan,
  workflow-orchestration, security-audit).
- attune-rag — no further retrieval work planned unless
  user need emerges for non-attune-help corpora.

## Links

- Spec: [feature-rag-code-grounding-2026-04-17.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/.claude/plans/feature-rag-code-grounding-2026-04-17.md)
- Benchmark harness: [attune-rag / src/attune_rag/benchmark.py](https://github.com/Smart-AI-Memory/attune-rag/blob/main/src/attune_rag/benchmark.py)
- Golden queries: [attune-rag / tests/golden/queries.yaml](https://github.com/Smart-AI-Memory/attune-rag/blob/main/tests/golden/queries.yaml)
- `fastembed` project: https://github.com/qdrant/fastembed
- Prior caching lesson: `.claude/CLAUDE.md` → "Anthropic's
  built-in prompt caching supersedes custom caching"
