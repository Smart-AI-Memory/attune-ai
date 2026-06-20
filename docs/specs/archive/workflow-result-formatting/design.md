# Design: Workflow result formatting

> **Status:** plan (2026-06-06) — resolves the 5 items the
> [proposal](proposal.md) "Next step" named, plus the 3 plan questions
> (see Resolved). Grounded in the current code state (see Findings).
> Ready for implementation on merge.

The [proposal](proposal.md) is approved and settled the *primitives*
(reuse `WorkflowReport`, grow `sections: list[Section]` with tiers, one
markdown renderer, subscription-aware cost, visible renderer crashes,
`NextStepsSection`). This plan resolves the deferred implementation
decisions and is grounded in what the code actually looks like today.

## Findings (current code state, 2026-06-06)

- **`src/attune/workflows/output.py`** already defines `WorkflowReport`,
  `ReportSection(title, content: Any, collapsed, style)`, `Finding`,
  `FindingsTable`, `MetricsPanel`, `format_workflow_result()`, and a
  **Rich-object** `WorkflowReport.render()` (`_render_rich`/
  `_render_plain`). This is the OLD model — flat `content: Any`
  sections, no tiers, rich-renderable output (not markdown).
- **It is effectively unwired.** The only `src/` reference to these
  symbols is a *comment* in `workflows/discovery_sweep/workflow.py`.
  No workflow's `execute()` returns a `WorkflowReport`; no surface
  imports the renderer. → **Replacing the model carries near-zero
  consumer-migration risk** (the proposal's "reconcile output.py vs
  voice" worry is smaller than feared).
- **Voice path** `voice/formatter.py:_extract_from_workflow_result`
  returns `(success, score, report_text, cost_line, error_msg)`.
  Today: `dict` → `final_output.get("formatted_report")`; else →
  `str(final_output)` (the repr leak); plus a summary+`metadata.findings`
  fallback. The renderer hooks in here, before the `str()` branch.
- **`final_output` crosses serialization boundaries** (SDK session →
  `WorkflowResult` → CLI/MCP/dashboard JSON), so the report must
  survive a `dict` round-trip — detection can't rely on `isinstance`
  alone.
- **Test churn surface:** 26 `tests/` references to
  `ReleaseReadinessReport` / `QualityGate(` — mostly unit tests of the
  dataclasses themselves (legit, stay); the at-risk ones are any
  asserting on `str(final_output)` / repr output. Audit in T0.

## D1 — Module layout (data vs rendering split)

**Decision:** data lives in `attune.workflows.output`; rendering lives
in a new `attune.voice.report_renderer`. Workflows own *content
classification* (which section, which tier); they never format.

`attune.workflows.output` (grow + replace the old model):

- Add `Section` ABC + subclasses `CalloutSection`, `ProseSection`,
  `TableSection`, `ListSection`, `FindingsSection`, `NextStepsSection`,
  plus `NextAction`, each carrying `tier: Literal["essential","useful",
  "detail"]` (per proposal §1).
- `WorkflowReport.sections` becomes `list[Section]`; add the `.findings`
  back-compat property and `.from_findings()` constructor; add
  `to_dict()` / `from_dict()` (see D2).
- Keep `Finding` as-is (it's the one genuinely-used type, via the
  `.findings` shape).
- **Remove** the old rich-object path — `ReportSection`,
  `WorkflowReport.render()`/`_render_rich`/`_render_plain`,
  `FindingsTable`, `MetricsPanel`, `format_workflow_result()`. They are
  unwired (Findings), so deletion is safe; do it in the same PR that
  adds the new model so output.py never holds two parallel models.
  (Drift-guard: a test asserts `output.py` exposes no `.render(` method
  on `WorkflowReport` — rendering is the renderer's job.)

`attune.voice.report_renderer` (new):

- `render(report: WorkflowReport, *, disclosure: Literal["summary",
  "full"]="summary", show_cost: bool=False) -> str` → markdown
  (proposal §3). One `isinstance`-dispatch per `Section` subclass.
- The renderer is the ONLY place that knows markdown. CLI feeds its
  output to `rich.markdown.Markdown`; dashboard parses to HTML; MCP
  returns verbatim.

Rationale: keeps `output.py` import-light (no `rich` needed for the
data model — the current `try: import rich` guard goes away), and
matches the proposal's "workflows own content, not formatting."

## D2 — Conversion contract + voice detection

**Decision:** per-workflow **converter function** (not a method on the
bespoke type), plus a serialized discriminator for cross-boundary
detection.

- Each workflow that has a bespoke result dataclass adds a module-level
  `_to_workflow_report(x) -> WorkflowReport` (the proposal's release-prep
  example). Bespoke types stay pure (no rendering knowledge); the
  converter is co-located with the workflow that owns the semantics.
- `execute()` sets `final_output = report.to_dict()` where `to_dict()`
  emits `{"_type": "WorkflowReport", "title": ..., "sections": [{"kind":
  "table", "tier": ..., ...}, ...], ...}`. The `kind` discriminator on
  each section drives `from_dict()` reconstruction.
- **Voice detection** (`_extract_from_workflow_result`): new branch
  *before* the `str()` fallback —
  `if isinstance(fo, dict) and fo.get("_type") == "WorkflowReport":
  report = WorkflowReport.from_dict(fo); report_text =
  report_renderer.render(report, disclosure="summary",
  show_cost=resolve_show_cost())`. The existing `{"formatted_report"}`
  dict branch stays for not-yet-migrated workflows; the `str()` branch
  becomes the **safety net** (proposal §6: generic pretty-printer +
  visible "renderer not migrated" banner) instead of a raw repr.

Rationale: a serialized dict survives the SDK/MCP/JSON boundary that an
`isinstance(WorkflowReport)` check would not; the discriminator keeps
detection unambiguous.

## D3 — `show_cost_metrics` flag

**Decision:** add `show_cost_metrics: bool | None = None` to
`attune.config`. Resolution (in a `resolve_show_cost()` helper):

```python
if config.show_cost_metrics is not None:
    return config.show_cost_metrics          # explicit override
return bool(os.environ.get("ANTHROPIC_API_KEY"))  # auto: on for API users
```

`None` (default) = auto: off for subscription users (no API key), on for
pay-per-call users. Mirrors the established "None means use-the-default"
pattern (cf. `get_max_budget_usd`). Metadata always stays in
`WorkflowReport.metadata` and in `--json`; only the human renderer hides
it. (Honors `feedback_workflow_output` — cost figures don't apply to
subscription users.)

## D4 — Test-surface audit (do FIRST, T0)

Before any code: `grep -rn 'str(.*final_output)\|formatted_report\|
ReleaseReadinessReport(' tests/` and classify each of the 26 hits as
(a) unit test of the dataclass itself → keep, or (b) asserts on
repr/`str()` output → will change. Expectation: most are (a). Record the
(b) list in `tasks.md` so the migration PR updates them in the same
commit (per the "changing user-facing output strings cascades through
test assertions" lesson). The four test layers from proposal §"Test
strategy" (repr-leak drift guard, tier-classification guard, structural
renderer assertions, renderer-crash visibility) are authored alongside
the renderer, not after.

## D5 — Migration rank (from telemetry × ugliness)

`~/.attune/telemetry/usage.jsonl`, real workflows (test/stub excluded):

| Rank | Workflow | Runs | Note |
|------|----------|-----:|------|
| 1 | **release-prep** | — | motivating case, ugliest output; ships with the renderer |
| 2 | code-review | 1229 | highest real run count |
| 3 | dependency-check | 845 | |
| 4 | bug-predict | 837 | |
| 5 | test-gen | 774 | |
| 6 | document-manager | 542 | |
| 7 | refactor-plan | 484 | |
| 8 | perf-audit | 458 | |
| 9 | doc-audit | 344 | |

Migrate in this order; each workflow's `_to_workflow_report()` + its
repr-leak drift-guard test is one small PR. The safety-net banner keeps
unmigrated workflows non-broken in the interim.

## Phasing → see [tasks.md](tasks.md)

Bounded PRs: (T0 test audit) → (T1 data model + delete old) →
(T2 renderer + 4 test layers) → (T3 voice wire + safety net) →
(T4 CLI `rich.markdown`) → (T5 MCP verbatim) → (T6 dashboard panel) →
(T7 release-prep migration) → (T8+ migrate the rest by D5 rank).

## Resolved (2026-06-06)

The three plan questions are decided:

1. **Delete the old unwired `output.py` rich path in T1** — not
   deprecate. It has no real consumers (Findings), so a deprecation
   window would only carry a dead parallel model.
2. **Renderer module: `attune.voice.report_renderer`** — rendering is
   the voice layer's job; `output.py` stays pure data.
3. **Config key: `show_cost_metrics`** (`bool | None`, `None` = auto:
   on iff `ANTHROPIC_API_KEY` is set).

Plan is fully specified; implementation proceeds as the T0–T8+ sequence
on merge.
