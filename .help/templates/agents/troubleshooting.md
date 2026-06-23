---
type: troubleshooting
name: agents-troubleshooting
feature: agents
depth: troubleshooting
generated_at: 2026-06-23T22:44:18.994422+00:00
source_hash: 9f8352e822bbdc7e4000d3afae65bd38c29cb5a219fd6aded8e91de285f5a54a
status: generated
---

# Universal Agent Factory — create, run, and orchestrate AI agents across frameworks

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'BaseAgent.invoke' was never awaited` | `invoke` / `run` called without `await` | They are coroutines — `await` them or use `asyncio.run` | high |
| Constructing a non-native factory raises / `is_available()` is `False` | The framework's optional dependency isn't installed | Install the framework extra, or use `native`; check `list_frameworks(installed_only=True)` | high |
| `recommend_framework` / `list_frameworks` "needs an instance" error | Called as if instance-only | They are callable on the class; call `AgentFactory.list_frameworks()` | low |
| `get_agent(name)` returns `None` | No agent with that name was created on this factory | Check `list_agents()`; names are per-factory | low |
| A tool isn't used by the agent | Tool not added / wrong schema | Build it with `create_tool(...)` and pass it via `tools=` or `add_tool(...)` | medium |

### Risk areas

- **The run methods are async.** `invoke`, `run`, and `stream` are
  coroutines — forgetting to `await` is the most common mistake.
- **Non-native frameworks are optional.** They load lazily; check
  `is_available()` / `list_frameworks(installed_only=True)` before
  selecting one.
- **Scope.** This feature is the Factory; the release agent team and
  its state store live under release-prep, not here.

### Diagnosis order

1. Confirm you are awaiting: `await agent.invoke(...)` /
   `await workflow.run(...)`.
2. Confirm the framework is installed: `AgentFactory.list_frameworks(
   installed_only=True)`.
3. For a missing agent, check `list_agents()`.
4. For tool issues, confirm the tool was built with `create_tool` and
   attached.
