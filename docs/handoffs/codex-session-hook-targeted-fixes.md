# Agent work handoff

## Goal

Retain all three session-start hooks and fix their identified false-negative
and wrong-artifact/repository checks, as Patrick authorized on 2026-09-09.

## Acceptance criteria

- Missing help-template directories produce a warning, including a missing tree.
- Both starter hooks select the same branch/newest handoff and project starter;
  the legacy global starter is selected only when neither has content.
- Qualified references never become wrong-repository PR verdicts or suppress
  local newer-merge warnings. Matching repository references remain checkable;
  foreign references and explicit issue links are visibly unverified.
- Codex branches are recognized; banners distinguish state from decision content.
- Regressions, real hook subprocess receipts, coverage, and relevant gates pass.

## Scope and assumptions

- Branch/worktree: `codex/session-hook-targeted-fixes`, Codex worktree `af69`.
- Baseline: `5922aaa0d3eba0efec9b962e10cbc2c588caa71c` (matched cached origin/main).
- Provider/session: Codex implementing; advisory review delegated below.
- Structured one-shot. Existing informational behavior, caps and deadline retained.
- Foreign references are reported unverified; cross-repository network checking
  is outside this targeted fix. Decision-content checking remains outside scope.

## Current state

- Implementation and review complete on the local branch; inspect Git for the
  current commit and working-tree state.
- Changed files: three hook scripts; four hook regression test files;
  this handoff and the cross-review receipt ledger. The corpus loader remains
  unchanged after restoring standalone symbol access.
- Main checkout was dirty and its main branch behind cached origin/main;
  it was not modified. Work is confined to this separate worktree.
- No remote push or PR. Windows CI has not run; local receipts are macOS/Python 3.10.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Starting repository meets preflight requirements | `python3 scripts/collaboration_preflight.py` | 0 failures; 87 governance tests passed; 3 Git-state warnings |
| Existing three-hook baseline | `PYTHONPATH=src ANTHROPIC_API_KEY='' python3 -m pytest tests/unit/hooks/test_help_freshness_nudge.py tests/unit/hooks/test_starter_prompt_nudge.py tests/unit/hooks/test_starter_reconciler.py -q -o addopts=''` | 146 passed before changes |
| Added regressions detect original defects | Alignment, reference-scope and help suites against original production code | 12 failed, 13 passed |
| Final hooks, reference handling and spec corpus | `PYTHONPATH=src ANTHROPIC_API_KEY='' python3 -m pytest tests/unit/hooks/test_help_freshness_nudge.py tests/unit/hooks/test_starter_prompt_nudge.py tests/unit/hooks/test_starter_reconciler.py tests/unit/hooks/test_starter_hook_alignment.py tests/unit/hooks/test_starter_reference_scope.py tests/unit/hooks/test_spec_status_corpus.py -q -o addopts=''` with coverage for all three hooks | 181 passed; 98.01% combined statement/branch coverage |
| Real standalone imports, git discovery, file reads and output agree | `test_standalone_hooks_read_the_same_branch_handoff` | Passed using real subprocesses and a local git repository; no network needed |
| Both selected artifacts survive a slow-git deadline | `TestSharedDeadline::test_hook_completes_under_registered_timeout_with_slow_git` | Both banners present under the registered 12-second limit; standalone rerun passed in 6.40s |
| SDK gating, path guard and fleet wiring retained | `PYTHONPATH=src ANTHROPIC_API_KEY='' python3 -m pytest tests/unit/plugins/test_sdk_subprocess_gate.py tests/unit/gates/test_path_validation_gate.py tests/unit/scripts/test_sync_session_hooks.py -q -o addopts=''` | 68 passed |
| Independent review corrections hold | `targeted_fix_review` (gpt-5.6-sol), followed by central six-suite rerun above | All five accepted findings corrected; reviewer 40 focused tests passed; no correction-specific failures |
| Pinned formatting and lint | Black 24.10.0 `--check`; cached Ruff 0.8.4 `check` on changed Python files | Passed |
| Review ledger validity | Precision, rejection-format and countersign-format suites | 28 passed |

Review findings and dispositions are recorded in
`docs/specs/cross-review/receipts.md` (2026-09-09 rows). Retention tradeoff:
startup still runs separate processes and uses heuristic evidence; bounded
checks and explicit unverified labels preserve its informational role.

## Next action

If shipping is requested, verify this branch's commit/status, open the scoped PR,
and wait for required CI, including Windows, before merging. Remove this handoff
when the branch merges.
