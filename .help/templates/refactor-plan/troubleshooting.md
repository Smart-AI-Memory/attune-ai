---
type: troubleshooting
name: refactor-plan-troubleshooting
feature: refactor-plan
depth: troubleshooting
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
status: generated
---

# Troubleshoot refactor plan

## Symptom table

| If you observe | Check |
|----------------|-------|
| `RefactorPlanWorkflow.execute()` raises an exception | Read the full traceback — the raise site names the file and line. Confirm the path argument passed to `execute()` exists and is readable. |
| Report is empty or missing sections (Summary, Refactoring, Suggestions) | Check what `format_refactor_plan_report(result, input_data)` received. A missing key in `result` or `input_data` causes sections to be skipped silently. |
| One or more subagents produce no output | The workflow coordinates three subagents (`debt-scanner`, `impact-analyzer`, `plan-generator`). Confirm each can reach the target path and has sufficient read permissions. |
| CLI (`main()`) exits without output | Run with a concrete path argument and check stderr for errors before assuming the workflow itself failed. |
| Results are inconsistent across runs | Check for environment drift — changed files, modified environment variables, or a caching layer between runs. |
| Execution is unexpectedly slow | The workflow calls three subagents sequentially. Large directory trees multiply the cost; try scoping the path to a subdirectory first. |

## Diagnose the issue

### 1. Reproduce with a minimal path

Narrow the input to the smallest path that still triggers the failure:

```python
from workflows.refactor_plan import RefactorPlanWorkflow

workflow = RefactorPlanWorkflow()
result = workflow.execute(path="src/auth/")  # swap in the failing path
print(result)
```

If the failure disappears with a smaller scope, the problem is likely in the content being analyzed, not the workflow itself.

### 2. Inspect what `execute()` returns

`execute()` returns a `WorkflowResult`. Before blaming report formatting, confirm the result object is well-formed:

```python
result = workflow.execute(path="src/auth/")
print(type(result))
print(vars(result))  # or result.__dict__ if dataclass
```

If `result` is `None` or missing expected fields, the failure is inside `execute()`, not in `format_refactor_plan_report()`.

### 3. Check the report formatter in isolation

If `execute()` returns data but the report looks wrong, test `format_refactor_plan_report()` directly:

```python
from workflows.refactor_plan_report import format_refactor_plan_report

# Use the raw dict from your execute() call
report = format_refactor_plan_report(result=your_result_dict, input_data=your_input_dict)
print(report)
```

A `KeyError` or empty string here points to a mismatch between what `execute()` produces and what the formatter expects.

### 4. Run the targeted tests

```bash
pytest -k "refactor_plan" -v
```

A failing test that covers your scenario gives you a reproducible fixture and a clear pass/fail signal before you change any code.

### 5. Enable debug logging

If the above steps don't isolate the issue, raise the log level to `DEBUG` and re-run. The subagent coordination layer logs state transitions that can reveal which of the three subagents (`debt-scanner`, `impact-analyzer`, `plan-generator`) stalled or returned unexpected output.

## Common fixes

**The path does not exist or is not readable**
`execute()` requires a valid, accessible path. Verify it before invoking the workflow:

```bash
ls -la src/auth/   # confirm the path exists and is readable
```

**A required key is missing from `result` or `input_data`**
`format_refactor_plan_report(result, input_data)` expects both arguments to contain the keys the formatter references. If `execute()` returned an error state, the result dict may be incomplete. Add a guard before calling the formatter:

```python
if result and not result.get("error"):
    report = format_refactor_plan_report(result=dict(result), input_data=input_data)
```

**Subagent output is missing a required section**
The synthesized report must include `## Summary`, `## Refactoring`, and `## Suggestions` sections. If a subagent returns no findings, that section may be absent, causing the formatter to produce an incomplete report. Re-run with a broader path to confirm there is analyzable content.

**Dependency version mismatch**
A dependency upgrade can change the behavior of the Agent SDK subagents. If the workflow worked previously, check whether a recent `pip install --upgrade` changed a relevant package:

```bash
pip show <dependency-name>
```

Pin the version in your requirements file if the upgrade introduced a regression.

**Stale environment state**
If the workflow fails intermittently without a code change, check for modified environment variables or cached state from a previous run. A clean environment often resolves this:

```bash
unset <relevant-env-var>
# then re-run
```

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 30 (code fence) | error | `from workflows.refactor_plan import …` — module not importable |
| Line 56 (code fence) | error | `from workflows.refactor_plan_report import …` — module not importable |
