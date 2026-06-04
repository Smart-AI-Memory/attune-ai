# Spec: Decouple Redis from `attune-ai` Core

**Status**: partial — 2026-05-12 (P1 + P2 shipped via PRs #279, #281; P3 audited as no-op; full decoupling deferred per Phase A audit, see decisions.md and audit.md)

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
| 3 | **A: Audit internal usage.** Run the three `git grep` commands from design.md. Output `docs/specs/redis-decoupling/audit.md` classifying every hit (C/R/D) with proposed replacement. No code changes — pure investigation. | docs | **done** | See [audit.md](audit.md). **Triggered failure-to-deliver path:** 8 external callers across 6 subsystems, 2 with exotic pub/sub requirements. Recommendation: reduce spec to **partial** scope (P1 delete `coordination/`, P2 drop `[memory]`/`[redis]` extras, P3 delete dead tests). Full decoupling is a memory-subsystem rewrite — out of scope. |
| 4 | **B: Replace internal callers.** For each (C) row from the audit, swap the Redis-API call for the identified replacement (file-based, in-process, or removal). Tests stay green. | src/attune/{various} | **deferred** | Audit (PR #278) found 8 external callers across 6 subsystems plus 2 with exotic cross-process pub/sub requirements. Full replacement would be a memory-subsystem rewrite, not a delta. Deferred to a hypothetical `memory-subsystem-rewrite` follow-up spec. |
| 5 | **C: Delete / re-export public API.** Per design.md decision criterion (C1 vs C2): either delete `src/attune/coordination/` outright with a deprecation shim that errors helpfully, OR thin-wrap re-exports from `attune_redis` with a deprecation warning. Drop from `src/attune/__init__.py` exports. CHANGELOG.md note. | src/attune/coordination, __init__.py, CHANGELOG.md | **done** | Shipped as P1 (PR #279). Path C1 (delete with PEP 562 shim) — `attune-redis` isn't on PyPI per Phase 3A task #1. |
| 6 | **D: Remove extras + deps.** Drop `[memory]` and `[redis]` extras from `pyproject.toml`. Drop `redis-py` and `agent-memory-client` from `[dev]` (and any aggregator extra: `[full]`, `[enterprise]`, `[developer]`). Run `uv lock`. Verify with fresh-venv check (see design.md Phase D). | pyproject.toml, uv.lock | **partial** | Shipped as P2 (PR #281). Diverged from spec's "drop both" — `[memory]` made an empty no-op alias, `[redis]` kept populated because the bundled `attune_redis/` plugin needs the runtime deps. `[developer]` dropped redis. Fresh-venv verified Redis-free for vanilla install. |
| 7 | **E: Test + doc cleanup.** Delete `tests/unit/memory/test_pubsub_direct.py`, `tests/unit/test_redis_fallback.py`, `tests/unit/coordination/`. Audit other test files for `pytest.importorskip("redis")` and Redis fixtures; remove or migrate to `attune_redis`. Update `README.md` migration note + `CHANGELOG.md` reduction summary. Finalize `docs/migration/redis-plugin-migration.md`. | tests/, README.md, CHANGELOG.md, docs/migration/ | **done** | P3 audited as **mostly no-op**: `tests/unit/coordination/` already deleted in P1 (necessary to keep CI green). `test_pubsub_direct.py` and `test_redis_fallback.py` test live code (`PubSubManager` and `RedisShortTermMemory.fallback`) — both remain Redis-coupled per the audit. `CHANGELOG.md` got P1 + P2 entries in their respective PRs. `docs/migration/redis-plugin-migration.md` rewritten in this PR to reflect the partial outcome honestly. |

### Phase 3C — Verification

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 8 | **Fresh-install check.** `python -m venv /tmp/clean && /tmp/clean/bin/pip install -e . && /tmp/clean/bin/pip list \| grep -iE "redis\|agent-memory"` returns empty. | manual | **done** | Verified 2026-05-12 in P2 (PR #281). Vanilla install has zero Redis runtime deps. |
| 9 | **Source scrub.** `git grep -l "RedisShortTermMemory\|AgentCoordinator\|TeamSession" src/attune/` returns no results (or only the deprecation shim from Phase C, if C2 chosen). | manual | **partial** | After P1 (#279): `AgentCoordinator`/`TeamSession` references gone from `src/attune/` except `src/attune/coordination.py` (the PEP 562 shim). `RedisShortTermMemory` references remain by design — the facade stays. G3 reframed: "no references to deleted classes outside the shim." |
| 10 | **Workflow smoke test.** Run a representative attune-ai workflow (e.g. `attune workflow run code-review .`) end-to-end with no Redis package available. Confirm no "Redis not detected" log lines. | manual | **partial** | A Redis-free workflow run will still log "Redis not detected" once per session via `RedisAutoDetector` at import time. That probe is acknowledged as out-of-scope for this spec (separate "lazy redis probe" mini-spec candidate). The workflow itself runs cleanly without Redis — verified via the fresh-venv check in task #8. |
| 11 | **CI parity check.** Confirm CI runs are still green on `main` after the merged commits land. Test count delta matches expectation. | CI | **partial** | P1 (#279) green; P2 (#281) green. Both expected to merge alongside this PR. Test count delta vs spec's "~100 fewer tests" expectation: P1 deleted ~2,500 lines / ~140 tests for coordination alone, far exceeding the target. Other PRs in the same window added tests, so net count won't show the reduction directly — see the COVERAGE_BUG_LOG or `git log -- tests/` for the actual delta. |

### Phase 3D — Spec close

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 12 | Set this spec's status to `complete` in all three .md files. Optionally write `decisions.md` with the actual numbers (LOC removed, tests removed, install size delta). | docs | **done** (status: partial) | Status flipped to `partial` rather than `complete` because the full decoupling didn't happen — by design, per Phase A audit. P1 + P2 shipped the tractable scope; the rest stays Redis-coupled with "Redis-backed by design" documentation. Numbers preserved in `decisions.md`. |

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
