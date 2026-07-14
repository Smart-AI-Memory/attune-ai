# Tutorial: Bug Prediction

You'll finish this tutorial with a working Python script that scans a directory, runs the full three-subagent bug prediction workflow, and prints a formatted risk report — so you can see exactly what the tool does and why each piece exists.

## Prerequisites

- Python 3.10 or newer
- The `attune` package installed in your environment
- A directory of Python source files to scan (the tutorial uses `src/` as the target)

## What you will build

A short async script that runs `BugPredictionWorkflow` and renders its
`WorkflowResult` into a readable report using the shared
`attune.voice.report_renderer`, producing output like this:

```
# Bug Prediction

Risk: 2 high-severity findings, moderate overall risk.

**Score:** 55/100

## Pattern Scanner
- 🔴 src/hooks/executor.py:89 — eval() on user input
- 🔴 src/plugins/loader.py:142 — exec() in plugin loader
...
```

By the time the script runs successfully, you'll understand how the orchestrator coordinates its three subagents and how raw results become a readable report.

---

## Step 1 — Import the workflow and the renderer

The workflow and the report renderer live in separate modules — analysis
and presentation are intentionally decoupled. Import both so you can see
the boundary.

```python
from attune.workflows.bug_predict import BugPredictionWorkflow
from attune.voice.report_renderer import render
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

`execute()` is a coroutine — `await` it (or drive the script with
`asyncio.run`). The orchestrator sends each subagent a task derived from
`_TASK_PROMPT_TEMPLATE`, substituting your path for `{path}`.

```python
result = await workflow.execute(path="src/")
```

This is the step where the real work happens: `pattern-scanner` flags dangerous patterns (`eval()`, bare `except:`, TODO markers), `risk-correlator` weighs complexity and change frequency, and `prevention-advisor` ranks remediation strategies. The returned `WorkflowResult` bundles all three subagents' findings.

**You should see:** `execute()` return without raising. Check `result.success` before formatting — a `False` value means `result.error` explains what went wrong instead of a report.

---

## Step 4 — Render the result into a human-readable report

Keeping formatting separate from analysis means you can reuse the workflow
output in other contexts (a CI comment, a dashboard) without re-running
the scan. `result.final_output` carries a `WorkflowReport` when the
subagents' findings parsed as structured output; `render()` turns that
into markdown. Fall back to `result.summary` (always a plain string) when
you just need the one-line takeaway.

```python
from attune.workflows.output import WorkflowReport

if isinstance(result.final_output, WorkflowReport):
    print(render(result.final_output))
else:
    print(result.summary or result.final_output)
```

**You should see:** a report with a title, an overall `**Score:** N/100` line, and one section per subagent (pattern scanner findings, risk correlations, prevention advice).

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
import asyncio

from attune.workflows.bug_predict import BugPredictionWorkflow
from attune.workflows.output import WorkflowReport
from attune.voice.report_renderer import render


async def main() -> None:
    workflow = BugPredictionWorkflow()
    result = await workflow.execute(path="src/")

    if not result.success:
        print(f"Scan failed: {result.error}")
        return

    if isinstance(result.final_output, WorkflowReport):
        print(render(result.final_output))
    else:
        print(result.summary or result.final_output)


asyncio.run(main())
```

Save this as `run_bug_predict.py` and run it with `python run_bug_predict.py`.

---

## What you learned

- **Step 1** — The workflow and the renderer are separate imports because analysis and presentation are intentionally decoupled.
- **Step 2** — `BugPredictionWorkflow()` sets up three subagents (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) under a single orchestrator without any required configuration.
- **Step 3** — `execute(path=...)` is a coroutine that drives all three subagents and returns a unified `WorkflowResult`; you don't call each subagent yourself.
- **Step 4** — `attune.voice.report_renderer.render()` converts a structured `WorkflowReport` into markdown; `result.summary` is always available as a plain-string fallback.
- **Step 5** — Each finding maps a pattern category to a concrete location, and the scanner's false-positive filtering means you can trust HIGH findings to reflect real risk.

## Next steps

Read the full pattern reference — every pattern category, scoring algorithm, and configuration option — by running:

```
attune help-docs ref-skill-bug-predict
```

<!-- attune-generated: source_hash=c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde feature=bug-predict kind=tutorial generated_at=2026-05-16 -->
