# Per-decision log — Redis decoupling

Append-only log. Pre-flight findings (Phase 3A tasks #1–#2) below.
Per-phase execution decisions appended as commits land.

---

## Phase 3A pre-flight (2026-05-10)

### Task #1 — `attune_redis` PyPI state → forces **C1** (deprecate + delete)

**Finding**: `attune-redis` does **not** exist on PyPI. Verified two
ways:

- `https://pypi.org/pypi/attune-redis/json` → HTTP 404
- `https://pypi.org/pypi/attune_redis/json` → HTTP 404
- PyPI simple-index search for "attune" returns: `attune`,
  `attune-ai`, `attune-author`, `attune-gui`, `attune-help`,
  `attune-lite`, `attune-project-api`, `attune-puthon`,
  `attune-python`, `attuned` — no `attune-redis`.

No local checkout either (`~/attune-redis` does not exist; the
sibling-repo grep during the deprecated-module-retirement spec also
came back clean for it).

**Implication for design.md C1 vs C2**:

The decision is **forced** rather than chosen. C2 ("thin-wrap
re-exports from `attune_redis`") presupposes the package exists on
PyPI to import from. It doesn't. So the live options collapse to:

- **C1 — delete with deprecation shim that errors helpfully**
  (proceed today; no upstream dependency)
- **C2-deferred — publish `attune-redis` first, then thin-wrap**
  (requires building, packaging, naming, releasing a new sibling
  package; substantially larger scope than this spec)

Recommendation: **proceed with C1**. It's the spec's default path
and was already framed as the lower-friction option in design.md.
If `AgentCoordinator` / `TeamSession` users surface during Phase B's
audit (task #3) and demand a continuing import path, that's the
trigger to revisit C2 — but until evidence of consumers appears,
C1's "deprecation shim that errors helpfully" is sufficient.

### Task #2 — Baseline test count (local)

**Result**: `pytest tests/unit/ -n auto` →
**14,122 passed, 5 failed, 71 skipped, 10 xfailed in 62.86s**
(local machine, 2026-05-10, pre-redis-decoupling).

The 5 local failures are environment-sensitive, not redis-related:

| Test | Cause |
|---|---|
| `tests/unit/agent_factory/test_langgraph_adapter.py::TestLangGraphAdapterGetLLM::test_anthropic_returns_chat_anthropic` | `langchain_anthropic` import path or env |
| `tests/unit/agent_factory/test_langgraph_adapter.py::TestLangGraphAdapterGetLLM::test_anthropic_no_api_key_raises` | same |
| `tests/unit/test_tier_recommender.py::TestEstimateCost::test_estimate_cost_default_capable` | tier estimation default constants |
| `tests/unit/test_token_utils.py::TestCountTokens::test_api_counting_success` | `ANTHROPIC_API_KEY` env var required |
| `tests/unit/test_token_utils.py::TestCountMessageTokens::test_api_message_counting` | same |

These pass on a CI runner with the API key + extras configured; they
are not blockers for this spec. They surface here only because the
local venv differs from CI's `pip install -e .[dev]` shape.

**Caveat**: Task #2 was supposed to land "after `ci-debt` Phase A
gives us a green CI." Phase A landed but CI is currently red on
main with a silent test-hang pattern (see PR #212 for the diagnostic
patch). The 14,122 number is therefore a **local-environment**
baseline, not a "post-CI-green" baseline. For Phase E's purpose
(verifying the ~100-test delta after redis removal), this is still
the right number — the delta is measured from the same starting
point regardless. The CI-vs-local count discrepancy is orthogonal.

### Bonus — named-removal-scope enumeration

The spec's Phase E names three deletion targets:
- `tests/unit/memory/test_pubsub_direct.py`
- `tests/unit/test_redis_fallback.py`
- `tests/unit/coordination/`

Collected count for these three: **74 tests** (well under the
spec's "~100 fewer tests" expectation, which means Phase B's audit
will need to identify ~25 additional redis-coupled tests for
removal/migration to hit the projected delta). A `grep` for
`import redis | from redis | RedisShortTermMemory | redis_auto_detect`
across `tests/` returns 17 candidate files; the gap (74 → ~100)
likely lives in some subset of:

- `tests/memory/` (8 redis-coupled files)
- `tests/unit/memory/test_redis_*.py` (4 files)
- `tests/unit/test_coverage_batch7.py`, `test_coverage_batch9.py`
  (mixed coverage files that may include redis-touching cases)

This becomes Phase B's audit work (task #3 / `audit.md`); flagged
here so the audit doesn't start cold.

### Phase 3A status

- **Task #1**: done — finding above; C1 path confirmed.
- **Task #2**: done — baseline 14,122 captured.

Phase 3B (audit + replace internal callers) is unblocked from a
research standpoint, but the recommended sequence remains: land
PR #212 → use the named hung test from CI to inform the audit →
then start Phase B.

---

## Phase 3B task #3 — audit complete (2026-05-12)

See [audit.md](audit.md) for the full classification table. Summary:

- **Three greps** ran (after fixing `--include` → pathspec). 155 +
  55 + 38 raw hits; most are self-references inside the module
  being audited.
- **8 external callers** across 6 subsystems: `core_modules/`,
  `mcp/memory_handlers`, `meta_workflows/session_context`,
  `telemetry/{feedback_loop,approval_gates}`,
  `agents/release/base_agent`, `memory/cross_session/`.
- **2 callers with exotic requirements** (cross-process pub/sub):
  `agents/release/base_agent.py` (`self.redis.publish(...)`) and
  `memory/cross_session/coordinator.py` (`pubsub.subscribe(...)`).
- Plus a soft pub/sub case: `core_modules/short_term_memory.py`'s
  `send_signal`/`receive_signals` public methods.

### Verdict: spec downgrades to partial

The spec's prose said "AgentCoordinator and TeamSession aren't
referenced internally." True for those two specific classes. But
the **Redis-shaped APIs** (`stash`, `retrieve`, `stage_pattern`,
`publish`/`subscribe`) extend across `core_modules/`, telemetry,
session context, and cross-session coordination. Full decoupling
isn't a delta on this spec — it's a memory-subsystem rewrite.

Per the spec's own failure-to-deliver path, the audit triggers
both the ">10 callers" threshold (borderline at 8) and the
"exotic requirements" threshold (cross-process pub/sub).

### Recommended partial scope

Three deliverables, each tractable:

1. **P1 — Delete `attune/coordination/` with deprecation shim.**
   `AgentCoordinator` and `TeamSession` have no internal callers;
   only the module itself references them. Path C1 (forced by
   Phase 3A task #1).
2. **P2 — Drop `[memory]` and `[redis]` extras from
   `pyproject.toml`.** `[dev]` already pulls `redis` for tests.
   Aggregator extras (`[full]`, `[enterprise]`, `[developer]`)
   re-audited.
3. **P3 — Delete tests covering the deleted surface.**
   `tests/unit/coordination/`, `tests/unit/test_redis_fallback.py`,
   `tests/unit/memory/test_pubsub_direct.py` (if PubSubManager is
   no longer reachable). Expect ~60–80 test reduction, under the
   spec's original "~100" target.

Everything else (`RedisShortTermMemory` facade, unified memory,
telemetry, MCP memory handlers, cross-session subsystem,
agents/release pub/sub) stays Redis-dependent and is documented
as "Redis-backed by design" rather than carried as debt.

### Adjacent finding (not actioned here)

`RedisAutoDetector` probing at import time is reachable as its
own one-file mini-spec: convert to lazy detection on first
`.stash()` call. Out of scope for this audit but worth flagging.
