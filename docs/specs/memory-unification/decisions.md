# Memory Unification — Decisions

## D1 — Files + Redis, NO graph middle layer (LOCKED, Patrick 2026-07-04)

Patrick pushed past the original files-canonical/graph-derived
recommendation to the cleaner endpoint: **no MemoryGraph object and
no `curated_graph.json` in the curated pipeline at all**. Files are
the store; Redis is the serving layer; nothing in between.

| Option | Shape | Verdict |
|---|---|---|
| **(a2) Files + Redis, no graph** | `.md` files canon; hydrate derives digest/edges directly from files | **LOCKED** |
| (a1) Files-canonical, graph-derived | original recommendation — graph/JSON as derived middle layer | Superseded — the middle layer buys nothing (see audit below) |
| (b) Graph-canonical | graph store, files projected | Rejected — fights every existing tool |
| (c) Two stores, one protocol | status quo | Rejected as end-state |

Capability audit that justified the cut: edges already derive from
`[[links]]` at hydrate (Redis IS the graph at recall time,
`recall_related` walks it); NodeTypes ≡ `metadata.type`;
`find_similar` is outclassed by FT.SEARCH+synonyms (all eval
numbers are from the Redis path); with files canon and Redis
rebuilt per-session, JSON round-trip fidelity has nothing left to
protect.

**Scope guard (the accepted pushback):** this decision covers
Patrick's curated-memory ARCHITECTURE. Deleting
`attune.memory.MemoryGraph` from the shipped package is a SEPARATE
exercise behind the removing-dead-code / subsystem-value gate
(usage evidence, PersonalMemory dependency check, breaking-change
versioning) — tracked as T6, not bundled here.

## OQ1 — Curated files live in `~/.attune/memory/curated/` (RE-LOCKED 2026-07-04)

**Correction, same day:** the first lock (harness memory dirs, on
the agent's "one corpus" recommendation) was reversed by Patrick on
review — recorded here in place, not rewritten. Four reasons, the
first decisive:

1. **Git source of truth.** `~/.attune/memory` is a pushed git
   repo; the harness memory dirs are un-versioned. The first lock
   would have retired the git-tracked graph JSON and moved the most
   durable memories OUTSIDE version control.
2. **Cross-project nature.** Curated nodes are machine-wide (cf.
   the same-day shared-namespace decision); per-project harness
   dirs force arbitrary project assignment.
3. **Context cost.** Every file in the harness dirs adds a
   MEMORY.md pointer line loaded into context each session —
   eroding the rules-corpus-jit savings for zero recall benefit.
4. **Write-layer ownership.** `promote()` stays inside attune's own
   store; no cross-system writes into harness-owned paths.

The real unification is the SERVING layer (one Redis index over
all corpora, already live) — physical co-location bought
aesthetics, not capability. Residuals accepted: curated facts are
not in MEMORY.md's browse index (digest + FT.SEARCH are the
curated read paths; one static MEMORY.md line points at the dir),
and `memory_lint` adds the curated dir to its sweep list (T1).

## OQ2 — `curated_graph.json` retired (LOCKED, "go")

Hydrate derives the digest set from curated-marked files each run;
no committed graph artifact. Git history preserves the old JSON if
archaeology is ever needed.

## D2 — Curated marker schema (additive)

```yaml
metadata:
  type: user | feedback | project | reference
  curated: true            # optional; absent = un-promoted file layer
  status: active           # optional; digest-visible lifecycle state
  node_id: <original id>   # provenance for migrated/promoted nodes
  promoted_from: <memory_idx uuid>   # stash provenance, when applicable
```

Additive-only so every existing file stays valid; `memory_lint.py`
gains validation for the new keys. Curated-marked files hydrate
into BOTH `@layer:{file}` (pointer recall) and the curated digest
set — one file, two serving roles.

## D3 — Sequencing gate (RESOLVED 2026-07-04)

D1/OQ1/OQ2 are locked; Phase 4 is un-gated. The overruled
evidence-first pushback stays on record with the R5 no-regression
eval gate (`eval_pointer_index.py` re-run) as the compensating
control: if unification degrades recall numbers, that IS the
miss-evidence, caught before ship.

## D4 — The typed digest is the one consumer that must not silently degrade

`recall_digest` today renders typed/statused nodes hydrated from
the graph JSON. Under D1 it must render identically from
curated-marked files — explicit task (T3), verified by comparing
digest output before/after migration on the same 13 nodes.
