# Subsystem Value Gate — Requirements

**Status:** living (2026-07-14) — reusable subsystem gate procedure, proven twice (socratic #1060, memorygraph #1256); approved 2026-06-11 · **Owner:** Patrick + agent
**Born:** discipline-review chat, 2026-06-11 (improvement #1 of 6).

## Problem

The strongest recurring waste pattern in the repo's own lessons:
infrastructure built well, validated against user value only AFTER
the build. The receipts:

- BEP middleware: 93 tests, clean protocol, zero working skills,
  zero CLI integration.
- `hot_reload/`: 1,038 production lines + 1,409 test lines, zero
  inbound imports outside its own package.
- Semantic cache: 420MB dependency, 0.2% measured hit rate against
  a 70% claim.
- `socratic/embeddings/`: 240 lines of passing tests, zero imports
  from any workflow/CLI/MCP path.

The corrective lessons exist ("validate infrastructure against user
value before extending", "passing tests don't prove integration",
"a spec's measurable premise should be probed in Phase 0") — but
they fire REACTIVELY, during audits, after the build cost is sunk.
The successes prove the gate works when applied: Phase 0 measurement
killed the Agent Surface Rebalance spec for $8.78; the
fastembed decision matrix routed cleanly. The gap is that nothing
makes the gate fire BEFORE a subsystem is born.

## Outcome

New subsystems pay a cheap value-validation toll before significant
build investment, and existing zero-consumer code is surfaced on a
schedule instead of by accident.

## Scope

- **Forward gate:** a lightweight Phase-0 requirement for new
  SUBSYSTEMS (new package/top-level module/new infrastructure layer
  — not features inside existing surfaces, not bug fixes).
- **Backward sweep:** a recurring inbound-import / dead-surface audit
  that proposes deletions or integration work.

## Requirements

- **R1 — Define "subsystem" precisely.** The gate must not tax
  ordinary feature work. Proposed trigger: new top-level directory
  under `src/attune/`, new sibling package, or new always-on
  background machinery (hooks, daemons, caches). The definition is
  written into the /spec skill guidance so it fires at spec-authoring
  time, where it's cheapest.
- **R2 — The toll is small and concrete.** One Phase-0 artifact
  answering: (a) who is the consumer (a named surface: CLI command,
  skill, workflow, dashboard panel — "future use" doesn't count);
  (b) what measurable claim justifies it; (c) the hand-crafted
  prototype or measurement that tests the claim (the
  "hand-crafted summary prototype is the fastest ceiling
  measurement" lesson is the template). Target cost: an hour, not
  a day.
- **R3 — Quarterly inbound-import sweep.** A script (single-file,
  `scripts/` convention, wiring-audit pattern) that for each
  `src/attune/` top-level module reports inbound imports from
  outside itself + the surfaces that reach it (CLI/MCP/skill/
  dashboard). Zero-consumer modules land in a dated report under
  `docs/specs/subsystem-value-gate/` with a disposition column
  (integrate / deprecate / delete) — the spec-backlog disposition
  matrix pattern, applied to code.
- **R4 — Deletion is the default disposition** for a module with
  zero consumers and no named adopter after one sweep cycle. Git
  history is the archive (established rule). PEP 562 shims where a
  public surface existed.
- **R5 — The sweep is advisory, not a CI gate.** Per the
  enforcement-vs-documentation boundary: zero-consumer detection
  needs judgment (entry points, reflection, sibling repos resolve
  dynamically — the `resolve_backend()` lesson), so a human reads
  the report; CI does not block on it.

## Non-goals (this spec)

- Retroactively auditing everything at once (the sweep is
  incremental; the first run will be the worst).
- Gating experimentation — scratch branches and prototypes are
  exempt; the gate applies at "merge a new subsystem to main".
- Test-coverage policy (owned by test-quality-program).

## Done when

- The subsystem definition + Phase-0 toll is in the /spec guidance
  and `decision-routine.md` cross-references it.
- The sweep script exists with one executed report, dispositions
  recorded, and at least one disposition acted on (an integration
  or a deletion PR).
- A calendar/cron reminder exists so the next sweep doesn't depend
  on memory.
