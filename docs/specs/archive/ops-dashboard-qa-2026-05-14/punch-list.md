# Ops Dashboard QA — 2026-05-14

Find-and-rank QA pass. **No fixes in this session** — every entry is a
finding, ranked by severity, with file/line pointers so a follow-up PR
can act directly.

**Execution plan:** the action artifact for this punch list is
[../ops-dashboard-polish/](../ops-dashboard-polish/decisions.md).
Each P1 / P2 / P3 finding below is sequenced into Phases A-D of that
spec. When a punch-list item closes, its row gets a "Closed by PR
#NNN" annotation and the corresponding spec task is marked
`pr-merged`.

## Scope

| Item | Value |
|---|---|
| Baseline (read-only) | `http://127.0.0.1:8765` — current `main` (last commit `4b864440`) |
| Worktree under test | `http://127.0.0.1:8775` — preview-launched from `claude/reverent-brown-937823` (clean off `main`) |
| In-flight reference | PR #358 (Specs page width fix) — code lives in `.claude/worktrees/exciting-roentgen-1d3e0d/`, reviewed by source read |
| Viewports tested | 1366×900 and 1920×1080 |
| Pages walked | Home, Workflows, Specs, Spec detail, Telemetry, Health, Run view |
| Pages expected but missing | Memory, Sessions, Run history (index) |

## Severity scale

- **P0 — blocker**: dashboard reports wrong data or misrepresents
  success/failure. Users will make wrong decisions.
- **P1 — high**: significant UX or accessibility defect; primary
  workflows degraded.
- **P2 — medium**: confusing, inconsistent, or sub-optimal — fixable
  in a sitting.
- **P3 — low**: polish, nits, nice-to-haves.

---

## P0 — Blockers

### P0-1 — Home & Telemetry "by_day" rollup always empty (known `ts` / `timestamp` bug)

- **Symptom**:
  - Home → KPI "Today's events" shows `0` despite Recent Runs listing
    completed runs from today.
  - Home → KPI "7-day spend" shows `$0.00` despite Telemetry showing
    `$81.00` cumulative spend.
  - Home → "Daily activity (7 days)" panel shows
    `No telemetry recorded yet. Run a workflow to start seeing data
    here.` — false.
  - Telemetry → "Last 14 days" panel shows
    `No daily activity in the last 14 days.` — false; same page header
    shows 19,014 events.
- **Root cause**: [src/attune/ops/data.py:360](../../../src/attune/ops/data.py#L360) reads
  `event.get("timestamp")` but `~/.attune/telemetry/usage.jsonl`
  entries use the field name `ts` (verified — 19,014 events, all use
  `ts`; zero use `timestamp`). The by-day aggregator silently buckets
  nothing.
- **One-line fix**:
  `ts = str(event.get("ts") or event.get("timestamp") or "")` — same
  pattern as the existing lesson in CLAUDE.md.
- **Why P0**: dashboard's headline metric ("how much have I spent?")
  is broken; users won't trust the rest of the data either.

### P0-2 — Failed runs show as "completed (exit 0)" with a green chip

- **Symptom**: navigate to `/runs/f8ed53713add/view` (a `code-review`
  run). Status chip is **green** and says `completed (exit 0)`. Log
  body shows a `claude_agent_sdk` internal Exception, a Python
  traceback, and a workflow-emitted NextSteps block titled "What
  Went Wrong … Agent SDK error". The work clearly failed.
- **Root cause**: [src/attune/ops/static/js/run_view.js:93-98](../../../src/attune/ops/static/js/run_view.js#L93)
  classifies status purely on the outer-process exit code, which
  is `0` because the CLI dispatcher swallows the SDK exception
  instead of propagating it. The dashboard does no content-scan on
  the stream.
- **Two fix lanes** (either or both):
  1. **CLI side** — `attune workflow run …` should exit non-zero
     when the workflow's `WorkflowResult.success` is false. That
     fixes the symptom at the source.
  2. **Dashboard side** — when finalising a stream, mark the chip
     `chip-warn` (yellow) if the captured log contains an
     `ERROR` / `Traceback` / `Exception` token even when exit_code
     is 0. Defence in depth.
- **Why P0**: dashboard misrepresents success/failure. Users will
  ship broken work thinking it succeeded.

---

## P1 — High

### P1-1 — Specs page overflows viewport at 1366px (resolved in PR #358 — needs merge)

- **Symptom on baseline (8765)**: viewport 1366px wide, table is
  3492px wide (verified by `document.documentElement.scrollWidth`).
  That's 2201px of horizontal scroll. "Tasks" column is entirely
  off-screen. Long custom statuses like
  `"phase 0 complete + skills survey complete; **spec retired**"`
  expand their cell and push everything right.
- **Resolution**: PR #358 reviewed by source-read of
  `worktrees/exciting-roentgen-1d3e0d/src/attune/ops/templates/specs.html`
  and `…/static/css/main.css:602-731`. Adds:
  - `<table class="data-table specs-table">` with
    `table-layout: fixed`
  - `.col-slug { min-width: 180px; max-width: 320px }` +
    `.col-phase { width: 130px }`
  - Compact pills (dot + 3-letter code) — `drf / rvw / apv / cpl`
    for known statuses; `first-8-chars…` for custom ones; full
    string in tooltip.
  - CSS tooltips via `[data-tooltip]::after` replacing native
    `title`.
  - Click-to-edit pill — keyboard accessible (`role="button"`
    `tabindex="0"`, Enter/Space).
- **Action**: confirm PR #358 merges. Below are defects observed in
  the PR #358 source.

### P1-2 — Spec detail page dumps raw markdown instead of rendering it

- **Symptom**: navigate `/specs/ignored-tests`. Each phase's body is
  rendered inside `<pre class="log-output spec-phase-body">{{ contents[phase.name] }}</pre>`. Users see literal
  `**Status:** approved` and `# Per-file resolution decisions`
  instead of bold text and headings. Tables, links, code fences —
  all unrendered. Hostile to readers.
- **Source**: [src/attune/ops/templates/spec_detail.html:36](../../../src/attune/ops/templates/spec_detail.html#L36)
- **Fix path**: server-side render the markdown to HTML
  (`markdown-it-py` is already a transitive dep via `mkdocs`), or
  switch to a `<div>` with the rendered HTML inside. Inline links
  to phase files (`decisions.md` → `/specs/<slug>/raw/decisions.md`)
  would close the loop.

### P1-3 — Custom-path textbox is always visible on Workflows page

- **Symptom**: every workflow row shows the scope dropdown **and** a
  `placeholder="e.g. src/attune/security/"` text input below it,
  even though only the `Custom path…` mode is supposed to expose
  the input. Visual clutter × 20 rows.
- **Root cause**: HTML uses `<input … hidden …>` and the JS toggles
  `custom.hidden = true/false`
  ([runner.js:303, 306, 387](../../../src/attune/ops/static/js/runner.js#L303)),
  but the CSS at [main.css:656-657](../../../src/attune/ops/static/css/main.css#L656)
  declares `.scope-custom { display: block; }` — author CSS beats
  the UA `[hidden] { display: none }` rule. The `hidden` attribute
  has no visual effect.
- **Fix**: add `.scope-custom[hidden] { display: none; }` (one line),
  or drop the `display: block` from `.scope-custom` and rely on the
  UA default.

### P1-4 — Memory and Sessions pages do not exist

- **Symptom**: `/memory`, `/sessions`, `/api/sessions` all return
  404. No template files exist
  (`ls src/attune/ops/templates/` → only home, workflows, specs,
  spec_detail, telemetry, health, run_view, 404, base).
- **Status**: ambiguous. User's QA request lists them; either
  (a) they're planned but unimplemented and should be flagged as a
  product gap, (b) the user confused them with `~/.attune/memory/`
  / `~/.attune/sessions/` directories shown only as chip status on
  Health, or (c) they live in a different app (e.g. attune-gui, the
  template-browser sidecar).
- **Action**: confirm intent. If planned, file a follow-up spec.
  Health page does mention "Memory dir" + "Sessions dir" — surfacing
  those contents (recent memory writes, last 10 sessions) is the
  natural next step.

### P1-5 — Run view's "Recent" strip shows the current run

- **Symptom**: on `/runs/f8ed53713add/view`, the meta-line includes
  `Recent: f8ed5371 completed`. That chip is the run being viewed.
  Confusing — "recent" should mean *other* recent runs of the same
  workflow, or at minimum mark the current one.
- **Source**:
  [src/attune/ops/templates/run_view.html:25](../../../src/attune/ops/templates/run_view.html#L25)
  uses
  `<div class="run-view-history" data-recent-runs="{{ run.workflow }}" hidden></div>`
  which `runner.js` populates from the workflow's recent-runs list
  without filtering out the current run id.
- **Fix**: in `runner.js`'s `setupRecentRuns` populator, skip any
  entry whose id matches the page's `run.id`. Or render with a
  `(current)` marker.

---

## P2 — Medium

### P2-1 — Tooltip system is inconsistent across pages

- PR #358 introduces a CSS `[data-tooltip]::after` tooltip on the
  Specs page (~100ms delay, custom styling, max 280px word-wrap).
  Every other page uses the native `title` attribute (browser-
  default delay, plain styling). Examples of `title` survivors:
  `<code class="env-value" title="…">attune-ai</code>` in
  [base.html](../../../src/attune/ops/templates/base.html), workflow
  scope option `<option value="…" title="{{ f.description }}">` in
  [workflows.html:53](../../../src/attune/ops/templates/workflows.html#L53),
  scope-na `<span class="scope-na" title="…">` in workflows.html:63.
- **Why it matters**: hover behaviour changes mid-page. Specs feels
  responsive; everything else feels laggy.
- **Fix path**: lift `[data-tooltip]` into a global pattern and
  migrate the remaining `title=…` sites, OR (cheaper) move
  `data-tooltip` rules to a shared component CSS block so the
  helper isn't Specs-only.

### P2-2 — Workflow scope picker has no per-workflow default

- **Symptom**: at 8765, all 20 workflow rows preselect
  `src/attune/agents` in the scope dropdown. Clicking Run on
  `release-prep` accidentally scopes to `agents/`. The picker
  doesn't know what each workflow is "about".
- **Root cause**: [runner.js:398-411](../../../src/attune/ops/static/js/runner.js#L398)
  uses one global fallback (`cfg.firstFeaturePath || cfg.allCodePath`)
  for every workflow on first load, where `firstFeaturePath` is
  alphabetically the first path in `features.yaml`.
- **Fix path**: either default to `Project-wide` (empty string)
  until the user explicitly chooses (the simpler call), or map each
  workflow to a recommended scope via metadata in
  `features.yaml` / workflow class attributes.

### P2-3 — Run buttons have no `aria-label`

- **Symptom**: 20 Run buttons on Workflows all say literally
  `Run`. The select+input around each get
  `aria-label="Scope for <workflow>"` and
  `aria-label="Custom scope path for <workflow>"` respectively,
  but the button is left bare.
- **Source**:
  [workflows.html:67](../../../src/attune/ops/templates/workflows.html#L67)
  `<button class="btn btn-run" type="button" data-run-button data-workflow="{{ w.name }}">Run</button>`
- **Fix**: add `aria-label="Run {{ w.name }}"`.

### P2-4 — "Stages 0" for meta-orchestration workflows

- **Symptom**: `health-check`, `orchestrated-health-check`,
  `secure-release` show `0` in the Stages column. Looks like a bug
  — actually a category the table doesn't model.
- **Fix path**: display `—` (em-dash) with tooltip
  "Meta-orchestration; no explicit stage list", or hide the cell.

### P2-5 — No global `:focus-visible` styles; one rule actively *removes* outline

- **Symptom**: `main.css` has no global `:focus-visible` ring.
  Worse — [main.css:669](../../../src/attune/ops/static/css/main.css#L669)
  removes the default outline on `.scope-custom:focus`. Keyboard
  users tabbing into the custom-path input get **no** focus
  indicator.
- **Fix**: add a project-wide `:focus-visible { outline: 2px solid
  var(--accent); outline-offset: 2px; }` and either remove the
  `.scope-custom:focus { outline: none }` rule or replace it with
  a non-removing alternative.

### P2-6 — Status pill click target below WCAG 2.5.5 AA (24×24px)

- **Measured**: `.status-pill` is 11px font + 2px/8px padding →
  rendered ~18px tall × variable width. WCAG 2.1 SC 2.5.5 (Target
  Size, AA) recommends 24×24px; AAA wants 44×44px. Pills are
  click-to-edit on Specs — touch users on tablets will mis-tap.
- **Fix**: bump padding to `4px 10px` (or wrap the click target in
  a larger invisible hit area). Same rule applies to the
  `chip-ok/warn/muted` chips on Home/Telemetry.

### P2-7 — Run view scope path overflow

- **Symptom**: on `/runs/<id>/view`, `run.path` is rendered inline
  in the meta-line as a `<span class="run-view-scope">scope <code>{{ run.path }}</code></span>`.
  Long paths (e.g.
  `/Users/.../worktrees/funny-driscoll-b668c8/src/attune/agents`)
  wrap to a second line and break the layout flow.
- **Fix**: ellipsize the path (`text-overflow: ellipsis` + max-width)
  with a CSS-tooltip showing the full path on hover.

### P2-8 — Test/stub workflows pollute the production Telemetry top-list

- **Symptom**: Telemetry "By workflow (top 20)" is dominated by
  `test-tier-fallback (3400 events, $31.16)`,
  `test-gen (766/$26.66)`, `stub-workflow (4653/$1.63)`,
  `test-workflow (3334/$4.89)`, `success-workflow (1544/$0.54)`,
  `failing-stub (263/$0.09)`. These are dev/test artifacts
  costing real money in the user-visible total.
- **Fix path** (any of):
  - Tag events with `kind=test|prod` and filter in the rollup.
  - Add a "Hide test workflows" toggle in the UI.
  - Use a separate JSONL log for test runs.

### P2-9 — Static asset cache busting is partial

- PR #358's worktree CSS link includes `?v=762340` cache-bust
  (`main.css?v=…`). All other CSS/JS assets are served bare. Per
  the existing v6.8.0 lesson, returning users keep old JS until
  Ctrl-Shift-R. After a release that touches `runner.js`,
  `run_view.js`, or `specs.js`, behaviour silently breaks.
- **Fix**: extend the version-bust to all static assets — Jinja
  helper that appends `?v=attune.__version__` to every
  `url_for('static', …)` call.

---

## P3 — Low / Polish

### P3-1 — Home Recent Runs row click target is split

- Only the workflow-name `<code>` and run-id `<code>` cells are
  links. Status / duration / started / lines cells are
  non-interactive. Whole-row click would match the affordance.

### P3-2 — `/runs/<id>/view` 404s after eviction (known)

- Run-id evicted from in-memory `RunnerService._runs`
  (history_limit=20) or after server restart returns 404, even
  when `~/.attune/ops/runs/<wf>/<id>.json` is on disk. Existing
  lesson in CLAUDE.md.

### P3-3 — Health page row headers missing `scope="row"`

- [health.html:11-19](../../../src/attune/ops/templates/health.html#L11)
  uses `<th>` inside `<tbody>` rows with no `scope="row"`. Some
  screen readers may not associate the header with its cell.
  Trivial accessibility fix.

### P3-4 — Health page is sparse

- No attune-ai package version (Home shows it as a KPI, but
  Health is the supposedly-comprehensive env snapshot).
- No sibling-package versions (attune-help, attune-author,
  attune-rag, attune-gui) — they show on Home's "Family
  snapshot" but not Health.
- No Redis status (presence of `~/.attune/redis-config.json`
  or live ping).
- No MCP server status.
- No working venv path / `which python`.

### P3-5 — "Reported savings = $0.00" without explanation

- Telemetry shows `Reported savings: $0.00` with no tooltip. What
  does this measure? Cache savings? Tier-fallback savings? When
  it's zero, is the feature disabled or just unused? Add a
  `data-tooltip` or `title`.

### P3-6 — No "currently running" indicator in nav

- Running workflow is only visible from the page that spawned it
  (header carries a "running health-check" chip until you
  navigate). Existing lesson notes Home/nav lacks a global
  current-run indicator.

### P3-7 — Wasted horizontal space at 1920px

- Main content max-width pins ~1280px, leaving ~640px (33%) empty
  at 1920px. Tables (especially Workflows scope column and
  Telemetry by_workflow) would benefit from more breathing room.
  Bump max-width to 1600px, or make it adaptive.

### P3-8 — Run-view status string is two concerns in one span

- [run_view.js:93](../../../src/attune/ops/static/js/run_view.js#L93)
  builds `setStatus(info.status + " (exit " + info.exit_code + ")")`.
  Better as a chip (status) + a separate label (exit code) so the
  green/red signal isn't visually muddled by the literal "exit 0"
  text inside it.

### P3-9 — "refresh page for live data" footer only on Home

- Home's footer notes auto-refresh is not enabled. Other pages
  (Workflows, Telemetry, Health) have the same constraint but no
  footer affordance, so users don't know whether the data is
  stale.

### P3-10 — Tooltip top-position only

- PR #358's `[data-tooltip]::after { bottom: calc(100% + 6px); }`
  always positions the tooltip *above* the element. On the first
  table row, with the page-head section close above, this can
  clip the tooltip against the viewport edge or against the meta
  line. Consider a flip-on-overflow helper.

### P3-11a — Project name displays worktree slug when launched from a worktree

- **Symptom**: launch `attune.ops` with `--project-root` pointing at a
  worktree (e.g.
  `/Users/.../attune-ai/.claude/worktrees/exciting-roentgen-1d3e0d`).
  Header shows `PROJECT  exciting-roentgen-1d3e0d` — the worktree's
  slug — instead of the actual project name (`attune-ai`).
- **Root cause**:
  [base.html](../../../src/attune/ops/templates/base.html) derives
  the displayed name from `Path(project_root).name`, which is the
  basename of the path. A worktree's directory IS its slug, so the
  basename is the wrong answer for naming purposes.
- **Fix options** (when prioritized — flagged 2026-05-14 by user
  while reviewing PR #358 preview, deferred as out-of-scope for
  PR #358):
  - **A** — read `name` from `pyproject.toml` in `project_root` (or
    first ancestor that has one). Fall back to `Path.name` if no
    pyproject is found. Robust for any non-worktree edge case too.
  - **B** — strip a leading `.claude/worktrees/<slug>/` prefix from
    the path before taking `Path.name`. Worktree-specific but
    cheaper.

### P3-11 — `select.showPicker()` not gated for older browsers

- [specs.js:191-197](../../../src/attune/ops/static/js/specs.js#L191)
  calls `select.showPicker()` inside a try/catch that swallows
  errors silently. Works, but a feature-detect (`'showPicker' in
  HTMLSelectElement.prototype`) avoids the silent throw on
  Safari < 17 and Firefox < 121.

---

## What I did not test

- **Mobile (≤768px)** — out of scope; the user asked for 1366 and
  1920. Spot-check at 768px would be a useful follow-up.
- **Dark mode** — there is no dark-mode toggle in the UI; if a
  `prefers-color-scheme: dark` rule exists I didn't audit it.
- **Run streaming under load** — verified the buffered replay
  message exists; didn't simulate a multi-thousand-line stream.
- **`?read-only` mode** — the template branches on `allow_run`
  but I exercised only the editable mode. Read-only Specs page
  should fall back to plain chips, not click-to-edit pills —
  worth a smoke test.
- **Live PR #358** — Specs page changes were assessed by source
  read of `worktrees/exciting-roentgen-1d3e0d/` (the branch
  that has them); the 8775 preview server kept loading `main`'s
  editable-install code via setuptools' MetaPathFinder, which
  beats `PYTHONPATH` prepending for editable installs. Worth
  noting if you try the same trick later: launch from the
  worktree with its OWN venv to actually serve worktree code.

---

## In-flight resolutions (during this QA session)

### Specs page "Updated" column — label + accessibility (2026-05-14)

Made on PR #358's working tree
(`/Users/patrickroebuck/attune-ai/.claude/worktrees/exciting-roentgen-1d3e0d/`,
branch `fix/ops-specs-page-width`). **Uncommitted in that tree** — left
for the PR's owner to stage and commit alongside the other in-flight
edits on that branch.

**Label rename**: `Last modified` → `Updated` in both the column header
and the matching `aria-label`. Same width as "Changed" with no `ctime`
vs `mtime` Unix-ambiguity; matches the conventional app-UI label
(GitHub / Linear / Notion).

**Accessibility upgrades** (rationale: support color-blindness and
blindness equally, not just sighted users):

1. `<span class="spec-mtime">` → `<time class="spec-mtime"
   datetime="{iso}">`. Semantic element; assistive tools that recognise
   the `<time>` role announce it as a timestamp, and `datetime` keeps
   the precise ISO machine-readable even when the visible text is
   relative ("6h ago").
2. **Empty-state cell** now carries `aria-label="No update time
   recorded"`. Previously the cell was just `<span>—</span>` and
   screen readers announced "dash" — meaningless. The visible
   em-dash stays for sighted users; the aria-label replaces the
   announcement for screen reader users.
3. **`specs.js renderMtime()`** now updates `aria-label` to match the
   rendered relative-time. Previously the visible text became "6h ago"
   but the `aria-label` kept the raw ISO string
   (`Updated 2026-05-14T13:20:41.316504+00:00`) forever, so screen
   reader users heard 24 raw ISO timestamps when scanning the table.
   Now they hear `Updated 6h ago` matching what the sighted user
   sees. The full ISO remains accessible via the `<time datetime>`
   attribute and the CSS `data-tooltip` on hover/focus.

**Verified in browser preview** (worktree's own venv on port 8775,
24-row Specs page): all 24 cells render as `<time>` elements with
`aria-label="Updated 6h ago"` matching visible text, semantic tag is
`TIME`, `datetime` attribute holds full ISO, `data-tooltip` unchanged.
Visual layout identical to pre-change (table-layout:fixed + 110px
`col-mtime` width preserved).

**Color-blindness note**: this column is timestamp text only, no
color encoding. The adjacent status pill columns already address
color-blindness via dot + 3-letter code (`drf`/`rvw`/`apv`/`cpl`) +
truncated text for custom statuses — verified during the source read
of PR #358. Distinguishable without color.

**Files touched**:
- `src/attune/ops/templates/specs.html` — 2 sites (header `<th>`
  text, populated-cell element + aria-label; new empty-cell
  aria-label)
- `src/attune/ops/static/js/specs.js` — `renderMtime()` sets
  `aria-label` alongside `textContent`

**Not touched intentionally**: CSS classes (`col-mtime`,
`spec-mtime`, `spec-mtime-empty`), `data-mtime` attribute — all
describe the underlying data field and stay stable regardless of
the user-facing label.

---

## Suggested action ordering

1. Land P0-1 (`ts`/`timestamp` rename) — single-line fix; biggest
   trust unlock.
2. Land P0-2 (CLI exit-code propagation + dashboard heuristic).
3. Merge PR #358 (closes P1-1).
4. P1-3 (CSS one-liner) and P1-5 (filter current run from recent
   list) — both small, both visible.
5. Decide P1-4 (Memory/Sessions): build, defer, or rename the
   user's QA expectation.
6. P1-2 (markdown render on spec detail) is the biggest UX upgrade
   left after that.
7. Sweep the P2 list in a single accessibility/polish PR.
