# Diagrams — structure is mermaid's job

chartkit draws *quantity* (nine chart types from a JSON spec — see
[Chart Widgets](chartkit.md)). For *structure* — modules, flows,
schemas, states — the ruled answer is **mermaid**: measured 1.2–2.1×
cheaper to author than a widget spec, and it renders natively on
GitHub (READMEs, PRs, issues), on this docs site, and in Claude
artifacts. No build, no supplement. (The ruling and the measured
probes live in `docs/specs/diagramkit/decisions.md`.)

Every example below is a live render — view this page's source to
copy the fence.

## Software structure — `flowchart`

Modules and their dependencies:

```mermaid
flowchart LR
    tool[chart_widget_tool] --> spec[chart_spec]
    comp[chart_components] --> spec
    server[mcp.server] --> tool
    kernel["chartkit kernel (sealed JS)"] -.reads dist.- tool
```

## Interactions — `sequenceDiagram`

Who calls whom, in order — protocols, API flows:

```mermaid
sequenceDiagram
    participant C as Claude
    participant T as chart_render_widget
    participant K as kernel
    C->>T: chart_id + spec (~100 tokens)
    T->>T: validate (field-level errors)
    T-->>C: {success, html}
    C->>K: html on the widget surface
    K-->>C: rendered SVG
    C->>T: chart_id + patch (tens of bytes)
```

## Databases — `erDiagram`

Entities, relationships, cardinality:

```mermaid
erDiagram
    FORM_TEMPLATE ||--o{ FORM_RESPONSE : "cast as"
    SESSION ||--o{ FORM_RESPONSE : collects
    FORM_TEMPLATE {
        string name PK
        json slots
    }
    FORM_RESPONSE {
        string response_id PK
        string template_id FK
    }
```

## Lifecycles — `stateDiagram-v2`

State machines — a spec's life, a job's phases:

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Approved: chair review
    Approved --> Probing: Phase-0 authorized
    Probing --> Building: premise holds
    Probing --> Closed: premise fails
    Building --> Shipped
    Closed --> Probing: reopen trigger fires
```

## More types

`classDiagram` (UML), `gantt` (schedules), `gitGraph` (branch
topology), `timeline`, C4 context diagrams, and network/cloud
`architecture` diagrams — see the
[mermaid documentation](https://mermaid.js.org/intro/) for the full
set. All render anywhere the four above do.

## When NOT mermaid

- **Quantitative shape** — trends, distributions, comparisons:
  that's [chartkit](chartkit.md); mermaid's chart types are
  rudimentary.
- **Diagrams a session updates in place** — a status DAG patched
  turn by turn. That niche was probed and closed 2026-08-06
  ("mermaid wins" — reopen on a second real occurrence; see the
  diagramkit spec).
- **Notation-exact standards** — symbol-true BPMN, vendor network
  stencils. Mermaid approximates; if exactness is ever required,
  that is an embed-a-specialized-renderer decision, not a mermaid
  fence.
