# CI matrix right-sizing — skip advisory lanes on test/docs-only diffs

**Status:** complete — D1–D3 decided 2026-06-13, workflow implemented;
slim-path proof discharged + required-lane regression guard landed
2026-06-19 via PR #937 (see decisions.md)
**Opened:** 2026-06-13
**Layer:** attune-ai (CI / `.github/workflows/tests.yml`)
**Owner:** Patrick + agent

---

## Problem

The `Tests` workflow runs a **12-lane matrix** (3 OS × 4 Python) on
every push/PR. Only **one** lane gates the merge —
`test (ubuntu-latest, 3.12)`. The other 11 (all 4 Windows, all 4 macOS,
ubuntu 3.10/3.11/3.13) are **advisory**: they run but gate nothing.

Because the repo is **public, Actions minutes are free** — so the cost
is not dollars. It is:

- **merge latency** — Windows lanes take ~13 min; waiting on them
  delays low-risk merges;
- **CI noise** — 12 check rows + a non-required `security` cancel make
  "is it green?" harder to read at a glance;
- **the temptation to wait** — advisory lanes look like gates, so an
  operator (human or agent) waits on them when they don't block. This
  literally happened on #797/#798: ~30+ min spent watching Windows
  lanes that were never required.

For a **test-only or docs-only** diff, the full cross-platform×Python
matrix is especially low-value: a change that touches no `src/` cannot
introduce a cross-platform *source* regression.

---

## Verified findings (grounded, 2026-06-13)

| Fact | How verified |
|------|--------------|
| Required checks = `CodeQL, code-quality, coverage, lint, platform-compat, pre-commit, test (ubuntu-latest, 3.12)` | `gh api repos/.../branches/main/protection/required_status_checks` |
| Matrix = `[ubuntu, macos, windows] × [3.10–3.13]`, only the one ubuntu-3.12 lane required | `.github/workflows/tests.yml:29-33` + the required list above |
| Repo is public → free minutes | `gh repo view --json visibility` → PUBLIC |

This corrects an earlier impression that "the 12-lane matrix is the
merge gate." It is not — 11 of 12 lanes are advisory.

---

## Goals

- On `tests/**`- or `docs/**`-only diffs (no `src/` change), **do not
  spawn** the 11 advisory matrix lanes.
- **Never** change which checks are *required* in a way that can leave
  a required check "missing" (the merge-blocking trap — see Risks).
- Keep the change to a single workflow file; no branch-protection edit
  if avoidable.

## Non-goals

- Not changing required-check policy or branch protection (that's the
  heavier "two-tier" alternative, deferred).
- Not touching the separate `security`/CodeQL/pre-commit workflows.
- Not addressing the `security` CANCELLED cosmetic-noise issue (a
  separate, known item — `cancel-in-progress: false` on that scan).

---

## Design (recommended): dynamic matrix via paths-filter

Keep one workflow, make the matrix breadth conditional:

1. **`changes` job** — a paths-filter step (`dorny/paths-filter` or a
   `git diff --name-only` against the merge base) sets
   `outputs.src = true|false` (true if any `src/**` or packaging file
   changed).
2. **`setup-matrix` job** (`needs: changes`) — emits matrix JSON:
   - `src == true` → full `{os:[ubuntu,macos,windows], py:[3.10–3.13]}`
   - `src == false` → slim matrix (see **D1**).
3. **`test` job** — `strategy.matrix: ${{ fromJSON(needs.setup-matrix.outputs.matrix) }}`.

**The trap this design must respect:** GitHub matches required checks
by job name *including* matrix params — `test (ubuntu-latest, 3.12)`.
That exact lane MUST be present in *every* variant of the matrix, or a
test-only PR leaves the required check **missing → merge blocked
forever** (this is the documented stacked-PR "required check stays
MISSING" failure mode). The slim matrix therefore always includes
`ubuntu-latest / 3.12`.

`coverage`, `lint`, `platform-compat`, `code-quality`, `pre-commit`,
`CodeQL` are single ubuntu jobs and keep running unconditionally — they
are fast and required, so no change.

### Alternative (deferred): two-tier required checks

Demote the whole matrix to advisory, add one fast always-on required
"gate" job, then path-filter the matrix freely. Cleaner long-term but
needs a branch-protection change → larger blast radius. Revisit only if
the dynamic-matrix approach proves fiddly.

---

## Decisions needed (Patrick)

- **D1 — slim matrix shape.** On a test/docs-only diff, run:
  - (a) `ubuntu-3.12` only, **or**
  - (b) `ubuntu-3.12 + windows-3.12` (one Windows smoke).
  *Recommendation: (b).* A test-only PR's one realistic platform break
  is a new test using POSIX-only path assumptions (`/tmp`, separators);
  one Windows lane catches it cheaply, and it keeps the merge-relevant
  signal honest.
- **D2 — what counts as "needs full matrix."** Proposed `src` trigger =
  any change under `src/**`, `pyproject.toml`, `setup.cfg`,
  `.github/workflows/tests.yml`. Everything else (`tests/**`,
  `docs/**`, `.claude/**`, `*.md`) → slim. Confirm or adjust.
- **D3 — behavioral note.** Independent of the workflow change: codify
  that for test/docs-only PRs we merge on the 7 required greens without
  waiting on advisory lanes. Record in this spec's decisions, and/or as
  a lesson. (The structural change makes this moot for the *skipped*
  lanes, but the rule still matters for src-touching PRs where the
  advisory macOS/Windows lanes run but don't gate.)

---

## Build tasks (deferred — after D1–D3)

1. Add `changes` + `setup-matrix` jobs to `tests.yml`; wire
   `test.strategy.matrix` to the dynamic JSON. Preserve the
   `test (ubuntu-latest, 3.12)` lane in both variants.
2. Prove the required-check name is emitted on a `tests/**`-only PR
   (open a throwaway test-only PR; confirm `test (ubuntu-latest, 3.12)`
   reports and the PR is mergeable; confirm the 11 advisory lanes did
   NOT spawn).
3. Prove a `src/**` PR still spawns the full 12 lanes.
4. Record D1–D3 outcomes in `decisions.md`; one-line `CHANGELOG`/note
   if user-visible (it isn't — CI-internal).

## Risks

- **Required-check-missing → permanent block** (HIGH) — mitigated by
  always including the `ubuntu-3.12` lane; verified by build task #2
  before relying on it.
- **paths-filter merge-base edge cases** — first push to a new branch,
  or force-pushes, can confuse `git diff` base detection;
  `dorny/paths-filter` handles PR vs push contexts but needs the PR
  event (not just push). Default to **full matrix on ambiguity** (fail
  safe = run more, never fewer required signals).
- **Matrix-name drift** — if Python pin in the required lane ever
  changes (3.12 → 3.13), branch protection's required context must be
  updated in lockstep, or it goes missing. Note in the workflow comment.
