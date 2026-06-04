# Spec: Workflow Failure Exit Propagation

> Make `attune workflow run` exit with a non-zero status when the
> underlying workflow's `WorkflowResult.success` is False (or when
> an uncaught exception inside the SDK adapter is swallowed at the
> CLI boundary).

---

## Phase 1: Requirements

**Status**: approved (design + tasks complete; implemented in one PR —
see `design.md`, `tasks.md`)

### Problem statement

The CLI dispatcher (`attune workflow run <name>`) currently returns
exit code `0` on workflows that internally failed. Evidence:

1. The ops dashboard's QA punch list (2026-05-14, P0-2) caught this:
   `/runs/f8ed53713add/view` rendered with a **green "completed (exit 0)"**
   chip despite the log containing a `claude_agent_sdk` Exception
   plus the workflow-emitted "What Went Wrong" voice-layer block.
2. Patrick hit the same shape this session running
   `perf-audit` from the dashboard — the workflow's SDK call
   raised, the CLI swallowed it, the dashboard reported success.
3. The Specs page QA findings (B1, B2 — fixed) and the dashboard
   log-scan workaround (PR #N — temporary) all exist *because*
   the CLI side doesn't propagate failure.

The dashboard log-scan is a defense-in-depth bandage: it scans for
`Traceback`, `What Went Wrong`, and `<Class>Error:` tokens to flag
chip-warn instead of chip-ok. Real fix is at the source — `attune
workflow run` should exit non-zero when the work failed.

### Scope

**In scope:**

- Audit every code path in `src/attune/cli_minimal.py` (and any other
  CLI entry point that exposes `workflow run`) that calls a workflow's
  `execute()` and discards the `WorkflowResult.success` field when
  setting the process exit code.
- Define the exit-code contract:
  - `0` — workflow ran AND `WorkflowResult.success is True`
  - `1` — workflow ran AND `WorkflowResult.success is False` (planned
    failure)
  - `2` — workflow ran AND raised an uncaught exception (unplanned
    failure) — distinguish from `1` so scripts can branch
  - `3` — CLI-level error (workflow not found, bad path, etc.)
- Update the workflow-result-formatting voice-layer block emission
  so the "What Went Wrong" section *requires* a non-zero exit (it's
  currently emitted on failed workflows even when the CLI exits 0,
  which is the broken state).
- Ensure dashboard-side: when the new contract lands, the ops
  dashboard log-scan can be downgraded from P0-priority defense to
  a P3 nice-to-have (or removed if it becomes redundant).
- Add a test for each exit-code path (table-driven test in
  `tests/unit/cli/test_workflow_exit_codes.py`).

**Out of scope:**

- Restructuring how workflows report failure internally
  (`WorkflowResult.success`, error message format, etc.) — that's
  upstream.
- Changing dashboard-side rendering — the existing chip color
  scheme is fine once exit codes are correct.
- Migration path for tools that may currently rely on the buggy
  exit-0 behavior — explicit non-goal; this fix is correctness
  before backwards-compat.

### Acceptance criteria

1. `attune workflow run security-audit --path /nonexistent/path`
   exits **3** (CLI-level error).
2. A workflow that internally returns `WorkflowResult(success=False,
   ...)` exits **1**.
3. A workflow whose `execute()` raises an uncaught exception exits
   **2** with the traceback printed to stderr.
4. Existing passing workflows exit **0** with no behavior change.
5. The ops dashboard's `/runs/<id>/view` log-scan-fallback fires on
   ZERO runs after the fix lands (because no exit-0 run carries
   failure signals anymore — defense in depth becomes redundant).
6. The CHANGELOG documents the new exit codes as a behavior change.

### Non-goals / explicitly deferred

- **Auto-retry on exit code 2.** The SDK has its own retry logic;
  CLI shouldn't second-guess it.
- **Splitting WorkflowResult.success into multiple failure
  categories.** Out of scope; this spec accepts the boolean field
  as-is.

### Decision matrix (pre-committed)

Per the `feedback_color_and_hover_affordances` / "decision matrices
survive contact with data" lesson, these are decided up front:

| Decision | Choice |
|---|---|
| Exit code on planned failure | `1` |
| Exit code on unplanned failure (uncaught exception) | `2` |
| Exit code on CLI-level error | `3` |
| Backwards-compat for shell scripts relying on exit-0 on failure | **Not preserved.** Failure must propagate. CHANGELOG notes the change. |
| Dashboard log-scan workaround | Keep for one release after this lands; remove in the release after. |
| Workflow voice-layer "What Went Wrong" block | Required to coexist with exit-1 (and exit-2). Block is informational; exit code is the contract. |

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| CI scripts using `attune workflow run` in shell pipelines may break (`set -e` would now propagate failure) | Low–Medium | This is the CORRECT behavior. CHANGELOG note + a deprecation cycle wasn't justified — the buggy state IS the bug. |
| Differentiating exit-1 (planned) vs exit-2 (unplanned) requires the CLI to catch and classify all SDK exceptions cleanly | Medium | Build a single `_run_workflow_with_exit_code()` helper that wraps the call; centralize the classification logic. |
| Dashboard's existing log-scan fallback could mask the issue post-fix (false-positive on legit error-message-discussing workflows) | Low | Plan to remove the log-scan in a follow-up release once the new exit codes are observed in telemetry. |
