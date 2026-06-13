# Decisions — CI matrix right-sizing

Append-only log.

---

## 2026-06-13 — D1–D3 decided (Patrick), implementation built

- **D1 — slim matrix shape: `ubuntu-3.12 + windows-3.12`.** On a
  tests/docs-only diff, run the required ubuntu-3.12 lane plus one
  Windows smoke. Rationale: a test-only PR's one realistic platform
  break is a new test baking in POSIX-only path assumptions; one
  Windows lane catches it for ~13 min instead of dropping all
  cross-platform signal.
- **D2 — full-matrix trigger paths:** `src/**`, `pyproject.toml`,
  `setup.cfg`, `.github/workflows/tests.yml`. Any change matching these
  runs the full 12-lane matrix. Everything else (tests, docs, `.claude`,
  markdown) runs slim.
- **D3 — behavioral rule codified:** for tests/docs-only PRs, merge on
  the 7 required green checks; do not wait on advisory Windows/macOS
  lanes (they don't gate). For `src/`-touching PRs the advisory lanes
  run but still don't gate — the "wait for Windows before merging"
  caution applies only to source changes touching paths / subprocess /
  encoding / the filesystem. Captured as a lesson in `.claude/lessons.md`.

### Implementation note

Built in `.github/workflows/tests.yml`: a `changes` job (git-diff
paths filter, fail-safe to full matrix on any ambiguity) → a
`setup-matrix` job (emits full/slim matrix JSON) → the `test` job
consumes `fromJSON(...)`. No third-party action added (pure git diff)
and no branch-protection edit — the required `test (ubuntu-latest,
3.12)` lane is present in both matrix variants, so the required check
name is always emitted.

### Verification owed (post-merge)

This PR touches `tests.yml`, a D2 trigger, so it runs the FULL matrix
and validates the full path + that the required name still emits. The
SLIM path must be proven by a follow-up **tests-only** PR: confirm
`test (ubuntu-latest, 3.12)` reports, `test (windows-latest, 3.12)`
runs, the PR is mergeable, and the other 10 lanes did NOT spawn.
