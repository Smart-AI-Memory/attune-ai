---
type: troubleshooting
name: doc-gen-troubleshooting
feature: doc-gen
depth: troubleshooting
generated_at: 2026-06-23T16:17:04.175824+00:00
source_hash: bcc987b14e370273da9042e975c82dcf5af466e245d407e9ce45d5250d354384
status: generated
---

# Generate new documentation from source code with three specialized subagents

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'DocumentGenerationWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` (e.g. passing a source string instead of `path`) | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Generation stops early / partial document | The depth's agent-turn or budget cap was reached | Use a narrower `path`, a shallower `depth`, or accept a deeper (costlier) run | medium |
| Expected files weren't written | Doc-gen returns content in the result; it does not write files | Take the document from `final_output` and place it yourself | low |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the main
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **Pass `path`, not a source string.** `execute` reads `path` (and
  `depth`); it does not take a raw source-code string or a
  `doc_type`. The CLI and Python API supply `path` correctly.
- **It generates, it doesn't place.** The output is documentation
  content in the result, not files on disk — review and position it
  yourself.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. If `error` is "path argument is required", confirm you passed
   `path=` (not a source string or other kwarg).
4. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
5. Confirm the scope: `result.metadata` echoes the `path`, `depth`,
   and `max_turns`.
