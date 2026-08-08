# redis-config-truth — requirements

**Status:** approved (2026-08-08 — chair, in-session review; see
decisions.md D2. Execution grounding in D3: the real reader set is
15 files / 42 direct env reads, and two partial resolvers already
exist — T1 rules the canonical home.)

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

A single `resolve_redis_connection()` (home ruled in rct-1 — see
decisions.md D3; two partial resolvers already exist) is the ONLY
way any component derives a Redis connection spec. Documented
precedence:

1. Explicit URL already carrying credentials.
2. `REDIS_URL` merged with `REDIS_PASSWORD` / `REDIS_USER` when the
   URL lacks them.
3. `REDIS_PUBLIC_URL` / `REDIS_PRIVATE_URL` variants (same merge).
4. Host / port / db / password components.
5. Default `redis://127.0.0.1:6379/0`.

Consumers migrated in this spec: the full grep-derived reader set
(15 files, decisions.md D3), including `roundtable.Board`,
`memory/config.py` internals, `BaseOperations`, session hooks, and
the entry-point backend probe.

**Conflict rule (defined, not vibes):** precedence always decides —
the resolver never raises on redundant or disagreeing settings.
When a lower-precedence variable is overridden with a DIFFERENT
value (e.g. a credentialed URL disagrees with `REDIS_PASSWORD`, or
public and private URLs coexist), the override is recorded in the
resolver's source-map and surfaced by R2's doctor and R3's
loud-once path. Only malformed values (unparseable URL, non-numeric
port) raise, with an actionable message.

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

- One resolver; a drift-guard test proves zero access to the
  `REDIS_*` connection env names in ANY form — `os.environ.get`,
  `os.environ[...]`, `os.getenv`, including `REDIS_PASSWORD` /
  `REDIS_HOST` component reads — outside the resolver module
  (allowlist seeded empty; AST- or pattern-based, and it must
  catch a planted violation in each access form).
- The 2026-08-08 incident shape (password-less URL + requirepass +
  `REDIS_PASSWORD` set) connects successfully.
- An auth failure surfaces a visible once-per-session notice; a
  server-absent failure stays silent.
- R4 lane green locally; suite green keyless in CI.
