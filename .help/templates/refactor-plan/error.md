---
type: error
name: refactor-plan-error
feature: refactor-plan
depth: error
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
status: generated
---

# Refactor Plan errors

Errors in the refactor plan feature fall into two categories: failures during workflow execution (orchestrating the three subagents and synthesizing their output) and failures during report formatting (converting the raw result into a human-readable report).

## Common error signatures

Errors most commonly appear in these forms:

- **Missing or invalid path** — `RefactorPlanWorkflow.execute()` receives a path that doesn't exist or isn't accessible, causing the workflow to fail before any subagent runs.
- **Malformed result dict** — `format_refactor_plan_report(result, input_data)` raises a `KeyError` or `TypeError` when `result` is missing expected keys (such as `Summary`, `Refactoring`, or `Suggestions` sections) or when `input_data` is `None`.
- **Subagent synthesis failure** — the orchestrator (`debt-scanner`, `impact-analyzer`, or `plan-generator`) returns an incomplete response, leaving `result` in a partial state that `format_refactor_plan_report()` cannot render.
- **CLI argument error** — `main()` exits early if required arguments are not supplied or are in an unexpected format.

## Where errors originate

- **`RefactorPlanWorkflow.execute()`** — orchestrates the three subagents and produces a `WorkflowResult`. Failures here usually indicate a bad input path, a subagent that did not complete, or a synthesis step that produced unexpected output structure.
- **`format_refactor_plan_report(result, input_data)`** — converts the workflow's `result` dict and the original `input_data` dict into a readable report string. Failures here usually mean `execute()` returned a result dict that is missing required sections or has an unexpected shape.
- **`main()`** — the CLI entry point that wires together argument parsing, `RefactorPlanWorkflow`, and `format_refactor_plan_report()`. Errors here are often missing CLI arguments or an unhandled exception bubbling up from one of the two functions above.

## How to diagnose

1. **Read the traceback call stack top-to-bottom.** Identify whether the raise site is in `refactor_plan.py` (workflow/subagent layer) or `refactor_plan_report.py` (formatting layer). That tells you which half of the pipeline failed.

2. **Check the exception type at the raise site.**
   - A `KeyError` in `format_refactor_plan_report()` means `result` is missing a key the formatter expects — inspect the dict returned by `execute()` to see what sections are present.
   - A `TypeError` in `format_refactor_plan_report()` often means `result` or `input_data` is `None`, which points back to `execute()` returning an empty or failed `WorkflowResult`.
   - An `OSError` or `FileNotFoundError` in `execute()` means the path passed to the workflow does not exist or is not readable.

3. **Inspect the `result` dict before formatting.** If you can reproduce the failure, print or log the value of `result` after `execute()` returns and before passing it to `format_refactor_plan_report()`. The three expected top-level sections are `Summary`, `Refactoring`, and `Suggestions` — a missing section identifies which subagent (`debt-scanner`, `impact-analyzer`, or `plan-generator`) did not complete successfully.

4. **Verify the path argument.** The `_TASK_PROMPT_TEMPLATE` requires a `{path}` value. If `main()` is the entry point, confirm the path argument was supplied and points to a readable file or directory.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
