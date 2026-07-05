# MemoryGraph Value-Gate — Tasks

Single PR (spec + removal, the memory-unification precedent).

- [x] **T1 — src removal.** Delete
  `src/attune/memory/{graph,nodes,edges}.py` and
  `src/attune/agent_factory/memory_integration.py`; strip
  `memory_graph_*` knobs from `agent_factory/{factory,base}.py`;
  remove the `memory_graph` health check from
  `resilience/health.py`.
- [x] **T2 — pointed-error shim.** Strip removed names from
  `attune.memory.__init__` (TYPE_CHECKING, lazy map, `__all__`);
  `__getattr__` raises an error naming the curated-file successor
  for the removed names.
- [x] **T3 — tests.** Delete whole-file guards
  (`tests/{memory,unit/memory}/test_graph*.py`,
  `tests/memory/test_memory_graph.py`,
  `tests/unit/memory/test_{nodes,edges}_coverage_boost.py`,
  `tests/unit/memory/test_graph_structures.py`,
  `tests/agent_factory/test_agent_factory_memory.py`,
  `tests/agent_factory/test_memory_integration_behavioral.py`);
  trim partial references in `test_agent_factory.py`,
  `test_llm_toolkit_core.py`, `test_intelligence_integration.py`,
  `test_health.py`. Add a shim test: removed names raise the
  pointed error.
- [x] **T4 — docs.** Delete `docs/how-to/memory-graph.md`; remove
  its nav entry + 4 inbound links (`auto-chaining`, `how-to/index`,
  `resilience-patterns`, `smart-router`); strip
  MemoryAwareAgent/memory_graph content from
  `how-to/agent-factory.md` and
  `reference/agent-factory-{api,overview,readme}.md`.
- [x] **T5 — bookkeeping.** CHANGELOG `feat!:` entry (Unreleased);
  check off memory-unification T6 with a pointer here.
- [x] **T6 — verification.** Full-symbol grep → 0 in `src/`
  outside the shim; pytest green; `audit_doc_imports.py`,
  `audit_docs_wiring.py`, `mkdocs build --strict` green;
  pre-commit pre-flight (pinned black/ruff) before staging.

## Verification receipts (2026-07-05)

- Full-symbol grep: 0 hits in `src/` outside the shim; 0 in served
  docs/content/plugin.
- Test suite: 20,562 passed / 191 skipped / 6 xfailed (keyless).
- `audit_doc_imports.py` exit 0; `audit_docs_wiring.py` no
  findings; `mkdocs build --strict` green.
- **Live dogfood (non-mocked):** (1) `from attune.memory import
  MemoryGraph` fails with ImportError; attribute access raises the
  pointed "removed in 10.0.0" message (note: Python's from-import
  machinery swallows the pointed text — attribute access shows it).
  (2) `promote()` round-trip: probe node written to
  `~/.attune/memory/curated/`, hydrate served it in Redis
  (14 -> 15 nodes, FT.SEARCH hit), probe removed clean (back to
  14, search 0). (3) `register_default_checks` live run: no
  `memory_graph` check, overall healthy. (4) `AgentFactory
  .create_agent` live: returns `ResilientAgent`, no graph knobs.
- Bonus doc-fiction fixes found during the sweep:
  `which-memory-is-which.md` claimed `memory_store` MCP tools were
  graph-backed (they use `UnifiedMemory`); `ARCHITECTURE.md`
  referenced a nonexistent `graph/relationships.db` and "Memory
  Graph API". Both corrected to match live code.
