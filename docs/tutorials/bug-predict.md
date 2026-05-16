# Tutorial: Bug Prediction

You'll finish this tutorial with a working Python script that scans a directory, runs the full three-subagent bug prediction workflow, and prints a formatted risk report — so you can see exactly what the tool does and why each piece exists.

## Prerequisites

- Python 3.10 or newer
- The `attune` package installed in your environment
- A directory of Python source files to scan (the tutorial uses `src/` as the target)

## What you will build

A short script that wires together `BugPredictionWorkflow` and `format_bug_predict_report` to produce output like this:

```
Bug Prediction Report
Risk Score: 73/100 | Files: 34 | Findings: 8

HIGH (2 findings)
  src/hooks/executor.py:89   dangerous_eval  eval() on user input
  src/plugins/loader.py:142  dangerous_eval  exec() in plugin loader
...
```

By the time the script runs successfully, you'll understand how the orchestrator coordinates its three subagents and how raw results become a readable report.

---

## Step 1 — Import the two building blocks

The workflow and the formatter live in separate modules. Import both so you can see the boundary between "running the analysis" and "presenting the results".

```python
from attune.workflows.bug_predict import BugPredictionWorkflow
from attune.workflows.bug_predict_report import format_bug_predict_report
```

Run this as a standalone script. If neither import raises an `ImportError`, your installation is complete.

**You should see:** no output and no errors.

---

## Step 2 — Instantiate the workflow

`BugPredictionWorkflow` is an SDK-native orchestrator. When you instantiate it, you're setting up three specialized subagents — `pattern-scanner`, `risk-correlator`, and `prevention-advisor` — that will each handle a distinct part of the analysis.

```python
workflow = BugPredictionWorkflow()
```

You don't need to pass any arguments for a first run; the defaults use the built-in system prompt that instructs the orchestrator to be thorough but concise and to cite file paths with line numbers.

**You should see:** the object created without exceptions. Print `workflow` to confirm it exists.

---

## Step 3 — Run the scan against a target path

Call `execute()` with the path you want to analyze. The orchestrator sends each subagent a task derived from `_TASK_PROMPT_TEMPLATE`, substituting your path for `{path}`.

```python
raw_result = workflow.execute(path="src/")
```

This is the step where the real work happens: `pattern-scanner` flags dangerous patterns (`eval()`, bare `except:`, TODO markers), `risk-correlator` weighs complexity and change frequency, and `prevention-advisor` ranks remediation strategies. The returned `WorkflowResult` bundles all three subagents' findings.

**You should see:** `execute()` return without raising. You can print `raw_result` to inspect the raw synthesis before formatting.

---

## Step 4 — Format the results into a human-readable report

`format_bug_predict_report` takes the raw result dict and the original input data and produces the structured markdown report. Keeping formatting separate from analysis means you can reuse the workflow output in other contexts (a CI comment, a dashboard) without re-running the scan.

```python
report = format_bug_predict_report(
    result=raw_result,
    input_data={"path": "src/"},
)

print(report)
```

**You should see:** a report with a `## Summary` section showing an overall risk score (0–100), a `## Bugs` section organized by severity (HIGH / MEDIUM / LOW), and a `## Suggestions` section with prioritized remediation advice.

---

## Step 5 — Read a finding and understand what it means

Find a HIGH-severity line in your output, for example:

```
src/hooks/executor.py:89   dangerous_eval  eval() on user input
```

Each field tells you something specific:

| Field | Meaning |
|---|---|
| `src/hooks/executor.py:89` | Exact file and line — click to jump there in your editor |
| `dangerous_eval` | Pattern category — `eval()` / `exec()` / `compile()` on dynamic input |
| `eval() on user input` | Plain-English description of why this is risky |

The scanner applies false-positive filtering automatically: `eval()` inside test fixture strings and JavaScript `regex.exec()` calls are suppressed, so every HIGH finding in your output is one the orchestrator judged to be a real risk.

**You should see:** at least one finding per severity tier if your codebase contains any TODO/FIXME comments or broad `except` blocks.

---

## Complete script

```python
from attune.workflows.bug_predict import BugPredictionWorkflow
from attune.workflows.bug_predict_report import format_bug_predict_report

workflow = BugPredictionWorkflow()

raw_result = workflow.execute(path="src/")

report = format_bug_predict_report(
    result=raw_result,
    input_data={"path": "src/"},
)

print(report)
```

Save this as `run_bug_predict.py` and run it with `python run_bug_predict.py`.

---

## What you learned

- **Step 1** — The workflow and the formatter are separate imports because analysis and presentation are intentionally decoupled.
- **Step 2** — `BugPredictionWorkflow()` sets up three subagents (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) under a single orchestrator without any required configuration.
- **Step 3** — `execute(path=...)` drives all three subagents and returns a unified `WorkflowResult`; you don't call each subagent yourself.
- **Step 4** — `format_bug_predict_report` converts that result into the tiered severity report (HIGH / MEDIUM / LOW) with file links and risk scores.
- **Step 5** — Each finding maps a pattern category to a concrete location, and the scanner's false-positive filtering means you can trust HIGH findings to reflect real risk.

## Next steps

Read the full pattern reference — every pattern category, scoring algorithm, and configuration option — by running:

```
attune help-docs ref-skill-bug-predict
```

<!-- attune-generated: source_hash=c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde feature=bug-predict kind=tutorial generated_at=2026-05-16 -->
