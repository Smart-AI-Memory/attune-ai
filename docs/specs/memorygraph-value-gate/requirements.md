# MemoryGraph Value-Gate — Requirements

**Status:** approved (2026-07-05) · **Owner:** Patrick + agent
**Born:** memory-unification T6 (the deferred value-gate exercise).

## Problem

The memory-unification spec (2026-07-04) moved the curated memory
pipeline off `attune.memory.MemoryGraph` onto plain `.md` files +
Redis-derived serving. T6 deferred the question: with its one real
consumer gone, should `MemoryGraph` remain in the shipped package?

## Gate evidence (2026-07-05)

Four removal signals fire (the removing-dead-code rule needs two):

1. **Zero live consumers.** `promotion.py` imports only
   `session_stash`; `unified.py` and `memory_tool.py` have zero
   graph references; `nodes.py`/`edges.py` are imported only by
   `graph.py` itself. The triad stands or falls together.
2. **Both outside importers are dead paths.**
   `agent_factory/memory_integration.py` (`MemoryAwareAgent`) is
   gated behind `memory_graph_enabled` — no caller in the repo
   ever sets it, and `AgentFactory` has no CLI/MCP/workflow
   consumer. `resilience/health.py`'s `memory_graph` check reads
   the legacy cwd-relative `patterns/memory_graph.json`, a
   pre-unification path that is no longer written.
3. **Orphaned motivation.** The originating consumer (curated
   memory) migrated to files; `curated_graph.json` is retired.
4. **Well-tested, zero consumers.** 10+ test files (including
   duplicate `tests/memory/test_graph.py` vs
   `tests/unit/memory/test_graph.py`) guard code nothing calls.
   Local telemetry: 0 invocations.

**PersonalMemory dependency check (T6's explicit worry): CLEAN** —
`personal.py` is files + attune-author/attune-rag; no graph import.

## Outcome

`MemoryGraph` and its dead-path web are removed from the shipped
package as a breaking change; anyone importing the removed names
gets a pointed error naming the successor.

## Scope (full drag — D2)

- Delete `src/attune/memory/{graph,nodes,edges}.py`.
- Delete `agent_factory/memory_integration.py`
  (`MemoryAwareAgent`) and the never-set `memory_graph_*` knobs in
  `factory.py` / `base.py`.
- Remove the `memory_graph` health check in
  `resilience/health.py`.
- Strip the removed names from `attune.memory.__init__` (lazy map,
  TYPE_CHECKING block, `__all__`); the module `__getattr__` raises
  a pointed error for removed names (successor: curated `.md`
  files, see memory-unification).
- Delete/trim the guarding tests; fix the 5 doc pages
  (`how-to/memory-graph.md` deleted + nav/inbound links removed;
  agent-factory pages stripped of MemoryAwareAgent sections).
- CHANGELOG `feat!:` entry; ships in the next major (10.0.0) —
  D1.

## Non-goals

- Removing `agent_factory` itself (working pattern per
  removing-dead-code rule; only its dead memory wrapper goes).
- Touching curated memory, PersonalMemory, UnifiedMemory, or the
  memory-tool bridge.
- Cutting the 10.0.0 release (separate release-execute exercise).

## Done when

- The full symbol set (`MemoryGraph`, `MemoryAwareAgent`, `Node`,
  `NodeType`, `Edge`, `EdgeType`, node subclasses, edge constants,
  `memory_graph_*` knobs) greps to zero in `src/` outside the
  pointed-error shim.
- Test suite green; doc-import audit + docs wiring audit + mkdocs
  strict green.
- memory-unification T6 checked off, pointing here.
