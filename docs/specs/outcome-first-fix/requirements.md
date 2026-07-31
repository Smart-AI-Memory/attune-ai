# Outcome-First Fix — Requirements

**Status:** draft (2026-07-30) — deliberately narrow spec authorized
by the roundtable ruling. Grants NO Build/Fix/Ship implementation
authority. Its only executable unit is Task 0 in
[tasks.md](tasks.md), and executing it still requires a chair go.
**Slug:** `outcome-first-fix`
**Provenance:** roundtable thread `q-outcome-first-attune-ux-001`
([docs/reports/roundtable/q-outcome-first-attune-ux-001.md](../../reports/roundtable/q-outcome-first-attune-ux-001.md)),
chair Patrick Roebuck, 2026-07-30, promoted synthesis message 6.
Two seats (Claude, Codex) converged in one round; Antigravity
absent (tenant policy).

## Hypotheses

- **H1 — facade sufficiency.** An explicit outcome facade,
  `attune fix "<request>"`, layered over existing public
  interfaces can deliver a verified fix without the user needing
  to understand Attune's internal machinery.
- **H2 — receipt honesty.** A boundary DTO (goal, done
  conditions, constraints, verification probes) plus a separate
  execution receipt (changes made, probes executed with
  provenance, results, remaining uncertainty, safest next action)
  makes success reporting truthful. A successful workflow exit is
  never sufficient proof that a done condition was satisfied.
  This is a measured failure mode, not a hypothetical: the
  lessons corpus records `attune workflow run` on mismatched
  input exiting 0 with a traceback that downstream surfaces
  classified as success.
- **H3 — no parallel framework.** The facade requires no new
  planner, registry, executor, evidence store, orchestration
  layer, telemetry system, execution lifecycle, or source of
  truth. Every concept maps to an existing interface or is
  removed from the design.

## Non-goals

- No Build or Ship public surface (Phases 5–6 of the ruling,
  gated on Fix evidence).
- No natural-language intent inference at launch. Explicit
  `attune fix "<request>"` only; NL routing is gated behind the
  Phase 4 labeled corpus and chair-ratified thresholds, with
  false confident routes weighted more heavily than abstention.
- No public universal outcome schema. The DTO stays internal
  until at least two intents demonstrate identical semantics.
- No new execution state or telemetry. `--explain` (and any
  later `--trace`) project existing execution data only.
- No change to `attune workflow run` or specialist commands.
  Product success means users do not NEED the internal
  machinery, not that expert access disappears.

## Canonical Fix scenario (chair-decided 2026-07-30)

**Hardened failing-test** (decisions.md D1): a deterministic
fixture package with one seeded failing test and green sibling
tests. Done conditions are plural and distinct from the fix
target:

1. the target test passes;
2. the full fixture suite is green;
3. the diff is confined to the fixture's source code — the fix
   changes the code, never the test.

Determinism keeps repeated evaluation cheap; the plural probes
keep the goal and its verification separate artifacts, so the
slice genuinely exercises H2's DTO separation instead of letting
the fix target and the probe collapse into one.

## Public compatibility constraints

- The `attune fix` top-level namespace is free — verified
  2026-07-30 against `src/attune/cli_minimal.py` and
  `src/attune/cli_commands/` (no existing `fix` subcommand).
- Adjacency: the plugin-level `/fix-test` skill lives on the
  Claude Code surface, not the CLI. Neither replaces the other;
  any user-facing docs for `attune fix` must state the
  relationship explicitly so the surfaces don't blur.
- Documented `attune workflow run` behavior is preserved and
  pinned by characterization tests BEFORE any facade work
  (Task 0), including the current exit-code-vs-
  `WorkflowResult.success` divergence, so later phases change it
  deliberately or not at all.
- Help and docs pages for this surface are projector-owned like
  every other feature page — edit the master, re-project.
- Sensitive prompt text is not persisted by default.

## Expansion gates (from the ruling)

- No Build or Ship public surface before Fix has a
  real-boundary receipt and measured routing results.
- No shared public outcome abstraction before at least two
  intents demonstrate identical semantics.
- No `--trace` until the required data already exists and can
  be projected.
- No new execution lifecycle or source of truth.
- This spec grants no implementation authority; each phase's
  executable task is authored only after the prior phase's
  acceptance passes and the chair says go.

## Metrics

The ruling's full Phase 3 list stands: contract-edit rate,
route-correction rate, false-confident-route rate, abstention
rate, evidence-valid receipt completeness, verification-failure
honesty, compatibility regressions, time and cost to verified
outcome, abandonment before a useful result, completion without
requiring knowledge of internal machinery.

Initial measurement set (PROPOSED — decisions.md D3): start with
false-confident-route rate, evidence-valid receipt completeness,
verification-failure honesty, and time-to-verified-outcome;
defer the routing-behavior metrics to Phase 4, where the labeled
corpus they require exists anyway.

## Counter-case

Optimizing the contract around Fix may make Ship's side effects
and Build's ambiguity awkward. The DTO therefore stays internal
initially, and promotion into a stable public abstraction
requires semantic-reuse evidence across at least two intents. If
Ship's semantics do not survive reuse testing, a separate
adapter is the honest design — not a forced universal model.
