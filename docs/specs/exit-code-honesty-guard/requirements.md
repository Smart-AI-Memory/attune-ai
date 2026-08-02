# Exit-Code Honesty Guard — Requirements

**Status:** drafted (2026-08-02) — AWAITING CHAIR REVIEW. No
implementation authority until the chair approves; this draft
exists so the review has a concrete object.
**Slug:** `exit-code-honesty-guard`
**Provenance:** chair directive 2026-08-02 ("spec 3 and 4 for chair
review"). Evidence base: dashboard run `87d8438e3e8c` (2026-08-02)
— a SUCCEEDED code-review run exited 1 because post-success
run-meta emission crashed on a non-blocking pipe (fixed #1904); the
Jul 15 run `63c533fb6e46` failed the same way.

## Problem

The CLI's exit code is the contract consumed by the ops dashboard
chips, CI, and scripts. The class of bug: work that runs AFTER the
workflow result is determined (telemetry emission, report encoding,
daemon plumbing) can raise and overwrite the honest exit code.
#1904 fixed the one known instance; nothing prevents the class from
returning when the next post-success step is added.

## Proposed mechanism (for review, not ratified)

- R1. A drift-guard test pins the invariant on
  `run_workflow_with_exit_code` (`_exit_codes.py`): with a
  successful `WorkflowResult`, an exception raised by the
  `print_result` / `on_result` / emission path must NOT change the
  exit code from the result-derived value. (Today this holds only
  because `_emit_run_meta_for_daemon` catches OSError internally —
  the guard should hold even if that local guard is refactored
  away.)
- R2. The invariant is enforced at the `run_workflow_with_exit_code`
  layer (catch-log-continue around post-result callbacks), not by
  trusting each callback to guard itself. Uncaught exceptions
  BEFORE the result exists keep the existing exit-2 contract.
- R3. The guard test injects a raising callback for each post-result
  hook point and asserts exit 0 with a stderr warning.

## Open questions for the chair

- Q1. Should a post-success plumbing failure be visible anywhere
  beyond stderr (e.g. a run-record annotation), so silent-warn
  doesn't hide chronic breakage?
- Q2. Does the same invariant belong on the MCP handler path
  (`_workflow_response`), which has its own error-shape history?

## Acceptance criteria (when approved)

- R2's catch-log-continue lands in `_exit_codes.py` with the R3
  drift-guard test red-before/green-after recorded in decisions.md.
- The #1904 regression suite continues to pass unchanged.

## Out of scope

- The runner/daemon side (covered by #1904's read-side fix).
- Exit-code taxonomy changes (0/1/2/3 contract stays as specified
  in the workflow-failure-exit-propagation spec).
