# Decisions — Probe C: Memory Investigation

**Status:** Draft (2026-05-11)
**Owner:** Patrick
**Predecessors:** Probe B (in `docs/specs/coverage-canonical-pattern/`)

---

## Problem

Probe B (PR #212) chased an OOM during CI test runs. Five iterations
of pytest/coverage tuning narrowed it down. Iter 4 mem-tick data
revealed peak memory was 1.5 GB / 16 GB on Linux — **no OOM**. The
real blocker was `--cov-fail-under` failing.

Then iter 6 (matrix without coverage, `-n 1`, no branch coverage)
showed a different pattern: memory **does** grow to 15.7 GB —
but only during a specific cluster of test files:

| Test file | Crashes seen on |
|---|---|
| `tests/unit/memory/test_pubsub_direct.py` | ubuntu-3.12 |
| `tests/unit/memory/test_redis_auto_detect.py` | windows-3.10, macos-3.12 |
| `tests/unit/memory/test_redis_bootstrap.py` | macos earlier runs |
| `tests/unit/test_memory_features.py` | windows-3.10 |

Local isolated run of `test_pubsub_direct.py`: 40 tests pass in
27 s with **3.4 GB peak RSS**. That's already heavy for 40 tests
worth of mocked redis interactions. In CI's sequential `-n 1` mode,
the worker process accumulates state across hundreds of test files
before reaching this cluster — pushing the cluster's 3.4 GB
allocation over the 16 GB ceiling.

PR #212 ships with these four files `--ignore`d in CI. This spec
investigates *why* they leak and decides whether the fix is local
(rewrite the tests / fixtures) or structural (extract redis into
its own package).

## Hypothesis

The four files all exercise redis detection / pub-sub paths and
share an expensive import or fixture pattern. Candidate causes:

1. **Importing `redis` package transitively pulls in heavy state**
   — the redis-py library imports a lot at module load and may
   cache connection objects somewhere global. xdist workers don't
   release these between test files.
2. **MagicMock chains for `_base._client._metrics._config…`**
   create large object trees. The `_make_real_base()` helper in
   `test_pubsub_direct.py` builds nested MagicMock that may not
   release between tests.
3. **Module-level cache in `attune.memory.redis_auto_detect`**
   (`_CACHE_TTL` and friends) holds objects across tests.
4. **`@patch("threading.Thread")` mocks don't fully release
   threading internals** — Python's threading module has module-
   level state that mocks may inadvertently keep alive.
5. **PubSubManager's reconnect loop** has `import redis` inside
   a function body. Each invocation may add to sys.modules /
   module cache without cleanup.

The four files all touch one or more of these surfaces.

## Investigation plan

Phase 1 — characterize:

- [ ] Profile each file in isolation with `memory_profiler`
- [ ] Run pairs of files together (e.g. test_long_term.py +
      test_pubsub_direct.py) and see if memory compounds
- [ ] Identify which line of which test triggers the largest
      allocations

Phase 2 — decide:

If the cause is **local** (fixture pattern, mock chain leak, etc):
- Rewrite the offending tests to release state
- Restore them to CI

If the cause is **structural** (importing `redis` pulls in too
much, or attune.memory.redis_* has module-level state we can't
clean up safely):
- Extract redis into a separate package (`attune-redis`?)
- attune-ai depends on it as an optional extra
- Test files move with the package
- Worst-case option Patrick named the night of 2026-05-10

## What this does NOT change

- The four files stay `--ignore`d in CI until this spec
  resolves. They still run locally and in isolated invocations.
- `attune.memory` and `attune.memory.short_term` continue to
  work — only the tests are affected, not the runtime.
- The "switch to larger CI runners" spec (docs/specs/larger-runners/)
  is orthogonal — solving Probe C still has value even on 32 GB
  runners because the suite is currently brittle.

## Acceptance criteria

- All four `--ignore`d files either:
  - (a) Run in CI without crashing workers, OR
  - (b) Have been moved to a separate package with its own CI
- Local isolated run of the relevant tests still passes
- `docs/specs/probe-c-memory-investigation/` closed with the
  resolution noted in `decisions.md`
