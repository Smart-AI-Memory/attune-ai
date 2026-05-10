# Spec: Decouple Redis from `attune-ai` Core

**Status**: approved
**Created**: 2026-05-09
**Sibling spec**: `docs/specs/ci-debt/` (in flight; this spec is its
natural follow-up — Phase A's redis dep wrangling motivated the
question "what is Redis even for?")

---

## Phase 1: Requirements

### Problem statement

`attune-ai` ships with Redis as a deeply-integrated core capability:

- Two optional extras (`[memory]`, `[redis]`) that pull in `redis-py`
  and `agent-memory-client`.
- A facade class `RedisShortTermMemory` with 15 specialized submodules
  (caching, security, sessions, pubsub, streams, sorted sets, etc.).
- A `RedisAutoDetector` that probes for a running Redis server at
  module load time.
- Every Redis op has a paired `use_mock=True` branch — doubling the
  surface to maintain.
- Two public coordination classes (`AgentCoordinator`, `TeamSession`)
  re-exported from `src/attune/__init__.py`.

**The audit (2026-05-09):** `git grep` shows
`AgentCoordinator` and `TeamSession` are **not consumed by any
workflow, agent, or orchestration module in `attune-ai`'s own
source tree**. Only tests and one example reference them. They're
load-bearing public API only in the abstract sense — nothing in
the package's actual feature set uses them.

The legacy `src/attune/redis_memory.py` already declares itself
deprecated:

> "Deprecated — use `attune_redis.AMSMemoryBackend`. REMOVE IN v4.0.0
> — see `docs/migration/redis-plugin-migration.md`."

We are at v6.6.0. The migration is overdue.

### What Redis actually delivers (when enabled)

For attune-ai's actual usage pattern (a solo developer running
Claude Code one session at a time), Redis delivers:

- **In-process work:** nothing the dict-backed mock doesn't already
  cover.
- **Cross-process coordination** (`AgentCoordinator`, `TeamSession`):
  unused internally. Available to consumers in principle, but not a
  documented part of any user-facing workflow.
- **Cross-session persistence:** overlaps with the existing file-based
  `~/.attune/` memory plus Claude Code's own auto-memory.

For multi-user / multi-machine team coordination — a real but
narrow use case — Redis is genuinely needed. That's exactly what
the `attune_redis` PyPI package is for.

### What Redis costs (today)

- **Test debt:** `tests/unit/memory/test_pubsub_direct.py` (40 tests),
  `tests/unit/test_redis_fallback.py` (21 tests), Redis fixtures
  scattered across the suite.
- **Local-CI parity hazard:** dev machines often run Redis;
  CI doesn't. Tests pass locally, fail in CI, repeatedly.
  (This spec was prompted by spending 30+ minutes today debugging
  exactly this kind of failure in `ci-debt` Phase A.)
- **Doubled code paths:** every method has a "real Redis" path and a
  "use_mock" path. Bugs hide in the asymmetry.
- **Install-time complexity:** two extras (`[memory]`, `[redis]`)
  for a feature that most users don't need.
- **Cognitive load on contributors:** 15 specialized Redis submodules,
  pubsub, streams, transactions, conflict negotiation. The framework
  reads as bigger than it is.

### Why this matters now

- The `ci-debt` Phase A explicitly added `redis>=5.0.0,<8.0.0` to
  the `[dev]` extra to make CI green. That's the right short-term
  fix. But it doubled down on a deeper decision that should be
  reconsidered.
- The `attune_redis` plugin already exists. The migration is
  half-finished; the legacy `attune.redis_memory` deprecation
  warning has been firing for 2+ versions.
- The smaller the core, the easier everything else is — install,
  testing, contribution, migration to new versions.

### Goals

- **G1: Redis is no longer a dependency of `attune-ai` core.**
  `pip install attune-ai` and `pip install attune-ai[dev]` do not
  pull `redis-py`, `agent-memory-client`, or any Redis-adjacent
  package.
- **G2: Code paths that exist only to support the "no Redis"
  fallback are gone.** No more `use_mock` branches. The default
  in-process implementation IS the implementation.
- **G3: `AgentCoordinator`, `TeamSession`, and the
  `RedisShortTermMemory` facade are removed from `attune-ai`'s
  public API.** Either deleted or re-exported via `attune_redis`
  for the consumers who need them.
- **G4: One in-process / file-based default for short-term memory.**
  `stash`, `retrieve`, `stage_pattern`, etc. — whichever of these
  are still used internally — keep working without Redis.
- **G5: Migration path documented for users currently using
  `[memory]` / `[redis]` extras.** Single instruction:
  `pip install attune-redis`. Behavior identical.

### Non-goals

- **Not killing the `attune_redis` plugin.** It stays. Users with
  multi-machine coordination needs install it explicitly.
- **Not breaking any user workflow that's actually used.**
  If `AgentCoordinator` has consumers in the wild, it gets a
  deprecation cycle, not a hard delete.
- **Not redoing the in-process memory model from scratch.** Whatever
  short-term memory `attune-ai` workflows actually use today (file-
  based, in-process), we keep — just unwound from the Redis-shaped
  abstraction.
- **Not in scope: long-term memory.** This spec is about Redis (which
  was the short-term layer). `attune.memory.long_term` is separate
  and untouched.
- **Not in scope: the `attune-rag` runtime dep.** Different pattern;
  different lifecycle.

### Success criteria

- `grep -r "redis" src/attune/ --include='*.py' | wc -l` returns
  approximately zero (a few historical comments are OK).
- `pip install attune-ai` results in no Redis-related packages on
  the user's `pip list`.
- `pip install attune-ai[dev]` ditto.
- `pip install attune-ai && python -c "from attune.workflows import …"`
  works for every workflow that previously worked, with no
  "Redis not detected" log lines.
- Test count drops by the size of `tests/unit/memory/test_pubsub_direct.py`
  + `tests/unit/test_redis_fallback.py` + scattered Redis-specific
  test fixtures (rough estimate: 100+ tests).
- The `attune_redis` plugin's PyPI install + import path documented
  in `README.md` and `CHANGELOG.md`.

### Risks

- **Risk 1 — silent consumers.** Someone out there may import
  `AgentCoordinator` from `attune.coordination` and rely on it.
  Mitigation: deprecation cycle (one minor version) before deletion;
  re-exports from `attune_redis` for backward compat where feasible.
  Risk-accepted: hard breaks for the truly obscure paths, with a
  clear `CHANGELOG.md` note.

- **Risk 2 — file-based replacement isn't equivalent.** If any
  internal code uses Redis-specific features (TTL, atomic counters,
  pub/sub) that file-based can't reproduce, the swap requires more
  work. Mitigation: audit before deleting; in-scope swaps stay
  in-scope, anything exotic gets a separate spec.

- **Risk 3 — `attune_redis` plugin isn't ready to absorb the moved
  classes.** If `AgentCoordinator` and `TeamSession` need to live
  somewhere accessible, and they're moved out of core, they need a
  home that's actually published. Mitigation: verify `attune_redis`'s
  current state before declaring move-target; if not ready, hold
  the move or carve a slimmer plugin scope.

- **Risk 4 — CI surfaces unrelated failures during the cleanup.**
  Touching every Redis code path will land in a lot of files;
  expect some "while I'm in there" detours. Mitigation: stage by
  category (extras → mock paths → coordination classes → tests),
  not by file.

- **Risk 5 — `ci-debt` Phase A's `[dev]` redis addition creates
  conflicts.** This spec rolls back exactly that change. Mitigation:
  land `ci-debt` first (CI green, dependabot unblocked), then this
  spec; the rollback is intentional once `ci-debt` has served its
  purpose.
