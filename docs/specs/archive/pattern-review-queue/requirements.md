# Spec: Pattern Review Queue

> Put a **human in the loop** before discovered patterns enter the
> active pattern library. Today `PatternLibrary.contribute_pattern()`
> adds patterns directly. This spec adds a **review queue**:
> discovered patterns are *staged*, surfaced for review (CLI + ops
> dashboard), and only **promoted** into the active library on
> approval — or **rejected**. It captures the design of the dormant
> `PatternStagingMixin` (the one piece of the old in-tree Redis
> coordination code with genuine, vendor-unique user value) and
> re-homes it on the current backend stack, off the deprecated
> Redis coupling.

**Status:** complete (2026-06-09) — R1–R5 + R8(unit) shipped in #689,
R6 (dashboard panel) and R7 (opt-in routing) shipped 2026-06-09. R7's
Phase-0 audit found the only live contribution seams are
`SharedLibraryMixin.contribute_pattern` and
`ConfigurationStore._contribute_to_pattern_library`; the other
spec-named paths (`agent_monitoring.py`, `pattern_persistence.py`,
`core.py`) are metrics/load paths, correctly left untouched.
**Owner:** Patrick + agent
**Related:**

- [`docs/redis/best-practice-alignment.md`](../../redis/best-practice-alignment.md)
  — why PatternStaging is "capture" and the coordination mixins are
  "retire"
- [`redis-facade-direction/decisions.md`](../redis-facade-direction/decisions.md)
  — the facade direction this implements one half of
- `src/attune/memory/types.py::StagedPattern` — the data model
  (already exists, **not** deprecated)
- `src/attune/pattern_library.py::PatternLibrary.contribute_pattern`
  — the promote target
- `src/attune/redis_memory_patterns.py::PatternStagingMixin`
  (DEPRECATED) — the design we capture (stage/get/list/promote/reject),
  re-homed off Redis

---

## Problem

attune's `PatternLibrary` accepts contributed patterns directly via
`contribute_pattern(agent_id, pattern)` — there is no review step.
Auto-discovered patterns (from bug fixes, workflow runs, agent
contributions) land in the active library unfiltered, so:

1. Low-confidence or noisy patterns can pollute matching/recall.
2. There's no human checkpoint to curate what the system "learns."

The old `PatternStagingMixin` solved exactly this (stage → review →
promote/reject) but is coupled to the deprecated in-tree Redis
`RedisShortTermMemory` and is not wired to any live surface.

## Goal

A review queue, re-homed on the current backend stack:

- Discovered patterns are **staged** (persisted as `StagedPattern`)
  instead of contributed directly.
- A reviewer **sees the queue** (CLI + ops dashboard) with name,
  type, confidence, source agent, code preview.
- Reviewer **promotes** (→ `PatternLibrary.contribute_pattern`) or
  **rejects** (drops from the queue).

## Requirements

- **R1 — Stage.** A `stage_pattern(StagedPattern)` path that persists
  to attune's memory backend (file by default; AMS when configured),
  **not** the deprecated Redis mixin.
- **R2 — List/inspect.** `list_staged_patterns()` (filterable by
  type/agent/confidence) and `get_staged_pattern(id)`.
- **R3 — Promote.** `promote_pattern(id)` converts the `StagedPattern`
  to a `Pattern` and calls `PatternLibrary.contribute_pattern`, then
  removes it from the queue.
- **R4 — Reject.** `reject_pattern(id, reason)` drops it (with the
  reason recorded for audit).
- **R5 — CLI surface.** `attune patterns review` (list) /
  `attune patterns promote <id>` / `attune patterns reject <id>` —
  the human-in-the-loop entry point.
- **R6 — Dashboard surface.** A "Pattern review" panel in the ops
  dashboard: queue list + promote/reject actions (defense-in-depth
  via the existing `X-Attune-Client` token gate on the mutating
  routes).
- **R7 — Opt-in routing.** Discovery paths route to *staging* only
  when review is enabled (config flag); default behavior unchanged
  until a reviewer opts in (no surprise gating of existing
  auto-contribution).
- **R8 — Tested.** Mocked unit tests for stage/list/promote/reject +
  the CLI; one live round-trip (stage → promote → assert in library)
  auto-skipping without a backend where relevant.

## Non-goals

- No multi-agent *negotiation* over patterns (that's the
  `ConflictNegotiationMixin` surface — explicitly **retired**, not
  revived; Anthropic subagents/Managed-Agents cover real multi-agent
  coordination).
- No change to how patterns are *matched* at runtime — only how they
  *enter* the library.
- No Redis dependency — the queue persists on the same backend
  abstraction as the rest of attune memory (file/AMS).

## Done when

- A discovered pattern can be staged, reviewed in CLI + dashboard,
  and promoted into `PatternLibrary` or rejected.
- `PatternStagingMixin` (deprecated) has no remaining unique
  capability the queue doesn't cover → it can be retired with the
  rest of the coordination mixins.
- Tests green; the feature is opt-in and default-off.

## Phase 0 (verify before building)

Grep the live discovery/contribution paths
(`agent_monitoring.py`, `pattern_persistence.py`,
`core_modules/shared_library.py`, `core.py`) to confirm where
`contribute_pattern` is actually called, so R7's opt-in routing taps
the real seam rather than an assumed one. (One-hour check; mirrors
the "verify the seam before wiring" discipline.)
