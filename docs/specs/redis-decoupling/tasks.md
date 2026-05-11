# Spec: Decouple Redis from `attune-ai` Core

**Status**: approved

---

## Phase 3: Tasks

### Phase 3A — Setup

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Confirm `attune_redis` plugin's current state on PyPI: does it ship `AgentCoordinator` / `TeamSession` already, or would Phase C need to push them upstream first? | research | done | **`attune-redis` is not on PyPI** (HTTP 404 on both naming forms; absent from simple-index). Forces **C1** path (delete + deprecation shim). See `decisions.md`. |
| 2 | Capture the **current** test count baseline. `pytest tests/unit/ -n auto` (after `ci-debt` Phase A lands so the suite is green). Record so Phase E's "~100 fewer tests" expectation can be verified. | test-infra | done | **Baseline: 14,122 passed** (local, 2026-05-10). 5 env-sensitive failures unrelated to redis. Caveat: captured before CI is green — see `decisions.md`. |

### Phase 3B — Per-phase resolution

Each row is a single PR. Verify CI green between each.

| # | Phase | Layer | Status | Notes |
|---|-------|-------|--------|-------|
| 3 | **A: Audit internal usage.** Run the three `git grep` commands from design.md. Output `docs/specs/redis-decoupling/audit.md` classifying every hit (C/R/D) with proposed replacement. No code changes — pure investigation. | docs | todo | Single page. Becomes the work plan for Phase B. If audit reveals more than ~5 internal callers OR any with exotic needs, pause and reconsider scope. |
| 4 | **B: Replace internal callers.** For each (C) row from the audit, swap the Redis-API call for the identified replacement (file-based, in-process, or removal). Tests stay green. | src/attune/{various} | todo | Stop condition: any caller needing a non-trivial replacement (atomic counters, distributed locks, time-window queries) escalates to the design.md "stop and decide" branch. |
| 5 | **C: Delete / re-export public API.** Per design.md decision criterion (C1 vs C2): either delete `src/attune/coordination/` outright with a deprecation shim that errors helpfully, OR thin-wrap re-exports from `attune_redis` with a deprecation warning. Drop from `src/attune/__init__.py` exports. CHANGELOG.md note. | src/attune/coordination, __init__.py, CHANGELOG.md | todo | |
| 6 | **D: Remove extras + deps.** Drop `[memory]` and `[redis]` extras from `pyproject.toml`. Drop `redis-py` and `agent-memory-client` from `[dev]` (and any aggregator extra: `[full]`, `[enterprise]`, `[developer]`). Run `uv lock`. Verify with fresh-venv check (see design.md Phase D). | pyproject.toml, uv.lock | todo | `langchain-anthropic` and `tiktoken` (added by `ci-debt` Phase A) stay or go based on whether their tests still exist post-Phase-B. |
| 7 | **E: Test + doc cleanup.** Delete `tests/unit/memory/test_pubsub_direct.py`, `tests/unit/test_redis_fallback.py`, `tests/unit/coordination/`. Audit other test files for `pytest.importorskip("redis")` and Redis fixtures; remove or migrate to `attune_redis`. Update `README.md` migration note + `CHANGELOG.md` reduction summary. Finalize `docs/migration/redis-plugin-migration.md`. | tests/, README.md, CHANGELOG.md, docs/migration/ | todo | Test count should drop ~100. If it drops far more or far less, audit before merging. |

### Phase 3C — Verification

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 8 | **Fresh-install check.** `python -m venv /tmp/clean && /tmp/clean/bin/pip install -e . && /tmp/clean/bin/pip list \| grep -iE "redis\|agent-memory"` returns empty. | manual | todo | G1 from requirements.md. |
| 9 | **Source scrub.** `git grep -l "RedisShortTermMemory\|AgentCoordinator\|TeamSession" src/attune/` returns no results (or only the deprecation shim from Phase C, if C2 chosen). | manual | todo | G3 from requirements.md. |
| 10 | **Workflow smoke test.** Run a representative attune-ai workflow (e.g. `attune workflow run code-review .`) end-to-end with no Redis package available. Confirm no "Redis not detected" log lines. | manual | todo | G4 from requirements.md. |
| 11 | **CI parity check.** Confirm CI runs are still green on `main` after the merged commits land. Test count delta matches expectation. | CI | todo | |

### Phase 3D — Spec close

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 12 | Set this spec's status to `complete` in all three .md files. Optionally write `decisions.md` with the actual numbers (LOC removed, tests removed, install size delta). | docs | todo | The "Redis costs" section in requirements.md will read like ancient history. Worth preserving the before/after. |

### Failure-to-deliver path

If Phase B's audit (task #3) reveals any of the following:

- **More than ~10 internal callers** of Redis-shaped APIs across
  workflows/agents/orchestration → the migration is bigger than this
  spec. Mark spec as `partial`, complete what's tractable, document
  the rest as follow-up debt.
- **Exotic requirements** (atomic counters, distributed locks,
  pub/sub for cross-process events) in any internal caller → that
  caller stays Redis-dependent. Move it to `attune_redis` or document
  as broken-without-plugin.
- **`attune_redis` plugin not ready to host moved classes** (Phase A
  task #1 reveals this) → Phase C goes with C1 (hard-delete with
  helpful error) instead of C2.

In each case, the spec ends `partial` rather than `complete`, and
the unfinished work is its own follow-up entry.

The spec is **done** when verification tasks #8, #9, #10 all pass
on `main`.
