# Round table — short-term memory / Redis enhancement opportunities

**Thread:** `q-short-term-memory-enhancements-001` · 2026-08-08 ·
1 round, halted on convergence · Seats: Antigravity (44.8s),
Claude (57.2s), Codex (74.7s) — all answered blind.
**Full transcript:** machine-local at
`~/.attune/reports/roundtable/q-short-term-memory-enhancements-001.md`
(local-first carve; the board thread TTLs at 7 days).

This stub carries the chair-promoted, subsystem-wide outcomes. The
config-scoped mandate lives in
`docs/specs/redis-config-truth/` (its D1 records the promotion).

## Unanimous (3/3, independently)

1. **One canonical Redis connection resolver** used by Board,
   `memory/config.py`, hooks, and the entry-point backend — every
   seat's #1, citing the live 2026-08-08 `AuthenticationError`
   (password-less `REDIS_URL` + `requirepass` + unmerged
   `REDIS_PASSWORD`). → promoted as spec `redis-config-truth`.
2. **Degrade gracefully ≠ degrade invisibly** — keep never-block,
   classify failures, warn loudly once on non-self-healing classes
   (auth/misconfig), stay quiet on server-absent. → same spec.
3. **Premise correction (the pushback):** this layer needs
   *hygiene, not horsepower*. All three seats independently
   rejected Redis Cluster, alternative backends, new capability
   modules, and speculative perf work at sole-developer-plus-agents
   scale.
4. **Real-Redis parity test lane** — the dict mock proves the mock;
   MGET shape, TTL, and SCAN semantics need a non-mocked,
   skip-when-unreachable contract suite.

## Standing rulings (chair, 2026-08-08)

- **Batch-primitive generalization: DEFERRED** by rule of three —
  `batch.py` has one consumer shape; parameterize when a second
  real caller appears. Do not re-pitch without one.
- **Facade work (63 methods, 16 modules): GATED on usage
  evidence** — answer "which methods do live sessions invoke"
  (telemetry or non-test call-site grep) before restructuring
  (Antigravity's namespacing) or pruning (Claude's
  should-this-exist pass). The two approaches compose:
  evidence → prune → namespace survivors.
- **Keyspace `empathy:*` → `attune:*`:** direction agreed 3/3,
  ambition unruled (cheap TTL-window rename vs KeyRegistry vs
  versioned `attune:v1:` contract with dual-read). Unscheduled;
  Codex's framing recorded: "the value is the contract, not the
  rebrand."

## Unique-seat items (recorded, unscheduled)

- **Codex — atomicity audit** of read-modify-write coordination
  paths (queue claims, conflict transitions, cursor advancement):
  "the users are concurrent agents, so races are a correctness
  problem, not a theoretical Redis concern."
- **Codex — TTL by data class** (blanket 86400s is wrong for
  leases vs conflicts vs sessions) — also answers Antigravity's
  follow-up (per-class policy, not one global cap).
- **Codex — namespace inventory visibility** (key counts, missing
  TTLs, hydration freshness) at scan-bounded cost.

## Promotions

Chair promoted: spec `redis-config-truth` (C1+C2) and an outbox
lesson on the URL/password split failure class. Curated content
beyond this stub was declined; the transcript stays machine-local.
