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

## D2 — Phase-0 requirements and decisions APPROVED as drafted

**Date:** 2026-08-06 · **Status:** APPROVED (chair: Patrick, in
session, after reviewing both documents)

The chair approved `requirements.md` (Phase-0 premise probes P1–P3,
candidate requirements R1–R6, out-of-scope list, AC-0–AC-3, the
Phase-0 task list) and this decision log unchanged from the draft.
Effect: the premise probes are authorized to run; kernel code stays
gated behind AC-0's probe ruling and the formkit/infokit queue
(family R1/R2) shipping first. The requirements header now carries
the approved status.

## D3 — Phase-0 probe results (P1–P3, measured 2026-08-06)

**Date:** 2026-08-06 · **Status:** results recorded — AC-0 ruling
owed by the chair. Probe scripts + rendered receipts live in
[probes/](probes/); every number below was measured by running them
against the live 11.3.0 tree (`merge_patch` semantics from the
shipped chartkit implementation).

### P1 — capability (three real artifacts, authored both ways)

| Artifact | Nodes/edges | Mermaid | diagramkit spec |
|---|---|---|---|
| family queue DAG | 6 / 5 | 354 B (~88 tok) | 456 B (~114 tok) |
| PR #1963 pipeline | 6 / 7 | 376 B (~94 tok) | 469 B (~117 tok) |
| elicitation imports | 14 / 22 | 492 B (~123 tok) | 1,016 B (~254 tok) |

**Honest finding: mermaid is CHEAPER to author** — 1.2–2.1× —
because its edge syntax auto-creates nodes while the spec's
id-keyed map names every node once. The kernel's case does NOT
rest on initial authoring cost. It rests on the update axis (P3),
persistence, host-theme fidelity, and the seal.

### P3 — patch value (the axis mermaid lacks)

- Status flip (`formkit` → done): **34 B (~8 tok)** as an RFC 7386
  patch vs **349 B** mermaid full re-emission (no partial update
  exists) — a 10× advantage that grows with graph size.
- Topology change (add node + edge): **147 B** — node map merges,
  edge list replaces wholesale; the attribute-vs-topology split is
  legible in the patch itself.
- **Design finding (binding for any build): nodes MUST be an
  id-keyed map, not a chartkit-style array.** The same status flip
  costs **343 B** with array nodes (RFC 7386 replaces arrays
  wholesale) vs 34 B with the map — the map is what makes patches
  cheap. Edges stay an array (topology changes replace them
  together with a server-side re-layout, which is the correct
  coupling).

### P2 — layout (server-side, pure Python)

- Layout code: **1,569 bytes / 58 lines** of stdlib Python
  (longest-path layering + 4 barycenter sweeps + coordinate
  assignment) — a trivial server-side dependency, no vendored
  engine ([probes/probe_p2_layout.py](probes/probe_p2_layout.py)).
- Rendered receipts (committed):
  [6 nodes](probes/a-queue.svg) ·
  [6 nodes, pipeline](probes/b-pipeline.svg) ·
  [14 nodes](probes/c-imports.svg) ·
  [31 nodes](probes/d-large.svg) — SVGs 2.1–10.4 KB; judged
  readable at all four sizes in live review.
- **Finding: long-edge routing is mandatory, not polish.** A
  same-row edge spanning layers renders as a straight line THROUGH
  intervening node boxes, reading falsely as a chain (caught live
  on the 6-node queue). A 12-line bowed-route fix resolved it.
  At 31 nodes, congestion around high-fan-out nodes is visible but
  traceable; beyond ~40 nodes channel routing would be needed —
  consistent with R2's size expectations.

### Recommendation to the chair (AC-0)

The premise HOLDS with a **narrowed value claim**: diagramkit
should never be pitched as cheaper chart-authoring for one-shot
diagrams — mermaid wins that. It earns in on *living* diagrams:
status-bearing graphs a session updates in place (spec-task DAGs,
pipeline state), where the 10× patch advantage, session
persistence, and host theming apply. Recommend: proceed per plan
(build stays queued behind formkit/infokit), with R2 amended to
require id-keyed node maps and long-edge routing.
