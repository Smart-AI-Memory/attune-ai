# Spec: Decouple Redis from `attune-ai` Core

**Status**: approved

---

## Phase 2: Design

### Architecture

Five phases, each one PR. Order matters: each phase builds on the
previous and verifies a clean state before the next.

```
Phase A: AUDIT INTERNAL USAGE         ← read-only investigation
   │
   ├─ List every internal caller of: RedisShortTermMemory, AgentCoordinator,
   │  TeamSession, attune.memory.short_term.*, attune.coordination.*
   ├─ Document what each caller actually NEEDS (TTL? atomic? pubsub?)
   └─ Output: docs/specs/redis-decoupling/audit.md
   │
   ▼
Phase B: REPLACE INTERNAL CALLERS     ← swap to file/in-process equivalents
   │
   ├─ For each internal caller: replace Redis-API call with file-based or
   │  in-process equivalent
   ├─ Tests still green
   └─ Verify: nothing in src/attune/{workflows,agents,orchestration,llm}
              touches attune.memory.short_term or attune.coordination
   │
   ▼
Phase C: DELETE / RE-EXPORT PUBLIC API ← coordination classes
   │
   ├─ Delete src/attune/coordination/ (or re-export from attune_redis if
   │  it can host them)
   ├─ Drop from src/attune/__init__.py exports
   ├─ Add deprecation shim that imports from attune_redis if installed,
   │  else raises with a clear message
   └─ Update CHANGELOG.md with breaking-change note
   │
   ▼
Phase D: REMOVE EXTRAS + DEPS         ← pyproject.toml
   │
   ├─ Drop [memory] and [redis] extras from pyproject.toml
   ├─ Drop redis, agent-memory-client from [dev]
   ├─ Drop redis-related packages from any other extra
   ├─ Update uv.lock
   └─ Verify: pip install attune-ai && pip list | grep redis → empty
   │
   ▼
Phase E: TEST + DOC CLEANUP           ← scrub
   │
   ├─ Delete tests/unit/memory/test_pubsub_direct.py
   ├─ Delete tests/unit/test_redis_fallback.py
   ├─ Delete tests/unit/coordination/test_coordination_smoke.py +
   │  test_smoke.py
   ├─ Audit other test files for Redis fixtures; either remove or migrate
   │  to attune_redis test suite
   ├─ Update README.md migration note
   └─ Update CHANGELOG.md with the full reduction
```

### Phase A — Audit internal usage

**Why this is first:** before deleting anything, we need to know what
ACTUALLY uses Redis-shaped APIs. The original audit (in
requirements.md) said "AgentCoordinator and TeamSession aren't
referenced internally." That covers the public coordination classes,
but Redis-shaped APIs include `stash`, `retrieve`, `stage_pattern`,
pubsub, streams, etc. Some of those may still be in use somewhere.

**Method:**

```bash
# Direct API calls
git grep -nE "RedisShortTermMemory|\.stash\(|\.retrieve\(|\.stage_pattern\(" src/attune --include='*.py'

# Indirect imports
git grep -nE "from attune\.memory\.short_term|from attune\.coordination|import attune_redis" src/attune --include='*.py'

# Pub/sub & streams
git grep -nE "PubSubManager|RedisStream|publish\(|subscribe\(" src/attune --include='*.py'
```

For each hit, classify:

- **(C) Caller** — calls a Redis-API method.
- **(R) Re-export** — re-exports the public API (e.g. `attune/__init__.py`).
- **(D) Deprecated** — already in a module marked deprecated.

Output `docs/specs/redis-decoupling/audit.md` with:

| File | Line | Type | Method | What it needs | Replacement |
|---|---|---|---|---|---|
| ... | ... | C / R / D | `stash` | TTL? Atomic? | File-based / in-process / delete |

This single audit page becomes the work plan for Phase B.

### Phase B — Replace internal callers

For each (C) row from the audit, swap the Redis-API call for the
identified replacement. Most will fall into one of three patterns:

1. **`stash`/`retrieve` with no TTL needed:** swap for a simple
   `attune.memory.local_store` (file-based JSON in `~/.attune/state/`)
   or, if scope is single-workflow, a Python dict.

2. **Pattern staging:** if any workflow stages patterns and a later
   stage retrieves them, replace with explicit dataclass passing
   between stages (which is how every other workflow already works).

3. **Pub/sub:** if any code subscribes to events for cross-process
   coordination, that code is exactly the use case `attune_redis`
   exists to serve — move it to the plugin (Phase C territory).

**Stop condition:** if Phase A's audit reveals more than ~5 internal
callers OR any caller needs a non-trivial replacement (atomic
counters, time-window queries, distributed locks), pause and decide:
- Replace with file-based (more code, more tests).
- Move the caller to the `attune_redis` plugin.
- Document the caller as broken-without-redis and link users to the
  plugin install.

### Phase C — Delete / re-export public API

After Phase B, `AgentCoordinator` and `TeamSession` have no internal
callers. Two options:

**Option C1: Delete from core entirely.**
- Remove `src/attune/coordination/` directory.
- Remove from `src/attune/__init__.py` exports.
- Add a deprecation shim at `src/attune/coordination.py` that raises
  `ImportError` with: "AgentCoordinator/TeamSession moved to the
  `attune_redis` plugin. `pip install attune-redis` and import from
  `attune_redis.coordination`."

**Option C2: Re-export from `attune_redis`.**
- Move the actual classes to `attune_redis` repo.
- Add a thin `src/attune/coordination/__init__.py` that does
  `from attune_redis.coordination import AgentCoordinator, TeamSession`
  (with a deprecation warning).
- One minor version of warning, then C1.

**Decision criterion:** check whether `attune_redis` already ships
these classes or has a plan to. If yes → C2. If no → C1 with the
clear error.

### Phase D — Remove extras + deps

**Extras to drop from `pyproject.toml`:**

```diff
-# Memory subsystem (requires Redis server 8.4+ recommended)
-memory = [
-    "redis>=5.0.0,<8.0.0",
-]
-redis = [
-    "agent-memory-client>=0.14.0",
-    "redis>=5.0.0,<8.0.0",
-]
```

**Drop from `[dev]`:**

```diff
-    "redis>=5.0.0,<8.0.0",
-    "langchain-anthropic>=0.3.0,<1.0.0",
-    "tiktoken>=0.7.0,<1.0.0",
+    # langchain-anthropic and tiktoken kept iff their tests still need them
+    # post-Phase-B audit. Otherwise remove.
```

(`langchain-anthropic` and `tiktoken` were added by `ci-debt` Phase A.
Whether they stay in `[dev]` after this spec depends on whether the
tests that pulled them in still exist.)

**Update `uv.lock`** with `uv lock`.

**Aggregator extras** like `[full]`, `[enterprise]`, `[developer]`
likely include `redis` or `agent-memory-client` transitively. Audit
these too — drop the Redis bits.

**Verify:**

```bash
rm -rf .venv-test && python -m venv .venv-test
.venv-test/bin/pip install -e .
.venv-test/bin/pip list | grep -iE "redis|agent-memory" || echo "(none)"
```

Expected: `(none)`.

### Phase E — Test + doc cleanup

**Delete:**
- `tests/unit/memory/test_pubsub_direct.py` (40 tests)
- `tests/unit/test_redis_fallback.py` (21 tests)
- `tests/unit/coordination/` (smoke tests for deleted classes)
- Any other test files that import `RedisShortTermMemory` or
  `attune.coordination.*`.

**Audit:**
- Remaining test files for `pytest.importorskip("redis")` calls —
  if the file no longer needs redis after Phase B, drop the
  importorskip; if it still does, the test file itself should
  probably be deleted or moved to `attune_redis`.
- Conftest fixtures that pull from `attune.memory.short_term`.

**Documentation:**
- `README.md`: add a migration note: "Redis support moved to the
  `attune_redis` plugin in v6.7.0. If you used
  `pip install attune-ai[memory]` or `[redis]`, switch to
  `pip install attune-redis`."
- `CHANGELOG.md`: full reduction summary (test count, line count,
  extras removed, replaced-by-plugin note).
- `docs/migration/redis-plugin-migration.md` (already referenced
  in the deprecated `redis_memory.py`): finalize.
- `docs/specs/test-infrastructure/`,
  `docs/specs/ci-debt/`,
  `docs/specs/ignored-tests/`: brief mention if redis-related
  context shifts.

### Verification gates

After each phase:

1. **Push the change to a feature branch.**
2. **CI passes.**
3. **Local sanity:** `pytest tests/unit/ -n auto` green.
4. **For Phase D specifically:** the fresh-venv check above.
5. **For Phase E specifically:** test count delta matches expectation
   (~100 fewer tests, no surprises).

### Out-of-scope cross-references

- **`ci-debt` spec:** must land first. Phase A of this spec partially
  rolls back `ci-debt` Phase A (the redis dep addition). That's
  intentional: `ci-debt` Phase A makes CI green NOW; this spec makes
  Redis go away later. Both are right at their respective times.
- **`attune_redis` plugin development:** out of scope here. If C2 is
  chosen, the plugin owners need to accept the moved classes.
- **The `attune-rag` core dep:** different package, different lifecycle,
  not Redis-shaped. Untouched.
- **`attune.memory.long_term`:** different subsystem (memdocs-backed).
  Not in this spec.

### Failure-to-deliver fallback

If Phase A reveals deeper internal coupling than expected (more than
~10 internal callers, or any with exotic requirements):

1. **Mark this spec as `partial`.** Document the blockers in
   `docs/specs/redis-decoupling/decisions.md`.
2. **Land Phases C, D, E as much as possible** — even if internal
   `stash`/`retrieve` calls remain, removing the public coordination
   classes and the extras shrinks the surface meaningfully.
3. **The remaining internal Redis usage becomes its own follow-up
   spec.** Document it as known debt.

The spec is **done** when:
- `pip install attune-ai && pip list | grep -i redis` is empty.
- `git grep -l "RedisShortTermMemory\|AgentCoordinator" src/attune/`
  is empty.
- Migration note published in README + CHANGELOG.
