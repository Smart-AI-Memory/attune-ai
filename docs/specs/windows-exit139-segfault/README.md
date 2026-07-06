# windows-exit139-segfault — tracked failure class

**Status:** open — fixable hypothesis confirmed (2026-07-06)
**Split from:** [ci-runner-hang](../ci-runner-hang/) per the 5th-capture
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
| 2 | 2026-07-06 | `28772959348` | PR #1274 | [ci-runner-hang capture #5](../ci-runner-hang/evidence/run-28772959348/) — end-of-session shape, controller dump truncated, worker dumps empty |
| 3 | 2026-07-06 | `28806701681` | PR #1279 | [ci-runner-hang capture #6](../ci-runner-hang/evidence/run-28806701681/) — **complete worker dump with a test frame** |

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

## Fix plan (narrow, per parent decisions.md step 4)

1. **Default the memory stack's Redis host to the literal loopback**
   `127.0.0.1` (or resolve-once-and-cache), eliminating per-call
   `getaddrinfo` on the default path. Env-provided hosts unchanged.
2. **Test-lane belt-and-suspenders:** set `REDIS_HOST=127.0.0.1` in
   `tests/conftest.py` so no unit test ever name-resolves, even where
   a future call site regresses.
3. Do **not** chase the segfault-during-faulthandler itself — it is
   downstream of the wedge (interpreter/teardown internals); with no
   wedge there is no dump to segfault in.

**Verification bar (parent design.md G3):** the wedge is intermittent —
require ≥10 clean `windows-latest` reruns under `-n auto` after the
fix, and no new exit-139 sighting over a monitoring window.

**Reopen/expand criteria:** an exit-139 with the fix in place and no
`getaddrinfo`/connect frame in the dump means a second mechanism —
capture and re-classify here, don't fold it back into ci-runner-hang.
