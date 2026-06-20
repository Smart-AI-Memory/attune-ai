# Proposal: Workflow result formatting — kill the dataclass repr

**Status:** Planned (2026-06-06) — see [design.md](design.md) +
[tasks.md](tasks.md). Awaiting plan approval before implementation.
**Author:** Patrick (with Claude as drafter)
**Scope:** `src/attune/workflows/output.py` (data model),
`src/attune/voice/` (renderer), `src/attune/cli_commands/`,
`src/attune/ops/`, `src/attune/mcp/` (display surfaces)

---

## Problem

Running `release-prep` today emits this as its final line on the
dashboard, CLI, and MCP tool response:

```
ReleaseReadinessReport(approved=True, confidence='high',
quality_gates=[QualityGate(name='Security', threshold=0.0, actual=0.0,
passed=True, critical=True, message='Security: PASS (actual: 0.0,
threshold: 0.0)'), QualityGate(name='Test Coverage', threshold=80.0,
actual=85.0, passed=True, critical=True, ...
```

It's a Python `__repr__` of a nested dataclass, several hundred
characters wide, with embedded enum reprs (`<Tier.CHEAP: 'cheap'>`),
nested dicts, and no line breaks. Patrick called it "almost unreadable"
and he's right — there's nothing in that string a human would call
*output*.

This isn't a one-workflow problem. Every workflow whose final result
is a custom dataclass (or whose `final_output` is a complex dict the
voice layer doesn't recognize) hits the same fallback path in
`attune.voice.formatter._extract_from_workflow_result`:

```python
elif result.final_output is not None:
    report_text = str(result.final_output)   # <-- repr of the dataclass
```

The voice layer's job is to produce readable text. When it gets handed
an opaque object, it gives up and prints the repr. That's the bug
surface.

## The contract that's missing

Workflows have an implicit contract with the voice layer that has two
shapes:

1. **String final_output** — voice prints it verbatim. Works.
2. **Dict final_output** with `{"formatted_report": "...", "score":
   N}` — voice extracts those keys. Works.

Anything else — bare dataclass, plain dict without those keys, list of
findings — degrades to `str()`. No workflow author is warned at write
time, no test enforces the shape, and the failure mode is invisible
until a real user runs the workflow and sees the repr dump.

Two distinct kinds of fix:

- **Tactical (per-workflow):** Each workflow that returns a
  custom dataclass adds a renderer. ~10–15 workflows to touch.
- **Strategic (voice-layer):** The voice layer learns to format
  arbitrary dataclasses well, OR enforces a single shape that all
  workflows must conform to.

The proposal below leans tactical for the first ship — least churn,
fastest user value — with a strategic follow-up to prevent recurrence.

## Goals

1. **Scannable in one glance.** A user opening a finished run sees
   the verdict, the gate status, and the cost/time in the first
   screenful — without scrolling and without parsing prose. If
   the run had something the user has to act on (a blocker, an
   undocumented thing, a failing test), it's visible at this level.
2. **Concise without losing useful information.** Not every field
   from the result dataclass is "useful information." Agent UUIDs,
   tier enums, confidence floats, internal `mode='rule_based'`
   markers — these are noise to the human reader. They get cut from
   the default view, not formatted prettier. If a field doesn't help
   the user decide their next action, it doesn't belong in the
   essential block.
3. **Progressive disclosure for the rest.** Information that is
   useful to *some* readers but not *most* (the long list of 44
   undocumented functions, the per-agent timings, the raw findings
   dict) stays accessible but stays out of the default view. On the
   dashboard, that means a `<details>` collapsible block. On the
   CLI, it means a `--verbose` flag (or `--full`). On MCP, it means
   the structured-data envelope already returned alongside the
   formatted text — Claude Code can drill in when asked.
4. No workflow run on the CLI / dashboard / MCP ever prints a Python
   dataclass repr again. If we can't format the result, the failure
   mode is a polite "renderer unavailable — raw fields below" block,
   not `Foo(a=1, b=2, ...)`.
5. **One result type, one renderer.** Every workflow returns a
   `WorkflowReport`; one renderer turns that into markdown. Surfaces
   (CLI / dashboard / MCP) adapt the markdown for their medium.
   Workflows own *content classification* — what's a section, what
   tier, what kind of layout — not raw output formatting.
6. Adding a new workflow that returns a dataclass other than
   `WorkflowReport` (or a `WorkflowReport` whose sections were never
   classified into tiers) fails a test, not a user.

## Design principles

- **Scannable first, readable second.** The default view rewards a
  *glance*, not a *read*. Pass/fail marks, column-aligned numbers, a
  one-line verdict — these earn their place before paragraphs do.
- **Default to less.** When a field's value is interesting only when
  it's wrong (e.g. `confidence: 0.5` when most reports cite high
  confidence), show it only when it's the wrong value. When the field
  is internal plumbing (e.g. `agent_id: 'security-auditor-b6c4e952'`),
  cut it from human-facing output entirely. `--json` keeps it for
  consumers that care.
- **Drop-downs over diff-blame.** Per-renderer judgment about what
  belongs in the default view vs the collapsed details is a *design*
  decision, not a per-user toggle for every field. The renderer
  picks; the user expands when they want more.
- **Three rendering targets, one markdown source.** Every renderer
  call produces a markdown string. The CLI pipes it through `rich`
  for TTY-aware terminal styling (auto-strips on pipe-to-file). The
  dashboard parses it to HTML; `<details>` blocks become native
  browser collapsibles. MCP returns the markdown verbatim — Claude
  Code's chat panel renders markdown natively. No surface duplicates
  layout logic. Disclosure (summary vs full) is a single argument to
  the renderer; what varies per surface is how it physically presents
  collapsed content.

## Non-goals

- Redesigning the voice layer's tone, personality, or
  "What I'd do next" suggestions. That layer works; we're plugging the
  hole where it gives up.
- Letting every workflow keep its bespoke result dataclass forever.
  Bespoke types may still exist *internally* during workflow
  execution, but the boundary into voice / CLI / dashboard / MCP is
  `WorkflowReport`. Internal types either convert (`to_report()`) or
  are reconstructed at the boundary.
- Replacing the `--json` output path. JSON consumers already get
  structured data via `WorkflowResult` serialization; this is purely
  about the human-readable path.
- Building a custom markdown renderer. The CLI uses `rich.markdown`,
  the dashboard uses any standard JS markdown lib, MCP returns raw
  markdown to its caller. We're not in the markdown business.

## Surface map (where this hits)

| Layer | Path | What it does today | What it does after |
|---|---|---|---|
| **Workflows** | each `execute()` | Stuffs bespoke dataclass / dict into `final_output` | Returns `WorkflowReport` (sections classified by tier). Bespoke result types may still exist internally, with a `to_report() -> WorkflowReport` conversion at the boundary. |
| **Voice / renderer** | new `attune.voice.markdown_renderer` (or similar) | n/a — voice today does ad-hoc dict extraction | Single function `render(report: WorkflowReport, disclosure: Literal["summary","full"]) -> str` producing markdown. Knows tiers; emits `<details>` blocks for `detail`-tier sections in summary mode |
| **Voice extraction** | `voice/formatter.py:_extract_from_workflow_result` | Falls back to `str(final_output)` (the repr leak) | Detects `WorkflowReport` final_output → calls markdown renderer. Falls back to **safety net** (generic pretty-printer + visible "renderer unavailable" header) for unmigrated workflows |
| **CLI** | `cli_commands/workflow_commands.py:_print_workflow_result` | Prints the voice-formatted text | Calls renderer with `disclosure="summary"` by default, `"full"` when `--verbose`. Pipes through `rich.markdown.Markdown` for TTY-aware terminal styling (color/tables/headings auto-strip on pipe-to-file) |
| **MCP** | `mcp/server.py:format_mcp_response` | Formats the result for the MCP envelope | Returns the raw markdown (summary mode) as the human-readable content. Claude Code renders markdown natively; no rich involvement. Structured `WorkflowReport.to_dict()` JSON travels alongside |
| **Dashboard** | `ops/templates/run_view.html`, `runner.js` line renderer | Streams subprocess stdout as plain text | Run-view page gets a new structured panel above the existing terminal-text stream: fetches `WorkflowReport` JSON from `/runs/<id>` API, parses summary markdown to HTML, `<details>` blocks become real native collapsibles. Terminal stream stays for in-progress lines and pre-completion output |

## Proposed approach

Brainstorm 2026-05-14 settled on these choices. Plan / execution
phases refine the implementation, not these primitives.

### 1. Grow `WorkflowReport` with `sections: list[Section]`

`attune.workflows.output.WorkflowReport` is the universal result
type. Sections are the new content-carrying field. The existing
`title`, `summary`, `score`, `metadata`, `suggestions` fields stay
as-is.

`findings` migrates from a top-level list to a kind of section
(`FindingsSection`). Workflows that just emit findings get a one-line
convenience constructor; a `.findings` property on `WorkflowReport`
introspects sections for back-compat reads.

```python
from typing import Literal, ClassVar
from dataclasses import dataclass, field

Tier = Literal["essential", "useful", "detail"]

@dataclass
class Section:
    """Base class. Subclasses carry kind-specific content."""
    title: str
    tier: Tier
    kind: ClassVar[str]  # set by each subclass for serialization

@dataclass
class CalloutSection(Section):
    text: str
    emphasis: Literal["info", "ok", "warn", "danger"] = "info"
    kind: ClassVar[str] = "callout"

@dataclass
class ProseSection(Section):
    text: str
    kind: ClassVar[str] = "prose"

@dataclass
class TableSection(Section):
    columns: list[str]
    rows: list[dict[str, object]]
    kind: ClassVar[str] = "table"

@dataclass
class ListSection(Section):
    items: list[str]
    kind: ClassVar[str] = "list"

@dataclass
class FindingsSection(Section):
    findings: list[Finding]
    kind: ClassVar[str] = "findings"

@dataclass
class NextAction:
    """A single forward-looking step the user can take after this report.

    `text` is always present and reads as the bullet's main line.
    `command` is an optional shell command the dashboard can wire to
    a one-click run button (and the CLI prints syntax-highlighted).
    `file` is an optional ``path[:line]`` reference the dashboard
    turns into a clickable link (and the CLI prints as inline code).
    """
    text: str
    command: str | None = None
    file: str | None = None

@dataclass
class NextStepsSection(Section):
    """Forward-momentum section every report should end on when
    non-empty. Always rendered last in summary mode. Tier is always
    ``"essential"`` by convention — next steps are the whole point of
    bothering to make the report scannable. Omitted from the rendered
    output entirely when ``items`` is empty (don't render an empty
    ``"Next steps:"`` header).
    """
    items: list[NextAction]
    kind: ClassVar[str] = "next-steps"

@dataclass
class WorkflowReport:
    title: str
    summary: str = ""
    score: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    suggestions: list = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        """Back-compat: surfaces findings from any FindingsSection."""
        out: list[Finding] = []
        for s in self.sections:
            if isinstance(s, FindingsSection):
                out.extend(s.findings)
        return out

    @classmethod
    def from_findings(cls, title: str, findings: list[Finding],
                      tier: Tier = "essential", **kwargs) -> "WorkflowReport":
        """Convenience: build a one-section report for findings-only workflows."""
        return cls(
            title=title,
            sections=[FindingsSection(title=title, tier=tier, findings=findings)],
            **kwargs,
        )
```

Workflows build their report by composing sections. Release-prep
becomes:

```python
def _to_workflow_report(rrr: ReleaseReadinessReport) -> WorkflowReport:
    verdict = "APPROVED" if rrr.approved else "BLOCKED"

    gates_section = TableSection(
        title=f"Quality Gates ({sum(g.passed for g in rrr.quality_gates)}/"
              f"{len(rrr.quality_gates)} passed)",
        tier="essential",
        columns=["Gate", "Actual", "Threshold", "Pass"],
        rows=[
            {"Gate": g.name, "Actual": g.actual, "Threshold": g.threshold,
             "Pass": "✓" if g.passed else "✗"}
            for g in rrr.quality_gates
        ],
    )

    agents_section = TableSection(
        title="Per-agent breakdown",
        tier="detail",
        columns=["Agent", "Score", "Time"],
        rows=[
            {"Agent": a.agent_role,
             "Score": a.score,
             "Time": f"{a.execution_time_ms / 1000:.1f}s"}
            for a in rrr.agent_results
        ],
    )

    sections = [
        CalloutSection(
            title="Verdict",
            tier="essential",
            text=f"Release **{verdict}** — confidence: {rrr.confidence}",
            emphasis="ok" if rrr.approved else "danger",
        ),
        gates_section,
        agents_section,
    ]
    if rrr.blockers:
        sections.append(ListSection(
            title="Blockers", tier="essential", items=rrr.blockers))
    if rrr.warnings:
        sections.append(ListSection(
            title="Warnings", tier="essential", items=rrr.warnings))

    # Forward momentum — what the user should do next. Outcome-
    # conditional: success path nudges to the release ceremony,
    # failure path names a concrete recovery action.
    next_steps: list[NextAction] = []
    if rrr.approved:
        next_steps.append(NextAction(
            text="All gates pass. Cut the release.",
            command="attune release prep",
        ))
        if undoc_count := _undoc_count_from(rrr):
            next_steps.append(NextAction(
                text=f"{undoc_count} undocumented functions — not blocking, "
                     "but worth closing before users see them.",
                command="attune workflow run doc-gen --path src/attune/memory/",
            ))
    else:
        # Blockers reference the file/line that failed; surface them
        # as actionable items, not just status.
        for b in rrr.blockers:
            next_steps.append(NextAction(
                text=f"Resolve blocker: {b.message}",
                file=b.file_line if b.file_line else None,
            ))
    sections.append(NextStepsSection(
        title="Next steps", tier="essential", items=next_steps))

    return WorkflowReport(
        title="Release readiness",
        summary=f"Release {verdict} — confidence: {rrr.confidence}",
        sections=sections,
        metadata={"total_duration": rrr.total_duration,
                  "total_cost": rrr.total_cost},
    )
```

### 2. Content tiers (the design rule)

Every section gets a `tier`:

| Tier | Goes where | Example sections |
|---|---|---|
| **essential** | Always shown. Drives user's next action. | Verdict callout, quality gates table, blockers, warnings, **next steps** |
| **useful** | Shown in summary mode (below essentials). Adds context. | Top-N samples of larger lists, top-level score callouts |
| **detail** | Hidden in summary mode, shown in `full` mode (= `<details>` on dashboard, `--verbose` on CLI). | Per-agent breakdown, full undocumented-function list, raw findings dicts |

`NextStepsSection` is special — it's always last in `summary` mode and
always `tier="essential"` when present. A report without forward-
looking steps is technically valid but unusual; the renderer omits the
section header entirely when `items` is empty so empty "Next steps:"
labels never appear.

Internal plumbing (`agent_id`, `mode="rule_based"`, `escalated: bool`,
`confidence: 0.5`, `tier_used: <Tier.CHEAP: 'cheap'>`) never makes it
into a section. `--json` keeps it for consumers that care.

Heuristic for unclassified fields: *would the user notice if this
field disappeared from the human-facing report?* No → cut. Yes →
essential or useful. Some users → detail.

### 3. One markdown renderer

A single function turns a `WorkflowReport` into markdown:

```python
def render(report: WorkflowReport, *,
           disclosure: Literal["summary", "full"] = "summary",
           show_cost: bool = False) -> str:
    """Render a WorkflowReport as markdown.

    disclosure="summary" includes essential + useful sections;
                         wraps detail sections in <details>.
    disclosure="full"    includes all sections inline (no <details>).
    show_cost            controls whether cost/time/confidence/tier
                         metadata renders at all (see #4 below).
    """
```

Walks `report.sections` in order. For each section, dispatches by
`isinstance(s, TableSection | ListSection | …)`. Each kind has a
markdown emitter:

- `CalloutSection` → fenced quote block, color/icon via emphasis.
- `ProseSection` → paragraph.
- `TableSection` → markdown table (auto-aligns columns).
- `ListSection` → unordered list.
- `FindingsSection` → markdown table sorted by severity, with
  `file:line` formatted as inline code.
- `NextStepsSection` → bulleted list, last in summary order. Each
  `NextAction` renders as one bullet:
  - `text` alone → plain bullet text.
  - `text` + `command` → bullet followed by a fenced one-liner
    code block with the command. CLI: `rich` syntax-highlights it
    so the user can copy. Dashboard: parses the markdown but also
    augments the rendered HTML with a "Run" button that POSTs to
    `/workflows/<name>/run` (re-using the existing runner
    infrastructure) when the command parses as an `attune
    workflow run <name> …` invocation.
  - `text` + `file` → bullet with `path:line` as inline code.
    Dashboard turns it into a link (vscode:// or the existing
    `file:line` linking pattern in the line renderer). CLI just
    shows it as inline code.
  - Both `command` and `file` are independent; either, both, or
    neither can be present.

Detail-tier sections in `summary` mode get wrapped in `<details>`:

```markdown
<details><summary>Per-agent breakdown</summary>

| Agent | Score | Time |
|-------|------:|------:|
| Security Auditor | 50.0 | 6.9s |
| …                |  …   |  …   |

</details>
```

The CLI renders that markdown via `rich.markdown.Markdown` (terminal
color, table layout, TTY detection); dashboard parses to HTML
(`<details>` renders natively); MCP returns the markdown verbatim.

### 4. Cost / confidence / tier are config-gated

A new flag (working name `attune.config.show_cost_metrics: bool`)
controls whether the renderer emits cost lines, model-tier markers,
or confidence floats. Default behavior:

- **Off** when no `ANTHROPIC_API_KEY` is set (subscription user).
- **On** when `ANTHROPIC_API_KEY` is set (pay-per-call user).
- **Forced on/off** by explicit config setting if the user sets it.

This addresses the standing note that cost figures don't apply for
subscription users. The metadata stays in `WorkflowReport.metadata`
and is always present in `--json`; only the human renderer hides it.

### 5. Renderer crash is visible

If `render(report, …)` raises (bug, schema drift, attribute missing),
the voice layer:

1. Catches the exception.
2. Emits a one-line error banner: `⚠ Report renderer error:
   AttributeError: 'NoneType' object has no attribute 'value'`.
3. Falls through to the safety net (#6 below) so the user still
   sees something.

Result: rendering bugs are visible at the surface, not silently
swallowed. CI test fixture: feed a deliberately broken report into
the renderer and assert both the error banner and the fallback block
appear.

### 6. Safety net for unmigrated workflows

When a workflow's `final_output` is still a bespoke dataclass and no
`to_report()` exists, the voice layer detects this and emits:

```
⚠ Renderer not yet migrated for ReleaseReadinessReport. Raw fields:

  approved: True
  confidence: high
  quality_gates: [4 items]
  agent_results: [4 items]
  blockers: (empty)
  warnings: (empty)
  …
```

Generic dataclass pretty-printer: enums become `.value`, nested
dataclasses indent, lists show count or first few items. This is
intentionally not pretty — it satisfies "no repr ever" without
satisfying "designed output." The visible "renderer not yet migrated"
banner makes the gap obvious so it gets addressed.

### Implementation order

1. **Ship the data model**: `Section` ABC + 5 subclasses,
   `WorkflowReport.sections` field, `.findings` property,
   `.from_findings()` constructor.
2. **Ship the renderer**: one function, markdown out, with disclosure
   levels and the safety-net fallback.
3. **Wire the surfaces**: CLI via `rich.markdown.Markdown`, dashboard
   via run-view panel fetching `/runs/<id>` JSON, MCP returns
   markdown.
4. **Migrate workflows** to return `WorkflowReport`, starting with
   release-prep (the motivating case). Telemetry × ugliness ranks the
   rest.

## Test strategy

Four layers, each cheap to write and maintain:

1. **Repr-leak drift guard** — for every workflow + a representative
   fixture, assert the rendered markdown contains no `<class '`,
   `=<` (enum repr), or the workflow's bespoke dataclass class name.
   One failing test per workflow that regresses, with the workflow
   name in the message.

2. **Tier-classification guard** — for every workflow's report
   fixture, assert that running `render(report, disclosure="summary")`
   does *not* contain section titles that were marked `tier="detail"`,
   and *does* contain section titles marked `tier="essential"`.
   Catches mis-tiering at the section construction site.

3. **Structural assertions on the renderer** — feed synthetic reports
   to the renderer and assert behaviors, not exact strings:
   - A `WorkflowReport` with one `CalloutSection(emphasis="danger")`
     produces a markdown blockquote containing the text.
   - A detail-tier section in `summary` mode is wrapped in
     `<details><summary>…</summary>…</details>`.
   - In `full` mode, no `<details>` tags appear.
   - `show_cost=False` strips `metadata.total_cost` from the output.
   These tests survive cosmetic layout tweaks.

4. **Renderer-crash visibility test** — pass a deliberately broken
   report (e.g. a `TableSection` with `rows=None`) and assert both
   the `⚠ Report renderer error: …` banner and the safety-net
   pretty-printed fallback appear in the output.

Snapshot tests on exact markdown output are deliberately *not*
proposed. They're brittle and the structural tests above cover the
properties that matter.

## Risks

- **Test-string churn.** The CLAUDE.md lesson "Changing user-facing
  output strings cascades through test assertions" applies directly.
  Any test in the repo that pattern-matches the current repr-style
  output (likely zero, but worth grepping for
  `ReleaseReadinessReport` / `QualityGate` substrings in tests/) will
  need updating. Audit before implementing.

- **Migration cost for existing workflows.** Every workflow whose
  `execute()` returns a bespoke dataclass needs a `to_report()`
  conversion (or to be reworked to return `WorkflowReport` directly).
  The safety-net fallback keeps unmigrated workflows from breaking
  in the meantime, but the visible "renderer not migrated" banner
  is the pressure that drives the migration. Plan for ~10–15
  workflows over a few weeks, not a single PR.

- **`.findings` back-compat property surprises.** Code that does
  `report.findings = [...]` (assignment) breaks — it's a property
  now, not a writable field. Grep for assignment patterns before
  shipping. Read access via `report.findings` keeps working.

- **Disclosure classification is opinionated.** Marking a section
  `tier="detail"` is a design call, and someone will eventually want
  a section that's hidden by default. Mitigation: (a) `--verbose` /
  `<details>` makes detail-tier sections always reachable;
  (b) `--json` keeps everything, including plumbing fields, available
  verbatim; (c) reclassification is a renderer edit (one
  `tier="detail"` → `tier="useful"` change), not a data-shape
  change — cheap.

- **MCP response size — markdown is multi-line.** The MCP envelope
  returns markdown as text. Pretty markdown is several × longer than
  a one-line repr. Mitigation: the summary / detail tier split
  bounds default growth (only essential + useful sections inline;
  detail-tier is in `<details>` blocks that LLM clients can either
  render natively or strip).

- **Dashboard has two rendering paths.** The structured-panel
  rendering of the final `WorkflowReport` lives alongside the
  streamed-stdout terminal pane on `/runs/<id>/view`. Risk: report
  appears twice. Mitigation: panel renders the summary markdown
  parsed to HTML; terminal pane shows in-progress lines and pre-
  completion subprocess output. Once the workflow completes, the
  panel is the canonical view; the terminal block becomes a
  collapsible "process log" below it.

- **Loss of structure for text-scraping consumers.** Anyone parsing
  the current ad-hoc text output (unlikely but possible — e.g. a
  chained workflow that reads the upstream report) will break when
  the format changes. The `--json` path remains canonical for
  machine consumers; document this in the migration note.

- **"Hidden by default" surprises users who don't know to expand.**
  A user who needs the per-agent timings and doesn't realize the
  `<details>` block is collapsible (or that `--verbose` exists)
  thinks the data isn't there. Mitigation: detail-tier sections
  always render with an explicit `<summary>` line on the dashboard
  ("Per-agent breakdown — click to expand"); on the CLI, the
  summary mode prints a closing line "(run with `--verbose` for per-
  agent breakdown, undocumented function list)".

- **`rich.markdown` is opinionated.** Default rich styling for
  markdown is busy: heavy box-drawing characters around tables,
  bright colors, large heading blocks. Mitigation: configure a
  minimal `rich.console.Console(theme=...)` with subdued styling for
  tables and headings. ~30-line tweak; document the theme in a
  module near the CLI print path so it's easy to find when someone
  wants to adjust.

## What this spec doesn't decide

- Visual polish in the markdown source — emoji choice, exact column
  alignment, ASCII separator vs `·`, whether the verdict callout
  uses a fenced quote or a heading. Plan / execution refines.
- The `rich` theme — color palette, table border style. Plan picks
  a starting point; future PRs tweak.
- Dashboard structured-panel CSS — visual treatment of the section
  containers, how `<details>` blocks animate when expanded.
- The exact HTML/CSS shape of dashboard "Run" buttons attached to
  `NextAction` items whose `command` parses as `attune workflow run
  <name> …`. Plan picks a starting point; dashboard styling refines.
- Migration order beyond "release-prep first." Heuristic: run
  frequency from telemetry × current output ugliness.
- The exact config flag name for `show_cost_metrics` — naming
  decision in plan.

## Success criteria

A release-prep run emits a summary that:

1. **Fits on one screen** at a standard terminal width and the
   default dashboard run-view panel size. No scroll-to-find-verdict.
2. **Leads with the verdict** in the first line. A user with three
   seconds to glance learns approved-vs-blocked and the headline
   numbers without parsing.
3. **Omits noise.** No agent UUIDs, no `<Tier.CHEAP: 'cheap'>`
   enum reprs, no internal `mode='rule_based'` markers, no
   confidence floats that nobody asked for. These either live in
   the `details` tier or in `--json` only.
4. **Has an explicit "more" affordance** for the disclosure tier —
   on the dashboard, a `<details>` block labeled "Show full
   report"; on the CLI, a closing line telling the user about
   `--verbose`.
5. **Reads like a status report**, not a stack trace.

A new workflow added next quarter that returns a `FooReport`
dataclass without a registered renderer gets a generic pretty-printed
block, not a repr — and a CI test fails if anyone tries to ship one
that does emit a repr.

### Illustrative target: the release-prep run from 2026-05-14

The renderer's source-of-truth output is markdown. Below is what it
emits in `disclosure="summary"` mode (with `show_cost=False` for a
subscription user):

````markdown
# Release readiness

> ✓ Release **APPROVED** — confidence: high

## Quality Gates (4/4 passed)

| Gate          | Actual | Threshold | Pass |
|---------------|-------:|----------:|:----:|
| Security      |    0.0 |       0.0 |  ✓   |
| Test Coverage |   85.0 |      80.0 |  ✓   |
| Code Quality  |   10.0 |       7.0 |  ✓   |
| Documentation |   98.5 |      80.0 |  ✓   |

## Documentation

44 of 3012 functions undocumented. Top 3:

- `src/attune/memory/nodes.py:139` — `__post_init__`
- `src/attune/memory/personal.py:126` — `__init__`
- `src/attune/workflows/rag_code_gen.py:107` — `__init__`

<details><summary>Per-agent breakdown (4 agents)</summary>

| Agent             | Score | Time  |
|-------------------|------:|------:|
| Security Auditor  |  50.0 |  6.9s |
| Test Coverage     |  85.0 | 90.9s |
| Code Quality      |  10.0 |  0.3s |
| Documentation     |  98.5 |  1.0s |

</details>

<details><summary>Undocumented functions (full list — 44 items)</summary>

- `src/attune/memory/nodes.py:139` — `__post_init__`
- `src/attune/memory/nodes.py:152` — `__post_init__`
- … (41 more)

</details>

## Next steps

- All gates pass. Cut the release.
  ```
  attune release prep
  ```
- 44 undocumented functions — not blocking, but worth closing before
  users see them.
  ```
  attune workflow run doc-gen --path src/attune/memory/
  ```
````

**What each surface does with that:**

- **Dashboard** parses to HTML, renders the table with proper
  styling, `<details>` blocks become native collapsibles the user
  can expand.
- **CLI** pipes through `rich.markdown.Markdown` — table renders
  with column alignment in the terminal, `<details>` blocks are
  replaced with a single line "(run with `--verbose` to expand:
  Per-agent breakdown, Undocumented functions)".
- **MCP** returns the raw markdown to Claude Code, which renders
  markdown natively in the chat panel.

**What's cut entirely from the human-facing report** (still in
`--json` for consumers that care):

- `agent_id="security-auditor-b6c4e952"`
- `confidence: 0.5`
- `mode: "rule_based"`
- `tier_used: <Tier.CHEAP: "cheap">`
- `escalated: False`
- `timestamp: "2026-05-14T10:54:09.875476"`

**With `show_cost=True`** (set by `ANTHROPIC_API_KEY` users), the
verdict callout gains a second line: `Total: 90.9s · $0.00`.

Layout above is illustrative. The *tiering* (what's essential vs
detail vs cut) is the spec commitment; the exact markdown
typography is for plan to refine.

## Brainstorm record (2026-05-14)

Brainstorm conversation settled the following premises:

1. **Reuse `WorkflowReport`, don't invent a new type.** The
   `RenderedReport(summary, details)` shape proposed earlier was
   dropped in favor of growing `WorkflowReport.sections: list[Section]`.
   `Section` is an ABC with six concrete subclasses
   (`CalloutSection`, `ProseSection`, `TableSection`, `ListSection`,
   `FindingsSection`, `NextStepsSection`). Each section carries its
   own `tier`. Findings migrate from a top-level field into
   `FindingsSection`; a `.findings` property + `.from_findings()`
   constructor preserve the existing ergonomics.

2. **Markdown is the wire format.** A single renderer function turns
   `WorkflowReport` into markdown. Surfaces adapt it (CLI: rich-rendered
   to a terminal; dashboard: parsed to HTML; MCP: returned verbatim).
   No two-string `(summary, details)` API; disclosure is expressed
   inline via `<details>` blocks emitted by the renderer when in
   `disclosure="summary"` mode.

3. **Subscription-aware metadata.** Cost / confidence / tier fields
   are hidden by default when no `ANTHROPIC_API_KEY` is set
   (subscription user), shown by default when it is. Controllable by
   explicit config flag.

4. **Renderer crashes are visible.** A renderer exception → one-line
   error banner + safety-net fallback. Bugs surface; runs don't break.

5. **`rich` for CLI rendering.** `rich.markdown.Markdown` provides
   TTY-aware terminal output (color, table layout) that auto-strips
   on pipe-to-file. Markdown stays the source; rich just renders it
   at print time.

6. **Every report ends on forward momentum.** A new `NextStepsSection`
   carrying `list[NextAction]` is the canonical place for "what the
   user should do next." Each `NextAction` is `(text, command?, file?)`:
   the dashboard turns commands into one-click run buttons (re-using
   the runner infrastructure) and files into clickable links; the CLI
   prints commands as syntax-highlighted code blocks and files as
   `file:line` inline code. Reports without forward-looking steps just
   omit the section. Surfaced as a separate premise (vs. squeezing
   into `WorkflowReport.suggestions`) because forward momentum is a
   first-class element of report design — not metadata, not a
   footnote.

## Next step

Plan via `/spec`. Plan should:

1. Sketch the file/module layout — where do the `Section` subclasses
   live, where does the renderer module live, what's the public API
   exposed from `attune.workflows.output` vs `attune.voice`.
2. Define the conversion contract for existing workflows
   (`to_report()` method on bespoke result types, or a per-workflow
   converter function in voice).
3. Pick the `show_cost_metrics` config flag name and default-
   resolution logic.
4. Audit the test surface for repr-style assertions before any code
   lands (per the test-string churn risk).
5. Rank workflows for migration by run frequency from
   `~/.attune/telemetry/usage.jsonl` × current output quality.
   Release-prep is the obvious first one; the rank determines the
   rest.
