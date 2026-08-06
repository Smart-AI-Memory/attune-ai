# diagramkit — Phase-0 requirements: node-and-edge diagrams as a display member

**Status:** CLOSED — mermaid wins (chair: Patrick, 2026-08-06 — D4
in [decisions.md](decisions.md), ruling on the D3 probe results).
No kernel will be built from this spec as it stands. Reopen trigger:
a SECOND real session needing in-place diagram updates
(promote-on-repeat); any future build inherits D3's binding
findings (id-keyed node maps, mandatory long-edge routing).
**Direction ruled:** 2026-08-06, Patrick, via pushback form (receipt
`resp-20260806-054445`): one diagram kernel, one vocabulary first,
layout server-side — over "expand now across classic + software +
BPMN" (his opening position) and "no kernel, use mermaid".
**Parent pattern:** [widget-kernel-family](../widget-kernel-family/)
— sealed kernel + declarative spec + RFC 7386 patch; chartkit is the
worked example.
**Sequencing:** AFTER formkit (family R1) and infokit (family R2),
whose budgets are already chair-ratified. This spec may *design* in
parallel; it builds only when the queue ahead of it has shipped.

## The idea

Extend the display grammar from quantitative shape (chartkit) to
*structural* shape: dependency DAGs, pipeline flows, spec-task
graphs — as a small declarative spec the model authors (~100 tokens),
rendered by a sealed kernel, updated by merge patch ("mark the deploy
step failed" should cost tens of bytes, not a re-emitted diagram).

## The constraint that shapes everything

Auto-layout is where diagram complexity lives — layered placement,
edge routing, crossing minimization. Dagre-class engines are tens to
hundreds of KB; the family's per-kernel ceiling is 20,480 bytes.
Therefore: **layout is computed server-side in Python** (the
`expand_component` precedent — pure-Python Sugiyama is small), the
spec reaching the kernel carries *positioned* nodes and edges, and
the kernel only draws. The kernel never lays out.

## Phase-0 premise probe (before any build)

The kernel earns existence only if it beats the zero-build
alternative. Mermaid already renders natively on several surfaces
and costs the model a comparable token count to author.

- **P1 — capability probe.** Take three real session artifacts (a
  spec-task DAG, a pipeline flow with statuses, a module dependency
  graph). Author each twice: as mermaid text and as a candidate
  diagramkit spec. Compare measured token cost, theming fidelity
  (light/dark via host CSS variables), and — the differentiator —
  update-in-place: change one node's status in both. If mermaid's
  full re-emission is not materially worse in practice, the kernel
  does not earn in; record that and stop.
- **P2 — layout probe.** Lay out the same three graphs with a
  pure-Python layered layout on realistic sizes (5–40 nodes).
  Receipt: rendered SVG that a human judges readable, plus the
  measured size of the layout code — it must be a reasonable
  dependency, not a vendored engine.
- **P3 — patch-value probe.** Demonstrate the RFC 7386 patch on a
  positioned spec: a status flip that does NOT move nodes is a
  tens-of-bytes patch; a topology change re-runs layout server-side
  and replaces `nodes`/`edges` wholesale. Confirm the split is
  legible in the tool's response messages.

## Requirements (candidates — confirmed only after Phase-0)

- **R1 — one kernel, sealed.** `src/attune/widgets/diagramkit/`
  under the family rules: imports nothing outside itself, nothing
  imports its internals, built artifact ≤ 20,480 bytes, enforced by
  `scripts/check_widget_kernel_boundaries.py`.
- **R2 — one vocabulary first: software graphs.** Nodes (box,
  rounded, cylinder/store, diamond/decision), directed edges with
  optional labels, node status coloring (the `done` / `in_flight` /
  `blocked` vocabulary the grammar already uses). Closest to what
  attune sessions actually show. Classic flowchart symbols and BPMN
  are OUT until their fork class recurs (the promote-on-repeat
  discipline, elicitation V7's R5).
- **R3 — server-side layout.** `expand_diagram(...)`-style Python
  entry point computes positions; the kernel-facing spec is
  positioned. The model may author the *unpositioned* form
  (nodes + edges + kinds) and never coordinates.
- **R4 — patch semantics per the family.** Stable `diagram_id`,
  spec persisted in session memory, RFC 7386 patch for
  attribute-level updates; topology changes re-layout server-side.
  Persistence degrades legibly (chartkit's D5 wording).
- **R5 — errors field-level at author time.** Unknown node kind,
  edge referencing a missing node id, cycle where a DAG is required
  — each a named-field problem the model can self-correct.
- **R6 — one MCP tool.** `diagram_render_widget`, returning
  `{success, html, ...}` for `show_widget`; tool-count guard and
  README list updated per the family checklist.

## Out of scope

- Auto-layout inside the kernel — permanently (the ceiling rules
  it out; that is the point of R3).
- BPMN and classic-flowchart vocabularies — until recurrence is
  demonstrated (rule of three / promote-on-repeat).
- Interactive diagram editing — display member; it reports.
- Combo/layered compositions — same rationale as chartkit's
  type-expansion exclusion.

## Acceptance criteria — receipts, not registration

- **AC-0 — premise receipt.** P1–P3 results recorded in
  decisions.md with measured numbers BEFORE any kernel code; a
  "mermaid wins" outcome closes the spec as a valid result.
- **AC-1 — live render receipt.** A real session artifact rendered
  through the tool on the live widget surface (chartkit's dogfood
  pattern: rendered SVG screenshot + measured spec bytes).
- **AC-2 — patch receipt.** A status flip applied as a measured
  tens-of-bytes patch against a stored spec.
- **AC-3 — seal receipt.** Boundary script green on the new kernel;
  built size recorded.

## Tasks (for review — Phase-0 only)

1. P1 capability probe (three artifacts, both authorings, measured).
2. P2 layout probe (pure-Python layered layout, rendered receipts).
3. P3 patch-value probe (attribute patch vs topology re-layout).
4. Decisions entry with numbers; chair rules build / no-build.
