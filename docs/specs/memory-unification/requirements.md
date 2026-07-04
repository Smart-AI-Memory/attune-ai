# Memory Unification — Requirements

**Status:** draft (2026-07-04) — Patrick form-locked "start
unification now," overruling the defer-to-evidence pushback; D1
below still needs his architectural lock before Phase 4 code.
**Owner:** patrick + agent

---

## Problem

Two memory systems author independently and only meet at the Redis
serving layer:

1. **Harness auto-memory** — 146 lint-clean `.md` files
   (global + per-project), `[[link]]` graph, MEMORY.md index.
   Richly populated; the surface Patrick and the agent actually
   write to.
2. **Attune curated graph** — `~/.attune/memory/curated_graph.json`
   (13 nodes, 9 edges, NodeTypes `USER_CONTEXT`/`FEEDBACK`/
   `PROJECT_CONTEXT`/`REFERENCE`), fed by the stash→promotion path
   (9.5.0), served by `recall_digest`.

Same concepts, two schemas, two authoring paths, double curation
cost. The read side is already unified (`idx:attune_memory`, 4
layers); the WRITE side is not.

## Evidence base (why this is buildable)

- `project_curated_memory_eval` (2026-07-02): MemoryGraph ingested
  the full file corpus faithfully — 76 nodes / 66 edges survive a
  fresh-instance reload; recall 6/6 vs grep 5/6.
- The file schema's `metadata.type` values map 1:1 onto the four
  curated NodeTypes.
- Corpus hygiene now enforced end-to-end (0 violations; bare
  `memory_lint --check-all` sweeps every dir).
- Ratified doctrine (friction-log 2026-07-02): curated =
  durable-only (30-day test); operational handoff = short-term
  layer; git = source of truth, Redis = serving layer.

## Requirements

- **R1 — One authoring surface.** A durable memory is written
  exactly once, as a lint-conforming `.md` file. No fact should
  require both a file write and a separate graph write.
- **R2 — Curated is a marker, not a copy.** Curated status is
  declared in file frontmatter (opt-in field), not by duplicating
  content into `curated_graph.json`. The 30-day admission test
  applies to setting the marker.
- **R3 — Graph is derived.** Node identity, NodeType, and edges
  (from `[[links]]`) are DERIVED from files at hydration/promotion
  time. `curated_graph.json` becomes a build artifact or is
  retired; it is never hand-authored after migration.
- **R4 — Promotion lands as a file.** The stash→curated promotion
  path (`promote()`) writes/updates a `.md` file (with provenance
  frontmatter) instead of writing graph JSON, then re-derives.
  Receipts unchanged (status=active, R4 receipts per
  curated-memory-productionization D10).
- **R5 — Serving contract unchanged.** `recall_digest`,
  `recall_related`, layer tags, and the pointer-recall discipline
  (`feedback_query_first_recall`) keep working identically —
  consumers must not notice the cutover. Golden-query eval numbers
  must not regress (re-run `eval_pointer_index.py` as the gate).
- **R6 — Migration with receipts.** The 13 existing curated nodes
  are migrated to files once, mechanically, with a diff-able
  receipt (node id ↔ file stem map). No content is dropped; edges
  survive as `[[links]]`.
- **R7 — Round-trip guard.** A non-mocked test proves file →
  derived graph → Redis → digest end-to-end ("registered ≠
  working"), running in CI where feasible and as a local check
  otherwise.

## Non-goals

- AMS stash layer (short-term) — unchanged; promotion remains the
  only bridge (and stays namespace-shared per the 2026-07-04
  friction-log decision).
- Lessons corpus and rules-tail layers — already file-canonical,
  untouched.
- New recall surfaces or Lua procedures — serving stays as-is (R5).

## Open questions (for Patrick at D1 lock)

- OQ1: Do migrated curated files live in the per-project memory
  dirs (visible to the harness) or a dedicated
  `~/.attune/memory/curated/` dir (visible only to attune)? The
  former makes them recallable by BOTH systems natively; the
  latter keeps the harness index lean.
- OQ2: Retire `curated_graph.json` entirely (derive in-memory at
  hydrate) or keep it as a committed build artifact for
  inspection/versioning?
