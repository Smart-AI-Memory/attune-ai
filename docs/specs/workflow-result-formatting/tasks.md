# Tasks: Workflow result formatting

**Status:** partial (2026-06-09) — T1 (the `WorkflowReport` / Section
data model in `src/attune/workflows/output.py`) shipped in #649 and is
in use (e.g. `discovery_sweep`); remaining tasks pending.

> Bounded PRs; see [design.md](design.md) for the decisions each task
> implements.

## T0 — Test-surface audit (no code)

- `grep -rn 'str(.*final_output)\|formatted_report\|ReleaseReadinessReport('
  tests/`; classify the 26 hits as keep (dataclass unit tests) vs
  will-change (assert on repr/`str()` output). Record the will-change
  list here before T1. (Design D4.)

## T1 — Data model (`attune.workflows.output`)

- Add `Section` ABC + `CalloutSection`, `ProseSection`, `TableSection`,
  `ListSection`, `FindingsSection`, `NextStepsSection`, `NextAction`,
  each with `tier`. (Proposal §1.)
- `WorkflowReport.sections: list[Section]`; add `.findings` property,
  `.from_findings()`, `to_dict()` / `from_dict()` with `_type` +
  per-section `kind` discriminators. (Design D2.)
- **Delete** the unwired old path: `ReportSection`,
  `WorkflowReport.render()`/`_render_rich`/`_render_plain`,
  `FindingsTable`, `MetricsPanel`, `format_workflow_result()`. Drop the
  `rich` import guard from output.py.
- Tests: round-trip `to_dict()`/`from_dict()` identity; `.findings`
  property; `.from_findings()`; drift-guard that `WorkflowReport` has no
  `render` attribute.
- One PR. No consumers to migrate (Findings: unwired).

## T2 — Renderer (`attune.voice.report_renderer`)

- `render(report, *, disclosure="summary", show_cost=False) -> str`
  (markdown), `isinstance`-dispatch per section kind; `<details>` wrap
  for `detail`-tier in summary mode; `NextStepsSection` always last,
  omitted when empty; renderer-crash → error banner + safety-net.
  (Proposal §3/§5/§6.)
- Author all 4 test layers (proposal §"Test strategy"): repr-leak drift
  guard, tier-classification guard, structural renderer assertions,
  renderer-crash visibility.
- One PR.

## T3 — Voice wiring + safety net

- `_extract_from_workflow_result`: add the `_type=="WorkflowReport"`
  branch before the `str()` fallback → reconstruct + render; turn the
  bare `str()` branch into the safety-net pretty-printer + "renderer not
  migrated" banner. Add `resolve_show_cost()` + `config.show_cost_metrics`.
  (Design D2/D3.)
- One PR.

## T4 — CLI

- `cli_commands/workflow_commands.py:_print_workflow_result`: render
  `disclosure="summary"` default, `"full"` on `--verbose`; pipe markdown
  through a minimally-themed `rich.markdown.Markdown`; `<details>` → a
  "(run with --verbose to expand: …)" closing line. (Proposal §3,
  Surface map.)

## T5 — MCP

- `mcp/server.py:format_mcp_response`: return the summary markdown
  verbatim as human content; `WorkflowReport.to_dict()` JSON travels
  alongside. (Surface map.)

## T6 — Dashboard panel

- `/runs/<id>` API exposes the `WorkflowReport` JSON; `run_view.html`
  adds a structured panel above the terminal stream that parses summary
  markdown → HTML (`<details>` native collapsibles); terminal pane
  becomes a collapsible process log post-completion. `NextAction.command`
  → "Run" button (reuse runner infra); `.file` → link. (Surface map,
  proposal §3.) Largest task; may split.

## T7 — Migrate release-prep (motivating case)

- Add `_to_workflow_report(ReleaseReadinessReport)` (proposal's worked
  example); `execute()` sets `final_output = report.to_dict()`. Update
  the T0 will-change tests in the same commit. Verify the success-
  criteria example renders (proposal §"Illustrative target").

## T8+ — Migrate remaining workflows (D5 rank)

- code-review → dependency-check → bug-predict → test-gen →
  document-manager → refactor-plan → perf-audit → doc-audit. One small
  PR each (converter + repr-leak drift-guard test). Safety-net banner
  covers the not-yet-migrated tail.

## Notes

- Use Opus for T1–T3 (data-model + renderer judgment); T4–T8 are more
  mechanical.
- Each PR: full `coverage run --branch`, watch the Windows lane (the
  unified-memory xdist flake is unrelated but the matrix is the gate).
