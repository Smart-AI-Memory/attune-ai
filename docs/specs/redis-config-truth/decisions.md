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

## D5 — Redis stays bundled and zero-config; the backend STATE becomes visible (RULED 2026-09-06, chair, via pushback card)

**Date:** 2026-09-06 · **Status:** ruled (chair pick on the lead's
pushback card: "Keep bundled and zero-config; make the state visible and
fix the friction")

**Question.** The chair asked whether Redis should become an optional
install, or an option during the initial install, "without damaging
performance to users", and invited pushback.

**Facts the ruling rests on (verified 2026-09-06).** The Redis SERVER is
already optional at runtime: with the Agent Memory Server unreachable
`resolve_backend()` returns `FileStashBackend` (`is_fallback=True`) in
0.15 s; with the plugin absent, in 0.04 s. The two client libraries
(`redis`, `agent-memory-client`) are core dependencies and the
`attune_redis` plugin is bundled in the wheel; the `[redis]` extra was an
empty alias never used. Performance is not at stake in either
direction: recall digest 4.6 ms on files vs 0.6 ms on Redis; importing
the client libraries costs ~131 ms once. The AMS URL comes from the
plugin config (`AMS_BASE_URL`, default `http://localhost:8000`), not
from the Redis URL variables. `backend_status()` already distinguishes
live-upgrade / file-fallback / dark-upgrade; the SessionStart recall
hook warns only in the dark case; `attune doctor` reported raw Redis
reachability but never the memory backend, and `attune memory` had no
`status`.

**Positions.** (a) Optional install or install-time option (chair's
opening approach): `pip` cannot prompt, so this is a first-run question
plus a real extra — two install paths, and the decision lands at the
moment users know least; the last interactive installer here is where
the #1418 "installed nothing, printed a checkmark" bug lived. (b) Make
the extra real: client libraries out of core, plugin degrades; lighter
base install, but a user with Redis and no extra silently gets the file
tier. (c) **Keep bundled and zero-config; make the state visible; fix
the friction** — the lead's alternative, adopted. Counter-case to (c),
stated to the chair before the pick: bundling drags two client
libraries and their closure into every install for users who never run
Redis, and the empty alias was a standing lie in `pyproject.toml`.

**What (c) means in code.** `attune memory status` (with `--json`)
names the resolved backend, transport and reachability and prints the
guidance for each state (zero-config file tier + how to upgrade;
degraded with a dark upgrade; not usable with the reason). `attune
doctor` gains a "Memory backend" line that never contributes a FAIL —
memory is optional. The empty-alias comment in `pyproject.toml` is
corrected. The friction findings come from the Redis install/config
audit the chair started the same night (chip `task_af6763f5`); fixes
land under this ruling, not under a new install path. The standing
strategy memory ("leverage the Redis work, don't decouple") is
unchanged by this ruling.

**Not ruled.** Whether the client libraries should ever move to a real
extra. If the base-install weight becomes the concern the chair holds,
(b) is the honest answer and its one cost is the silent fallback.
