# redis-config-truth — requirements

**Status:** draft (2026-08-08 — promoted from roundtable
`q-short-term-memory-enhancements-001`; awaiting chair review)

## Problem

The Redis connection configuration has four half-resolvers and zero
authoritative ones: `roundtable.Board` reads only `REDIS_URL`;
`memory/config.py` checks `REDIS_URL` / `REDIS_PUBLIC_URL` /
`REDIS_PRIVATE_URL`; `BaseOperations` takes host/port/password
kwargs; and the `attune.memory_backends` entry point resolves
per-environment. On 2026-08-08 this produced a live failure: the
local server had `requirepass` enabled, `REDIS_PASSWORD` was set in
the user's shell, but no consumer merged it into the password-less
`REDIS_URL` — every Redis-backed feature failed with
`AuthenticationError`, and the fail-open hooks hid the
misconfiguration for an unknown period.

The round table (3/3 unanimous, each seat's top priority) ruled the
fix is configuration truth plus failure observability — not new
capability.

## Requirements

### R1 — one canonical resolver

A single `resolve_redis_connection()` (location:
`attune.memory.config`) is the ONLY way any component derives a
Redis connection spec. Documented precedence:

1. Explicit URL already carrying credentials.
2. `REDIS_URL` merged with `REDIS_PASSWORD` / `REDIS_USER` when the
   URL lacks them.
3. `REDIS_PUBLIC_URL` / `REDIS_PRIVATE_URL` variants (same merge).
4. Host / port / db / password components.
5. Default `redis://127.0.0.1:6379/0`.

Consumers migrated in this spec: `roundtable.Board`,
`memory/config.py` internals, `BaseOperations`, session hooks, the
entry-point backend probe. Conflicting settings produce an
actionable diagnostic, never a silent pick.

### R2 — redacted effective-config diagnostic

A `doctor`-style probe (extend `redis_health_check` and/or
`attune memory doctor`) reports: which env vars resolved, the
resulting URL shape with the password REDACTED, whether AUTH
succeeded, and which backend the entry point selected and why.

### R3 — classified, loud-once degradation

Graceful degradation stays (ratified P15: never block work). Failure
classes are distinguished:

- `degraded_auth` / invalid config — will never self-heal: warn
  loudly ONCE per session (structured log + SessionStart notice or
  health-snapshot line).
- `degraded_connectivity` (server absent / transient) — stay quiet,
  as today.
- `disabled` (intentional) — distinguished from broken.

Secrets stay redacted in every message.

### R4 — the incident's regression guard

A non-mocked round trip proving the password-merge path against a
`requirepass` server (skip when no local Redis): set
`REDIS_URL` without credentials + `REDIS_PASSWORD`, assert the
resolver produces an authenticated connection. Unit tests cover
precedence ordering.

## Non-goals

Ruled by the round table (see decisions.md D1 and
`docs/reports/roundtable/q-short-term-memory-enhancements-001.md`):
no Redis Cluster support, no new backends, no new capability
modules, no speculative performance work.

## Acceptance criteria

- One resolver; grep shows zero direct `os.environ.get("REDIS_URL")`
  outside it (allowlist: the resolver module itself).
- The 2026-08-08 incident shape (password-less URL + requirepass +
  `REDIS_PASSWORD` set) connects successfully.
- An auth failure surfaces a visible once-per-session notice; a
  server-absent failure stays silent.
- R4 lane green locally; suite green keyless in CI.
