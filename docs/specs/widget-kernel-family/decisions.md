# Widget Kernel Family — decisions

Decision log for [requirements.md](requirements.md). Append-only;
newest at the bottom.

## D1 — Intake rulings (form-collected, 2026-08-05)

**Date:** 2026-08-05 · **Status:** decided (Patrick, via live
elicitation forms) · receipts named per fork.

Four design forks settled through the elicitation grammar before
drafting (spec-intake form `resp-20260805-131112`; pushback form
`resp-20260805-131610`; session contract `resp-20260805-130002`
supplied outcome/done-when/effort cap):

1. **Mechanism = the chartkit pattern generalized** — sealed
   kernel per widget type, model emits spec/patch. (Agent
   recommendation, taken.)
2. **Latency receipt = both** — model-authored tokens per
   render/update as the GATE, wall-clock time-to-first-render
   informational only.
3. **Infographic v1 = tiles only, board phase-gated** — Patrick
   initially picked "both presets"; the agent pushed back
   (mechanism-without-seam risk: the triage board's consumer flow
   is an unratified draft in `discovery-sweep-rich-surface`) and
   Patrick **switched** to the alternative. The board lands as the
   kernel's first preset amendment when its flow ratifies.
4. **Spec home = this umbrella spec** (`widget-kernel-family`) —
   owns pattern, seal rules, latency budgets; feature specs get
   cross-links (R5 boundary: feature-behavior rulings stay in the
   feature's own decisions.md).

**Honesty clause carried into R4:** the spec claims L1 (authored
tokens), not L2 (zero widget bytes through context) — the
`show_widget` re-emission residual is named in requirements with
its eliminator (elicitation V6 MCP Apps adapter) left sequenced in
that spec.
