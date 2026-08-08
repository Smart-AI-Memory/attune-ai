# Agent work handoff

## Goal

redis-config-truth rct-4: every direct Redis connection-env reader
migrated to `resolve_redis_connection()`, with a drift guard that
fails CI on ANY new direct read of the eight connection names
outside the resolver module.

## Acceptance criteria

- Grep-clean: zero direct reads of REDIS_URL / PRIVATE / PUBLIC /
  HOST / PORT / DB / PASSWORD / USER outside
  `src/attune/memory/config.py`.
- Drift guard fires on planted violations in EVERY access form
  (environ.get, environ[...], os.getenv, bare getenv import,
  get_attune_env, environ-alias subscript) — allowlist seeded empty.
- R4 incident shape connects through every migrated consumer
  (parametrized).
- Full unit suite green; keyless CI semantics unchanged.

## Scope and assumptions

- Branch/worktree: `claude/rct-4-consumer-migration` off origin/main.
- Provider/session: Claude lead, 2026-08-08 starter session (cont.).
- Assumptions: execution scope is the CURRENT-tree grep (10 files /
  45 hits), not D3's 15-file snapshot — five named files no longer
  read env; toggles (REDIS_MODE, ATTUNE_REDIS_MOCK, REDIS_ENABLED,
  SSL/timeout knobs) are NOT connection components and keep their
  reads.

## Current state

- Status: implemented + tested; PR pending; D11 lane pending.
- Changed files: redis_config.py (delegator rewrite — mode/SSL kept,
  components from resolver), memory/config.py (password property,
  URL_VARS export, own legacy helpers migrated), recall_redis.py,
  unified.py, features.py, redis_auto_detect.py, redis_bootstrap.py
  (each: `_resolved_password()`), roundtable/board.py + routine.py,
  attune_redis/config.py; new gate
  tests/unit/gates/test_redis_env_access_gate.py; new
  tests/unit/memory/test_rct4_incident_shape.py; 8 existing tests
  updated (hermetic env scrubs + new private-helper signature +
  canonical-name switch).
- Decisions: (1) URL-typed config fields (unified.redis_url,
  RedisPluginConfig.redis_url) stay None unless a URL var sourced
  the connection — preserves the pub/sub and explicit-URL gates;
  (2) EMPATHY_REDIS_HOST/PORT compat for CONNECTION vars retired
  (canonical names only — release-note); (3) REDIS_PORT/DB without
  REDIS_HOST no longer honored in legacy local mode (R1 tier 4 is
  host-anchored — release-note); (4) resolver merges REDIS_PASSWORD
  into passwordless URLs everywhere (the incident fix — the
  headline behavior change).
- Risks or open questions: staging/CI envs with stale
  REDIS_PASSWORD start authenticating (and failing loudly via
  rct-2's degraded_auth) — intended, release-note for 11.6.0.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Corpus grep-clean | drift-guard corpus test + manual grep | pass |
| Guard fires per form | 8 planted-violation params | pass |
| Incident shape everywhere | test_rct4_incident_shape.py (9) | pass |
| No behavior regressions | redis_config 40-test suite + memory + roundtable suites, serial | 2285+ passed |
| Live-fire | real requirepass env: Board ensure_functions OK (fixed today's board_unreachable), recall PING True, legacy check connected | pass |

## Next action

D11 codex lane (memory/security surface) → ledger row → PR → chair
merge read on explicit go. Delete this file when the branch merges.
Next rung: rct-5 (self-provisioning requirepass lane).
