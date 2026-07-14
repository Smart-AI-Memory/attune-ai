# Analysis-Workflow Output Widgets — decisions

## D1 — two widget families, not one (grounding overturned the kickoff)

**Date:** 2026-06-28 · **Status:** decided

The kickoff form picked 7 workflows expecting one uniform "findings
widget." Grepping each workflow's result construction (the
"spec-named scope drifts from code" discipline) showed five of them
(`code_review`, `bug_predict`*, `refactor_plan`, `dependency_check`,
`deep_review`) build **zero** `WorkflowReport`/`Finding` objects and
return markdown via `raw_output=True` or a text `feedback` field. Only
perf-audit (and the already-shipped security-audit / discovery-sweep)
carry structured `Finding`s.

So the program splits: **Family A** (structured dashboard, the shipped
pattern) and **Family B** (rich-markdown panel). Forcing a findings
dashboard onto a markdown workflow would be the exact fiction the
removing-dead-code / doc-fiction rules warn against. (*bug-predict's
`predictions` resolve to report findings *iff* its report has a
`FindingsSection` — FR-0 confirms before it's assigned to A.)

## D2 — shared renderer lands FIRST, by extraction from the shipped pair

**Date:** 2026-06-28 · **Status:** decided

#1148 (board) and #1149 (dashboard) each carry a private ~15-line copy
of the severity palette + `esc`/`location`. Rather than add a third
copy, FR-1 extracts `attune.workflows.findings_widget` and migrates both
onto it — a pure de-dup with no behaviour change — and every Family-A
rollout builds on it. This is the "generalize a working sibling" rule:
the primitive is lifted from two proven consumers, not designed up front.
Gated on #1148 + #1149 being on main (can't refactor in-flight files).

## D3 — extend existing tool responses; never add an MCP tool

**Date:** 2026-06-28 · **Status:** decided

Same as #1148/#1149: each workflow's existing MCP response gains a
`dashboard_html` (A) or `panel_html` (B) field. A new render tool would
push the live count 47→48 and ripple into the README / `features.ts` /
the `TestCapabilityCountsSync` guard. And every new `*_html` field must
ship with the exact-dict-test fix pattern (#1149 lesson: pop the field,
keep legacy keys exact) or it reddens every matrix lane.

## Open

- FR-0 per-workflow shape confirmation is the first execution task; its
  results may move bug-predict between families and may surface a
  workflow with metadata-bullet findings (a third, minor sub-shape).
- Whether Family B should also linkify `file:line` in the rendered
  markdown (nice-to-have) or just style headings/severity callouts.
