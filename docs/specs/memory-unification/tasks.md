# Memory Unification — Tasks

Gate resolved 2026-07-04 (D1/OQ1/OQ2 locked — see decisions.md).
Architecture: files + Redis, no graph middle layer.

- [ ] **T1 — Schema + lint.** Add `curated`/`status`/`node_id`/
  `promoted_from` to the memory frontmatter schema;
  `memory_lint.py` validates them (and still rejects other unknown
  keys).
- [ ] **T2 — Migration (one-time, receipted).** The 13 curated
  nodes → lint-conforming `.md` files in the harness memory dirs
  (OQ1) with `curated: true` + provenance `node_id`; edges become
  `[[links]]`; MEMORY.md pointers added. Receipt (node-id ↔
  file-stem map) lands in this spec dir.
- [ ] **T3 — Hydrate cutover + typed digest (D4).**
  hydrate.py derives the curated layer (nodes, status sets, edges)
  from curated-marked files; `curated_graph.json` read path
  removed (OQ2). Verify `recall_digest` output matches the
  pre-migration render on the same 13 nodes.
- [ ] **T4 — Promotion writes files.** `promote()` in
  `src/attune/memory/` lands a `.md` file + MEMORY.md pointer with
  provenance frontmatter instead of writing graph JSON; R4
  receipts preserved (status=active). attune-ai PR + tests.
- [ ] **T5 — Round-trip guard + R5 gate.** Non-mocked file →
  hydrate → digest test; re-run `eval_pointer_index.py` — class
  A/B/C numbers must not regress vs the 2026-07-04 baseline.
- [ ] **T6 — MemoryGraph value-gate (separate exercise).** With
  the curated pipeline off the graph, run the removing-dead-code /
  subsystem-value gate on `attune.memory.MemoryGraph` in the
  shipped package: usage evidence, PersonalMemory dependency
  check, breaking-change versioning. Own spec/PR if removal is
  warranted — NOT bundled into T1–T5.
