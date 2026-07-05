# Memory Unification — Tasks

Gate resolved 2026-07-04 (D1/OQ1/OQ2 locked — see decisions.md).
Architecture: files + Redis, no graph middle layer.
**T1–T5 executed same day; receipts inline and in
migration-receipt.md.**

- [x] **T1 — Schema + lint.** Add `curated`/`status`/`node_id`/
  `promoted_from` to the memory frontmatter schema;
  `memory_lint.py` validates them (and still rejects other unknown
  keys) and adds `~/.attune/memory/curated/` to its bare
  `--check-all` sweep list.
- [x] **T2 — Migration (one-time, receipted).** The 13 curated
  nodes → lint-conforming `.md` files in `~/.attune/memory/curated/`
  (OQ1 re-lock) with `curated: true` + provenance `node_id`; edges
  become `[[links]]`; one static MEMORY.md line points at the dir.
  Receipt (node-id ↔ file-stem map) lands in this spec dir;
  committed + pushed in the memory repo.
- [x] **T3 — Hydrate cutover + typed digest (D4).**
  hydrate.py derives the curated layer (nodes, status sets, edges)
  from curated-marked files; `curated_graph.json` read path
  removed (OQ2). Verify `recall_digest` output matches the
  pre-migration render on the same 13 nodes.
- [x] **T4 — Promotion writes files.** `promote()` in
  `src/attune/memory/` lands a `.md` file in the curated dir with
  provenance frontmatter instead of writing graph JSON; R4
  receipts preserved (status=active). attune-ai PR + tests.
- [x] **T5 — Round-trip guard + R5 gate.** DONE: state parity
  EXACT (22/22 Redis keys) vs pre-cutover snapshot; eval re-run
  matches baseline (A ft 3/5·3/5, B 5/7, C no crowding); LIVE
  dogfood — promote() → file → hydrate → active curated node
  served, probe removed clean. Non-mocked promote() suite: 11
  passed (tests/unit/memory/test_promotion.py).
- [x] **T6 — MemoryGraph value-gate (separate exercise).** DONE
  2026-07-05: gate run, removal warranted (4 signals; Personal-
  Memory dependency check clean) and executed — own spec at
  `docs/specs/memorygraph-value-gate/` (D1 straight removal →
  10.0.0, D2 full drag).
