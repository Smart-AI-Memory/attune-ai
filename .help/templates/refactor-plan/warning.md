---
type: warning
name: refactor-plan-warning
feature: refactor-plan
depth: warning
generated_at: 2026-06-23T16:06:40.108874+00:00
source_hash: 198d821e7ba1dffdfe00c207be171d13fcf198bedb8c0fd84f251e83f8015fbb
status: generated
---

# Prioritize tech debt — scan for code smells and generate a refactoring roadmap

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'RefactorPlanWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Roadmap stops early / partial report | The depth's agent-turn or budget cap was reached | Use a narrower `path`, a shallower `depth`, or accept a deeper (costlier) run | medium |
| A finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **It plans, it doesn't apply.** Refactor-plan produces a roadmap;
  it does not edit code. Use simplify-code (or your own change) to
  act on it.
- **Findings are predictions, not proofs.** A high-priority item
  means "look here first," not a confirmed defect. Verify the
  effort and risk estimates against the real code before committing
  to them.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
4. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, and `max_turns`.
