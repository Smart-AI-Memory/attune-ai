---
name: security-audit
source: content/features/security-audit.md
tags:
- security
- audit
- owasp
- scanning
- cve
type: troubleshooting
---

# Audit code for vulnerabilities with four Agent SDK subagents

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'SecurityAuditWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Audit stops early / partial report | The depth's agent-turn or budget cap was reached | Use a shallower path or accept a deeper (costlier) run | medium |
| `metadata["subagent_transcripts"]` is empty | The session transcript could not be recovered for this run | The synthesized `final_output` is still authoritative; transcripts are a supplement | low |
| A finding looks like a false positive | Findings are LLM predictions, not verified exploits | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **Findings are predictions, not proofs.** The four subagents
  apply LLM judgment; a CRITICAL finding means "audit this first,"
  not "this is a confirmed vulnerability." Verify before acting —
  and never treat a clean report as a security guarantee.
- **Deep audits cost more.** `deep` engages extended thinking and
  a larger budget; reserve it for high-risk areas rather than
  whole-repo sweeps.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
4. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, and `max_turns` actually used.
5. Cross-check findings against `metadata["subagent_transcripts"]`
   to see which subagent surfaced each.
