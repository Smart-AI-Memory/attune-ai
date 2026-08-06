# diagramkit — decisions

## D1 — Direction ruled: Phase-0 spec, one kernel, one vocabulary, layout server-side

**Date:** 2026-08-06 · **Status:** RULED (Patrick, via pushback
form; validated receipt `resp-20260806-054445`)

Patrick's opening position was to expand the widgets across three
diagram families at once (classic graph symbols, software graphs,
business process graphs). The pushback construct presented the
counter-position and he picked it:

- **One kernel candidate (diagramkit), one vocabulary first** —
  software graphs (dependency DAGs, pipeline flows, spec-task
  graphs), because they are what attune sessions actually display.
  Classic-flowchart and BPMN vocabularies wait for demonstrated
  recurrence (promote-on-repeat, same rule as V7 templates).
- **Layout is server-side, permanently** — dagre-class auto-layout
  cannot fit the family's 20,480-byte sealed-kernel ceiling; Python
  computes positions (the `expand_component` precedent), the kernel
  only draws.
- **Phase-0 premise probe before any build** — the kernel must beat
  mermaid-on-surface on the one axis mermaid lacks (patch-updatable,
  session-persistent diagrams) or it does not earn in; "mermaid
  wins" is a valid closing outcome.
- **Sequenced after formkit and infokit**, whose chair-ratified
  budgets hold the front of the family queue.

Rejected alternatives, recorded per the pushback shape: "expand now
across all three families" (layout won't seal; three vocabularies
inverts earn-your-way-in; jumps the ruled queue) and "no kernel —
mermaid only" (loses patch updates, persistence, and the seal
without testing whether those matter — that test IS Phase-0).
