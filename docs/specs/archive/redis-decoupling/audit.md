# Phase A audit — Internal Redis usage

**Date**: 2026-05-12
**Method**: three `git grep` commands from `design.md` against
`src/attune/**/*.py`. False positives filtered (Anthropic batch SDK's
`.retrieve(batch_id)`, `ops/runner.py`'s asyncio generator
`subscribe()`).
**Outcome**: spec's scope assumption (`AgentCoordinator` and
`TeamSession` aren't referenced internally) was correct for those
two classes — but Redis-shaped APIs (`stash`/`retrieve`/
`stage_pattern`/`publish`) extend far deeper than the audit
expected. **Recommendation: reduce scope to "partial" per spec's
own failure-to-deliver path.**

---

## Grep summary

| Grep | Total hits | Files | Notes |
|---|---|---|---|
| 1. Direct API (`RedisShortTermMemory`, `.stash(`, `.retrieve(`, `.stage_pattern(`) | 155 | 36 | Many self-references inside `attune/memory/short_term/` (the module being audited); long-term-memory `.retrieve()` calls are on `self.storage` (memdocs), not Redis. |
| 2. Indirect imports (`from attune.memory.short_term`, `from attune.coordination`, `import attune_redis`) | 55 | 25 | Almost entirely internal to `attune/memory/short_term/` (own submodule imports). External imports: `attune/redis_config.py`, `attune/memory/cross_session/`. |
| 3. Pub/sub (`PubSubManager`, `RedisStream`, `publish(`, `subscribe(`) | 38 | 7 | Real pub/sub use in `agents/release/base_agent.py` and `memory/cross_session/coordinator.py`. |

False positives filtered: `llm/providers/anthropic_batch.py` (Anthropic SDK), `ops/runner.py`+`ops/routes/runner.py` (asyncio
generator).

---

## Caller classification (C = caller / R = re-export / D = self-reference inside module-being-moved)

External callers — code OUTSIDE `attune/memory/short_term/`,
`attune/coordination/`, and the legacy `redis_*.py` shims — that
would need to be migrated if Redis is removed:

| File | Type | Methods used | What it needs | Replacement difficulty |
|---|---|---|---|---|
| `attune/__init__.py` | R | re-exports `RedisShortTermMemory` | n/a (export only) | Trivial — delete export |
| `attune/core.py` | R | re-exports `RedisShortTermMemory` | n/a | Trivial |
| `attune/core_modules/memory_interface.py` | C | `memory.stash`, `memory.retrieve` | KV with TTL | **Easy** — already a thin wrapper; pass through to whatever backend the unified memory hosts. |
| `attune/core_modules/short_term_memory.py` | C | `stash`, `retrieve`, `stage_pattern`, `list_staged_patterns`, `send_signal`, `receive_signals` | KV + TTL + **pattern staging** + **cross-agent signals** | **Medium-hard** — `send_signal`/`receive_signals` are pub/sub-shaped (real-time agent coordination). Pattern staging is also Redis-specific shape. |
| `attune/mcp/memory_handlers.py` | C | `memory.stash`, `memory.retrieve`, `memory.persist_pattern` | User-facing MCP tools `memory_store`, `memory_retrieve`, `memory_search`. KV + pattern persistence. | **Medium** — file-based backend would work, but MCP tool surface is committed API. |
| `attune/meta_workflows/session_context.py` | C | `memory.stash` with `ttl_seconds`, `memory.retrieve` | KV with TTL for recording Socratic discovery choices | **Easy** — file-based with TTL works fine. |
| `attune/telemetry/feedback_loop.py` | C | `memory.stash` with TTL, `memory.retrieve`, **`memory.keys(pattern)`** | KV + TTL + **glob key scan** (`feedback:*:*:*`) | **Medium** — glob scan is a non-trivial Redis primitive; file-based replacement needs directory walk. |
| `attune/telemetry/approval_gates.py` | C | `memory.retrieve` (with `credentials=None`), plus **direct `memory._client.get/set`** access (raw Redis client) | KV + TTL for approval requests/responses; couples to Redis client API | **Medium-hard** — `_client.get()` direct-Redis access bypasses the facade, making it non-portable. |
| `attune/agents/release/base_agent.py` | C | `self.redis.publish(channel, json)` — **real cross-process pub/sub** | Cross-agent signal: "agent X completed task Y." Best-effort (try/except — Redis is optional). | **Hard — exotic per spec criterion** (cross-process pub/sub). Spec's failure path: caller stays Redis-dependent. |
| `attune/memory/cross_session/coordinator.py` | C | `client.publish(CHANNEL_SESSIONS, ...)`, `pubsub.subscribe(CHANNEL_SESSIONS)` | Real-time pub/sub for session join/leave announcements across processes | **Hard — exotic.** Same as base_agent.py. |
| `attune/memory/cross_session/service.py` | C | constructor takes `RedisShortTermMemory` (must not be mock) | Backing store for cross-session memory subsystem | Whole subsystem stays Redis-dependent or moves to `attune_redis`. |

### Re-exports / re-export-only files (R)

| File | What it re-exports |
|---|---|
| `attune/__init__.py` lines 132, 218, 332 | `RedisShortTermMemory` |
| `attune/core.py` lines 37-41 | `RedisShortTermMemory` (backward-compat) |
| `attune/memory/__init__.py` lines 42, 118, 210, 316 | `RedisShortTermMemory` |
| `attune/redis_config.py` | factory wrappers around `RedisShortTermMemory` |
| `attune/redis_memory.py` | legacy facade |
| `attune/redis_memory_storage.py` | legacy storage wrapper |

### Internal / deprecated / self-reference (D — within the module being moved)

`attune/coordination/{agent_coordinator,team_session}.py` —
the public coordination classes themselves (subject of Phase C).

All `attune/memory/short_term/*.py` — the Redis subsystem itself.

`attune/memory/config.py`, `control_panel.py`, `features.py`,
`file_session.py`, `long_term_*.py`, `mixins/*`, `redis_bootstrap.py`,
`simple_storage.py`, `summary_index.py`, `unified.py` — all internal
to `attune/memory/` and tightly composed around
`RedisShortTermMemory`. The unified memory facade
(`UnifiedMemoryBackend._short_term: RedisShortTermMemory | None`)
is the integration seam.

---

## Threshold check against spec's failure-to-deliver path

The spec's `tasks.md` "Failure-to-deliver path" enumerates three
failure modes. The audit hits two of them:

### 1. ">10 internal callers" — borderline (8 external callers)

8 files outside `attune/memory/short_term/` and `attune/coordination/`
call `RedisShortTermMemory`-shaped APIs:

```
attune/core_modules/memory_interface.py
attune/core_modules/short_term_memory.py
attune/mcp/memory_handlers.py
attune/meta_workflows/session_context.py
attune/telemetry/feedback_loop.py
attune/telemetry/approval_gates.py
attune/agents/release/base_agent.py
attune/memory/cross_session/{coordinator,service,conflicts,models}.py  (4 files in cross_session/)
```

Under the literal `>10` threshold (counting cross_session/ as one
subsystem). But the threshold is a rough cap — the audit *intent*
is "stop if the migration is bigger than expected." 8 callers across
6 subsystems (core_modules, mcp, meta_workflows, telemetry × 2,
agents/release, cross_session) is bigger than the spec's prose
implies ("AgentCoordinator and TeamSession aren't referenced
internally").

### 2. "Exotic requirements" — TRIGGERED

The spec lists exotic as "atomic counters, time-window queries,
distributed locks, **pub/sub for cross-process events**." Two
callers hit the pub/sub criterion explicitly:

- **`agents/release/base_agent.py`** — `self.redis.publish(...)`
  for cross-agent task-completion signals. Already wrapped in
  try/except with "Redis is optional" comment — degrades to no-op.
- **`memory/cross_session/coordinator.py`** — uses Redis pub/sub
  for cross-session join/leave announcements. The entire
  `cross_session/` subsystem is built around Redis pub/sub +
  shared state.

Plus a soft-pub/sub case:

- **`core_modules/short_term_memory.py`** — `send_signal` /
  `receive_signals` API methods. These wrap the Redis facade's
  pub/sub manager (`PubSubManager`). Public API surface.

Per the spec's failure path, exotic callers "stay Redis-dependent."
That means at minimum `agents/release/base_agent.py`,
`memory/cross_session/`, and `core_modules/short_term_memory.py`'s
signal methods can't be moved off Redis without rewriting their
semantics.

### 3. "`attune_redis` plugin not ready" — already known

Resolved in Phase 3A task #1 (decisions.md): `attune-redis` does
not exist on PyPI. C1 (delete with deprecation shim) is forced.

---

## Recommendation: reduce spec to "partial" with three concrete deliverables

Continuing with the original "full decoupling" framing would be a
multi-week refactor:
- Build file-based replacements with TTL, glob-scan, and pattern
  staging.
- Build an in-process EventBus to replace cross-agent pub/sub.
- Migrate `core_modules/short_term_memory.py`'s public API (likely
  breaks downstream users).
- Either rewrite `cross_session/` for file-based persistence or
  delete the subsystem.
- Migrate `telemetry/approval_gates.py`'s direct `_client.get`
  access path.

That's not "decouple Redis"; that's "rewrite the memory subsystem."
Out of scope per the spec's own failure-to-deliver text:
> "Even if internal `stash`/`retrieve` calls remain, removing the
> public coordination classes and the extras shrinks the surface
> meaningfully."

### Partial scope — three deliverables

These three are tractable, additive, and shrink the surface as the
spec promised:

**P1 — Delete `attune/coordination/` (Phase C path C1).**
`AgentCoordinator` and `TeamSession` have no internal callers
(grep 1 confirms — the only references are within the module
itself). Deletion + deprecation shim that raises a helpful
`ImportError` directing users to install the (theoretical)
`attune-redis` plugin. No `attune-redis` exists on PyPI today, so
the shim's "install attune-redis" message is forward-looking —
acceptable since these classes have no documented internal
callers anyway.

Estimated change: ~3 file deletions + 1 shim file + `__init__.py`
edit + CHANGELOG note. ~30 LoC change.

**P2 — Drop `[memory]` and `[redis]` extras from `pyproject.toml`.**
The `[dev]` extra already pulls `redis>=5.0.0,<8.0.0` for tests.
Users who want Redis explicitly can `pip install redis` — no
attune-ai extra needed. Aggregator extras (`[full]`, `[enterprise]`,
`[developer]`) re-audited and cleaned.

Estimated change: 5–10 lines in `pyproject.toml` + `uv lock` run.
Test pass-through verified by fresh-venv check from design.md.

**P3 — Delete tests for the deleted surface.**
- `tests/unit/coordination/` (smoke tests for the just-deleted
  classes).
- `tests/unit/memory/test_pubsub_direct.py` *if* PubSubManager is
  no longer reachable post-P1. If `core_modules/short_term_memory.py`
  still wraps it, keep the tests.
- `tests/unit/test_redis_fallback.py` if it tests the deleted
  coordination classes.

Estimated change: ~60–80 fewer tests (under the spec's "~100"
target but in the right direction).

### What stays Redis-dependent (out-of-spec deferral)

- `attune.memory.short_term.RedisShortTermMemory` facade
  (15-submodule architecture) — backbone for unified memory, MCP
  memory tools, telemetry, session context, feedback loop.
- `attune.memory.cross_session/` — cross-process pub/sub +
  Redis-backed shared state.
- `attune.agents.release.base_agent` — best-effort task-completion
  pub/sub.
- `attune.telemetry.feedback_loop` — glob-scan key pattern.
- `attune.telemetry.approval_gates` — direct `_client` access.
- `attune.meta_workflows.session_context` — KV with TTL (easy to
  migrate but only sensible alongside the larger memory rewrite).

Document these as "Redis-backed by design" rather than carrying
them as debt.

### Implication for the spec's `__init__.py` import-time Redis probe

`RedisAutoDetector` (mentioned in requirements.md) probes for a
running Redis server at module load time. That doesn't change with
the partial scope — Redis is still a runtime dependency for the
memory subsystem.

The "remove transient Redis probe at import time" win is **out of
this audit's path** but reachable independently: convert the
auto-detector to lazy detection (probe on first `.stash()` rather
than at `import attune`). That's a one-file change worth its own
mini-spec.

---

## Suggested updates to `tasks.md`

If the user accepts this audit's recommendation:

- Mark task #3 (this audit) **done** with link to this file.
- Reframe Phase B (task #4) as "Phase B — Delete `attune/coordination/` and audit aggregate extras" with the P1+P2 scope above.
- Mark Phase B's broader "replace internal callers" intent **deferred** with rationale: "8 callers across 6 subsystems, 2 of which need cross-process pub/sub. Full migration is a memory-subsystem rewrite, not a 'decouple Redis' delta."
- Reframe Phase E (task #7) to the narrower P3 scope.
- Update spec status to **partial** in all four .md files when P1+P2+P3 ship.

The unfinished work becomes its own follow-up — a much larger
`memory-subsystem-rewrite` spec if that ever becomes a priority. As
the spec's own failure-to-deliver text acknowledges:
> "The remaining internal Redis usage becomes its own follow-up
> spec. Document it as known debt."
