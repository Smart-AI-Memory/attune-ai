# Attune-Redis Plugin

**Created:** 2026-02-25
**Source:** /brainstorm session

## Problem

Attune-ai's core has 15 Redis modules baked into its
memory layer, creating bloat for users who don't need
Redis. Meanwhile, Redis developers lack Claude-powered
workflows tailored to their specific use cases. The
Redis ecosystem now has rich official tooling (Agent
Memory Server, MCP server, vector search) that makes
custom abstractions unnecessary.

## Goals

- **Must-have:** Separate Redis features into a standalone
  `attune-redis` plugin that requires attune-ai as a
  dependency
- **Must-have:** Build on Redis's official Agent Memory
  Server and MCP standard (not custom abstractions)
- **Must-have:** Provide Redis-specific developer workflows
  (debug, plan, brainstorm) informed by Redis University
  content and official best practices
- **Must-have:** Slim down attune-ai core to use default
  memory (Anthropic/Boris best practices, file-based) with
  no Redis requirement
- **Must-have:** Thin interop layer in attune-ai core that
  defines a memory backend interface for plugins
- **Nice-to-have:** RAG example app as a reference
  implementation
- **Nice-to-have:** A2A protocol support for multi-agent
  coordination down the road

## End State

A Redis developer can `pip install attune-redis`, connect
it to their Redis stack, and use Claude-powered workflows
tailored to Redis development tasks. The plugin is built
on official standards (MCP, Agent Skills) and wraps
Redis's own Agent Memory Server rather than reinventing
the wheel.

Attune-ai core installs and runs without Redis. The
plugin system allows attune-redis (and future plugins)
to extend attune's capabilities cleanly.

## Standards Alignment

The plugin aligns with four converging standards under
the Linux Foundation's Agentic AI Foundation (AAIF):

| Standard | Role in Plugin |
|----------|---------------|
| MCP | Agent-to-tool interface with Redis |
| Agent Skills | Package Redis workflows as discoverable skills |
| A2A | Future: multi-agent coordination |
| AGENTS.md | Agent behavior conventions |

### Anthropic Best Practices (Boris Cherny)

- Composable patterns: prompt chaining, routing,
  parallelization, orchestrator-workers
- Context engineering: compaction, structured note-taking,
  sub-agent architectures, progressive disclosure
- Verification loops for agent work
- CLAUDE.md for shared knowledge
- Start simple, add complexity only when measured
  improvements justify it

### Redis Official Tooling to Leverage

- **Agent Memory Server** (`agent-memory-client` PyPI) -
  dual-tier memory with REST API + MCP server
- **mcp-redis** - MCP server for Redis data operations
- **RedisVL** - vector library for semantic search,
  caching, routing
- **langgraph-checkpoint-redis** - agent state persistence
- **Redis 8** - vector sets, hybrid search, integrated
  RedisJSON/RediSearch
- **Three-tier memory model**: short-term (in-memory),
  long-term (vector search), episodic (streams)

## Approach

### Phase 1: Decouple (attune-ai core)

1. Define a memory backend interface (stash/retrieve/clear)
   in attune-ai core
2. Implement default file-based memory backend following
   Anthropic best practices
3. Move existing Redis modules out of core into a
   migration holding area
4. Ensure attune-ai works fully without Redis installed

### Phase 2: Scaffold Plugin (attune-redis)

1. Create `attune-redis` package with attune-ai as
   dependency
2. Integrate Redis Agent Memory Server as the memory
   backend
3. Configure MCP connection to Redis (via mcp-redis)
4. Implement the memory backend interface from Phase 1

### Phase 3: Redis Developer Workflows

1. Work through Redis University courses on AI agents
2. Build Redis-specific workflows informed by learnings:
   - Cache strategy planning
   - Key schema design review
   - Redis performance debugging
   - Agent memory architecture design
   - Vector search configuration
3. Package workflows as Agent Skills for discoverability

### Phase 4: Reference Implementation

1. Build an advanced agent using Redis as backbone
   (orchestrator-worker pattern)
2. Demonstrate three-tier memory (short-term, long-term,
   episodic)
3. Optional: RAG example app using RedisVL

## Phase 1 Checklist

- [x] Define memory backend interface (`MemoryBackend`
      protocol in `src/attune/memory/backend.py`)
- [x] Implement file-based default backend
      (`FileSessionMemory`)
- [x] Register file backend via entry-point
      (`pyproject.toml`)
- [x] Guard Redis imports with try/except in core
- [x] Consolidate shared types in `memory.types`
- [x] Update `redis_memory.py` to import from
      `memory.types` (not `redis_memory_models`)
- [x] Convert `redis_memory_models.py` to deprecation
      shim with DeprecationWarning
- [x] Add MemoryBackend protocol compliance tests
      (19 pass, 3 xfail tracking Redis gap)
- [x] Add Redis-optional fallback tests (4 pass)
- [x] Update `docs/getting-started/redis-setup.md`
      (removed stale `wizards_consolidated` references)
- [x] Add README to `_redis_holding/` with extraction
      timeline
- [ ] Add protocol adapter to `RedisShortTermMemory`
      (bridges credentials API to protocol — Phase 2)

## Phase 2 Checklist

- [x] Review Redis Agent Memory Server docs and
      `agent-memory-client` SDK
- [x] Scaffold `attune_redis/` package structure
      (plugin.py, memory.py, signals.py, config.py)
- [x] Implement `AMSMemoryBackend` wrapping
      `agent-memory-client` SDK
- [x] Register plugin via entry-points
      (`attune.plugins`, `attune.memory_backends`)
- [x] Add 56 tests (all passing, 3 xfail)
- [ ] Complete Redis University AI learning path
- [ ] Prototype MCP integration with mcp-redis

## Phase 3 Checklist (Legacy Cleanup)

- [x] Delete `redis_memory_models.py` (zero importers)
- [x] Delete `_redis_holding/` directory (staging copies)
- [x] Convert `redis_memory_storage.py` to deprecation
      shim
- [x] Convert `redis_memory_coordination.py` to
      deprecation shim
- [x] Convert `redis_memory_patterns.py` to deprecation
      shim
- [x] Convert `redis_memory.py` to deprecation shim
- [x] Update test imports (types from `memory.types`,
      guard deprecated imports)
- [x] Verify `core.py` import already guarded
- [x] Add deprecation docstrings to `redis_config.py`
- [x] Fix `TTLStrategy.COORDINATION` references (removed
      in v5.0, replaced with hardcoded TTL)
- [x] All tests passing (10591 passed, 0 failed)

## Phase 4 Checklist (Async/Sync + Integration)

- [x] Add `_run_sync()` async-to-sync wrapper in
      `attune_redis/memory.py`
- [x] Wrap all 10 SDK calls with `_run_sync()`
- [x] Switch `attune_redis/tests/conftest.py` to
      `AsyncMock` with async side_effects
- [x] Fix protocol compliance tests to use `AsyncMock`
      (import moved inside fixture)
- [x] Add integration test suite (14 tests, auto-skip
      when AMS unavailable)
- [x] All tests passing (56 passed, 14 skipped,
      3 xfail)

## Phase 5 Checklist (MCP Tool Integration)

- [x] Create `attune_redis/mcp_tools.py` with 5 tool
      definitions and async handlers
- [x] Add `register_mcp_tools()` to `BasePlugin` (no-op)
- [x] Override in `RedisPlugin` to register Redis tools
- [x] Add plugin discovery hook in `EmpathyMCPServer`
      (`_register_plugin_tools()`)
- [x] Add plugin handler dispatch in `call_tool()`
- [x] Add 31 MCP tool tests (all passing)
- [x] All 62 plugin tests passing, 14 integration skipped

## Phase 6 Checklist (Deprecation Removal Prep)

- [x] Audit remaining importers (2 production, 6 test)
- [x] Add `REMOVE IN v4.0.0` markers to all 5 deprecated
      modules + `memory/config.py`
- [x] Add deprecation comment to example file
- [x] Create migration guide
      (`docs/migration/redis-plugin-migration.md`)

## Phase 7 Checklist (Package Extraction)

- [x] Create standalone `attune_redis/pyproject.toml`
      with entry-points and dependencies
- [x] Add CI workflow
      (`.github/workflows/test-attune-redis.yml`)

## Next Steps

- [ ] Redis-specific developer workflows (cache
      strategy, key schema, perf debugging)
- [ ] Package workflows as Agent Skills
- [ ] Complete Redis University AI learning path
- [ ] Publish `attune-redis` to PyPI
- [ ] Update root `pyproject.toml` redis extra to
      depend on `attune-redis>=0.1.0`

## Open Questions

- What's the minimum viable memory interface that
  supports both file-based default and Redis plugin
  without being too thin or too thick?
- Should the plugin live in a separate repo or a
  monorepo alongside attune-ai?
- Which Redis University courses are most relevant to
  prioritize?
- How much of the existing 15-module facade code is
  reusable vs. should be replaced by the Agent Memory
  Server?

## Key Resources

- [Redis Agent Memory Server](https://github.com/redis/agent-memory-server)
- [Redis AI Agent Architecture 2026](https://redis.io/blog/ai-agent-architecture/)
- [Redis AI Agent Memory](https://redis.io/blog/ai-agent-memory-stateful-systems/)
- [Redis MCP Server](https://github.com/redis/mcp-redis)
- [Redis University AI Path](https://university.redis.io/learningpath/hbykf3qrnhwccy)
- [RedisVL Python Library](https://github.com/redis/redis-vl-python)
- [LangGraph Redis Checkpoint](https://github.com/redis-developer/langgraph-redis)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic: Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic: Agent Skills Spec](https://agentskills.io/home)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Agentic AI Foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
