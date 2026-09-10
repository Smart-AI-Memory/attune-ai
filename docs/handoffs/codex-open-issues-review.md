# Agent work handoff

## Goal

Close the bounded class CLI and hook coverage gaps selected while reviewing #1569,
and correct the parse-error false-success found by the new register CLI test.

## Acceptance criteria

- Scanner and register commands fail on unparseable source while retaining diagnostics.
- A custom rule named PARSE-ERROR on valid source is not treated as a parser failure.
- Focused tests, pinned hooks, and required CI pass before merge.
- The living #1569 program stays open; other issue decisions are independent.

## Scope and assumptions

- Branch/worktree: codex/open-issues-review, /private/tmp/attune-open-issues-review.
- Provider/session: Codex; GPT-5.6 Sol advisory review `review_issue_scan_fix`.
- Assumptions: no API spending; preserve other worktrees and dirty main checkout.

## Current state

- Status: local implementation and review complete; commit/push/CI remain.
- Changed files: scanner, six CLI/hook test files, changelog, bug log, review ledger.
- Decisions: parser failures remain hits and also enter scan_errors; custom collisions are checked by parsing.
- Risks or open questions: full matrix has not yet run on this branch. #2238 public API strategy and #2463 cross-repository scope have pending user questions.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Register silently accepted unparseable source before the fix | Real fixture repository in test_cli_fails_when_source_cannot_be_scanned | Reproduced exit 0 before fix; exit 1 after fix |
| Focused classes, hook, discovery and governance checks pass | pytest over classes, worktree guard, workflow initialization and relevant gates | 395 passed |
| Coverage clears the floor for all six dated-report candidates | /private/tmp/open-issues-final-coverage.json | Line coverage: class_m 100%, mock_worklist 95.61%, register 90.97%, teeth 96.15%, worktree_add_guard 100%, workflows init 87.5%; changed scanner 93.02% |
| Different-model finding corrected | GPT-5.6 Sol follow-up and independent root rerun of scanner/register suites | 36 passed; no remaining actionable review finding |

## Next action

Run pinned hooks after formatting, commit the reviewed change, remove this temporary
handoff once its branch work is complete, and push a PR referencing #1569. Wait for
all required CI and merge only the verified head; then reap this temporary worktree.
