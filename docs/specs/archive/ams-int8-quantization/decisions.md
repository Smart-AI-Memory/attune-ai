# Spec: AMS int8 Embedding Quantization — Decisions

**Status:** draft

> Pre-committed decisions captured 2026-06-04. Triggered by a
> review of the Redis 8.8 announcement against attune-ai's AMS
> integration. Verification this session established that int8 is
> not config-reachable in agent-memory-server (datatype hardcoded
> float32 on `main`, no open PR) but IS reachable via the
> `MEMORY_VECTOR_DB_FACTORY` extension seam without a fork.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Fork AMS vs use extension seam | **Extension seam** (`MEMORY_VECTOR_DB_FACTORY`) | AMS exposes a dotted-path factory `(embeddings) -> MemoryVectorDatabase`. We own schema + quantization in `attune_redis` with zero AMS source changes. Forking carries permanent merge cost; the seam is a supported API. |
| Ship-then-measure vs measure-then-ship | **Measure first (Phase 0 gates everything)** | Value rests on the premise "int8 holds recall on our corpus." Vendor's 99.99% number is for their corpora, not nomic 768-dim on our findings. Cost of measuring (~hours, our existing harness) is far below shipping a recall regression into the memory layer. |
| Benchmark harness | **attune-rag golden-query round-trip** | Already built, already trusted, already used for embedding-decision gates. No new measurement infra. |
| Go/no-go threshold | **int8 P@1 within 2 points of float32 AND recall@5 within 3 points** on the golden set | Mirrors the pre-committed-matrix discipline: thresholds set BEFORE running so the result routes the call cleanly. If int8 lands inside the band, ship; outside, park. Numbers revisitable only with stated reason before the run, never after. |
| Override granularity | **Subclass `RedisVLMemoryVectorDatabase`**, override `add_memories` encode + search-path VectorQuery | No narrower encode seam exists upstream (vector bytes are built inline in `add_memories`). Subclass duplicates ~40 lines; accept it and guard with R4 drift test. |
| Quantization scheme | **Decide in Phase 2 against RedisVL's int8 contract** | nomic vectors are L2-normalized; int8 needs a scale (likely ×127) and a distance-metric pairing RedisVL supports for int8. Exact encoding deferred to design after reading RedisVL's int8 field contract — do not guess it here. |
| Default state | **Off until Phase 0 passes and is ratified** | Reversible-while-empty only; flipping on before measurement risks an irreversible recall regression once the store fills. |
| Upstream PR timing | **After our factory ships, non-blocking** | Contribute `datatype`-settings-driven + quantize-on-write upstream so the ecosystem benefits and we can retire the override. Not on the critical path for our own adoption. |
| Scope: working-memory index | **Excluded** | Working memory is short-lived key/value `data`, not the semantic vector store. int8 buys nothing there. |

---

## Phase 0 outcome — GO (2026-06-04)

Benchmark ran on `redis:8` (Redis 8 CE, Query Engine bundled).
int8 vs float32 on the `.help` corpus (267 docs, 40 golden
queries): **P@1 delta 0.0, recall@5 delta 0.0**, top-1 ranking
agreement 0.925. Inside the pre-committed gate on both axes →
**GO**. Full numbers in [phase0-results.md](phase0-results.md).

Environment caveat discovered: int8 vector fields require the
**Redis 8 Query Engine**. The local redis-stack 7.4 (RediSearch
2.10.20) and Homebrew redis 8.8 (no query engine) both lack it.
This makes the AMS-host Redis version a **hard prerequisite** for
Track A — the production rollout must target a Redis 8 CE backend,
and the int8 factory should fail loudly (not silently fall back to
float32) if the server rejects `TYPE INT8`.

---

## Resolved questions (verified 2026-06-04, RedisVL 0.19.0)

- **Q1 — RedisVL int8 contract — RESOLVED.** We pre-quantize.
  `redisvl/schema/validation.py` int8 validator requires values
  already in `[-128, 127]`; RedisVL validates the range but does
  NOT quantize float input. So our override quantizes
  float→int8 before storing (nomic is L2-normalized ~[-1,1] →
  `round(v × 127)` clamped to `[-128, 127]`), writing
  `np.array(q, dtype=np.int8).tobytes()` in place of the base's
  float32 encode.
- **Q2 — Query-vector encoding — RESOLVED (same scheme).** The
  query vector must be quantized identically (×127, round, clamp)
  so it matches the int8 field. Exact AMS VectorQuery
  construction sites to override are confirmed present in the
  search methods; pin them in Phase 2 implementation.
- **Q3 — Distance metric under int8 — RESOLVED.** int8 is valid
  with HNSW (our `redisvl_indexing_algorithm`); the only int8
  restriction in `redisvl/schema/fields.py` is on SVS-VAMANA,
  which we do not use. COSINE stays.

## Open questions (resolve in Phase 2 design)

- **Q4 — Benchmark harness fit.** R1 named the attune-rag golden
  harness, but that harness measures KEYWORD retrieval over the
  attune-help doc corpus — not AMS VECTOR recall. Phase 0 must
  route through AMS `search_long_term_memory`. Proposed
  resolution: reuse attune-rag's labeled `queries.yaml` + corpus
  as the text/query set, but run both arms through a live AMS
  (float32 default factory vs int8 prototype factory) and measure
  (a) int8-vs-float32 top-k agreement (primary — float32 is the
  baseline we must not regress against) and (b) P@1 vs the
  existing labels (secondary). Confirm before building.
- **Q5 — Two-arm mechanism.** Float32 vs int8 differ by index
  schema baked at creation. Run as two index names in one Redis
  (distinct `redisvl_index_name`), reconfiguring AMS between arms,
  or two AMS instances. Pick in Phase 2.
- **Q6 — Validation environment.** int8 arm must run against a
  real AMS with `MEMORY_VECTOR_DB_FACTORY` pointed at the
  prototype factory, not a unit-level encode test (passing unit
  tests don't prove the live round-trip).

---

## Verification notes (this session, 2026-06-03/04)

- `attune_redis` is a pure HTTP client over AMS; it sets no index
  or embedding config. All vector-index decisions live server-side
  in agent-memory-server + RedisVL.
- AMS `main` `_build_redis_schema()` hardcodes `"datatype":
  "float32"`; write path hardcodes
  `np.array(embedding, dtype=np.float32).tobytes()`; config.py has
  only `redisvl_index_name / distance_metric / vector_dimensions /
  index_prefix / indexing_algorithm`. No datatype setting, no open
  PR found.
- `MEMORY_VECTOR_DB_FACTORY` is the supported extension seam
  (`agent_memory_server.memory_vector_db_factory`, env-driven,
  validated to return a `MemoryVectorDatabase`).
