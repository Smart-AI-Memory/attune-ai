# Spec: AMS int8 Embedding Quantization

> Cut long-term agent-memory storage by ~75% and speed vector
> search by ~30% by storing embeddings as int8 in the Redis
> Agent Memory Server index — via AMS's pluggable factory seam,
> with no fork of agent-memory-server — but only if a Phase-0
> recall benchmark proves int8 holds retrieval quality on our
> corpus.

---

## Phase 1: Requirements

**Status**: approved

### Problem statement

attune-ai's cross-session memory (the `claude-cross-session-memory`
work) stores long-term findings as vector-embedded records in the
Redis Agent Memory Server (AMS). Embeddings are written and indexed
as `float32` — that is hardcoded in agent-memory-server, not a knob
we set.

Redis 8.x + RedisVL support int8 vector quantization: roughly 75%
memory reduction and ~30% faster search while retaining ~99.99% of
search accuracy in Redis's published numbers. Our store does not use
it today.

Two facts make this worth a spec rather than a config flip:

- **It is not config-reachable in AMS.** Verified on
  `agent-memory-server` `main` (2026-06-03):
  `memory_vector_db_factory._build_redis_schema()` hardcodes
  `"datatype": "float32"` (unlike `dims` / `distance_metric` /
  `algorithm`, which are settings-driven), and the write path
  hardcodes `np.array(embedding, dtype=np.float32).tobytes()`.
  No `redisvl_datatype` setting exists; no open upstream PR found.
- **AMS exposes a clean extension seam.** The
  `MEMORY_VECTOR_DB_FACTORY` env var accepts a dotted path to a
  `(embeddings) -> MemoryVectorDatabase` factory. attune can ship
  its own int8 factory in `attune_redis` and own the schema +
  quantization without touching agent-memory-server source.

Strategic fit: per the project direction to leverage Redis's work
rather than decouple from it, this rides their extension point and
optionally contributes the gap back upstream.

### Timing constraint (load-bearing)

Embedding precision cannot change cheaply once the long-term store
fills — re-embedding the whole store is required to switch datatype
after data accumulates. The store is effectively empty now, so this
is the cheap window. If the store fills before this lands, the cost
of adopting int8 rises sharply.

### Goals

- Store long-term-memory embeddings as int8 in the AMS RedisVL
  index, realized entirely within `attune_redis` via the
  `MEMORY_VECTOR_DB_FACTORY` seam.
- Gate adoption on a measured recall benchmark — do not flip the
  default on faith in the vendor's accuracy numbers.
- Keep a clean path to retire our override once upstream makes
  datatype settings-driven.

### Non-goals

- Forking or vendoring agent-memory-server.
- Changing the embedding model or vector dimensions (out of scope;
  this spec only changes datatype/precision).
- Quantization for the working-memory index (this spec is
  long-term-memory only).
- LangCache / semantic response caching (separately ruled out;
  Anthropic native prompt caching supersedes it for our prompts).

### Requirements

- **R1 — Phase-0 recall benchmark (first deliverable, gating).**
  Measure retrieval quality of int8 vs float32 on our corpus
  (nomic-embed-text, 768-dim) using the attune-rag golden-query
  round-trip harness. Produce P@1 / recall@k for both arms and a
  pre-committed go/no-go threshold (see decisions.md). No factory
  ships until this passes.
- **R2 — int8 factory.** `attune_redis` provides a factory
  resolvable as `MEMORY_VECTOR_DB_FACTORY` that builds the RedisVL
  schema with `datatype: int8`, reusing AMS settings for `dims`,
  `distance_metric`, and `algorithm` so it stays consistent with
  the float32 default.
- **R3 — write + query encoding.** Float embeddings are quantized
  to int8 on write, and the vector-query path encodes the query
  vector to match the int8 field. Recall parity with the benchmark
  arm must hold end-to-end through the live AMS server, not just in
  isolation.
- **R4 — drift guard.** A test fails CI if the subclassed
  agent-memory-server surface we override (the `add_memories`
  encode line and the search-path VectorQuery construction) drifts
  in a way our override no longer matches, so an AMS version bump
  can't silently break quantization.
- **R5 — opt-in + reversible-while-empty.** Adoption is explicit
  (env/config), defaults off until R1 passes and is ratified, and
  the docs state the empty-store precondition for safe enablement.
- **R6 — contribute-back stub (non-blocking).** Capture the
  upstream change (make `_build_redis_schema` datatype
  settings-driven + quantize-on-write) as a tracked follow-up so
  the override can eventually be retired.

### Acceptance criteria

- Phase-0 benchmark committed with both arms' numbers and the
  go/no-go call recorded in decisions.md.
- If go: int8 factory + encoding land in `attune_redis` with the
  drift-guard test; a live round-trip against a real AMS server
  shows recall within the benchmark's accepted band; docs state the
  empty-store precondition and the enable steps.
- If no-go: decisions.md records the measured gap and the spec is
  parked (premise invalidated) with the data, not silently dropped.
- No changes to agent-memory-server source in this repo; the
  upstream contribution is tracked separately.
