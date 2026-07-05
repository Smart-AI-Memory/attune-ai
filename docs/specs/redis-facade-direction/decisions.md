# Decisions: Redis Facade Direction

> **A proposal to ratify, not executed work.** This doc records the
> direction that came out of the 2026-06-07/08 facade review. No
> code has been changed on the strength of it. Bring corrections to
> the morning meeting; once ratified, each decision spawns its own
> scoped change.

**Status:** D1 relabel EXECUTED 2026-06-08 per Patrick's direction (Redis stays — no removal; align on Redis + Anthropic Claude). The `REMOVE IN v9.0.0` exit markers are retired. D2–D5 remain proposed.
**Owner:** Patrick
**Related:**

- [`docs/redis/best-practice-alignment.md`](../../redis/best-practice-alignment.md)
- [`anthropic-memory-tool-backend`](../anthropic-memory-tool-backend/requirements.md)
- [`pattern-review-queue`](../pattern-review-queue/requirements.md)
- [`project_redis_strategy_leverage`](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/project_redis_strategy_leverage.md)
  — "leverage their work, don't decouple" (the governing strategy)
- [`release_state`](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/release_state.md)
  — currently records the (now-superseded) "removal deferred to
  v9.0.0" framing

---

## Context (what was reviewed)

The 6 in-tree `attune.redis_*` / `memory/config` modules (1,492
lines) carry `REMOVE IN v9.0.0` "deprecated" markers. Patrick flagged
the deprecate/remove decision as hasty and asked for a review. The
review found:

1. The governing strategy is **leverage, not decouple** (2026-06-03
   directive). The `REMOVE IN v9.0.0` markers contradict it — they
   signal "exiting Redis" when the direction is "doubling down."
2. There are **two distinct Redis codebases**, conflated by the
   markers: the **old in-tree** code (`RedisShortTermMemory` +
   coordination mixins + `redis_config`) and the **new leverage path**
   (`attune_redis.AMSMemoryBackend` + int8 factory). "The work" is the
   new path.
3. The old code's distinctive value is its **coordination mixins**
   (pattern staging, conflict negotiation, signals, shared sessions)
   — but those are **dormant** (no live MCP/CLI reaches them; only
   `control_panel` instantiates `RedisShortTermMemory`, for
   `clear_short_term` + health).
4. Best-practice lens: Anthropic now ships **native multi-agent
   coordination** (subagents, Managed-Agents `multiagent`). Reviving
   custom Redis coordination primitives would reimplement a
   vendor-native capability.

---

## D1 — Do NOT remove the facades. Relabel them.

**Decision (proposed):** Keep the 6 modules. Replace the
`REMOVE IN v9.0.0` markers with **"superseded by `attune_redis`,
retained for compatibility"**. The strategy is leverage; the markers
should stop signaling exit.

**Why:** `RedisShortTermMemory` is still live via `control_panel`;
removal is a memory-subsystem change, not a facade delete; and the
markers contradict the leverage strategy. Relabel is a low-risk text
change (a few module headers + the migration doc), not a code change.

**Not yet done.** Proposed as a small, reviewable PR after
ratification.

## D2 — Retire the coordination mixins (do not revive).

**Decision (proposed):** Treat `ConflictNegotiationMixin`,
`CoordinationSignalsMixin`, `SessionManagementMixin` as **retired** —
keep as reference (don't delete blindly per the relabel decision),
but do **not** build product surface on them. If multi-live-agent
coordination becomes a real feature, build it on **Anthropic
subagents / Managed-Agents `multiagent`**, not custom Redis pub/sub.

**Why:** dormant (no live caller), and reviving them reimplements a
vendor-native capability — the opposite of "align with best practice"
(see alignment doc). `RedisStorageBase` is superseded by
`AMSMemoryBackend`.

## D3 — Capture PatternStaging as a user feature.

**Decision (proposed):** The **one** dormant piece with genuine,
vendor-unique value is `PatternStagingMixin`. Capture its design
(stage → review → promote/reject) as the **pattern-review queue**,
re-homed on the current backend stack (file/AMS), off the deprecated
Redis coupling. Spec:
[`pattern-review-queue`](../pattern-review-queue/requirements.md).

**Why:** no vendor-native equivalent (it's an attune-domain
curation workflow); the data model (`StagedPattern`) and promote
target (`PatternLibrary.contribute_pattern`) already exist and are
not deprecated.

## D4 — Invest in the AMS/Redis leverage path; add the Anthropic bridge.

**Decision (proposed):** Continue the `attune_redis`/AMS line (the
real "Redis work"): land the in-flight fixes (#666/#667/#668), ship
the **Anthropic Memory-tool backend bridge** (the one item that
makes "follows both vendors' best practices" demonstrable), bump
`agent-memory-server` 0.14.0 → 0.15.2 and re-verify, and ship the
upstream RedisVL **datatype contribute-back PR**. Spec:
[`anthropic-memory-tool-backend`](../anthropic-memory-tool-backend/requirements.md).

**Why:** strongest, most-claimable alignment; "contribute back" is
the highest-integrity leverage move.

## D5 — Update `release_state` once ratified.

**Decision (proposed):** After ratification, update the
`release_state` memory: the "removal deferred to v9.0.0" line is
superseded by "relabel-not-remove; leverage path is the work." 9.0.0
is **not** a facade-removal release.

## D6 — Redis memory deps become CORE dependencies (packaging catch-up with D1). EXECUTED 2026-07-04.

**Decision:** `redis>=5.0.0,<9.0.0` and
`agent-memory-client>=0.14.0,<0.15` move from the `[redis]` extra
into core `dependencies`. The `[redis]` extra stays as an empty
backward-compat alias (the `[memory]`/`[rag]` pattern); the `[dev]`
mirror entries are removed. Install docs (README, docs/features,
website homepage) now present memory as part of the standard
install, activating when a Redis Stack server is reachable.

**Why:** D1 ratified "Redis stays — align on Redis + Anthropic
Claude," and memory unification (9.6.0) made cross-session memory
the flagship story — yet the standard install couldn't run it
(`redis_memory_*` MCP tools failed in every venv that missed the
extra; the 2026-07-02 worktree-drift class). This REVERSES the
packaging half of the archived redis-decoupling spec ("vanilla
attune-ai is Redis-free") — deliberate, Patrick-directed 2026-07-04.

**Conditions shipped with the flip:** (1) tight cap on
agent-memory-client (`<0.15`) since it now sits on every user's
resolution path; (2) a no-server degradation gate — the memory
surface with deps installed but no reachable server must produce a
clean guidance message, not a traceback (the 9.3.0 "boot-only smoke
passes broken features" lesson).

---

## What this does NOT decide (open for the meeting)

- Whether to ever fully remove the in-tree `RedisShortTermMemory`
  (a real memory-subsystem migration) — out of scope here; the
  proposal is to stop *signaling* removal, not to schedule one.
- Whether the Memory-tool bridge lives in `attune.memory` or
  `attune_redis` (design.md open question).
- Sequencing of the leverage-track items relative to the next
  release cut.

---

## Ratification checklist (for the morning)

- [x] D1 relabel-not-remove — RATIFIED & EXECUTED 2026-06-08
- [ ] D2 retire coordination mixins — agree / amend?
- [ ] D3 capture PatternStaging as pattern-review queue — agree?
- [ ] D4 AMS bridge + upstream contribute-back + 0.15.2 bump — agree
      / sequence?
- [ ] D5 update `release_state` framing — agree?
