# Tasks — Ops Dashboard Polish

**Status:** parked (2026-07-13) — Phases A+B shipped (#361 #365 #367; B2 in #371), C2 Sessions (#377 #387 #390), D5 (#376); remaining: C1 /memory page, C3 memory nav+KPIs, D1 sweep+CI gate, D2-D4, D6 · Resume-Trigger: evergreen (no external clock).
**Owner:** Patrick

Cross-references the QA punch list at
[../ops-dashboard-qa-2026-05-14/punch-list.md](../ops-dashboard-qa-2026-05-14/punch-list.md).
Each task names the punch-list ID it closes (PL-Pn-m).

Status column legend: `todo` / `in-progress` / `pr-open` /
`pr-merged` / `done`.

---

## Phase A — Visible bug fixes (ship before publishing) ✓ complete

**Goal:** the dashboard no longer signals "under construction" at a
glance. Each PR is ~1 production file + tests, reviewable in under
15 minutes.

| ID | Task | Status | Closes | PR / commit |
|----|------|--------|--------|----|
| A1 | Fix Home KPI / Daily activity field-name bug (`event.get("timestamp")` → `event.get("ts") or event.get("timestamp")`); add regression test asserting non-zero KPI count when telemetry has events | done | PL-P1-1 | code: `src/attune/ops/data.py:850`; tests: `tests/unit/ops/test_telemetry_summary.py` (4 cases — `ts` recognized, legacy `timestamp` fallback, mixed-schema file, missing-timestamp) |
| A2 | Fix scope-textbox always-visible CSS bug (`.scope-custom` `display: block` overrides HTML `hidden` attr); use `display:none` by default + JS toggles `.is-visible` class, OR keep `hidden` semantics with `[hidden] { display: none !important }`; add Playwright/JS test asserting textbox hidden on first paint | done | PL-P1-2 | code: `src/attune/ops/static/css/main.css:941-965` (uses `.scope-custom:not([hidden])` selector so the user-agent `[hidden] { display: none }` still wins on first paint) |
| A3 | Per-workflow default scope (instead of all-workflows-default-to-first-feature). Server picks a workflow-relevant default from `features.yaml` based on each workflow's `primary_path` field (add field if missing); JS first-load fallback uses that per-row default | done | PL-P1-3 | PR [#365](https://github.com/Smart-AI-Memory/attune-ai/pull/365) (commit `986fab1f`) |

**Phase A definition of done:** ✓ All three items shipped. KPIs show real numbers in production (regression test locks the `ts`/`timestamp` contract). Scope textbox only appears for "Custom path…" (CSS uses `:not([hidden])` so the user-agent rule wins by default). Each workflow's default scope is auto-derived from `features.yaml` `primary_path`.

---

## Phase B — A11y + behavioral polish (4/5 shipped)

**Goal:** the dashboard reads correctly to a screen reader, the
keyboard-nav path is unbroken, and the recoverability gaps
(refresh, eviction) are closed.

| ID | Task | Status | Closes | PR / location |
|----|------|--------|--------|----|
| B1 | Add `aria-label="Run {{ workflow_name }}"` to every Workflows-page Run button; verify with screen-reader simulation; add test grepping rendered HTML for unique aria-labels | done | PL-P2-1 | `src/attune/ops/templates/workflows.html:128` (`aria-label="Run {{ w.name }}"`); test coverage to verify in a follow-up |
| B2 | Fix Run-view 404 on refresh by adding disk-fallback to `runs/{id}/view` route: if not in `RunnerService._runs`, read `~/.attune/ops/runs/<wf>/<id>.json` and render; add test that simulates eviction | done | PL-P2-2 | verified done 2026-07-21 (row was stale): `RunnerService.get_or_load` walks the persistence dir on memory miss; route wires it with `loaded_from_disk` (empty `stream_url`, server-rendered lines); 10 tests in `tests/unit/ops/test_persistence_and_history.py` incl. eviction fallback + 404 |
| B3 | Cache-bust static JS on release: `<script src="...runner.js?v={{ attune.__version__ }}">` in `base.html`; verify cached old-JS scenario via integration test | done | PL-P2-3 | `src/attune/ops/templates/base.html:7` ("Release-keyed cache-bust" comment); `attune_version` exposed as Jinja global at `server.py:86` |
| B4 | Make Home "Recent runs" rows fully clickable (entire `<tr>` links to `/runs/<id>/view`, not just the workflow-name and run-id cells); preserve keyboard focusability | done | PL-P2-4 | `src/attune/ops/templates/home.html:89-105` — implementation wraps each `<td>` in `<a class="row-link">` rather than using `<tr data-href>`, but functionally equivalent (whole row clickable, tab-stop preserved via `tabindex="-1"` on inner cells) |
| B5 | Relabel `Stages: 0` for meta-orchestration workflows to something honest (`Stages: meta`, `Stages: orchestrated`, or hide the column for those rows); decide between code-fix vs label-fix as part of the PR | done | PL-P2-5 | PR [#367](https://github.com/Smart-AI-Memory/attune-ai/pull/367) — meta-orchestration tooltip at `workflows.html:55` ("Meta-orchestration workflow — composes other workflows rather than declaring its own stages.") |

**Phase B definition of done:** 4/5 shipped. Remaining: B2 disk-fallback for evicted runs.

---

## Phase C — New surfaces (Memory + Sessions read-only views) (Sessions shipped; Memory not started)

**Goal:** close the "Operations dashboard for the workflow OS"
framing promise. Memory and Sessions were listed in the original
QA scope but don't exist as pages.

| ID | Task | Status | Closes | PR / location |
|----|------|--------|--------|----|
| C1 | `/memory` page: read-only view of the memory serving layer — premise re-validated 2026-07-21 (decisions.md): targets the post-#1239 Redis-derived index (`attune:memory:*`), not the retired `~/.attune/memory/`; family counts + paginated node table + detail view, degrade-on-unreachable | pr-open | PL-P3-A | held draft (2026-07-21): `src/attune/ops/memory_data.py`, `routes/memory.py`, `templates/memory{,_node}.html`, tests in `tests/unit/ops/test_memory_page.py` |
| C2 | `/sessions` page: read-only view of `~/.attune/sessions/` — most-recent-first list of session JSONL summaries (start time, duration, project, workflow count if any); link to viewing raw JSONL with syntax highlighting | removed | PL-P3-B | shipped in #377/#387/#390, then **deliberately removed in [#1545](https://github.com/Smart-AI-Memory/attune-ai/pull/1545)** (chair-ruled 2026-07-21); summarizer/cache kept surface-less |
| C3 | Add `/memory` and `/sessions` to top nav; add Memory/Sessions counters to Home KPI grid if data exists | pr-open | PL-P3-C | `/sessions` in top nav (server.py); `/memory` nav + Home "Memory nodes" KPI (hides on unreachable Redis) ride in the C1 held draft (2026-07-21) |

**Phase C definition of done:** Partial — Sessions shipped end-to-end; Memory (C1) and the Memory portion of C3 + KPI counters remain.

---

## Phase D — Audit pass (cross-cutting polish) (1/6 shipped, 1/6 partial)

**Goal:** the cross-cutting consistency work that's cheaper to do
as a single sweep than as N small PRs.

| ID | Task | Status | Closes | PR / location |
|----|------|--------|--------|----|
| D1 | Tooltip system unification: every existing `title=` attribute in the dashboard converted to `data-tooltip` (the fast CSS system PR #358 introduced); deprecate native title via grep test in CI | pr-open | PL-P3-1 | rollout in PR [#367](https://github.com/Smart-AI-Memory/attune-ai/pull/367); sweep + CI gate in held draft [#1571](https://github.com/Smart-AI-Memory/attune-ai/pull/1571) (lifts post-10.6.0-tag): last convertible `title=` → `data-tooltip`+`aria-label`; `<option>` titles sanctioned (CSS tooltips can't render there); gate `tests/unit/ops/test_template_tooltips.py` |
| D2 | Empty/error-state sweep: each page must render meaningfully when its data source is empty / unreachable / missing. Specifically: Specs with no docs/specs/, Workflows with no installed `attune-ai`, Health with `ANTHROPIC_API_KEY` unset, Telemetry with empty jsonl, Run history with no runs | pr-open | PL-P3-2 | sweep executed 2026-07-21 as `tests/unit/ops/test_empty_states.py` (9 assertions, all green with NO production changes — Phases A/B had handled the states; the suite is the lock). Findings in decisions.md |
| D3 | Keyboard-nav audit: every interactive element reachable via Tab in logical order; Enter/Space activates buttons and pills; Escape cancels edit mode; visible focus rings on all interactive elements (not just outline-color tweaks) | pr-open | PL-P3-3 | audited 2026-07-21 (decisions.md): tab order / Escape / focus-visible coverage pass; ONE defect fixed — editable status pill suppressed its focus ring |
| D4 | Color-contrast a11y audit: verify status pills (`chip-ok`/`chip-warn`/`chip-muted`/`chip-custom`) pass WCAG AA contrast against their backgrounds in both light and (future) dark mode; document any failures in this spec | pr-open | PL-P3-4 | audited 2026-07-21 with measured ratios (decisions.md): ok/warn pass both modes; `.chip-muted` hard-fail fixed (2.31→4.39 light / 6.58 dark); 0.11 residual to strict AA flagged for the chair |
| D5 | Fix project-name-shows-worktree-slug header bug (P3-11a): read `name` from `pyproject.toml` in `project_root`, fall back to `Path.name` if no pyproject; small one-file change | done | PL-P3-11a | PR [#376](https://github.com/Smart-AI-Memory/attune-ai/pull/376) — `derive_project_name` at `src/attune/ops/data.py:289` |
| D6 | Visual consistency sweep: same table padding everywhere, same hover affordances, same empty-state typography, same chip styling across pages | done | PL-P3-5 | audited 2026-07-21 (decisions.md): tables/chips single-sourced with documented overrides; dual empty-state idiom ruled a convention (rich = page-level absence, `p.empty` = inline) |

**Phase D definition of done:** Remaining: D1 sweep + CI grep-test gate, D2 empty/error sweep, D3 keyboard-nav, D4 color-contrast, D6 visual consistency.

---

## Phase E — Library Health snapshot tab (2026-07-14, in progress)

**Goal:** productize `docs/reports/library-health-2026-07-14.md` into
a standing, deterministic-only dashboard tab. See decisions.md's
Phase E section for the three ratified decisions this phase
implements.

| ID | Task | Status | Closes | PR / location |
|----|------|--------|--------|----|
| E1 | Docs-only spec amendment recording decisions 1-3 (this commit) | done | — | `docs/specs/ops-dashboard-polish/decisions.md`, `tasks.md` |
| E2 | `health_snapshot.py` collector: per-signal degradation, atomic versioned JSON write, `python -m attune.ops.health_snapshot` CLI entry | done | — | `src/attune/ops/health_snapshot.py` |
| E3 | `/health/library` page + `/health/library/refresh` POST + `/api/health/library/status` poll route; staleness-aware auto-refresh on GET | done | — | `src/attune/ops/routes/health_library.py`, `templates/health_library.html` |
| E4 | Unit + route test coverage (collector per-signal degradation, atomic write, schema shape; route renders latest, stale badge, refresh POST) | done | — | `tests/unit/ops/test_health_snapshot.py`, `tests/unit/ops/test_health_library_route.py` |

**Phase E definition of done:** the tab renders the deterministic
snapshot with a stale badge and working Refresh button; the collector
never crashes on a missing network/CLI dependency; 80%+ coverage on
the new module.

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

- **Phase A**: 3 PRs, ~4-6 hours total — ✓ shipped.
- **Phase B**: 5 PRs, ~1-1.5 days total — 4/5 shipped; B2 (run-view disk-fallback) remaining.
- **Phase C**: 3 PRs, ~2-3 days total — C2 shipped; C1 (`/memory` page) + C3 Memory portion + KPI counters remaining.
- **Phase D**: 6 PRs, ~1-1.5 days total — D5 shipped; D1 partial; D2–D4 + D6 remaining.

**Critical path**: Phase A complete (publish-ready gate met as of v7.0.0). Remaining items in B/C/D are post-publish polish — none blocks shipping. **Remaining concrete work (5 items + 1 partial):** B2, C1, C3-memory, D2, D3, D4, D6 (todo); D1 (partial — sweep + CI gate).

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
