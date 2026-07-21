# Decisions — Ops Dashboard Polish
**Status:** parked (2026-07-13 chair park, T1 of
`q-briefing-triage-001`; progress snapshot 2026-07-20: Phase A
complete, B 4/5, C Sessions shipped / Memory not started, D 1/6)
· Resume-Trigger: evergreen (no external clock)
**Owner:** Patrick
**Opened:** 2026-05-14
**Predecessors:**

- [PR #358](https://github.com/Smart-AI-Memory/attune-ai/pull/358) — Specs page width + compact status pills + fast CSS tooltips + Updated column with a11y
- [docs/specs/ops-runner-tier2](../ops-runner-tier2/) — scope picker, persisted runs, chainable pills
- [docs/specs/ops-dashboard-qa-2026-05-14](../ops-dashboard-qa-2026-05-14/punch-list.md) — full QA punch list (this spec selects and sequences the items)

---

## Problem

PR #358 closes the largest Specs-page UX gap, but a QA walk on
2026-05-14 surfaced ~14 polish items across the rest of the dashboard.
Without a disciplined plan, the natural failure mode is two:

1. **Cherry-pick the visible bugs** (the ones a screenshot would
   expose), ship a release, and silently carry the rest as
   "we'll get to it." The strategic gaps (Memory / Sessions pages,
   keyboard-nav audit) never land.
2. **Try to fix everything in one heroic PR** and stall on review
   surface area. Touching dashboard.py + 8 templates + the JS in
   one diff is unreviewable.

This spec breaks the punch list into four phases sequenced so each
is independently shippable, independently reversible, and each
phase's PRs review in under an hour. The top-3 visible bugs land
first because they're the difference between "demo-ready" and
"clearly under construction."

---

## Decision

**Four phases, each a small set of focused PRs (no PR touches more
than ~3 production files):**

- **Phase A — Visible bug fixes** (top 3 from QA walk). Ship before
  any external mention of the dashboard. ~4-6 hours total.
- **Phase B — A11y + behavioral polish** (mostly mechanical fixes).
  Ships the dashboard to "professional grade looks right" bar.
  ~1-1.5 days total.
- **Phase C — New surfaces** (Memory, Sessions read-only views).
  Closes the "Operations dashboard for the workflow OS" framing
  promise. ~2-3 days total.
- **Phase D — Audit pass** (empty states, keyboard nav, tooltip
  unification, design consistency). The cross-cutting work that
  benefits from a full sweep at the end rather than in pieces.
  ~1-1.5 days total.

Sequencing rationale: Phase A bugs are visible to anyone who looks.
Phase B touches the same files Phase A does and benefits from
Phase A's CI/test scaffolding being fresh. Phase C is genuinely
additive (new routes) so it can run in parallel with Phase B if
two sessions are available. Phase D needs Phase B's CSS-tooltip
system applied everywhere as a prerequisite — last on purpose.

---

## Discipline rules (apply to every PR in every phase)

1. **One PR per item.** No "and while we're here" creeping scope.
   The QA punch list already establishes the item-by-item
   accounting; the phase grouping is for ordering, not bundling.
2. **Every PR includes the test that would have caught the bug.**
   Especially the Phase A CI failures — bugs that escaped the test
   suite for months need a regression guard, not just a fix.
3. **Every PR's commit message names the QA punch-list ID it
   resolves** (e.g., "Resolves QA-P1-1: Home KPIs read wrong
   telemetry field"). When the spec closes out, we should be able
   to walk the punch list and tag each item with its closing PR.
4. **No PR sits open more than one working day.** Small PRs review
   fast; if reviewers stall, that's a process problem, not a
   "keep growing the PR" problem.
5. **Phase boundaries are commit-fences, not approval-fences.**
   When Phase A's PRs all merge, write a 1-line note in this
   `decisions.md` and move to Phase B. No formal sign-off needed;
   the punch list is the source of truth on completeness.

---

## Out of scope

- **The QA punch list's P3-11a (project name shows worktree slug)**
  is included in Phase D, not Phase A — it only affects local
  worktree development and isn't visible to dashboard users.
- **Dashboard publishing / release announcement.** This spec gets
  the dashboard to ready-to-publish state; the publishing decision
  is separate.
- **`feat/ops-dashboard-help-templates`** in-flight work on the
  3 `.help/templates/ops-dashboard/*.md` files — that's a separate
  effort already in progress; not duplicated here.
- **`runner.js` / `workflows.html` Workflows-page edits** sitting
  in the `exciting-roentgen-1d3e0d` worktree — those are someone
  else's in-flight work. If they land before this spec executes,
  this spec rebases on them; if they don't, this spec stands on
  PR #358 + main.

---

## Success criteria

The spec is complete when:

- Every QA punch-list item with severity P1 or P2 has a closing
  PR linked from the punch list.
- The dashboard renders cleanly at 1366px and 1920px on the seven
  pages walked in QA (Home, Workflows, Specs, Memory, Sessions,
  Health, Telemetry, Run history) with no horizontal scroll, no
  empty-state-when-data-exists glitches, no aria-label gaps on
  interactive controls.
- A first-time viewer comparing the dashboard to GitHub / Linear /
  Vercel dashboards wouldn't immediately spot something obviously
  unfinished.

The spec retires when Phase D's PRs merge. Lessons accumulated
during execution roll up into CLAUDE.md per the project convention.

---

## Phase E — Library Health snapshot tab (2026-07-14)

**Predecessor:** [docs/reports/library-health-2026-07-14.md](../../reports/library-health-2026-07-14.md)
— the ad-hoc report this phase productizes into a standing dashboard
surface.

### Problem

The library-health report was a manually-run, one-off sweep
(coverage, complexity, churn, docs gates, hygiene counts). Re-running
it requires a session and LLM judgment every time, even though most
of its signal is deterministic and cheap to recompute. Patrick wants
a standing dashboard tab that shows the deterministic half live,
without spending LLM credits on every page load.

### Decision

Three ratified decisions (2026-07-14), implemented verbatim in
`feat/ops-health-tab`:

1. **Deterministic-only snapshot.** The new tab renders a metrics
   snapshot computed from local/cheap sources only: coverage (Codecov
   API), radon complexity summary (avg + D-or-worse count), git-log
   churn, the four docs gates (`scripts/audit_doc_imports.py`,
   `scripts/audit_docs_wiring.py`, `scripts/check_help_completeness.py`,
   `attune.authoring.projector.check_projection_drift`), SLOC/file/
   test counts, TODO-marker count, and open PRs/issues via the `gh`
   CLI. The LLM judgment layer (the narrative findings + ranked
   improvement plan a human session produces) is **never regenerated**
   by this tab — it stays a link to the latest
   `docs/reports/library-health-*.md`.
2. **Staleness-aware refresh, no scheduler.** On tab load, if the
   latest persisted snapshot is older than 12h, the page kicks a
   background-thread refresh and renders the *previous* snapshot
   immediately (with its `collected_at` timestamp and a stale badge)
   rather than blocking the request on live collection. An explicit
   Refresh button triggers the same collector on demand. No cron, no
   scheduler process — refresh only happens on page load or user
   action.
3. **Docs-first sequencing.** Because the spec-freeze forbids new
   spec directories, this work amends the existing
   `ops-dashboard-polish` spec (this section) rather than opening a
   new one, and the first commit on the branch is this documentation
   change — code follows in a second commit.

### Naming note (deviation, not a ratified decision)

The existing `/health` route (`src/attune/ops/routes/dashboard.py`,
`templates/health.html`) is **Environment Health** — Python version,
platform, `~/.attune` state-file presence. It predates this phase and
is unrelated to the library-health metrics snapshot. To avoid
colliding two different concepts under one URL/nav label, this phase
ships the new surface at **`/health/library`** with its own nav entry
("Library Health") rather than overloading `/health`. The existing
Environment Health page is untouched. If Patrick later wants the two
merged or the existing page renamed, that's a follow-up — out of
scope here per the "one PR per item" discipline rule.

### Implementation

- `src/attune/ops/health_snapshot.py` — the collector. Each signal
  (coverage, complexity, churn, four docs gates, SLOC, TODOs, open
  PRs/issues) degrades independently to
  `{"status": "unavailable", "reason": ...}` on failure; the snapshot
  itself never raises. Versioned JSON (`schema_version: 1`) written
  atomically to `<attune_home>/ops/health/<timestamp>.json` +
  `latest.json`, mirroring `sweep_results.py`'s tempfile+`os.replace`
  pattern.
- `python -m attune.ops.health_snapshot` — standalone CLI entry for
  cron-free manual/CI collection.
- `src/attune/ops/routes/health_library.py` — `GET /health/library`
  (renders `latest.json`, kicks a background refresh if stale),
  `POST /health/library/refresh` (explicit manual trigger,
  client-token gated), `GET /api/health/library/status` (JS poll
  target for the in-flight refresh).
- `src/attune/ops/templates/health_library.html` — scoreboard tiles,
  gates table, hotspots table, stale badge, link to the latest LLM
  report.

### Out of scope (this phase)

- Regenerating or summarizing the LLM report — link only.
- A scheduler/cron for background collection — decision 2 is
  explicit: page-load and Refresh-button triggers only.
- Renaming/merging the existing `/health` Environment Health page.

## D2 sweep executed + Phase C status truth (2026-07-21)

**D2 (empty/error-state sweep):** the unified pass exists as
`tests/unit/ops/test_empty_states.py` — every page on main renders
meaningfully against a blank project root / empty telemetry / no
runs / no key / no snapshot (9 assertions, all passing WITHOUT
production changes — Phases A/B already handled the states; D2's
deliverable is the regression LOCK). Two findings from the sweep:

- **Run history is an API surface** (`/api/runs/{workflow}` feeding
  the workflows page), not a page — the D2 row's "Run history with
  no runs" is asserted as clean-empty-JSON.
- **C2/Sessions status truth:** the Sessions page was built
  (#377/#387/#390) and then **deliberately removed in #1545**
  (chair-ruled 2026-07-21; −1,215 lines; summarizer/cache kept,
  surface-less). C2's "done ... template at templates/sessions.html"
  row no longer describes main; updated to "removed".

**Flag for the chair (Monday, with held draft #1576):** C1 /memory
was built the same day #1545 ruled Sessions OFF the dashboard. The
rationales differ (Patterns was structurally empty; /memory has
~1,050 live keys and serves the memory-is-the-product thesis), but
the same ops-research lens could rule a memory browse page off too.
#1576 is a held draft precisely so this is a deliberate Monday call,
not a default-in.

## C1 premise re-validated — /memory targets the Redis-derived index (2026-07-21)

The original C1 row ("read-only view of `~/.attune/memory/` — list
top-level memory keys") predates memory-unification (#1239). That
directory is dev scratch today; the real serving layer is the local
Redis derived index — `attune:memory:*` hashes hydrated at session
start from the tracked corpus (lessons, file pointers, edges,
curated nodes; ~1,050 keys live). C1 built against THAT, preserving
the row's read-only list/click-through/pagination intent:

- `attune.ops.memory_data` (framework-free): family counts,
  paginated rows, node detail. Degradation contract mirrors the
  corpus rule — every function returns `None` when Redis is
  unreachable and the page renders an explanatory empty state,
  never a 500. The detail view refuses keys outside the
  `attune:memory:` namespace (the page must never become a generic
  Redis browser).
- Dogfood catch during the build: the namespace holds a few
  plain-STRING keys (e.g. `attune:memory:context`) — an `HMGET`
  pipeline against them WRONGTYPEs and would have degraded the
  whole page. Fixed with `execute(raise_on_error=False)` + a
  type-dispatching detail read; regression-locked in
  `tests/unit/ops/test_memory_page.py`.
- C3's memory half rides along: `/memory` in the top nav, and a
  Home "Memory nodes" KPI that HIDES on unreachable Redis instead
  of rendering a lying zero.
