# Memory Unification — Decisions

## D1 — Files-canonical, graph-derived (PROPOSED — needs Patrick's lock)

Three architectures were on the table:

| Option | Shape | Verdict |
|---|---|---|
| **(a) Files-canonical** | `.md` files are the single store; graph + Redis derived | **Recommended** |
| (b) Graph-canonical | graph is the store; files are generated views | Rejected — fights every existing tool (lint, MEMORY.md, harness recall, Patrick's authoring habit) and inverts the ratified git-source-of-truth doctrine |
| (c) Two stores, one protocol | keep both; promotion is the only bridge | Rejected as the end-state — it is the status quo whose double-authoring cost motivated this spec (fine as the transitional state during migration) |

Why (a): the eval already proved faithful file→graph derivation;
hydrate.py already rebuilds Redis from files each session (the
derivation pipeline 80% exists); the lint/hygiene enforcement all
targets files; `metadata.type` ↔ NodeType is a 1:1 map. The only
genuinely new machinery is (i) a `curated` frontmatter marker,
(ii) `promote()` writing files, (iii) the one-time 13-node
migration.

## D2 — Curated marker schema (additive)

```yaml
metadata:
  type: user | feedback | project | reference
  curated: true            # optional; absent = un-promoted file layer
  node_id: <original id>   # provenance for migrated/promoted nodes
  promoted_from: <memory_idx uuid>   # stash provenance, when applicable
```

Additive-only so every existing file stays valid; `memory_lint.py`
gains validation for the new keys (unknown-key rule updated).
Curated-marked files hydrate into BOTH `@layer:{file}` (pointer
recall) and the curated digest set — one file, two serving roles.

## D3 — Sequencing gate

Phase 4 (code) does not start until Patrick locks D1/OQ1/OQ2 —
the overruled pushback (miss-log empty; evidence-first) is noted
for the record, and the R5 no-regression eval gate is the
compensating control: if unification degrades recall numbers, that
IS the miss-evidence, caught before ship.
