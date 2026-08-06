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

## D2 — D11 review-lane amendments (form-adopted, 2026-08-06)

**Date:** 2026-08-06 · **Status:** decided (Patrick, via the D11
disposition form — all four amendments selected) · **Provenance:**
Codex cross-review lane, thread
`review-review-wkf-d11-lane-20260806-0715`, ledger row in
`docs/specs/cross-review/receipts.md`. The lead verified each
Codex finding against the code before presenting (two confirmed,
one narrowed), and added a fourth Codex missed.

1. **F1 (Codex, high — confirmed):** R4 gained a reproducible
   counting method (canonical compact JSON bytes, tokens ≈
   bytes/4) and per-kernel numeric budgets. The numbers are
   lead-proposed and standing unless the chair adjusts; the
   task-4 harness re-baselines them with measured values.
2. **F2 (Codex, high — confirmed, narrowed):** the spec text
   defined no identity/persistence for formkit patching, but the
   mechanism already ships in `chart_widget_tool`; R1 now binds it
   normatively (`form_id`, canonical stored spec in session
   memory, RFC 7386 patch, legible degradation).
3. **F3 (Codex, medium — narrowed):** AC-3 now binds its first
   consumer (ops Health tab metric cards; `spec_progress`
   summaries named second) and is unsatisfiable without the R5
   ruling recorded in the owning feature's decisions.md.
4. **F4 (lead addition — Codex missed):** formkit's size budget
   ruled up front at ≤ 40,960 bytes minified (2× default; the
   construct family + postback won't fit chartkit's budget —
   chartkit is 11.3KB unminified for charts alone). Retired
   rather than kept as slack if formkit lands under the default.

**Counter-case recorded:** amending a lead-authored spec in
response to a lead-commissioned review, before the chair's full
read, risks laundering the review. Mitigation: every amendment is
traceable to a named finding with the lead's verification verdict
stated, the numeric values are marked lead-proposed (not
chair-ratified), and the chair's review of THIS amendment PR is
the ratification step.
