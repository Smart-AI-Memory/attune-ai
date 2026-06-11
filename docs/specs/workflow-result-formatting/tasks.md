# Tasks: Workflow result formatting

**Status:** partial (2026-06-11) — T1 (the `WorkflowReport` / Section
data model, #649), T2 (the markdown renderer
`attune.voice.report_renderer` — `render()` + crash-visible
`render_safe()`, all 4 test layers, 98% branch, #741), T3 (voice
wiring + safety net + `show_cost_metrics`/`resolve_show_cost()`),
T4 (CLI terminal rendering), T7 (release-prep
migration — the motivating case), and T8 (adapter-level migration of
all 15 SDK-native workflows) shipped; T5/T6 pending.

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

## T3 — Voice wiring + safety net — DONE

- `_extract_from_workflow_result`: add the `_type=="WorkflowReport"`
  branch before the `str()` fallback → reconstruct + render; turn the
  bare `str()` branch into the safety-net pretty-printer + "renderer not
  migrated" banner. Add `resolve_show_cost()` + `config.show_cost_metrics`.
  (Design D2/D3.)
- One PR. Shipped: `WorkflowReport.is_report_dict` branch renders via
  `render_safe(disclosure="summary", show_cost=resolve_show_cost())`;
  plain-`str` final_output (SDK markdown) passes through unchanged; the
  bespoke-object branch emits the §6 banner + field pretty-print;
  rendered branches are exempt from the sparse summary fallback.
  `resolve_show_cost()` lives in `attune.config` (env var
  `ATTUNE_SHOW_COST_METRICS` also parsed as bool by `from_env`).

## T4 — CLI — DONE

- `cli_commands/workflow_commands.py:_print_workflow_result`: render
  `disclosure="summary"` default, `"full"` on `--verbose`; pipe markdown
  through a minimally-themed `rich.markdown.Markdown`; `<details>` → a
  "(run with --verbose to expand: …)" closing line. (Proposal §3,
  Surface map.)
- Shipped: `format_output(disclosure=...)` threads to the renderer;
  rich markdown only for report-carrying results AND only on a TTY
  (legacy results + piped output keep plain text). The CLI converts
  `<details>` pre-render because `rich.markdown` renders straight
  through HTML tags. Score-line + voice-next-steps duplication
  resolved: the wrapper suppresses both for rendered reports (the
  report's `**Score:**` and `NextStepsSection` own them).

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

## T7 — Migrate release-prep (motivating case) — DONE

- Add `_to_workflow_report(ReleaseReadinessReport)` (proposal's worked
  example); `execute()` sets `final_output = report.to_dict()`. Update
  the T0 will-change tests in the same commit. Verify the success-
  criteria example renders (proposal §"Illustrative target").
- Shipped: converter in `release_prep_team.py`; `execute()` returns a
  real `WorkflowResult` (it previously returned the bespoke dataclass
  directly — bypassing even the T3 safety net) and no longer prints
  `format_console_output()`. Note: the MCP `release_prep` handler uses
  the SDK-native `ReleasePreparationWorkflow`, a separate surface —
  its migration rides T8+ (adapter-level findings → report).

## T8+ — Migrate remaining workflows (D5 rank) — DONE

- ~~code-review → dependency-check → bug-predict → test-gen →
  document-manager → refactor-plan → perf-audit → doc-audit. One small
  PR each (converter + repr-leak drift-guard test). Safety-net banner
  covers the not-yet-migrated tail.~~
- Shipped 2026-06-11 as ONE adapter-level PR, not 8 per-workflow
  converters: every SDK-native workflow routes through
  `AgentSDKResultAdapter.from_agent_output`, so the converter lives
  there — when findings parse (text categories or structured output),
  `final_output` becomes `WorkflowReport.to_dict()` (dict items →
  `FindingsSection`, string bullets → `ListSection`, suggestions →
  `NextStepsSection`, score from `summary.score` or a text regex,
  cost/duration in report metadata where the renderer's `show_cost`
  gate reads them). All 15 SDK workflows pass `report_title`;
  findings-free prose still passes through as plain markdown. This
  also fixes the cost-line-on-subscription nit (`report_rendered`
  now True → the wrapper's `$0.0000` line is suppressed; design D3).
  Out of scope: document-manager (legacy multi-stage `BaseWorkflow`,
  not adapter-routed — covered by the T3 safety net; migrate only if
  its output surface ever matters).

## Notes

- Use Opus for T1–T3 (data-model + renderer judgment); T4–T8 are more
  mechanical.
- Each PR: full `coverage run --branch`, watch the Windows lane (the
  unified-memory xdist flake is unrelated but the matrix is the gate).
