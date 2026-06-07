# Spec: Workflow Failure Exit Propagation — Decisions

> Pre-committed decisions. Updates to this file after implementation
> begins require a follow-up PR with rationale.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Exit code on planned failure (`WorkflowResult.success is False`) | `1` | Conventional "non-zero means failure"; distinguishes from CLI errors. |
| Exit code on unplanned failure (uncaught exception) | `2` | Lets shell scripts branch — `2` is "process crashed", `1` is "process said no". Conventional in many CLIs (e.g. grep). |
| Exit code on CLI-level error (workflow not found, bad path) | `3` | Reserved for argument/config errors, separable from workflow execution problems. |
| Backwards-compat for shell scripts relying on the previous (buggy) exit-0 on failure | **Not preserved.** | The exit-0-on-failure state is the bug, not a contract. Preserving it would perpetuate the original problem from the dashboard's P0-2 finding. |
| Dashboard log-scan workaround (PR landed alongside spec draft) | Keep for one release cycle after this spec lands; mark for removal in the release after. | Defense in depth while CLI fix rolls out; safe to retire once telemetry confirms exit codes are correct. |
| Workflow voice-layer "What Went Wrong" block emission | Continues to coexist with exit-1 / exit-2. | Block is informational for users; exit code is the contract for scripts. They're independent. |
| Test coverage requirement | Table-driven test in `tests/unit/cli/test_workflow_exit_codes.py` covering all four exit codes. | Mirrors test-quality-program rubric's "tests must name the branch they cover." |

---

## Open questions — RESOLVED (design phase)

1. **Helper location → `cli_commands/_exit_codes.py` (new file).**
   The contract (`EXIT_*` constants + `run_workflow_with_exit_code()`
   + JSON threading) lives in a dedicated module under the existing
   `cli_commands/` package, keeping `cli_minimal.py` free of
   classification logic. The helper takes the workflow *class* and
   instantiates it inside its own `try`, so constructor failures are
   classified as exit 2 too. See `design.md` Q1.

2. **`--json` mode → thread `exit_code` + `sdk_error_kind`; `$?`
   stays authoritative.** JSON output additively gains `exit_code`
   and `sdk_error_kind` (read from `result.metadata`, populated by
   the sdk-error-message-fidelity primitives — no new classification
   here). Object outputs get the keys injected (`setdefault`, never
   clobbering); non-dict results are wrapped in an
   `{exit_code, success, sdk_error_kind, result}` envelope. The
   "last `{...}` block" invariant that `security-scan.yml` relies on
   is preserved. See `design.md` Q2.

3. **Migration snippet → yes, included in the CHANGELOG.** One
   copy-safe shell line showing how a script tolerates a planned
   failure (exit 1) while still failing on a crash (exit ≥ 2):
   `attune workflow run X; rc=$?; [ "$rc" -le 1 ] || exit "$rc"`.
   See `design.md` Q3.

---

## Decision-change log

> Append entries here when a decision above is revised. Reference
> the PR that revised it.

- 2026-05-14 — Initial decisions captured during spec draft.
  Triggered by ops-dashboard QA punch list item P0-2; companion
  defense-in-depth landed in dashboard log-scan PR (see
  `src/attune/ops/static/js/run_view.js` `detectLogErrorLeak`).
- 2026-06-04 — Open questions Q1–Q3 resolved during the design
  phase (see `design.md`) and implemented in one PR. No matrix rows
  were revised. Dashboard log-scan retirement remains deferred to a
  follow-up release per the matrix.
