---
type: troubleshooting
name: bug-predict-troubleshooting
feature: bug-predict
depth: troubleshooting
generated_at: 2026-07-14T22:05:25.786099+00:00
source_hash: 6651bf938b845a590d6af44512242264ef0650223553d1e58325a8c0c6b2e208
status: generated
---

# Predict likely bug hotspots with three Agent SDK subagents

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'BugPredictionWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Scan stops early / partial report | The depth's agent-turn or `max_budget_usd` budget was reached | Use a shallower path or raise depth deliberately (cost rises) | medium |
| `ImportError: cannot import name 'format_bug_predict_report'` | The pre-v4.2.0 formatter module was removed (dead code, zero live callers) | Read `result.final_output` / `result.summary` directly, or render via `attune.voice.report_renderer.render()` | medium |
| Editing `./attune.config.yml`'s `bug_predict` block changes nothing | That block configures the internal static pattern helpers, which the live SDK workflow does not run | Steer the scan with `system_prompt_suffix` (or a deeper `depth`) instead | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it
  is the single most common bug-predict mistake.
- **Findings are predictions, not proofs.** The subagents apply
  LLM judgment; a HIGH finding means "investigate first," not
  "this is definitely a bug." Confirm before acting.
- **The static helpers are not the live scanner.** The regex
  detectors in `bug_predict_patterns.py` and the
  `./attune.config.yml` `bug_predict` settings are a separate
  layer; they do not change what the three subagents do.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
4. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, and `max_turns` actually used.
5. Run the related tests: `pytest -k bug_predict -v`.
