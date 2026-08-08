# redis-config-truth — decisions

## D1 — Spec originated by chair promotion from the round table

**Date:** 2026-08-08 · **Status:** RULED (chair: Patrick, promotion
form in-session)

Origin: roundtable thread `q-short-term-memory-enhancements-001`
(1 round, halted on convergence; full transcript machine-local at
`~/.attune/reports/roundtable/`, subsystem-wide record at
`docs/reports/roundtable/q-short-term-memory-enhancements-001.md`).
All three seats independently ranked the same two items first, and
the chair promoted them as this spec's mandate:

- C1 — one canonical Redis connection resolver used everywhere
  (→ R1, R2).
- C2 — graceful degradation made observable: classified failures,
  loud-once on non-self-healing classes (→ R3).

Evidence receipt: the live 2026-08-08 `AuthenticationError`
incident — `requirepass` on, `REDIS_PASSWORD` set,
password-less `REDIS_URL`, four independent env readers, silent
fail-open hooks (→ R4 pins it as the regression guard).

Chair rulings recorded with the promotion (scope guards for this
spec): batch-primitive generalization stays DEFERRED (rule of
three); facade restructure/prune is GATED on usage evidence; no
cluster, no new backends, no capability additions (Non-goals).
The full subsystem-wide record, including per-seat positions and
the two member-originated questions, lives in the tracked
roundtable report — this spec's decisions do not restate it.

## D2 — Requirements APPROVED as drafted

**Date:** 2026-08-08 · **Status:** RULED (chair: Patrick, in-session
review via batched form)

All four Rs + non-goals approved without amendment. Same ruling set
the session scope: decompose into tasks only; execution waits for a
fresh chair go on the reviewed ladder.

## D3 — Execution grounding: the code is the contract

**Date:** 2026-08-08 · **Status:** recorded (moderator scope-grep,
receipt below)

The requirements named five consumers; the grep receipt
(`grep -rln 'REDIS_URL|REDIS_PASSWORD|...' src/attune attune_redis`)
found the REAL set: **15 files, 42 direct env reads**, spanning
`src/attune` AND the bundled `attune_redis` package. Two partial
resolvers already exist:

- `attune.redis_config` — DEPRECATED but comprehensive (URL
  override, cloud/local modes, SSL, sentinel, mock); its docstring
  points successors at `attune_redis.config.RedisPluginConfig`.
- `attune_redis.config.RedisPluginConfig` — the designated
  successor, plugin-scoped.

Consequence for the ladder: T1 does NOT green-field a third
resolver — it audits both candidates, recommends the canonical
home (chair checkpoint inside T1), and implements
`resolve_redis_connection()` there. R1's intent (ONE resolver,
documented precedence) is unchanged; only the assumed location
(`attune.memory.config`) is demoted from requirement to T1 input.

## D4 — D11 cross-review lane: 4/4 findings real, accepted, amended

**Date:** 2026-08-08 · **Status:** recorded (lead disposition;
thread `review-claude-redis-config-truth-spec-20260808-0640`)

Codex reviewed the spec-text diff (4 files sent, 0 omitted) and
returned 4 findings — all verified real and amended in-branch:
(1) R1 still hard-coded `attune.memory.config` after D3 demoted it
— R1 now defers to the rct-1 ruling; (2) the drift guard covered
only `os.environ.get("REDIS_URL")`-form reads — broadened to all
access forms and all REDIS_* component names, with per-form
planted-violation proof; (3) rct-5's skip-when-unconfigured lane
could leave the incident AC perpetually unverified — the lane now
PROVISIONS an ephemeral requirepass server and a meta-test fails
if it skips while the binary exists; (4) "conflicting settings"
was undefined — R1 now carries an explicit conflict rule
(precedence always decides; overrides recorded in the source-map
and surfaced; only malformed values raise). The spec-text-highest-
yield pattern holds: third consecutive spec-text lane with a 100%
real-finding rate.
