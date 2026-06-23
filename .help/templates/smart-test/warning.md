---
type: warning
name: smart-test-warning
feature: smart-test
depth: warning
generated_at: 2026-06-23T15:57:46.208360+00:00
source_hash: d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe
status: generated
---

# Find untested code with a coverage audit, then generate pytest tests to close the gaps

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `DeprecationWarning: ...execute(src_path=...) is deprecated` | The audit was called with the legacy `src_path` kwarg | Use `path=` instead (the audit still runs) | low |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry | medium |
| Generated tests don't pass as-is | Generation is a predictive starting point | Review, adjust, and run them before committing | medium |
| Audit finding looks like a false positive | Findings are LLM predictions, not verified defects | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is a
  coroutine on every smart-test workflow. Forgetting to `await` it
  is the single most common mistake.
- **Two slugs, one feature.** The skill / topic is `smart-test`,
  but the CLI slugs are `test-audit` and `test-gen`. And a
  same-named repo-level skill (`.claude/skills/smart-test`) does
  something different — it runs your diff's affected tests.
- **Generation is a draft.** `test-gen` writes a starting point.
  Run and review the output; a generated test that imports the
  wrong symbol or asserts the wrong value is on you to catch.

### Diagnosis order

1. Confirm you are awaiting: `result = await
   TestAuditWorkflow().execute(path="src/")` inside an `async def`
   or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. For a CLI "unknown workflow" error, confirm the slug is
   `test-audit` or `test-gen` (not `smart-test`).
4. On an SDK error, inspect `result.metadata` for the captured SDK
   error fields.
5. Confirm the scope: `result.metadata` echoes the run's `path` /
   `src_path`, `depth`, and `max_turns`.
