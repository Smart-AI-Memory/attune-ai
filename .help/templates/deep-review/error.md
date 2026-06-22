---
type: error
name: deep-review-error
feature: deep-review
depth: error
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 0166eb83fb8436c203cdd073439a7339645f40e53cdfe39db4fbed0559eac81d
status: generated
---

# Deep Review errors

## Common error signatures

Failures in `deep_review` typically fall into three categories, corresponding to the three subagents the workflow coordinates:

- **Input errors** — `execute()` receives a `path` argument that is missing, empty, or points to a location the process cannot read. These fail early, before any subagent is launched.
- **Subagent coordination errors** — one or more of the `security-reviewer`, `quality-reviewer`, or `test-gap-reviewer` subagents fails to return findings. The consolidated report may be incomplete or the workflow may raise an exception during synthesis.
- **Result errors** — `execute()` returns a `WorkflowResult` that is missing expected sections (`Security`, `Quality`, `Test Gaps`, `Suggestions`, `Summary`), which indicates a failure during the final consolidation step.

## Where errors originate

All errors originate in `DeepReviewAgentSDKWorkflow.execute()`, defined in `src/attune/workflows/deep_review.py`. The method orchestrates three subagents sequentially and then synthesizes their output. A failure in any subagent propagates through `execute()` to the caller.

When you read a traceback, locate the frame inside `execute()` first — it tells you whether the failure occurred during subagent dispatch or during consolidation.

## How to diagnose

1. **Identify which subagent failed.** The workflow runs `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer` as distinct passes. A traceback that names one of these subagent identifiers points to a domain-specific failure rather than a setup problem.

2. **Verify the `path` argument.** `execute()` takes `path` as a keyword argument. Confirm the path exists, is readable, and resolves to the directory or file you intend to review. An unreadable or nonexistent path will prevent all three subagents from producing findings.

3. **Check whether the report is partially populated.** If `execute()` returns a `WorkflowResult` but sections are empty or absent, one subagent completed while another did not. Compare which of `Security`, `Quality`, and `Test Gaps` are present to narrow down which subagent produced no output.

4. **Enable `DEBUG`-level logging before re-running.** The orchestrator logs state transitions between subagent passes. Raising the log level to `DEBUG` shows you the findings each subagent returned before consolidation, making it possible to see where the output diverges from what you expect.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`, `comprehensive-review`
