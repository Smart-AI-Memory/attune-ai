# Ops Dashboard QA — 2026-05-14

> Punch list of defects and follow-ups surfaced during the
> 2026-05-14 ops-dashboard polish session. Severity ranking and
> file:line refs included so the QA session can start ranked and
> ready.

**Pages reviewed this session:** Specs (focus), Workflows (incidental
during scope-picker debugging), Home (incidental via Recent strip).
**Pages NOT reviewed:** Memory, Sessions, Health, Run history,
Telemetry. Audit those before considering this list complete.

---

## Severity legend

| Tier | Meaning |
|---|---|
| **Blocker** | Breaks a primary user flow on a routine action |
| **High** | Breaks a non-primary flow OR makes a primary flow misleading |
| **Medium** | Visible defect that degrades usability but has a workaround |
| **Low** | Polish, consistency, or accessibility refinement |

---

## State-restoration bug class

Three related bugs share a single root pattern: **the dashboard
persists state and doesn't re-validate it against current workspace
state at restore time.** Worth fixing as a class, not as individuals.

### B1 — Disk-persisted run pills 404 after server restart

**Severity:** High

**Symptom:** Click a "Recent run" pill (e.g. `d4563e40`) in the Home
or Workflows Recent strip → 404 with message _"run X not found. The
runner keeps the last 20 runs in memory; older runs are pruned when
the server restarts."_

**Root cause:** `/runs/{run_id}/view` in
[src/attune/ops/routes/dashboard.py:111](src/attune/ops/routes/dashboard.py)
calls `runner.get(run_id)` which only checks the in-memory
`RunnerService` history. The Recent strip sources its run list from
`/api/runs/{workflow}` (disk-persisted via
[src/attune/ops/routes/runs_history.py](src/attune/ops/routes/runs_history.py)),
so it surfaces run IDs that survived a server restart — but clicking
those IDs hits a route that doesn't see disk persistence.

**Fix:** In `run_view_page`, fall back to disk on in-memory miss.
The disk record has enough fields (`workflow`, `path`, `status`, log
content) to render a static view. SSE stream would not reconnect
(correct — completed run); the view should communicate this.

**Effort:** ~30 lines in `dashboard.py:run_view_page` + a test that
restarts the runner and confirms the disk record renders.

---

### B2 — Scope picker restores stale path from a previous worktree

**Severity:** High (rendered the workflow runner non-functional in
the affected scenario)

**Symptom:** Click **Run** on a workflow → 400 _"invalid path: Path
'X' is outside allowed directory 'Y'. Operations are restricted to
the workspace."_ The "X" path is from a different worktree that the
user previously had open in the dashboard.

**Root cause:**
[src/attune/ops/static/js/runner.js:restoreScopeOnLoad](src/attune/ops/static/js/runner.js)
read the saved scope from localStorage and applied it without
validating that the path could exist under the current workspace.
When the user opened the dashboard in a different worktree session,
the previous worktree's path got restored and only failed at
run-trigger time when the server's `_validate_file_path` rejected it.

**Status:** **Fixed in this PR** (#358). Server-side
`workflows_page` now emits `workspaceRoot` in `scope-picker-config`;
client-side `restoreScopeOnLoad` calls new `isScopeInWorkspace` to
validate any saved absolute path, discarding stale ones with a
`console.warn`.

**Generalization:** Audit any other `localStorage`-restored state
the dashboard owns (page-specific filters, sort orders, last-viewed
workflow). Same shape can recur.

---

### B3 — Scope picker's displayed label can diverge from stored path

**Severity:** Medium

**Symptom:** Picker dropdown reads e.g. "All Code" but the actual
path sent to `/workflows/{name}/run` is a different value (often a
stale Custom path from localStorage). Diagnosed during B2 cleanup.

**Root cause hypothesis (unverified):** `wireScopeSave`
([runner.js:wireScopeSave](src/attune/ops/static/js/runner.js))
writes to localStorage only on the picker's `change` event. If the
picker's value is set programmatically (e.g. during
`restoreScopeOnLoad` or via test automation) no `change` event
fires, so localStorage doesn't update to match. Subsequent runs
read the stale localStorage value via the `getScope` flow.

**Fix:** Either
(a) save in `restoreScopeOnLoad` so localStorage and picker always
    agree post-restore, or
(b) read directly from picker state in `getScope` (current behavior)
    AND audit other call sites for the same divergence.

**Effort:** ~10 lines + a test that exercises restore → custom path
edit → run sequence.

---

## Cross-page consistency

### C1 — Tooltip implementation differs between pages

**Severity:** Low (visible during this session — Specs feels much
snappier than Workflows because tooltips fire ~100ms vs ~500-1500ms)

The Specs page got a fast CSS tooltip system (`[data-tooltip]::after`,
~100ms reveal). Other tables (Workflows, Home, run history) still
use native `title` attributes which have browser-controlled delays
(Safari ~1.5s).

**Fix:** Roll the CSS tooltip system out to Workflows, Home,
Memory, etc. — the CSS already exists in `main.css`; the work is
HTML changes only (`title="..."` → `data-tooltip="..."` plus
keeping `aria-label` for screen readers).

---

### C2 — `title` attribute mixed with `data-tooltip` will double-fire

If both `title` and `data-tooltip` are set on the same element,
hover shows BOTH the native and the custom tooltip stacked. Specs
page avoids this by stripping `title` in favor of `data-tooltip`;
needs to be the policy everywhere.

---

## Specs page polish (follow-ups to PR #358)

### S1 — Tooltip on phase-status pills includes status only, not phase name

**Severity:** Low

On hover, a pill shows e.g. `phase 0 complete + skills survey
complete; **spec retired**` but not which phase the status belongs
to. The cell's `data-phase` attribute carries it; the tooltip could
prepend `[design] phase 0 complete…`.

---

### S2 — "Updated" relative time doesn't refresh on idle dashboard

**Severity:** Low

The relative time (`2h ago`, `3d ago`) renders once at page load
via `renderMtime`. On a dashboard left open for hours, it stays
stale. Consider a `setInterval(renderMtime, 60000)` per cell, or
just live with the staleness (refresh fixes it).

---

### S3 — Empty-status custom statuses render as `(none)` rather than `—`

**Severity:** Low

Spec phases with a missing/empty `**Status**:` line render as
`(none)` inside a status pill, which looks like a deliberate
status. The em-dash `—` style used for missing-file rows
(no `**Status**` at all) reads more clearly. Consider unifying.

---

## Workflows page (incidentally observed during scope-picker debug)

### W1 — Long workflow descriptions may overflow on narrow viewports

**Severity:** Unknown (not audited)

The Workflows page renders descriptions inline. With long
descriptions and narrow viewports, horizontal scroll may appear.
Audit at 1280px.

---

## Pages NOT YET audited (open work for the QA session)

- **Home** (KPIs, sparkline, Recent strip — only briefly touched)
- **Memory** (no review this session)
- **Sessions** (no review this session)
- **Health** (no review this session)
- **Telemetry** (no review this session)
- **Run history** (the `runs-history.py` API, but no UI review)

For each: width fit at 1366px and 1920px, empty states,
long-string overflow, tooltip discoverability, keyboard navigation
(Tab/Enter/Esc), console errors. Port 8765 has a current-main
baseline running for visual comparison; port 8775 has the
fix/ops-specs-page-width branch.

---

## How to use this list

1. **Start with B-class items** — these are real defects users hit
   on routine actions. B2 is already done in PR #358; B1 and B3
   are the next-shortest paths to user-facing improvement.
2. **C-class** is consistency work — ship as a follow-up PR after
   B-class lands.
3. **S-class** is polish that depends on Specs polish landing
   (PR #358 itself).
4. **W-class** and the unaudited pages are unknown — start with a
   walkthrough at two viewport widths, capture defects with file
   refs, then triage.

**Suggested first-PR scope** after #358 merges:
B1 (run-view disk fallback) — high impact, ~30 lines, no design
decisions needed. Quick win to validate the QA-spec workflow.
