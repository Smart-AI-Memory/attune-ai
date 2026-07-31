# Outcome-first Attune UX — Roundtable Plan

**Thread:** `q-outcome-first-attune-ux-001`
**Date:** 2026-07-30
**Chair:** Patrick Roebuck
**Mode:** Planning only — no implementation authorized
**Promoted board item:** synthesis message `6`

## Question

Should attune-ai implement an outcome-first Build/Fix/Ship product
surface over its existing workflow and orchestration machinery?

The table was asked to critique the architecture, sequencing,
compatibility strategy, metrics, and artifact scope, favoring the
smallest user-visible vertical slice that would not create a parallel
framework.

## Round 1

| Seat | Position |
| --- | --- |
| Claude | Proceed with a thin explicit Fix slice; use an XML task for the first executable unit |
| Codex | Proceed Fix-first; use a narrow vision Spec with a derived XML task |
| Antigravity | Absent — tenant policy denied the repository exposure required by its CLI invocation |

The two available seats converged, so the moderator halted after one
round.

## Ruling-level synthesis

Implement the vision only as a thin outcome facade over existing public
interfaces. It must not introduce a parallel planner, registry,
executor, evidence store, orchestration layer, telemetry system,
execution lifecycle, or source of truth.

Prove the product first with an explicit:

```text
attune fix "<request>"
```

Do not begin with natural-language intent inference or expose Build and
Ship as implemented concepts.

The outcome contract is a boundary DTO:

- goal;
- done conditions;
- constraints;
- verification probes.

The execution receipt is separate evidence:

- changes made;
- probes executed and their provenance;
- results;
- remaining uncertainty;
- safest next action.

A successful workflow exit is never sufficient proof that a done
condition was satisfied.

Preserve `attune workflow run` and specialist commands. Product success
means users do not need to understand Attune's internal machinery; it
does not mean expert access disappears.

Require confirmation for unresolved ambiguity, destructive behavior,
external side effects, material paid execution, or material scope
changes. Routing must abstain safely: a false confident route is worse
than abstention.

`--explain` and any later `--trace` surface must project existing
execution data rather than create a second state or telemetry system.

## Artifact strategy

Use a deliberately narrow Spec to record:

- hypotheses;
- non-goals;
- public compatibility constraints;
- expansion gates;
- the counter-case.

That Spec does not authorize broad Build/Fix/Ship implementation. Its
only executable unit should be a cold-handoff-capable XML task for the
Fix proof slice.

This resolves the seats' artifact-tier split: Codex's Spec contains the
cross-cutting product decisions, while Claude's XML task bounds the
initial implementation.

## Phased plan

### Phase 0 — Architecture and characterization proof

- Inventory the existing CLI router, workflow registry,
  diagnosis/fix/test/review seams, result models, help projections, and
  telemetry.
- Map every proposed concept to an existing interface or remove it.
- Pin current natural-language routing and `attune workflow run`
  behavior with characterization cases.
- Select one repeatable canonical Fix scenario.

**Acceptance:** The scenario can be traced through existing interfaces
without requiring a parallel registry, planner, executor, evidence
store, lifecycle, or source of truth.

### Phase 1 — Dry explicit Fix contract

- Define the smallest internal boundary DTO for the goal, done
  conditions, constraints, and verification probes.
- Design `attune fix "<request>" --explain` to validate and preview the
  contract and selected existing workflow without execution.
- Keep the preview non-blocking by default.
- Require confirmation for ambiguity, destructive action, external
  side effects, material cost, or material scope changes.

**Acceptance:** Representative, ambiguous, and risky inputs produce
truthful previews or abstention. No universal public outcome schema is
promised.

### Phase 2 — Executable Fix proof

- Translate the boundary DTO once into existing workflow inputs.
- Execute one representative Fix through existing machinery.
- Render one unified receipt using real evidence provenance and
  independently evaluated probes.

**Acceptance:** An initially failing probe passes through a real
CLI/subprocess/file boundary. Changed artifacts, failed or skipped
probes, uncertainty, and the next action are truthfully reported.
Workflow exit alone never marks success.

### Phase 3 — Robustness, compatibility, and measurement

- Cover malformed, ambiguous, no-change, failed-verification,
  partial-success, and abstention paths.
- Preserve documented `attune workflow run` behavior.
- Add projected help/docs drift guards and real-boundary receipt
  coverage.
- Do not persist sensitive prompt text by default.

Measure:

- contract-edit rate;
- route-correction rate;
- false-confident-route rate;
- abstention rate;
- evidence-valid receipt completeness;
- verification-failure honesty;
- compatibility regressions;
- time and cost to verified outcome;
- abandonment before a useful result;
- completion without requiring knowledge of internal machinery.

### Phase 4 — Natural-language Fix routing gate

- Build a labeled evaluation corpus from real Fix requests.
- Set routing thresholds from measured data.
- Weight false confident routes more heavily than abstention.

**Acceptance:** Thresholds meet chair-ratified targets, and explicit Fix
remains the safe fallback.

### Phase 5 — Ship discovery

- Inventory Git, packaging, CI, publishing, approval, rollback, and
  other external boundaries.
- Test whether the Fix envelope and receipt semantics survive those
  side effects without distortion.
- Promote Ship only if semantic reuse is demonstrated.
- If reuse fails, design a separate adapter rather than force a false
  universal model.

### Phase 6 — Build discovery

- Begin only after users demonstrate understanding and trust in the
  outcome surface.
- Require at least two intents to demonstrate genuinely shared
  semantics.
- Keep Build outside the initial implementation scope.

## Expansion gates

- No Build or Ship public surface before Fix has a real-boundary
  receipt and measured routing results.
- No shared public outcome abstraction before at least two intents
  demonstrate identical semantics.
- No `--trace` until the required data already exists and can be
  projected.
- No new execution lifecycle or source of truth.
- This plan grants no implementation authority.

## Counter-case

Optimizing the contract around Fix may make Ship's side effects and
Build's ambiguity awkward. Keep the DTO internal initially and require
semantic-reuse evidence before promoting it into a stable public
abstraction.

## Open chair decision

Choose the canonical repeatable Fix scenario used as the live-boundary
proof. It should be important enough to exercise a code change, testing,
evidence, and uncertainty, but narrow and deterministic enough for
repeated evaluation.
