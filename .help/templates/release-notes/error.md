---
type: error
name: release-notes-error
feature: release-notes
depth: error
generated_at: 2026-06-23T21:24:13.287162+00:00
source_hash: 3bee45ea7e9bedc48f6fdc7744f2c05ff0fd177419dba9606233f53b10818ab6
status: generated
---

# Draft release notes and an LLM go/no-go readiness advisory with four Agent SDK subagents

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'ReleasePreparationWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with an empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity and retry | medium |
| Advisory stops early / partial report | The depth's agent-turn or budget cap was reached | Use a shallower `depth`, or raise the cap with `ATTUNE_MAX_BUDGET_USD` | medium |
| The release shipped despite a "no-go" | Release-notes is advisory — it never blocks | Use `release-prep` (`attune workflow run release-gate`) for an enforced gate | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the main
  public method and it is a coroutine. Forgetting to `await` it is the
  single most common mistake.
- **Advisory ≠ gate.** The go/no-go is a recommendation from an LLM
  assessor, not a measured pass/fail. Don't wire it into CI as a
  blocking check — use `release-prep` for that.
- **Pass `path`.** `execute` reads `path` (and `depth`); the CLI and
  Python API supply `path` correctly.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path=".")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error`.
3. If `error` is "path argument is required", confirm you passed
   `path=`.
4. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
5. Confirm the scope: `result.metadata` echoes the `path`, `depth`,
   and `max_turns`.
