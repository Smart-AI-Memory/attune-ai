# Analysis-Workflow Output Widgets — requirements

**Status:** approved (2026-06-28) · **Owner:** Patrick + agent
**Kickoff:** `/spec` widget form, response `resp-20260628-143856`
(goal = formalize the program; workflows = all 7; shared_renderer = yes;
"parallel acceptable").

Formalize the rich `show_widget` output pattern — already shipped for
discovery-sweep (`#1148`, triage board) and security-audit (`#1149`,
severity dashboard) — into a program that (a) extracts a **shared
renderer** and (b) extends rich output to the other analysis workflows.

## Grounding — the workflows are NOT uniform (verified, not assumed)

The kickoff picked 7 workflows expecting one widget each. The code says
otherwise — their MCP responses split into two shapes:

| Workflow | Handler pick | Output shape | Widget family |
|---|---|---|---|
| security-audit | `findings` | structured `Finding` | **A** (done `#1149`) |
| discovery-sweep | bespoke buckets | structured `Finding` | **A** (done `#1148`) |
| **perf-audit** (`performance_audit`) | `findings` + score | structured `Finding` | **A** |
| **bug-predict** | `predictions` (findings-like → report findings) | structured *iff* report has a `FindingsSection` | **A?** (confirm) |
| **code-review** | `feedback` + `quality_score` | `feedback` is NOT findings-like → text | **B** |
| **test-audit** | `raw_output=True` | markdown | **B** |
| **refactor-plan** | `raw_output=True` | markdown | **B** |
| **dependency-check** | `raw_output=True` | markdown | **B** |
| **deep-review** | `raw_output=True` | markdown | **B** |

`code_review` / `bug_predict` / `refactor_plan` / `dependency_check` /
`deep_review` construct **zero** `WorkflowReport`/`Finding` objects —
they are SDK-native and emit summary markdown. `_workflow_response` can
also return *metadata string-bullet* findings (`{stale: [...]}`) which
are NOT the structured `severity/file/line/message` shape either.

**Conclusion:** "add a findings widget to all 7" is fiction. There are
**two** widget families:

- **Family A — structured findings dashboard** (the shipped pattern):
  severity dashboard / triage board over `Finding{severity,file,line,
  message,code}`. Targets: perf-audit, bug-predict *(if confirmed)*.
- **Family B — rich markdown panel**: render the workflow's
  `summary_markdown` as a styled `show_widget` card (headings, severity
  callouts, file links) — NO false structure. Targets: code-review,
  deep-review, test-audit, refactor-plan, dependency-check.

## Functional requirements

- **FR-0 (confirm shapes).** Before building each workflow's widget,
  confirm its LIVE output shape (run it pattern-only/cheap or read its
  result construction). The table above is the hypothesis; the code is
  the contract.
- **FR-1 (shared renderer).** Extract `attune.workflows.findings_widget`
  — the severity palette + `esc`/`location` + finding-card primitives —
  and migrate the discovery-sweep board (`#1148`) and security-audit
  dashboard (`#1149`) onto it. No behaviour change; pure de-dup.
- **FR-2 (Family A rollout).** Apply the structured dashboard to the
  confirmed Family-A workflows via their existing `findings`/`predictions`
  picks → `dashboard_html`, skill Output wiring, tests.
- **FR-3 (Family B renderer).** A `markdown_to_panel_html` helper +
  `panel_html` field for the markdown workflows; skill Output prefers it,
  raw markdown as fallback. Injection-safe, display-only.

## Non-goals

- No new MCP tools (the 47-count guard / README / features.ts). Extend
  existing responses with `*_html` fields, as `#1148`/#1149 did.
- No reworking SDK-native workflows to manufacture structured findings
  where the LLM emits prose — Family B renders what's actually there.
- `slider`/`color` controls stay deferred (elicitation D11).

## Sequencing & parallelism (user OK'd parallel)

1. **FR-1 shared renderer** — must land FIRST (after `#1148`+`#1149` merge)
   so A-family widgets build on it, not on copies.
2. **FR-0 confirm** — parallel per-workflow (read-only).
3. **FR-2 / FR-3** — parallelizable per workflow (one PR each, or grouped
   by family). Worktree isolation if files conflict.

## Acceptance

- One shared `findings_widget`; board + dashboard import it; their tests
  still green.
- Each in-scope workflow's response carries the right `*_html`
  (dashboard for A, panel for B); skill prefers it, markdown fallback.
- Every helper injection-safe + unit-tested; no exact-dict response test
  broken (pop `*_html`, keep legacy keys exact — see `#1149` lesson).
