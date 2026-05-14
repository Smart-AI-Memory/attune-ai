# Tasks — Ops Dashboard Polish

**Status:** draft
**Owner:** Patrick

Cross-references the QA punch list at
[../ops-dashboard-qa-2026-05-14/punch-list.md](../ops-dashboard-qa-2026-05-14/punch-list.md).
Each task names the punch-list ID it closes (PL-Pn-m).

Status column legend: `todo` / `in-progress` / `pr-open` /
`pr-merged` / `done`.

---

## Phase A — Visible bug fixes (ship before publishing)

**Goal:** the dashboard no longer signals "under construction" at a
glance. Each PR is ~1 production file + tests, reviewable in under
15 minutes.

| ID | Task | Status | Closes | PR |
|----|------|--------|--------|----|
| A1 | Fix Home KPI / Daily activity field-name bug (`event.get("timestamp")` → `event.get("ts") or event.get("timestamp")`); add regression test asserting non-zero KPI count when telemetry has events | todo | PL-P1-1 | — |
| A2 | Fix scope-textbox always-visible CSS bug (`.scope-custom` `display: block` overrides HTML `hidden` attr); use `display:none` by default + JS toggles `.is-visible` class, OR keep `hidden` semantics with `[hidden] { display: none !important }`; add Playwright/JS test asserting textbox hidden on first paint | todo | PL-P1-2 | — |
| A3 | Per-workflow default scope (instead of all-workflows-default-to-first-feature). Server picks a workflow-relevant default from `features.yaml` based on each workflow's `primary_path` field (add field if missing); JS first-load fallback uses that per-row default | todo | PL-P1-3 | — |

**Phase A definition of done:** A1, A2, A3 all merged. KPIs show
real numbers in dev. Scope textbox only appears for "Custom path…".
Each workflow's default scope is plausible (e.g. `bug-predict` →
`src/attune/security/` not `src/attune/agents/`).

---

## Phase B — A11y + behavioral polish

**Goal:** the dashboard reads correctly to a screen reader, the
keyboard-nav path is unbroken, and the recoverability gaps
(refresh, eviction) are closed.

| ID | Task | Status | Closes | PR |
|----|------|--------|--------|----|
| B1 | Add `aria-label="Run {{ workflow_name }}"` to every Workflows-page Run button; verify with screen-reader simulation; add test grepping rendered HTML for unique aria-labels | todo | PL-P2-1 | — |
| B2 | Fix Run-view 404 on refresh by adding disk-fallback to `runs/{id}/view` route: if not in `RunnerService._runs`, read `~/.attune/ops/runs/<wf>/<id>.json` and render; add test that simulates eviction | todo | PL-P2-2 | — |
| B3 | Cache-bust static JS on release: `<script src="...runner.js?v={{ attune.__version__ }}">` in `base.html`; verify cached old-JS scenario via integration test | todo | PL-P2-3 | — |
| B4 | Make Home "Recent runs" rows fully clickable (entire `<tr>` links to `/runs/<id>/view`, not just the workflow-name and run-id cells); preserve keyboard focusability | todo | PL-P2-4 | — |
| B5 | Relabel `Stages: 0` for meta-orchestration workflows to something honest (`Stages: meta`, `Stages: orchestrated`, or hide the column for those rows); decide between code-fix vs label-fix as part of the PR | todo | PL-P2-5 | — |

**Phase B definition of done:** B1–B5 all merged. A keyboard-only
user can navigate every Workflows row and trigger Run. Browser
refresh on `/runs/<id>/view` always renders the run if its JSON
file exists. New releases don't blank out for returning users.

---

## Phase C — New surfaces (Memory + Sessions read-only views)

**Goal:** close the "Operations dashboard for the workflow OS"
framing promise. Memory and Sessions were listed in the original
QA scope but don't exist as pages.

| ID | Task | Status | Closes | PR |
|----|------|--------|--------|----|
| C1 | `/memory` page: read-only view of `~/.attune/memory/` — list top-level memory keys, allow click-through to view value JSON; pagination if >50 keys; same table styling as Specs | todo | PL-P3-A | — |
| C2 | `/sessions` page: read-only view of `~/.attune/sessions/` — most-recent-first list of session JSONL summaries (start time, duration, project, workflow count if any); link to viewing raw JSONL with syntax highlighting | todo | PL-P3-B | — |
| C3 | Add `/memory` and `/sessions` to top nav; add Memory/Sessions counters to Home KPI grid if data exists | todo | PL-P3-C | — |

**Phase C definition of done:** C1–C3 all merged. Top nav shows
Memory and Sessions tabs. Each page renders even when its
underlying directory is empty (proper empty state). KPI tiles for
memory/sessions counts live on Home.

---

## Phase D — Audit pass (cross-cutting polish)

**Goal:** the cross-cutting consistency work that's cheaper to do
as a single sweep than as N small PRs.

| ID | Task | Status | Closes | PR |
|----|------|--------|--------|----|
| D1 | Tooltip system unification: every existing `title=` attribute in the dashboard converted to `data-tooltip` (the fast CSS system PR #358 introduced); deprecate native title via grep test in CI | todo | PL-P3-1 | — |
| D2 | Empty/error-state sweep: each page must render meaningfully when its data source is empty / unreachable / missing. Specifically: Specs with no docs/specs/, Workflows with no installed `attune-ai`, Health with `ANTHROPIC_API_KEY` unset, Telemetry with empty jsonl, Run history with no runs | todo | PL-P3-2 | — |
| D3 | Keyboard-nav audit: every interactive element reachable via Tab in logical order; Enter/Space activates buttons and pills; Escape cancels edit mode; visible focus rings on all interactive elements (not just outline-color tweaks) | todo | PL-P3-3 | — |
| D4 | Color-contrast a11y audit: verify status pills (`chip-ok`/`chip-warn`/`chip-muted`/`chip-custom`) pass WCAG AA contrast against their backgrounds in both light and (future) dark mode; document any failures in this spec | todo | PL-P3-4 | — |
| D5 | Fix project-name-shows-worktree-slug header bug (P3-11a): read `name` from `pyproject.toml` in `project_root`, fall back to `Path.name` if no pyproject; small one-file change | todo | PL-P3-11a | — |
| D6 | Visual consistency sweep: same table padding everywhere, same hover affordances, same empty-state typography, same chip styling across pages | todo | PL-P3-5 | — |

**Phase D definition of done:** D1–D6 all merged. The CSS tooltip
system is the only tooltip system. All pages handle empty data.
Keyboard-only navigation is unbroken. Color contrast verified on
all chip variants. Worktree-launched dashboard shows the project
name, not the worktree slug.

---

## Parallelism strategy

Phases A and B can pipeline: while A1 is in review, A2 can be in
progress in another session. Don't pipeline within a phase across
items that touch the same file (A1 and A2 both edit Home assets;
A2 and A3 both edit Workflows-page assets — sequence those).

Phase C is genuinely additive (new routes, new templates) and can
run in parallel with Phase B in a second worktree if available.

Phase D needs Phase B (CSS tooltip system rolled out further) and
should not start until Phase B's PRs are merged.

---

## Sizing summary

- **Phase A**: 3 PRs, ~4-6 hours total (KPI fix is 5 minutes; the
  other two are 1-2h each with tests).
- **Phase B**: 5 PRs, ~1-1.5 days total.
- **Phase C**: 3 PRs, ~2-3 days total (new templates + routes,
  more code per PR).
- **Phase D**: 6 PRs, ~1-1.5 days total (mostly mechanical).

**Critical path**: Phase A is the gating publish-readiness work.
If publishing pressure is high, ship after Phase A. Phase B brings
the dashboard to "professional grade looks right." Phases C and D
are the difference between "looks right" and "feels right" and
can land post-publish without embarrassment.

---

## What goes in CLAUDE.md when each phase finishes

After each phase merges, append the lessons learned (one per
recurring failure pattern) to CLAUDE.md per the project convention.
Specifically watch for:

- Field-name drift between writer and reader (the `ts`/`timestamp`
  bug — likely the underlying lesson is "audit field names with a
  one-line grep before shipping a new reader").
- HTML `hidden` attribute being overridden by author CSS (the
  scope-textbox bug — likely needs a `[hidden] { display: none
  !important }` blanket rule somewhere).
- Per-workflow defaults vs global fallbacks (A3 — the lesson is
  about feature-keyed vs path-keyed config schemas, similar to
  the attune-help summaries.json drift documented in CLAUDE.md).
