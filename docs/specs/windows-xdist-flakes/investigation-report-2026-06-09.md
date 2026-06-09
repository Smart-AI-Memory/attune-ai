# Investigation Report — xdist Worker-Crash Flakes (2026-06-09)

Phase 4 execution of [design.md](./design.md). Probe A (inventory) was
run; the decision tree self-selected the **fix-the-polluter** branch; the
polluters were fixed.

---

## Probe A — inventory

**Method:** scanned the 40 most-recent failed `tests.yml` runs
(`gh run list --workflow tests.yml --status failure`), fetched each run's
failed-job log, and grepped the xdist crash signature
`worker '<id>' crashed while running '<testid>'`. 23 crash instances
found across the window (2026-06-03 → 2026-06-09).

> Note: the crashes are **not Windows-only** — the dominant entry
> surfaced on the ubuntu `coverage` job. The investigation cast a wider
> net than the spec title (all `tests.yml` failures, every OS lane).

### Crashes by test (aggregated)

| Test file | Crashes | Unique tests | Disposition |
|---|---|---|---|
| `tests/memory/test_unified_memory.py` | 13 | 1 (`TestUnifiedMemoryBackendInit::test_init_with_auto_start_file_first_fallback`) | **fixed here** |
| `tests/agents/test_notifications.py` | 6 | 2 (`TestComplianceAlerts::test_compliance_alert_structure`, `::test_sms_only_for_critical_high`) | fixed in #709 |
| `tests/unit/memory/test_redis_bootstrap.py` | 2 | 1 (`TestCheckRedisRunning::test_uses_custom_host_and_port`) | **fixed here** |

**3 distinct files** → per the design's stop conditions
(`<5 distinct files`), the decision tree selects the
**fix-the-polluter** branch (not marker-based xfail).

---

## Root causes — all the same class: real I/O in a unit test

Every crash is a test doing real network/subprocess I/O that, under xdist
parallelism, intermittently crashed its worker — the CLAUDE.md
"Windows xdist worker crashes often come from real socket probes" pattern.

1. **`test_init_with_auto_start_file_first_fallback`** (13 — dominant) —
   constructs `UnifiedMemory(MemoryConfig(redis_auto_start=True,
   redis_mock=False))`. The auto-start path calls
   `redis_bootstrap.ensure_redis(auto_start=True)`, which **spawns real
   subprocesses** (`brew`/`systemctl`/`docker` to start redis-server) and
   socket-probes Redis. The test only asserts *file-session* behaviour —
   the Redis auto-start is incidental to its intent.

2. **`test_uses_custom_host_and_port`** (2) — calls
   `_check_redis_running(host="nonexistent-host", ...)`, which does
   `redis.Redis(host="nonexistent-host").ping()` → a real DNS
   `getaddrinfo()` on a bogus hostname that hangs/crashes a worker.

3. **`test_notifications.py::TestComplianceAlerts`** (6) — already fixed
   in #709: `send_compliance_alert` reached real `smtplib.SMTP` +
   `requests.post` calls.

---

## Fixes applied

- **#1** — mock `attune.memory.redis_bootstrap.ensure_redis` to return an
  unavailable `RedisStatus`. This exercises the exact file-first fallback
  the test asserts, with zero subprocess/socket I/O.
- **#2** — replace the bogus hostname with the literal loopback IP
  `127.0.0.1` + a closed port. No DNS; an instant connection-refused
  yields the same graceful `False`, matching the proven-safe sibling test
  (`test_returns_false_when_not_running`, which already uses
  `localhost:16379`).
- **#3** — shipped in #709 (`smtplib.SMTP` + `requests.post` mocked).

All verified under `pytest -n 4` (the parallel crash condition).

xfail teardown (design DECIDE-3): none of the three crash sites carried
`xfail` markers — they crashed rather than being xfailed — so there is
nothing to remove.

---

## Follow-up (systemic, not done here)

The per-polluter fixes close the current inventory. A stronger guard
against regressions would be an `autouse` conftest fixture over the memory
test tree that fails fast on (a) real `ensure_redis` subprocess starts and
(b) `_check_redis_running` against non-loopback hosts — so a future test
re-introducing real Redis I/O is caught at authoring time, not via a CI
worker crash. Deferred: the three known polluters are fixed and the
inventory is clean.
