---
name: deep-review
source: content/features/deep-review.md
tags:
- review
- security
- quality
- tests
- comprehensive-review
type: error
---

# Multi-pass code review across security, quality, and test gaps

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'DeepReviewAgentSDKWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Invalid focus values. Valid: ..."` | `focus` contained only unrecognized values | Use a subset of `"security"`, `"quality"`, `"test-gaps"` (note the hyphen in `test-gaps`) | medium |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Review stops early / partial report | The depth's agent-turn or budget cap was reached | Use a shallower path, narrow with `focus`, or accept a deeper (costlier) run | medium |
| A finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **`focus` spelling matters.** The valid values are `"security"`,
  `"quality"`, and `"test-gaps"` — `"test-gap"` (no `s`) is
  silently dropped, and an all-invalid `focus` fails the run.
- **Findings are predictions, not proofs.** A CRITICAL or HIGH
  finding means "look here first," not a confirmed defect — and a
  clean review is not a guarantee. Verify before acting.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. For a focus error, confirm the values are a subset of
   `security` / `quality` / `test-gaps`.
4. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
5. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, `max_turns`, and active `focus`.
