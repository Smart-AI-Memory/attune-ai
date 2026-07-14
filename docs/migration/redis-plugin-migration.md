# Redis Decoupling Migration Guide

Reflects the **partial** outcome of `docs/specs/redis-decoupling/`
landed in v6.8.0 (PRs #279 and #281). Full decoupling was scoped down
to three small deliverables after the Phase A audit (PR #278) found
the original "Redis as core" framing didn't survive contact with the
codebase.

## What landed in v6.8.0

### Removed surface

- `attune.coordination/` package — including
  `AgentCoordinator`, `AgentTask`, `ConflictResolver`,
  `ResolutionResult`, `ResolutionStrategy`, `TeamPriorities`,
  `TeamSession`. A PEP 562 deprecation shim at
  `src/attune/coordination.py` raises `ImportError` with a
  helpful message on any attribute access.
- `[memory]` install extra — converted to an empty no-op alias
  for backward compatibility. `[redis]` is now the canonical
  opt-in for Redis-backed features.
- `[developer]` aggregator no longer pulls `redis-py` silently.

### Why this matters

Before v6.8.0, `pip install 'attune-ai[developer]'` silently
pulled `redis-py`. The `[memory]` extra confusingly suggested
memory itself was optional (it isn't — file-based memory is
core). Both are fixed.

## What stayed Redis-coupled (deferred)

Per the Phase A audit, these subsystems have legitimate exotic
requirements (cross-process pub/sub, glob key scan, direct
`_client` access) and stay Redis-backed by design:

- `attune.memory.short_term.RedisShortTermMemory` — the 15-submodule
  facade powering unified memory, MCP memory tools, telemetry,
  feedback loop.
- `attune.memory.cross_session/` — cross-process session
  coordination via Redis pub/sub.
- `attune.agents.release.base_agent` — best-effort task-completion
  pub/sub signal.
- `attune.telemetry.feedback_loop` — glob-scan key pattern
  (`feedback:*:*:*`).
- `attune.telemetry.approval_gates` — direct `_client.get/set`
  access for approval requests.
- `attune.meta_workflows.session_context` — KV with TTL for
  Socratic choice persistence.
- `attune.core_modules.short_term_memory` — public API:
  `stash`, `retrieve`, `stage_pattern`, `send_signal`,
  `receive_signals`.

Removing these would require building file-based replacements
with TTL, glob scan, pattern staging, and an in-process EventBus
— effectively a memory-subsystem rewrite, not a delta on
"decouple Redis." Not in scope for this spec; deferred to a
hypothetical follow-up.

> **Status: Redis is a permanent alignment — no removal planned.**
> The legacy in-tree facade modules (`attune.redis_memory`,
> `attune.redis_memory_storage`, `attune.redis_memory_coordination`,
> `attune.redis_memory_patterns`, `attune.redis_config`, and the
> deprecated parts of `attune.memory.config`) once carried
> `REMOVE IN v8.0.0` → `REMOVE IN v9.0.0` removal markers. Those markers
> have been **retired — there is no planned removal of Redis or these
> facades.** attune's direction is to *align on* Redis (the Agent
> Memory Server path via `attune_redis`) **and** Anthropic Claude — not
> to exit Redis. The facades are simply the *older* in-tree way of using
> Redis, **superseded by the newer `attune_redis` integration**; new
> code should use `attune_redis.AMSMemoryBackend`. `RedisShortTermMemory`
> still powers live subsystems (e.g. `memory/control_panel`).
> See [`docs/specs/redis-facade-direction/`](../specs/archive/redis-facade-direction/decisions.md).

## Install path

### Vanilla — Redis-free

```bash
pip install attune-ai
```

Pulls zero Redis runtime dependencies. The `attune.memory.short_term`
facade falls back to a mock backend; file-based memory works
natively. `attune.coordination` raises `ImportError` on any
attribute access.

### With Redis support

```bash
pip install 'attune-ai[redis]'
```

Pulls `redis>=5.0.0,<9.0.0` and `agent-memory-client>=0.14.0`.
Enables the bundled `attune_redis/` plugin (Redis Agent Memory
Server integration) and all Redis-coupled subsystems listed
above.

### Backward compatibility

```bash
pip install 'attune-ai[memory]'  # still works — empty no-op alias
```

## Legacy `attune.redis_*` modules

The top-level `attune.redis_*` modules (`attune.redis_memory`,
`attune.redis_config`, `attune.redis_memory_storage`,
`attune.redis_memory_coordination`, `attune.redis_memory_patterns`)
are **retained compatibility facades — not retirement candidates.**
attune's direction is to align on Redis (via the `attune_redis`
Agent Memory Server integration) and Anthropic Claude, so these
facades stay. New code can use `attune_redis.AMSMemoryBackend`
directly for the richer path. (A legacy `DeprecationWarning`
predating this direction still fires at import; aligning that
runtime message to drop the removal implication is a separate,
optional follow-up — no code change was made here.)

## See also

- [`redis-decoupling/audit.md`](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/specs/archive/redis-decoupling/audit.md) — Phase A audit findings (archived)
- [`redis-decoupling/decisions.md`](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/specs/archive/redis-decoupling/decisions.md) — per-phase decision log (archived)
- PR [#279](https://github.com/Smart-AI-Memory/attune-ai/pull/279) — P1 (delete `attune.coordination`)
- PR [#281](https://github.com/Smart-AI-Memory/attune-ai/pull/281) — P2 (drop `[memory]` extra)
