# Spec: Workflow Failure Exit Propagation — Design

> Phase 2 (technical design). Resolves the three open questions from
> `decisions.md`. The decision matrix itself is pre-committed and not
> re-litigated here.

---

## Overview

`attune workflow run <name>` dispatches through one path:

```
cli_minimal.main()
  → _dispatch_subcommand(args, "workflow")
    → cmd_workflow_run(args)          # cli_commands/workflow_commands.py
  → sys.exit(main())                  # process exit = main()'s int
```

`main()` returns whatever `cmd_workflow_run` returns and
`sys.exit(main())` makes that the process exit code. So the entire
fix lives in `cmd_workflow_run`'s return values — no other CLI entry
point sets the workflow-run exit code (verified by audit:
`_SUBCOMMAND_DISPATCH["workflow"]["run"] = cmd_workflow_run` is the
only binding).

The bug: `cmd_workflow_run` returned `0` unconditionally after
`execute()`, ignoring `WorkflowResult.success`, and returned `1` for
both CLI-level errors and uncaught exceptions (no distinction).

---

## Resolved open questions

### Q1 — Helper location → `cli_commands/_exit_codes.py` (new file)

A new module `src/attune/cli_commands/_exit_codes.py` houses
`run_workflow_with_exit_code()` plus the four `EXIT_*` constants and
the JSON-threading helper. `cli_commands/` is an established package;
this keeps `cli_minimal.py` (the argparse + dispatch surface) free of
classification logic and gives the contract one home that any future
CLI entry point can import.

The helper takes the workflow **class** (not an instance) and
instantiates it inside its own `try`, so a constructor failure is
also classified as exit 2 rather than leaking as an unhandled
exception out of `cmd_workflow_run`.

The human-readable voice-layer print is **injected** as a
`print_result` callback rather than imported, which (a) avoids an
import cycle (`workflow_commands` ↔ `_exit_codes`) and (b) preserves
the existing ops-daemon side-channel emission
(`_emit_run_meta_for_daemon`) that rides inside `_print_workflow_result`
— it only fires on the non-JSON path, unchanged.

### Q2 — `--json` mode → thread `exit_code` + `sdk_error_kind`, `$?` authoritative

In `--json` mode the helper threads two fields into the emitted JSON
so CI consumers parsing stdout don't *also* have to branch on `$?`:

- `exit_code` — the same int returned to the process.
- `sdk_error_kind` — the classified SDK failure kind from
  `result.metadata["sdk_error_kind"]` (populated by
  `BaseWorkflow._error_result()` per the sdk-error-message-fidelity
  spec), or `null`.

`$?` remains the authoritative signal; the JSON fields are a
convenience mirror.

Threading strategy (preserves the "last `{...}` block" invariant that
`.github/workflows/security-scan.yml` relies on):

- If the workflow rendered a JSON **object** in `final_output` (it
  honored `output_format="json"`), parse it and
  `setdefault("exit_code", ...)` / `setdefault("sdk_error_kind", ...)`
  — additive, never clobbering a key the workflow already set.
- Else if the result is itself a `dict`, inject into a copy of it.
- Else (string / dataclass / list) wrap in a small envelope:
  `{"exit_code", "success", "sdk_error_kind", "result"}`.

This keeps the two existing `--json` tests passing (extra keys are
harmless to consumers that read `status`/`count`) and makes the
non-dict path *more* useful than the legacy
`json.dumps(WorkflowResult, default=str)` (which emitted a quoted
dataclass repr with no braces — security-scan's extractor would have
fallen through to its placeholder).

### Q3 — CHANGELOG migration snippet → yes, one-line shell example

The CHANGELOG entry documents the behavior change and includes a
copy-safe migration snippet for scripts that need to tolerate a
planned failure:

```sh
# Treat exit 1 (workflow said "no") as non-fatal, still fail on a crash:
attune workflow run X; rc=$?; [ "$rc" -le 1 ] || exit "$rc"
```

---

## Exit-code mapping (implementation)

| Outcome | Detected where | Code | Constant |
|---|---|---|---|
| Workflow not found / bad JSON / bad path | `cmd_workflow_run`, before `execute()` | 3 | `EXIT_CLI_ERROR` |
| `execute()` (or constructor) raised | `run_workflow_with_exit_code` `except` | 2 | `EXIT_UNPLANNED_FAILURE` |
| `WorkflowResult.success is False` | `run_workflow_with_exit_code` | 1 | `EXIT_PLANNED_FAILURE` |
| `success is True` / legacy dict-str-None result | `run_workflow_with_exit_code` | 0 | `EXIT_SUCCESS` |

**Legacy compatibility:** "planned failure" is detected as
`getattr(result, "success", None) is False`. Workflows returning a
plain `dict` / `str` / `None` (no `success` attribute) keep exiting
`0`. Only a real `WorkflowResult` (or any object exposing a falsey
`success`) trips exit 1.

**Exit 2 surface:** `traceback.print_exc()` writes the traceback to
stderr (per acceptance criterion 3); the voiced one-line summary
(`format_error`) still goes to stdout for humans; `logger.exception`
preserves the structured log. These coexist — the exit code is the
contract, the voice block is informational (matches the decision
matrix row).

---

## Reuse, not duplication

`sdk_error_kind` is read from `result.metadata`, which is set by the
already-shipped sdk-error-message-fidelity primitives
(`classify_subprocess_failure`, `SdkSubprocessError`, the
`_error_result(..., sdk_error_kind=...)` plumbing in
`workflows/base.py`). This spec adds **no** new classification logic —
it surfaces the existing kind through the exit-code + JSON contract.

---

## Out of scope (this PR)

- Removing the ops-dashboard log-scan
  (`src/attune/ops/static/js/run_view.js` `detectLogErrorLeak`). Per
  the decision matrix it stays for one release after this lands;
  retirement is noted in the CHANGELOG / decisions log and happens in
  a follow-up.
- Version bump / publish — a separate release step (Patrick's call).

---

## Test plan

- New `tests/unit/cli/test_workflow_exit_codes.py` — table-driven,
  each case names its branch: 0 / 1 / 2 / 3 (sync + async), legacy
  dict-result → 0, and the `--json` threading (success, planned
  failure with `sdk_error_kind`, non-dict envelope).
- Update the existing assertions that encoded the old contract:
  `tests/unit/cli_commands/test_workflow_commands.py` (CLI errors
  1 → 3; uncaught exceptions 1 → 2, asserting the stderr traceback)
  and `tests/unit/voice/test_voice_wiring.py` (exception path 1 → 2).
