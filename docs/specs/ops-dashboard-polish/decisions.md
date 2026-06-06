# Decisions — Ops Dashboard Polish
**Status:** partial — Phase A complete; Phase B (4/5), C (Sessions shipped, Memory not started), D (1/6) in progress
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
