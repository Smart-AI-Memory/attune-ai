# Session prompts — ops dashboard step-4 closeout

Four prompts. Copy-paste each into a fresh Claude Code session. P1–P3 can fire in parallel; P4 fires Sunday after the prior three merge.

**Companion plan:** [`_sequencing-ops-dashboard-step4.md`](_sequencing-ops-dashboard-step4.md) (this PR).

**Locked decisions** (drove these prompts):

| Decision | Lock |
|---|---|
| Release cadence | Single release Sunday 2026-05-17 (or next Sunday if dated otherwise). `attune-ai 6.9.0` (minor bump from 6.8.0). v7.0 stays reserved for the 100%-coverage milestone. |
| Phase 4 (ops-runner-tier2 P5–P6) | Defer until after P3 lands; this doc covers P1–P3 + release. |
| `ATTUNE_OPS_SWEEP_RESULTS` gate | Phase 3 makes it default-on with opt-out (`=0` disables); full retirement in a separate follow-up commit ~3 weeks after Sunday (`chore/retire-ATTUNE_OPS_SWEEP_RESULTS-gate`, target 2026-06-07). |
| Smoke-failure handling (P1) | Separate `fix/...` PR, not bundled into the close-out. |
| Plan-doc gating | All four prompts open with a check that the plan doc (this PR) is merged to main before doing anything else. |
| CHANGELOG protocol | Each phase adds entries under `[Unreleased]` with Keep-a-Changelog subsections. Bold lead-in identifying phase + spec. Mechanical merge on conflict. |
| PR description template | Strict template (see prompts) — phase number, scope/acceptance verbatim from spec, test plan, explicit out-of-scope. |
| Cross-references / JSDoc / fixtures / consumer-page audits | Quality requirements embedded in the relevant prompts. |

---

## Prompt 1 — Phase 1: ops-security-hardening close

```text
Project: attune-ai
Mode: (b) Executing a planned spec
Outcome: ops-security-hardening spec marked complete. Phase 5 manual smoke
  verified. Phase 6 close tasks ticked. CHANGELOG entry under [Unreleased].
Done when: every Phase 5 + Phase 6 task in docs/specs/ops-security-hardening/tasks.md
  is checked with the verification artifact recorded inline; the spec's Status
  field reads "complete"; CHANGELOG.md has an entry under [Unreleased] ### Security.

Context:
- A prior session today shipped attune-rag v0.1.19 (Phase 2 of v1.0 roadmap),
  closed attune-rag Phase 3, audited attune-ai's ops dashboard work, pruned 16
  squash-merged ops/dashboard branches, and opened PRs #407 (spec status flip)
  + #408 (sequencing plan + session prompts including this one).
- The audit confirmed P1–P4 of ops-security-hardening are SHIPPED on main.
  Do NOT re-do them. Verify, smoke, tick, ship.
- Sunday's planned release is attune-ai 6.9.0 covering Phase 1 + 2 + 3 of the
  step-4 closeout. Phase 1 is the smallest, so it sets the CHANGELOG tone for
  the others.

FIRST-ACTION GATE (run this BEFORE touching anything else):
  git fetch origin
  git log origin/main --oneline -5
If PR #408's merge commit is not on main, STOP and tell Patrick "PR #408 not
yet merged; cannot proceed without the plan doc on main." Do not work around.

Worktree (only after the gate clears):
  cd /Users/patrickroebuck/attune-ai
  git worktree add .claude/worktrees/ops-security-hardening-close \
    -b chore/ops-security-hardening-close origin/main
  cd .claude/worktrees/ops-security-hardening-close

First steps inside the worktree:
  1. Read docs/specs/ops-security-hardening/tasks.md (Phase 5 + Phase 6 fully;
     Phase 1–4 for context).
  2. Re-state the scope back to Patrick in 5–10 lines, including the specific
     manual-smoke list from Phase 5.
  3. Propose a detailed task breakdown — for each P5 manual smoke, name the
     command/curl/test you'll run + the artifact you'll capture (curl output,
     log line, test ID). For each P6 close, name the file/line you'll touch.
  4. Get Patrick's nod, then execute.

Execution discipline:
- Each manual smoke result records inline in tasks.md under its task line.
  Format: a short paragraph or fenced block with the verification artifact
  (no screenshots needed; copy the relevant log / curl output / test name).
- If a smoke fails, document the failure inline, push an early commit on this
  branch, then OPEN A SEPARATE fix/... branch + PR for the actual bug fix.
  Do not bundle the fix into this close-out PR.
- Spec status field flips to "complete" only after all P5 + P6 tasks check.

CHANGELOG protocol (applies to all step-4 phases for consistency):
- Add entry to CHANGELOG.md under [Unreleased] in the appropriate Keep-a-
  Changelog subsection (### Security for this phase; ### Added or ### Fixed
  in other phases).
- Bold lead-in identifies phase + spec, e.g.:
    - **Ops security hardening complete** (Phase 1 of step-4 closeout,
      docs/specs/ops-security-hardening/). Phase 5 manual smoke + Phase 6
      close-out verified DNS-rebinding middleware, bounded subscriber queue,
      run-view route observability, and the E2E output-replay test.
- Before opening the PR: rebase on latest origin/main. If CHANGELOG conflicts,
  resolve mechanically (each entry is its own bullet).

PR description template (REQUIRED):
  ## Phase
  Phase 1 of 4 in the ops-dashboard step-4 closeout (plan: PR #408).
  ## Scope (verbatim from spec)
  <copy Phase 5 + Phase 6 task list from tasks.md>
  ## Acceptance (verbatim from spec)
  <copy the acceptance criteria; reference user stories / contracts if any>
  ## Test plan
  - [ ] All Phase 5 smoke tasks recorded inline in tasks.md with verification artifact
  - [ ] All Phase 6 close tasks ticked
  - [ ] Spec Status field flipped to `complete`
  - [ ] CHANGELOG.md entry under [Unreleased] ### Security
  - [ ] Rebased on latest origin/main; no conflicts
  ## Out of scope (explicit)
  - Re-implementing any of P1–P4 (they're already on main; this is verification only)
  - Code changes (unless smoke surfaces a real bug → separate PR)
  - Bumping pyproject.toml / __version__ (release-prep PR handles that Sunday)

PR target: main directly. Squash merge.

Critical constraints:
- This is NOT a place to re-implement P1–P4. The audit confirmed they're on
  main. Verify, smoke, tick, ship.
- Today is 2026-05-16 (Saturday). Sunday's release target = 2026-05-17.
  This phase is the smallest of the three; aim to PR-ready by Saturday EOD.
```

---

## Prompt 2 — Phase 2: ops-scope-picker-ia production implementation

```text
Project: attune-ai
Mode: (b) Executing a planned spec
Outcome: The ops dashboard's scope picker remembers the last-used scope and
  pre-selects it on page load. "All code" fallback option lands. localStorage
  round-trip with the design.md's fallback chain works.
Done when: AC-1 through AC-6 from docs/specs/ops-scope-picker-ia/requirements.md
  all pass; tests cover each AC; the picker continues to work correctly on
  EVERY existing consumer page; CHANGELOG.md entry under [Unreleased] ### Added.

Context:
- The design (storage model, fallback chain, edges) is greenlit per
  docs/specs/ops-scope-picker-ia/design.md. Do NOT re-litigate, implement.
- Today's prior session pruned 16 ops branches + opened PRs #407 + #408. The
  plan doc at docs/specs/_sequencing-ops-dashboard-step4.md is the orientation
  point for the step-4 closeout.
- Safe to run in parallel with Phase 1 (security-hardening close) and Phase 3
  (discovery-sweep UI). CHANGELOG [Unreleased] is the only likely conflict.
- Sunday's planned release is attune-ai 6.9.0 (minor bump). Your PR adds an
  entry under [Unreleased] ### Added.

FIRST-ACTION GATE:
  git fetch origin
  git log origin/main --oneline -5
If PR #408's merge commit is not on main, STOP and tell Patrick. Do not
work around.

Worktree:
  cd /Users/patrickroebuck/attune-ai
  git worktree add .claude/worktrees/ops-scope-picker-ia-impl \
    -b feat/ops-scope-picker-ia-impl origin/main
  cd .claude/worktrees/ops-scope-picker-ia-impl

First steps inside the worktree:
  1. Read docs/specs/ops-scope-picker-ia/requirements.md AND design.md fully.
  2. CONSUMER-PAGE AUDIT (highest-impact risk mitigation):
     - Grep the codebase for every template/route that renders or passes
       scope state. Suggested greps:
         git grep -nE "scope_picker|scope-picker|selectedScope|currentScope" -- 'src/attune/ops/'
         git grep -nE "ScopeKind|scope=" -- 'src/attune/ops/'
     - Build a list of consumer pages (e.g. /runs, /specs, /sweep-results, etc.).
     - Report the list to Patrick. Confirm completeness BEFORE writing code.
       Patrick may know of consumer pages not visible from grep.
  3. Map design.md's file list to the actual files in src/attune/ops/. Where
     design.md says "this file" but reality differs, note the divergence and
     ask Patrick before proceeding.
  4. Propose a task breakdown that includes a per-consumer-page smoke
     checklist (every page that uses the picker × every scope-state
     interaction: load, switch, reload, custom-path entry, "All code"
     fallback, unmatched-path fallback).
  5. Get Patrick's nod, then implement.

Implementation discipline (the high-impact risk):
- The scope picker is a SHARED COMPONENT. The implementation MUST be additive:
  - New localStorage layer wraps existing scope-resolution logic, does not
    replace it.
  - Existing pages keep working even if localStorage is empty (i.e. on the
    first-ever load before the user has interacted).
  - The fallback chain (last-used → alphabetically-first feature → "All code")
    activates only when localStorage is empty/invalid.
- Before opening the PR, manually walk EVERY consumer page and verify the
  smoke checklist. Record the walk in the PR description.
- Unit tests must cover AC-1 through AC-6 plus regression tests for each
  consumer page's expected behavior under each scope state.

Quality requirements (Opp 2 — JSDoc):
- Every new function in the scope-picker JS module gets a JSDoc block with
  @param, @returns, and @typedef for any non-trivial object shapes.
- The localStorage value shape gets an explicit @typedef.
- Exported APIs (functions other modules call) get the highest documentation
  level.

CHANGELOG protocol:
- Entry under [Unreleased] ### Added:
    - **Scope picker remembers last-used scope** (Phase 2 of step-4 closeout,
      docs/specs/ops-scope-picker-ia/). localStorage-backed with fallback
      chain: last-used → alphabetically-first feature → "All code". Adds the
      "All code" option for cross-feature views. Read-only on render; writes
      only on user action.
- Rebase before opening PR. Mechanical merge on conflict.

PR description template (REQUIRED):
  ## Phase
  Phase 2 of 4 in the ops-dashboard step-4 closeout (plan: PR #408).
  ## Scope (verbatim from spec)
  <copy from requirements.md + design.md>
  ## Acceptance (verbatim from spec)
  AC-1 through AC-6 from requirements.md
  ## Consumer-page smoke checklist (REQUIRED — walked before this PR is ready)
  - [ ] /runs: <each state walked>
  - [ ] /specs: <each state walked>
  - [ ] <other pages discovered in audit>
  ## Test plan
  - [ ] Unit tests cover AC-1 through AC-6
  - [ ] Regression tests for each consumer page's expected scope behavior
  - [ ] Manual smoke walked on a live local dashboard
  - [ ] JSDoc on every new function + typedef for storage shape
  - [ ] CHANGELOG.md entry under [Unreleased] ### Added
  - [ ] Rebased on latest origin/main; no conflicts
  ## Out of scope (explicit)
  - Refactoring existing scope-resolution logic (additive only)
  - New scope kinds beyond what design.md specifies
  - Bumping pyproject.toml / __version__ (release-prep PR handles that Sunday)

PR target: main directly. Squash merge.

Critical constraints:
- ~5 files, ~100 LOC + ~50–60 tests per design.md. If the diff balloons,
  STOP and ask Patrick whether scope has expanded.
- If consumer-page audit surfaces a page Patrick didn't expect, pause and
  align before writing code touching that page.
- If Phase 3 has already merged with sweep-results UI by the time you ship,
  add /sweep-results to your smoke checklist.
- Target Sunday-night merge so Phase 4 doesn't get backed up.
```

---

## Prompt 3 — Phase 3: discovery-sweep-ops-integration P3–P4 (Dashboard UI)

```text
Project: attune-ai
Mode: (b) Executing a planned spec
Outcome: Sweep results render as chips with drill-in views on the ops
  dashboard. ATTUNE_OPS_SWEEP_RESULTS flips to default-on (opt-out via
  `=0`); the env var is retained for emergency disable but is no longer
  required for the feature to work.
Done when: Phase 3's 6 task checkboxes in
  docs/specs/discovery-sweep-ops-integration/tasks.md are ticked; Phase 4's
  3 task checkboxes are ticked; a reviewer can launch the dashboard with NO
  env var set, trigger or load a sweep, see chips render with expected counts,
  drill into a chip and see the per-source results table; CHANGELOG.md entry
  under [Unreleased] ### Added.

Context:
- Backend is shipped: P0 audit, P1 event_sink API, P1b ATTUNE_DS stdout
  emission, P2A sweep-results storage primitives (PR #334), P2B daemon-side
  wiring + HTTP route — all on main. Phase 3 is purely UI.
- Sunday's planned release is attune-ai 6.9.0 (minor bump) covering Phase 1 +
  2 + 3 of the step-4 closeout. Your PR adds an entry under [Unreleased] ### Added.
- Safe to run in parallel with Phase 1 + 2. CHANGELOG [Unreleased] is the
  only likely conflict.

FIRST-ACTION GATE:
  git fetch origin
  git log origin/main --oneline -5
If PR #408's merge commit is not on main, STOP. Do not work around.

Worktree:
  cd /Users/patrickroebuck/attune-ai
  git worktree add .claude/worktrees/discovery-sweep-ops-phase3-ui \
    -b feat/discovery-sweep-ops-phase3-ui origin/main
  cd .claude/worktrees/discovery-sweep-ops-phase3-ui

First steps:
  1. Read docs/specs/discovery-sweep-ops-integration/tasks.md (Phase 3 +
     Phase 4 fully; Phase 0–2B for context).
  2. Read the existing storage + route code:
     - src/attune/ops/sweep_results.py
     - src/attune/ops/routes/sweep_results.py
     - src/attune/ops/sweep_results_watcher.py
  3. FIXTURE AUDIT:
     - Look for existing sweep-results JSON fixtures in tests/ (likely
       tests/unit/ops/ or tests/fixtures/).
     - If absent, generating a deterministic fixture set is the FIRST commit
       of this PR (not the last). Include:
         * a "rich" scope (≥2 sources, mixed severities)
         * an "empty" scope (drives the empty-state UI path)
         * a "single-source" scope (drives the no-chips edge)
     - Top-of-file docstring per fixture explaining shape + UI path exercised.
  4. Propose a task breakdown including:
     - Fixture audit/generation as first commit
     - UI tasks per the spec (chips + drill-in)
     - The env-gate transition (default-on with opt-out)
     - Phase 4 docs tasks
  5. Get Patrick's nod, then implement.

Gate transition (locked decision):
- Phase 3 makes the feature DEFAULT-ON; ATTUNE_OPS_SWEEP_RESULTS=0 explicitly
  disables (escape hatch). The env var is retained for emergency disable but
  not required for normal use.
- Document this in the spec's tasks.md + the CHANGELOG entry.
- A separate follow-up commit (`chore/retire-ATTUNE_OPS_SWEEP_RESULTS-gate`,
  target 2026-06-07) will fully remove the env var ~3 weeks after this lands.
- Do NOT remove the env var infrastructure in this PR — the staged rollout
  pattern (feature flag → default-on → retire) is the quality choice.

CHANGELOG protocol:
- Entry under [Unreleased] ### Added:
    - **Sweep-results dashboard UI** (Phase 3 of step-4 closeout,
      docs/specs/discovery-sweep-ops-integration/). Sweep results from
      discovery-sweep now render as severity-tagged chips on the dashboard
      with drill-in to per-source results tables. ATTUNE_OPS_SWEEP_RESULTS
      defaults to enabled; set `=0` to disable. The env var is scheduled for
      full removal in a 2026-06-07 follow-up.

PR description template (REQUIRED):
  ## Phase
  Phase 3 of 4 in the ops-dashboard step-4 closeout (plan: PR #408).
  ## Scope (verbatim from spec)
  <copy Phase 3 + Phase 4 task lists from tasks.md>
  ## Acceptance (verbatim from spec)
  <copy from tasks.md>
  ## Test plan
  - [ ] Fixture set committed with docstrings
  - [ ] Unit tests cover each Phase 3 task
  - [ ] Default-on smoke: launch dashboard with no env var, sweep renders
  - [ ] Opt-out smoke: ATTUNE_OPS_SWEEP_RESULTS=0 disables the UI cleanly
  - [ ] Empty-state path renders correctly (no fixtures for a scope)
  - [ ] CHANGELOG.md entry under [Unreleased] ### Added
  - [ ] Rebased on latest origin/main; no conflicts
  ## Out of scope (explicit)
  - Removing the env var infrastructure (separate follow-up commit ~2026-06-07)
  - Backend changes (P0–P2B are shipped; consume them as-is)
  - Bumping pyproject.toml / __version__ (release-prep PR handles that Sunday)

PR target: main directly. Squash merge.

Critical constraints:
- Backend is done. Don't touch sweep_results.py, the route, or the watcher
  beyond reading. If a real bug surfaces, open a SEPARATE fix PR.
- The scope picker may be consumed on your new sweep results page. If P2 has
  shipped by your ship time, use the upgraded picker; if not, use main's
  current version (and note the dependency in the PR description so Patrick
  can re-smoke after P2 lands).
- Target Sunday-EOD merge so Sunday's release-prep PR can fire.
```

---

## Prompt 4 — Sunday release-prep (fires after P1–P3 merge)

```text
Project: attune-ai
Mode: (b) Executing a planned spec — Sunday release
Outcome: attune-ai 6.9.0 published to PyPI, tagged on GitHub. CHANGELOG
  [Unreleased] is renamed to [6.9.0] - <today>. Phase 1 + 2 + 3 of the
  step-4 closeout are bundled into one release.
Done when: gh release create v6.9.0 fires; the publish workflow lands the
  wheel + sdist on PyPI after the manual env approval gate; pyproject.toml
  + __version__ bumped to 6.9.0; CHANGELOG section renamed.

Context:
- attune-ai is at 6.8.0; this is a minor bump to 6.9.0 covering Phases 1–3
  of the ops-dashboard step-4 closeout. v7.0 is reserved for the
  100%-coverage milestone — do NOT use it.
- Phase 4 (ops-runner-tier2 P5–P6) is intentionally NOT in this release.
  It ships separately later.
- Plan doc: docs/specs/_sequencing-ops-dashboard-step4.md.

FIRST-ACTION GATE:
  git fetch origin
  git log origin/main --oneline -10
Confirm all three phases have merged before proceeding:
- chore/ops-security-hardening-close (Phase 1)
- feat/ops-scope-picker-ia-impl (Phase 2)
- feat/discovery-sweep-ops-phase3-ui (Phase 3)
If any is missing, STOP and report to Patrick. Do not partially release.

Worktree:
  cd /Users/patrickroebuck/attune-ai
  git worktree add .claude/worktrees/release-6.9.0 \
    -b release/6.9.0 origin/main
  cd .claude/worktrees/release-6.9.0

Release-prep steps:
  1. Run /attune-release-check on attune-ai with target 6.9.0. Stop at any
     [!] failure; resolve before continuing.
  2. Bump pyproject.toml version: 6.8.0 → 6.9.0.
  3. Bump src/attune/__init__.py (or wherever __version__ lives) to 6.9.0.
  4. Edit CHANGELOG.md:
     - Rename "## [Unreleased]" to "## [6.9.0] - <today's ISO date>".
     - Add a fresh "## [Unreleased]" skeleton above it (with empty
       ### Added / ### Changed / ### Fixed / ### Security subsections per
       Keep a Changelog).
     - Add a top blockquote under [6.9.0] summarizing the release in 2–3
       sentences: "Step-4 closeout for the ops dashboard — ops-security-
       hardening spec complete (Phase 1), scope picker remembers last-used
       scope (Phase 2), sweep results render as chips on the dashboard
       (Phase 3). Phase 4 (ops-runner-tier2 P5–P6) ships separately."
  5. Verify the three Phase entries are present under their correct
     subsections (### Security for Phase 1, ### Added for Phases 2 + 3).
  6. Commit the version + CHANGELOG changes.
  7. Open the release-prep PR with title `release: 6.9.0 — ops dashboard
     step-4 closeout (Phases 1–3)`. PR description must enumerate the three
     phase PRs being shipped.
  8. After merge to main: run the attune-release-check skill against the
     merge commit to confirm green. Use the FULL 40-char SHA as
     --target.
  9. Fire:
       gh release create v6.9.0 \
         --target <40-char SHA of release-prep merge commit> \
         --title 'v6.9.0' \
         --notes-file <path to file containing the [6.9.0] section>
  10. Immediately grab the publish workflow URL via:
       gh run list --workflow=publish.yml --limit 1 --json url,databaseId
      Report the URL to Patrick — he approves the `pypi` environment in
      that workflow run.
  11. After the publish workflow completes/success, verify the wheel + sdist
      are on PyPI:
        curl -s https://pypi.org/pypi/attune-ai/6.9.0/json
      and report success.

PR description template:
  ## Phase
  Sunday release covering Phase 1 + 2 + 3 of the ops-dashboard step-4
  closeout. Phase 4 (ops-runner-tier2 P5–P6) ships separately.
  ## Phases included
  - Phase 1 (ops-security-hardening close): PR #<phase1-pr>
  - Phase 2 (ops-scope-picker-ia impl): PR #<phase2-pr>
  - Phase 3 (discovery-sweep-ops-integration P3–P4): PR #<phase3-pr>
  ## Release-check
  - [ ] attune-release-check skill green against the prep merge commit
  - [ ] pyproject.toml version = 6.9.0
  - [ ] __version__ = 6.9.0
  - [ ] CHANGELOG [6.9.0] section present with date
  - [ ] [Unreleased] skeleton above
  ## Test plan
  - [ ] gh release create v6.9.0 fires
  - [ ] publish workflow lands on PyPI after env approval
  - [ ] pip install attune-ai==6.9.0 succeeds in a clean venv
  ## Out of scope
  - Phase 4 (ships separately)
  - v7.0 work (reserved for 100%-coverage milestone)

Critical:
- ATTUNE_OPS_SWEEP_RESULTS retirement follow-up (`chore/retire-...`) is
  scheduled for ~2026-06-07 — NOT this release.
- If P2 slipped Saturday EOD per the contingency plan, the release prompt
  needs adjusting: ship Phase 1 + 3 only, defer Phase 2 to a mid-week
  point release. Ask Patrick before proceeding if the merge gate above
  reports a missing phase.
```

---

## Quick-reference for after Sunday

Three follow-ups already scheduled, not for this release:

1. **`chore/retire-ATTUNE_OPS_SWEEP_RESULTS-gate`** — target 2026-06-07 (3 weeks post-6.9.0). Removes the env var infrastructure now that the gate is default-on and stable.
2. **Phase 4 prompt** — drafted after P3 lands so we can adjust scope based on what we learned. Will cover ops-runner-tier2 P5 (Structured recommendations) + P6 (telemetry + close).
3. **Sequencing cross-references** — small PR adding "See also" lines between `_sequencing.md` and `_sequencing-ops-dashboard-step4.md`. Cosmetic; can ride with any other docs PR.
