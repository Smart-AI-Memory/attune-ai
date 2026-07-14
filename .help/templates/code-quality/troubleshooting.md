---
type: troubleshooting
name: code-quality-troubleshooting
feature: code-quality
depth: troubleshooting
generated_at: 2026-07-14T15:58:49.270997+00:00
source_hash: 1cda16e2ee597c3fc3187497350da0cf77783f31c42c22e4652888adb60ca679
status: generated
---

# Multi-subagent code review across security, quality, performance, and architecture

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'CodeReviewWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `attune workflow run code-quality` errors "unknown workflow" | The slug is `code-review`, not `code-quality` | Run `attune workflow run code-review` (the skill / help topic is `code-quality`) | medium |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Review stops early / partial report | The depth's agent-turn or budget cap was reached | Use a narrower `path`, a shallower `depth`, or accept a deeper (costlier) run | medium |
| A finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **The slug differs from the name.** The feature, skill, and help
  topic are `code-quality`; the workflow slug and MCP tool are
  `code-review`. Use `code-review` for `attune workflow run` and
  the MCP call.
- **Findings are predictions, not proofs.** A CRITICAL or HIGH
  finding means "look here first," not a confirmed defect — and a
  clean review is not a guarantee. Verify before acting.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. For an "unknown workflow" CLI error, confirm you used the
   `code-review` slug.
4. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
5. Confirm the scope: `result.metadata` echoes the `path`, `depth`,
   and `max_turns`.
