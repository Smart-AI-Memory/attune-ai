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

## D5 — Redis stays bundled and zero-config; a first-run notice lets users choose; the choice is honored (RULED 2026-09-06, chair — pushback card, then assumption review)

**Date:** 2026-09-06 · **Status:** ruled. First recorded from a card pick
the same night; rewritten the same night after the chair's assumption
review corrected the shape. The chair's own words are the record:

> Redis's primary goal is to "provide enhanced memory features using
> Redis's open source coding options."

> I want there to be a first run notice that lets users choose if
> possible.

**What was asked.** Whether Redis should become an optional install, or
an option during the initial install, "without damaging performance to
users"; the chair invited pushback.

**What is true (verified 2026-09-06).** The Redis SERVER was already
optional at runtime: with the Agent Memory Server unreachable
`resolve_backend()` returns `FileStashBackend` (`is_fallback=True`) in
0.15 s; with the plugin absent, in 0.04 s. The two client libraries
(`redis`, `agent-memory-client`) are core dependencies and `attune_redis`
is bundled in the wheel; the `[redis]` extra was an empty alias no one
ever used. Performance in the sense the chair meant (runtime speed) is
not at stake: recall digest 4.6 ms on files vs 0.6 ms on Redis; client
import ~131 ms once. The AMS URL comes from the plugin config
(`AMS_BASE_URL`, default `http://localhost:8000`). `backend_status()`
already distinguished live-upgrade / file-fallback / dark-upgrade, but
`attune doctor` never named the memory backend and `attune memory` had
no `status`.

**Ruling.**
1. Redis stays **bundled and zero-config**. No optional install, no
   install-time prompt in `pip` (it cannot prompt; the last interactive
   installer here is where the #1418 "installed nothing, printed a
   checkmark" bug lived). The strategy memory "leverage the Redis work,
   don't decouple" stands.
2. The backend **state is visible**: `attune memory status` (`--json`)
   and a doctor "Memory backend" line that never contributes a FAIL.
3. A **first-run notice lets users choose**, on every surface that can
   carry it: a SessionStart hook notice (the consent-notice pattern —
   once, anti-nag, "ACTION FOR CLAUDE: ask once"), a one-time notice on
   the first interactive `attune` run (informs and points at the
   choosing commands; never blocks a command with a prompt), an
   interactive prompt in `attune setup`, and `attune memory use
   <auto|file|redis>` for changing it later.
4. The choice is a **persisted preference the resolver honors**
   (`~/.attune/config.json` → `memory.backend`; `ATTUNE_MEMORY_BACKEND`
   overrides per process): `auto` = a reachable upgrade wins, else the
   file tier (today's behavior); `file` = the local tier only, the
   upgrade is never probed or reported dark; `redis` = prefer the Agent
   Memory Server, degrade to files when unreachable and say so loudly.
   A choice that changed nothing would be theater.
5. Redis's role is stated everywhere it is offered in the chair's words
   (`attune.memory.preference.REDIS_ROLE`).

**Positions considered.** (a) optional install / install-time option —
the chair's opening approach, declined for the reasons in 1; (b) make
the `[redis]` extra real — left **not ruled**: it is the honest answer
only if base-install weight becomes the concern, and its one cost is
the silent fallback for a user with Redis and no extra; (c) keep
bundled, make the state visible — adopted, then widened by the chair's
review to include the first-run choice (3) and its persistence (4).
Counter-case to the adopted position, stated before the pick: bundling
drags two client libraries and their closure into every install for
users who never run Redis.

**Process note.** The first D5 was written within minutes of the card
pick and recorded my framing, not the chair's. The assumption review
that followed found the shape wrong (item 3). Rulings are recorded in
the chair's words; a card pick settles one dimension, not the framing
around it (project memory
`feedback_assumption_review_before_recording_a_pick`).

**Friction.** The install/config friction list comes from the Redis
audit the chair started the same night (chip `task_af6763f5`); fixes
land under this ruling.
