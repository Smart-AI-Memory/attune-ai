---
type: troubleshooting
name: deep-review-troubleshooting
feature: deep-review
depth: troubleshooting
generated_at: 2026-06-02T10:54:11.455541+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Troubleshoot deep review

## Before you start

`deep_review` runs a multi-pass review by coordinating three subagents — `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer` — then synthesizes their findings into a single consolidated report. Most failures trace to one of three causes: a bad `path` argument, a subagent that didn't complete, or a synthesis step that produced an incomplete report.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `deep_review` raises an exception immediately | Whether `path` resolves to a real directory or file on disk |
| Report is missing a section (Security, Quality, or Test Gaps) | Which subagent produced that section — one of `security-reviewer`, `quality-reviewer`, or `test-gap-reviewer` may have failed silently |
| Overall code health score is absent from the Summary | Whether `DeepReviewAgentSDKWorkflow.execute()` returned a complete `WorkflowResult` or an early partial result |
| Review completes but findings appear empty or generic | Whether `path` pointed at the intended target — a wrong path yields a valid but content-free report |
| Execution is much slower than expected | Whether `path` targets a very large directory; the three subagents run across the full tree |

## Diagnosis steps

1. **Confirm the path argument is valid.**
   Run `ls <path>` (or `dir <path>` on Windows) before invoking `deep_review`. An inaccessible or misspelled path is the most common cause of immediate failure and costs nothing to check.

2. **Reproduce with the minimal call.**
   Strip the invocation down to its required argument:
   ```python
   from workflows.deep_review import DeepReviewAgentSDKWorkflow
   result = DeepReviewAgentSDKWorkflow().execute(path="<your-path>")
   print(result)
   ```
   Confirm the failure occurs outside any surrounding orchestration before investigating further.

3. **Check which subagents completed.**
   The three subagents are `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer`. If the consolidated report is missing one of the corresponding sections (Security, Quality, or Test Gaps), the matching subagent is the likely failure point. Review any exception or truncated output associated with that agent.

4. **Run the related tests.**
   ```
   pytest -k "deep_review" -v
   ```
   A failing test that exercises your code path will surface the exact input and fixture state that triggers the bug.

5. **Inspect the `WorkflowResult` directly.**
   If the call returns without raising but the report looks wrong, print the raw `WorkflowResult` returned by `execute()`. A partial or malformed result indicates the synthesis step — which runs after all three subagents finish — did not receive complete input.

## Common fixes

- **Wrong or inaccessible path.** Pass an absolute path to rule out working-directory ambiguity:
  ```python
  import os
  result = DeepReviewAgentSDKWorkflow().execute(path=os.path.abspath("relative/path"))
  ```

- **Subagent failure causing a missing report section.** If one subagent fails, the synthesis step may still run but produce an incomplete report. Re-run with a smaller, isolated subtree to confirm which subagent is failing:
  ```python
  result = DeepReviewAgentSDKWorkflow().execute(path="/path/to/single/module")
  ```

- **Dependency or environment mismatch.** A changed environment can cause subagent behavior to differ from expectations. Verify your installed packages match your lockfile:
  ```
  pip show attune
  ```
  This fix requires changes outside `deep_review` itself — align your environment before re-running.

- **Unexpectedly large scope.** If execution is slow, narrow `path` to a subdirectory. All three subagents traverse the full path, so pointing at a large monorepo root multiplies the cost.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`, `comprehensive-review`
