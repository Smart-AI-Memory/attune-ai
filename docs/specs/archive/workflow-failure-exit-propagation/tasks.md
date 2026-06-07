# Spec: Workflow Failure Exit Propagation — Tasks

> Phase 3 (task decomposition). One focused PR. Status reflects the
> implementing PR.

---

## Tasks

| # | Task | Files | Status |
|---|---|---|---|
| 1 | Add exit-code contract helper module | `src/attune/cli_commands/_exit_codes.py` (new) | **done** |
| 2 | Route `cmd_workflow_run` through the helper; CLI-level errors return `EXIT_CLI_ERROR` (3) | `src/attune/cli_commands/workflow_commands.py` | **done** |
| 3 | Table-driven exit-code test (0/1/2/3, sync+async, legacy, `--json` threading) | `tests/unit/cli/test_workflow_exit_codes.py` (new) | **done** |
| 4 | Migrate existing assertions encoding the old contract (CLI errors 1→3; exceptions 1→2) | `tests/unit/cli_commands/test_workflow_commands.py`, `tests/unit/voice/test_voice_wiring.py` | **done** |
| 5 | CHANGELOG: behavior change + migration snippet; note log-scan retirement | `CHANGELOG.md` | **done** |
| 6 | Record decisions (resolve Q1–Q3) | `docs/specs/workflow-failure-exit-propagation/decisions.md` | **done** |

---

## Acceptance criteria → coverage

| Criterion (requirements.md) | Covered by |
|---|---|
| 1. `run security-audit --path /nonexistent` exits 3 | Task 2 (`EXIT_CLI_ERROR` on bad path); Task 3 `test_bad_path_returns_cli_error` |
| 2. `WorkflowResult(success=False)` exits 1 | Task 1/2; Task 3 `test_planned_failure_returns_one` |
| 3. `execute()` raises → exit 2, traceback on stderr | Task 1; Task 3 `test_unplanned_failure_returns_two_with_traceback` |
| 4. Passing workflows exit 0, no behavior change | Task 3 `test_success_returns_zero` + legacy-dict cases; existing 352-test suite green |
| 5. CHANGELOG documents new exit codes | Task 5 |
| 6. CI green, one PR | full pre-commit + suite run before push |

---

## Explicitly deferred (follow-up PR)

- Retire the ops-dashboard log-scan
  (`src/attune/ops/static/js/run_view.js` `detectLogErrorLeak`) one
  release after this lands (decision-matrix row).
- No version bump / publish in this PR.
