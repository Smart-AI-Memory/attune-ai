# Outcome-first Attune UX — Roundtable Plan

**Thread:** `q-outcome-first-attune-ux-001`
**Date:** 2026-07-30
**Chair:** Patrick Roebuck
**Mode:** Planning only — no implementation authorized
**Promoted board item:** synthesis message `6`

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

## Open chair decision

Choose the canonical repeatable Fix scenario used as the live-boundary
proof. It should be important enough to exercise a code change, testing,
evidence, and uncertainty, but narrow and deterministic enough for
repeated evaluation.

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/q-outcome-first-attune-ux-001.md` and is
not distributed with the repository.*
