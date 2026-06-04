# Phase 0 Results — int8 vs float32 Recall Benchmark

**Status:** complete — **GO**. Both arms ran on Redis 8; int8
shows zero recall regression vs float32. Run 2026-06-04.

---

## Final result (both arms, Redis 8 CE)

| Metric | float32 | int8 | delta | gate |
|---|---|---|---|---|
| P@1 | 0.6875 | 0.6875 | 0.0 | ≤0.02 ✅ |
| recall@5 | 0.9062 | 0.9062 | 0.0 | ≤0.03 ✅ |
| int8↔fp32 top-1 agreement | — | 0.925 | — | — |
| int8↔fp32 top-5 Jaccard (mean) | — | 0.9003 | — | — |

**Verdict: GO.** int8 quantization preserves retrieval quality on
our corpus — no measurable P@1 or recall@5 loss, ~93% top-1
ranking agreement with float32. Ran against `redis:8` (Redis 8 CE,
Query Engine bundled, `TYPE INT8` accepted) on an alt port via
Docker; embeddings Ollama `nomic-embed-text`; per-vector max-abs
int8 scaling; COSINE + HNSW.

> Note: float32 P@1 here (0.6875) differs slightly from the
> redis-stack 7.4 baseline below (0.7188) — different engine build
> / HNSW. The decision metric is the int8-vs-float32 delta on the
> *same* engine, which is 0.0.

---

## What ran

Harness: [phase0_benchmark.py](phase0_benchmark.py). Corpus: this
repo's `.help/templates/` (267 docs across 25 feature dirs).
Queries: attune-rag golden `queries.yaml` (40 queries; 32 with an
`expected_feature` that maps to a `.help` feature dir). Embeddings:
Ollama `nomic-embed-text` (768-dim). Path: RedisVL `SearchIndex` +
`VectorQuery` — the same layer agent-memory-server uses.

## Float32 baseline (captured)

| Metric | Value |
|---|---|
| P@1 (top-1 hit's feature == expected) | **0.7188** |
| recall@5 (expected feature in top 5) | **0.9062** |
| corpus docs | 267 |
| labeled queries | 32 |

These numbers validate the full pipeline end to end
(corpus → embed → index → query → metric) and give the baseline
the int8 arm must stay within (P@1 −2 pts, recall@5 −3 pts).

## int8 arm — BLOCKED on Redis version

The int8 index creation is rejected by the **Redis server**, not
our code:

```
Bad arguments for vector similarity HNSW index `TYPE`: Unknown argument
```

Root cause: INT8/UINT8 vector-field support in the Redis Query
Engine landed in **Redis 8**. The local environment has neither:

| Redis present | Query engine | INT8 vector fields |
|---|---|---|
| redis-stack-server 7.4 (`:6379`, brew cask) | RediSearch 2.10.20 | **No** |
| redis 8.8.0 (`:6380`, brew formula) | none bundled (`FT.CREATE` unknown) | **No** |

RedisVL 0.19.0 supports int8 client-side (verified), and the
encoding contract is settled (per-vector max-abs scale to
`[-127,127]`, COSINE + HNSW). The only gap is a Redis 8 CE
distribution that ships the Query Engine.

## To unblock

Run the int8 arm against a Redis 8 CE with the Query Engine — e.g.
the `redis:8` / `redis/redis-stack-server` 8.x Docker image on an
alt port — then re-run the harness (it auto-detects int8
availability and computes agreement + int8 P@1/recall@5 + the
go/no-go gate). Docker is installed locally but the daemon was down
at run time.

## Notes

- Nomic embeddings are not unit-normalized (observed component
  −3.913), confirming per-vector max-abs int8 scaling over a fixed
  ×127.
- One `.help` template exceeded nomic's context window (HTTP 500);
  harness caps embed input at 3000 chars.
- Harness uses isolated `bench_*` indexes and drops them on exit;
  the `memory_records` / `working_memory` indexes are untouched.
