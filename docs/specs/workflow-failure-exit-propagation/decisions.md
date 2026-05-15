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

## Open questions (resolve during design phase)

1. **`_run_workflow_with_exit_code()` helper location.** Could live
   in `cli_minimal.py` or in a new `cli_commands/_exit_codes.py`.
   The latter is cleaner long-term; the former is one less file
   to wire up. Decide during design.

2. **Logging interaction.** When exit code is `2`, the traceback is
   already printed to stderr by Python's default exception handler.
   Do we also want a structured `--json` mode for CI consumers?
   Defer to design.

3. **Migration message.** Should the CHANGELOG entry include a
   one-line shell snippet for shop scripts that need to adapt?
   E.g. `if attune workflow run X || [ $? -eq 1 ]; then …`. Decide
   when CHANGELOG is drafted.

---

## Decision-change log

> Append entries here when a decision above is revised. Reference
> the PR that revised it.

- 2026-05-14 — Initial decisions captured during spec draft.
  Triggered by ops-dashboard QA punch list item P0-2; companion
  defense-in-depth landed in dashboard log-scan PR (see
  `src/attune/ops/static/js/run_view.js` `detectLogErrorLeak`).
