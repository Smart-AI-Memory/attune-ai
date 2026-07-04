# Memory Unification — Tasks

Gated on D1/OQ1/OQ2 lock (see decisions.md D3).

- [ ] **T1 — Schema + lint.** Add `curated`/`node_id`/
  `promoted_from` to the memory frontmatter schema;
  `memory_lint.py` validates them (and still rejects other unknown
  keys).
- [ ] **T2 — Migration (one-time, receipted).** Script the 13
  curated nodes → `.md` files per OQ1's location; emit the
  node-id ↔ file-stem receipt into this spec dir; edges become
  `[[links]]`.
- [ ] **T3 — Derivation.** hydrate.py (memory repo) builds the
  curated layer from curated-marked files; `curated_graph.json`
  per OQ2 (retire or build-artifact).
- [ ] **T4 — Promotion writes files.** `promote()` in
  `src/attune/memory/` lands a `.md` file + MEMORY.md pointer with
  provenance frontmatter, then triggers re-derivation; R4 receipts
  preserved.
- [ ] **T5 — Round-trip guard (R7).** Non-mocked file → graph →
  Redis → digest test; plus the R5 gate: re-run
  `eval_pointer_index.py`, numbers must not regress.
- [ ] **T6 — Retire dual authoring.** Remove/deprecate the direct
  graph-write path; docs + memory updates
  (`project_memory_subsystem_motivation` closes its loop).
