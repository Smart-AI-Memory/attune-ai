# Agent work handoff

## Goal

Make collaboration projector writes explicit and provide one read-only
session preflight for Git/worktree state, projection drift, ignored
Codex configuration, environment disclosure, and governance tests.

## Acceptance criteria

- Bare and `--check` skill-sync invocations are read-only.
- Only `--write` regenerates tracked skill mirrors.
- Unknown skill-sync arguments fail without writing.
- The preflight detects inconsistent branch/worktree metadata.
- Main-update guidance never switches or rebases the task worktree.
- Tests never create an environment implicitly.
- Focused behavioral tests and both projection drift checks pass.

## Scope and assumptions

- Branch/worktree: `codex/sync-main-and-review-changes`
- Provider/session: Codex desktop, 2026-07-18
- Assumptions: Cached `origin/main` is the authoritative remote snapshot
  for a read-only preflight; network freshness requires a separate,
  intentional fetch.

## Current state

- Status: implementation complete; final verification done (2026-07-18, receiving Claude session: live preflight 0 failed / 74 focused tests passed / pinned Black + Ruff clean)
- Changed files: collaboration contract master and its two instruction
  projections; canonical lessons and three generated help views;
  `scripts/sync_agents_skills.py`; `scripts/collaboration_preflight.py`;
  focused tests; this handoff
- Decisions: default to checking; require `--write`; never invoke `uv`
  from the preflight; use cached refs and report network freshness as
  explicitly unchecked
- Risks or open questions: pytest must already be available to run the
  focused suite; otherwise preflight reports SKIP without provisioning
  an environment

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Skill sync cannot write accidentally | CLI tests for bare, `--check`, `--write`, `--help`, and unknown args | pass |
| Branch inconsistency is legible | fixtures for missing, mismatched, and detached branch refs | pass |
| Preflight is repository-read-only | forbidden-command audit plus Git status before/after | pass |
| Failure reporting is covered | focused branch coverage for both scripts | 91% combined |
| Python quality gates pass | pinned Black plus Ruff on changed Python files | pass |
| Projectors remain synchronized | both projector `--check` commands | pass (final rerun 2026-07-18) |

## Next action

Commit on `codex/sync-main-and-review-changes`, push, and open the PR
to `main`. Delete this handoff file when the branch merges.
