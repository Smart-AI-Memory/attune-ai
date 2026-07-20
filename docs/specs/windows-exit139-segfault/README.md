# windows-exit139-segfault — tracked failure class

**Status:** shipped (2026-07-20) — fix #1282 landed 2026-07-06; verification bar met (receipts below)
**Split from:** [ci-runner-hang](../archive/ci-runner-hang/) per the 5th-capture
tripwire ("if a THIRD exit-139 arrives, consider splitting"). The third
arrived within 24 hours of the second, on the same lane.

## Class signature

`test (windows-latest, 3.12)`: pytest run wedges, the 20-minute
conftest watchdog fires and writes faulthandler dumps, then the pytest
process dies with **exit 139 (segfault)** — twice now *while
faulthandler was mid-write* (controller dump truncated in
`re/_parser`). Distinct from the parent spec's end-of-session wedge
(exit 124 timeout-kill, workers idle in `serve()`).

## Sightings

| # | Date | Run | Where | Evidence |
|---|------|-----|-------|----------|
| 1 | 2026-07-05 | 10.0.1 release chain | #1272 | clean-log; getaddrinfo hypothesis formed, literal-loopback fix applied to the bootstrap-probe test |
| 2 | 2026-07-06 | `28772959348` | PR #1274 | [ci-runner-hang capture #5](../archive/ci-runner-hang/evidence/run-28772959348/) — end-of-session shape, controller dump truncated, worker dumps empty |
| 3 | 2026-07-06 | `28806701681` | PR #1279 | [ci-runner-hang capture #6](../archive/ci-runner-hang/evidence/run-28806701681/) — **complete worker dump with a test frame** |
| 4 | 2026-07-06 | `28810092051` | PR #1281 (this spec's own docs-only PR) | [evidence](../archive/ci-runner-hang/evidence/run-28810092051/) — identical chain, different test (`test_session_context.py:440 test_workflow_with_session_context` → unmocked `UnifiedMemory` → `is_redis_running` → redis-py `_connect`). A markdown-only diff wedging the same way proved the trap was on `main`. Harvested 2026-07-20 from the unmerged `docs/exit139-class-split` branch. |

## Confirmed mechanism (sighting 3)

`test_session_context.py::test_record_execution_success` constructs
`UnifiedMemory(user_id="test_user")` unmocked → real backend init →
`features.is_redis_running(host="localhost")` → redis-py `_connect` —
**blocked 20 minutes despite `socket_connect_timeout=1`**. The socket
timeout bounds only the socket phase; `getaddrinfo("localhost")` runs
before it and is not interruptible by `--timeout-method=thread` (a
C-level call — exactly decisions.md step 3's H1/H2 I/O-polluter
family). When the runner's resolver stalls, the worker wedges; the
watchdog fires; the subsequent segfault during dump/teardown produces
exit 139.

#1272 fixed one test probe. The `host="localhost"` defaults remain at
production call sites in `src/attune/memory/`: `unified.py` (77, 133),
`features.py` (78), `redis_bootstrap.py` (61, 67),
`short_term/facade.py` (134), `redis_auto_detect.py` (163),
`control_panel.py` (92), `control_panel_api.py` (308), `types.py` (71).
Any unit test that builds `UnifiedMemory` without mocking walks into
the same resolver.

## Fix (landed — PR #1282, 2026-07-06)

1. **Literal-loopback defaults** — `"localhost"` → `"127.0.0.1"` at
   24 sites across `src/attune/memory/` and the centralized
   `src/attune/redis_config.py`, eliminating per-call `getaddrinfo`
   on the default path. Env-provided hosts unchanged; `_LOCAL_HOSTS`
   keeps `"localhost"` for string-compare mode inference only.
2. **Test-lane belt-and-suspenders** — `tests/conftest.py` pins
   `REDIS_HOST=127.0.0.1` (unset/empty/localhost only) so no unit
   test ever name-resolves, even if a future call site regresses.
3. The segfault-during-faulthandler was deliberately **not** chased —
   it is downstream of the wedge; with no wedge there is no dump to
   segfault in.

**Regression guard (2026-07-20):**
`tests/unit/memory/test_loopback_default_guard.py` — source-scan
over the full #1282 surface fails if a `host="localhost"` default or
`REDIS_HOST`-fallback reappears, plus a runtime assert that the
conftest pin is in effect. Fires on all planted regression shapes,
silent on the deliberate string-compare uses.

## Verification receipts (bar met, 2026-07-20)

Bar (parent design.md G3): ≥10 clean `windows-latest` reruns under
`-n auto` post-fix, no new exit-139 sighting over a monitoring
window. Measured over 2026-07-06 → 2026-07-20 (`tests.yml`):

- **99 successful full-matrix runs** since the fix merged — ~495
  clean `windows-latest` lanes against the ≥10 bar.
- **Zero wedge-shaped failures**: every failed `windows-latest` job
  in the window (40, across 28 failed runs) completed in 16–17 min —
  under the 20-minute watchdog, so none can be this class. That
  redness was the deterministic `test_dangerous_paths_rejected`
  path-validation failure, fixed by #1474 (2026-07-19); the matrix
  has been fully green since.
- **No exit-139 sighting in 14 days** of monitoring (last: sighting
  4, 2026-07-06, pre-fix).

**Reopen/expand criteria:** an exit-139 with the fix in place and no
`getaddrinfo`/connect frame in the dump means a second mechanism —
capture and re-classify here, don't fold it back into ci-runner-hang.
