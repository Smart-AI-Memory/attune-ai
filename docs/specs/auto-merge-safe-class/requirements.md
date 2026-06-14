# Auto-Merge-Safe Class — Requirements

**Status:** approved (2026-06-14)
**Owner:** Patrick + agent

---

## Problem

Autonomous QA/docs "auto-run" sessions open test-only or
docs-only PRs and enable non-admin `gh pr merge --auto --squash`,
which self-completes on green. The gap: when a **required check
hangs** (the systemic ci-runner-hang — partly mitigated by #874's
faulthandler watchdog + tightened timeouts), the happy path never
lands, and admin-merge is the only recovery.

Admin-merge requires an **explicit in-session human OK** every
time (the harness safety classifier; a starter-file note is
correctly not honored — see the "check-and-fix does NOT carry
admin-merge authorization" lesson). So an unattended run cannot
finish a hung-but-otherwise-green test PR.

---

## Goal

A durable mechanism that lets a **tight** class of PRs
(test/docs only) self-complete on the meaningful green signal
**without** a per-session human admin-merge OK — while keeping
code-touching PRs firmly out of the class.

---

## Key insight — the classifier is the wrong layer

There is no evidence the harness safety classifier honors any
settings/label grant for admin-merge; it wants conversational
authorization. So we do **not** try to configure the classifier.
Instead we take the agent **out of the merge loop**: a GitHub
Actions workflow performs the merge deterministically. GitHub
does the merge; no agent/classifier is involved.

---

## Functional requirements

- **R1** — A workflow admin-merges (squash) a PR only when ALL
  hold:
  1. PR carries the `auto-merge-safe` label.
  2. Every changed file is within the path class (see R2);
     fail-closed on any out-of-class path or empty file set.
  3. The `coverage` required check is `success` on the PR head.
  4. PR author login is `silversurfer562` (the repo owner).
  5. PR head repo == base repo (no forks) and PR is not a draft.
- **R2** — Path class: every changed file (including a rename's
  previous path) is under `tests/`, `docs/`, `.help/`, or is a
  root-level `*.md`. Anything else (notably `src/`, `.github/`,
  `pyproject.toml`, lockfiles, `mkdocs.yml`) makes the PR
  out-of-class.
- **R3** — The `auto-merge-safe` label is applied by the workflow
  itself (computed from the path class + author), not by hand, so
  humans/agents don't mis-apply it. The merge job **re-verifies**
  the path class independently, so a hand-applied label on an
  out-of-class PR still will not merge (label is necessary, not
  sufficient).
- **R4** — The merge uses a credential that bypasses the hung
  required check (a fine-grained admin PAT; `GITHUB_TOKEN`
  provably cannot — the bot is not a repo admin and there is no
  ruleset bypass).
- **R5** — The path-class guard is unit-tested and lives under
  `.github/` so changes to the guard itself are out-of-class and
  can never self-auto-merge.

---

## Exclusions (the whole ballgame)

- Any `src/` or production-code change => excluded, no
  exceptions.
- Any change to CI workflows, branch protection, or the
  auto-merge workflow itself => excluded (`.github/` is
  out-of-class).
- Fail closed: if the path filter cannot prove the PR is wholly
  test/docs, do nothing.

---

## Non-goals

- Bypassing the `coverage` gate. We bypass only the **redundant**
  hung lane; `coverage` (which re-runs the full suite) must be
  green.
- Widening the class to any code path.
- Solving the runner-hang itself (that is the ci-runner-hang
  spec; this rides on top of its mitigations).

---

## Acceptance criteria

- Spec recorded with `decisions.md` (class definition + rejected
  alternatives).
- `.github/workflows/auto-merge-safe.yml` + path-class guard with
  passing unit tests landed via PR with CI green.
- Verified on a throwaway test-only PR that it auto-merges, and
  on a deliberately `src/`-touching PR that it is **not** merged.
