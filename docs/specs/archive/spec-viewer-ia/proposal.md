# Spec Viewer IA — Grouping Proposal

**Status**: Approved (2026-05-14)
**Date**: 2026-05-14
**Scope**: attune-gui cowork dashboard, Specs page
**Touches**: `sidecar/attune_gui/templates/specs.html` (template only)

---

## 1. Audit of the current rendered list

**Surface**: `sidecar/attune_gui/templates/specs.html`, backed by
`/api/cowork/specs` from `cowork_specs.py` (federated multi-root
since PR #30).

**Volume today** (if all sibling specs roots are federated):

| Project       | Spec count |
| ------------- | ---------- |
| attune-ai     | 22         |
| attune-gui    | 6          |
| **Total**     | **28**     |

Realistic ceiling within ~6 months: 40–50 (attune-ai's
test-quality-program alone is producing ~1 spec/week).

**Per-row content** (left → right):

1. Feature slug (link to most-advanced phase file)
2. Phase badge (Requirements / Design / Tasks — the most
   advanced file only)
3. Status badge (draft / in-review / approved / complete /
   completed / done — only the most-advanced file's value)
4. Up to 3 file links (`requirements.md`, `design.md`,
   `tasks.md`)
5. One conditional "+ Design" / "+ Tasks" button

**Data the API already provides but the template DOES NOT
render**:

- `spec.project` — derived from root path (e.g. `attune-ai`,
  `attune-gui`). **Approved for rendering.**
- `spec.root` — absolute path of the source root.
  **Intentionally not rendered** (noise; surfaces filesystem
  paths in the UI).
- `spec.collision` — boolean, true when two roots both have a
  spec with the same slug. **Intentionally not rendered**;
  the natural "same slug appears under two project sections"
  is the visual signal instead.

**Dominant UX problem**: **the federation is invisible**. PR
#30 plumbed `project` onto every row, but the template doesn't
render it. The user sees 28 undifferentiated rows and has no
signal for which project owns each spec — exactly the
information the federation work was meant to surface. Density
and lack of filtering are secondary; project anonymity is
primary.

Secondary problems (not addressed by Option A grouping): no
filter, no sort affordance, **phase column collapses
progression to a single most-advanced badge**, **status column
hides older-phase state**. Grouping by project is orthogonal
to these — sections fix federation invisibility but each row
still under-reports the spec's actual state. A follow-on for
the per-row collapse is in §6.

---

## 2. Three candidate groupings

### A. Group by project

Render one collapsible section per project (e.g. `<details>`
per `project` value), with rows nested inside.

- **Clearer**: where each spec lives; which project owns the
  flow; collisions stand out (same slug under two sections).
  Federation becomes a first-class navigation axis.
- **Harder**: doesn't help find "what's in-review across all
  projects right now." Users who think workflow-first
  (status-driven) get an extra click per section.

### B. Group by status

Render one section per status bucket — `In-flight` (draft +
in-review), `Approved`, `Complete`, `No status`.

- **Clearer**: shows what's actually moving today; surfaces
  the "approved but not started" backlog and "in-flight"
  WIP at a glance.
- **Harder**: project context still invisible; same slug
  from two projects collides visually inside the same
  bucket. Status is single-axis but specs are
  multi-phase — a spec with `requirements.md=approved` and
  `design.md=draft` only shows up under the most-advanced
  status, which today is collapsed badly.

### C. Sort by recency (no grouping)

Sort rows by most-recent `mtime` of any phase file,
descending. No sections, just a different default order.

- **Clearer**: surfaces what's been touched lately; matches
  the "what was I working on?" mental model.
- **Harder**: not actually a grouping — density problem
  unchanged. Requires a new backend field (`mtime`) and
  doesn't address the federation invisibility at all.

---

## 3. Recommendation: Group by project (Option A) — approved

**Why**:

1. PR #30 is the most recent investment in this surface, and
   its central value-prop — federated multi-root listing — is
   currently invisible to the user. Option A is the change
   that *makes the recent investment legible*.
2. Project is a stable axis (changes only when a root is
   added/removed), so grouping is durable. Status is a
   churning axis that would re-shuffle the layout on every
   spec edit.
3. Option A composes cleanly with future filters (status,
   recency) — sections can be filtered independently. Option
   B chosen first would force a re-grouping later when
   federation becomes painful.
4. Collisions render naturally: same slug appearing under two
   project sections is the visual signal, replacing the
   currently-unrendered `collision` flag.

**Default state**: section for the active workspace project
expanded; sibling projects collapsed. (If
`get_workspace()` returns a path, that project's section
opens by default; otherwise the first root's section
opens.)

---

## 4. Implementation cost

| Surface | Change | Lines |
| --- | --- | --- |
| Template `specs.html` | Wrap the existing `{% for s in specs %}` in `{% for project, group in specs\|groupby('project') %}` + `<details><summary>{{ project }} ({{ group\|length }})</summary>` | ~10 lines Jinja |
| CSS | None required — `<details>` is browser-native. Optional 1-line polish: `summary { cursor: pointer; padding: 0.5rem 0; }` | 0–1 |
| JS | None | 0 |
| Backend | None — `project` already on every row | 0 |
| Tests | One template-render test asserting two distinct `<details>` blocks when `project` differs | ~15 lines pytest |

**Total**: one PR, single file mainly. Estimate 30–45 minutes
including a test.

---

## 5. Out of scope (explicitly not proposed)

- Filtering (status, project, text search)
- Sort affordances
- Multi-phase progress bar in the Phase column
- Per-phase status rendering
- Recency / `mtime` data
- Collision UI beyond the natural "same slug in two
  sections" visual

Each of these is a separate proposal. This one is the
cheapest unlock for the largest existing-but-hidden value.

---

## 6. Follow-on: per-row phase tracker (not in this PR)

Fix for the per-row collapse without adding columns:
replace `Phase` + `Status` (two columns) with one 3-cell
inline tracker — `R · D · T` — where each cell is a small
badge colored by that file's own status (gray=missing,
amber=draft, blue=in-review, green=approved/complete).
Hover text: `requirements.md: approved`.

Shows progression at a glance ("R green, D amber, T empty"
= design in progress) and surfaces per-phase status, not
just most-advanced. Same horizontal footprint as today.

Cost: ~15 lines Jinja, ~10 lines CSS, 0 JS, ~5 lines
backend to add per-file status to `_scan_feature`. Ship
after the grouping PR; deserves its own review because it
touches the API shape. Surfaced here so it isn't lost.
