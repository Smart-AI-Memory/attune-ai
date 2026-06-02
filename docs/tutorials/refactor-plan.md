# Tutorial: Refactor Plan

**What you will build:** A working Python script that runs `RefactorPlanWorkflow` against a real directory, then formats and prints the resulting prioritized refactoring roadmap using `format_refactor_plan_report`. When the script finishes, you will have a human-readable report showing tech-debt scores, prioritized issues, and actionable next steps — the same output you would see from `/refactor-plan` in Claude Code.

## Prerequisites

- Python 3.10 or newer
- The project installed in your environment
- A local codebase directory you want to analyze (the tutorial uses `src/` as the example path)

## What the workflow does under the hood

Before writing any code, it helps to know what runs when you call `execute()`. `RefactorPlanWorkflow` coordinates three specialized subagents — `debt-scanner`, `impact-analyzer`, and `plan-generator` — each focused on a different dimension of your code. After all three finish, an orchestrator synthesizes their findings into a single report with a tech-debt score, a prioritized refactoring list with effort and risk estimates, and a set of actionable suggestions. Understanding this three-subagent structure explains why the output is divided into **Summary**, **Refactoring**, and **Suggestions** sections.

## Step by step

### Step 1 — Import the two entry points

The workflow lives in `workflows.refactor_plan` and the report formatter in `workflows.refactor_plan_report`. Import both so you have everything the script needs.

```python
from workflows.refactor_plan import RefactorPlanWorkflow
from workflows.refactor_plan_report import format_refactor_plan_report
```

**Verify:** Run `python -c "from workflows.refactor_plan import RefactorPlanWorkflow"` in your terminal. No output means the import succeeded; an `ImportError` means the package is not on your `PYTHONPATH`.

---

### Step 2 — Initialize the workflow

Instantiate `RefactorPlanWorkflow`. The constructor accepts `**kwargs`, so you do not need to pass any arguments for the default configuration.

```python
workflow = RefactorPlanWorkflow()
```

This step creates the orchestrator object. Nothing runs yet — the subagents only start when you call `execute()`. Separating construction from execution lets you inspect or reconfigure the workflow before committing to a run.

**Verify:** `print(type(workflow))` should output `<class 'workflows.refactor_plan.RefactorPlanWorkflow'>`.

---

### Step 3 — Run the analysis

Call `execute()` and pass the path you want to analyze. The workflow uses it to fill the `{path}` slot in its internal task prompt and then dispatches the three subagents.

```python
workflow_result = workflow.execute(path="src/")
```

This is the step that does real work — expect it to take a few seconds depending on the size of `src/`. The return value is a `WorkflowResult` object.

**Verify:** `print(workflow_result)` should produce a non-empty representation. If it raises an exception, check that `src/` exists relative to your working directory.

---

### Step 4 — Extract the raw result dict

`format_refactor_plan_report` expects a plain `dict`, not a `WorkflowResult`. Access the underlying result and record the input data you passed so the formatter can annotate the report correctly.

```python
input_data = {"path": "src/"}
result_dict = workflow_result.result  # WorkflowResult wraps the raw dict
```

Understanding why this step exists: the formatter is a pure function — it takes data in, returns a string out. Keeping it separate from the workflow means you can reformat the same result multiple times or pipe it into different outputs without re-running the analysis.

**Verify:** `print(type(result_dict))` should show `<class 'dict'>`.

---

### Step 5 — Format and print the report

Pass both the raw result and the input data to `format_refactor_plan_report`. It returns a human-readable string structured into Summary, Refactoring, and Suggestions sections.

```python
report = format_refactor_plan_report(result_dict, input_data)
print(report)
```

**Verify:** Your terminal should display a report that begins with a tech-debt score out of 100, followed by a prioritized list of issues — each with an effort estimate (small / medium / large) and a risk level (low / medium / high). If the report is empty, confirm that `result_dict` was not `None` before this step.

---

### Putting it all together

Here is the complete script:

```python
from workflows.refactor_plan import RefactorPlanWorkflow
from workflows.refactor_plan_report import format_refactor_plan_report

# Initialize the orchestrator
workflow = RefactorPlanWorkflow()

# Run the three-subagent analysis against your source directory
workflow_result = workflow.execute(path="src/")

# Prepare data for the formatter
input_data = {"path": "src/"}
result_dict = workflow_result.result

# Print the human-readable roadmap
report = format_refactor_plan_report(result_dict, input_data)
print(report)
```

Save this as `run_refactor_plan.py` and run it with `python run_refactor_plan.py`. You should see a full refactoring roadmap in your terminal.

## What you learned

- **Step 1** showed you that the workflow and the report formatter live in separate modules (`workflows.refactor_plan` and `workflows.refactor_plan_report`), and why those responsibilities are split.
- **Steps 2–3** demonstrated that `RefactorPlanWorkflow` separates construction from execution — `__init__` configures the orchestrator, `execute(path=...)` dispatches the subagents.
- **Step 4** revealed the three-subagent structure (`debt-scanner`, `impact-analyzer`, `plan-generator`) and how the orchestrator synthesizes their output into a single `WorkflowResult`.
- **Step 5** showed that `format_refactor_plan_report` is a pure function: it turns a result dict into a readable report without re-running any analysis.

## Next steps

Now that you can generate a roadmap programmatically, read the full reference (`attune help-docs ref-skill-refactor-plan`) to understand every debt category the scanner detects, how the 0–100 score is calculated, and how effort and risk estimates are assigned — knowledge you will need to interpret the report reliably for real codebases.

<!-- attune-generated: source_hash=048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38 feature=refactor-plan kind=tutorial generated_at=2026-06-02 -->

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 21 (code fence) | error | `from workflows.refactor_plan import …` — module not importable |
| Line 21 (code fence) | error | `from workflows.refactor_plan_report import …` — module not importable |
| Line 35 (python fence) | error | Name "RefactorPlanWorkflow" is not defined  [name-defined] |
| Line 49 (python fence) | error | Name "workflow" is not defined  [name-defined] |
| Line 64 (python fence) | error | Name "workflow_result" is not defined  [name-defined] |
| Line 78 (python fence) | error | Name "format_refactor_plan_report" is not defined  [name-defined] |
| Line 78 (python fence) | error | Name "result_dict" is not defined  [name-defined] |
| Line 78 (python fence) | error | Name "input_data" is not defined  [name-defined] |
