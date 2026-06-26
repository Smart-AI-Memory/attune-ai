---
type: error
name: orchestration-error
feature: orchestration
depth: error
generated_at: 2026-06-26T16:19:58.397279+00:00
source_hash: 3da859c638c01505e80876fc298c0d02f94889242bbb1c93df05af5291945567
status: generated
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'run' was never awaited` | `AgentTeam.run` / `ExecutionStrategy.execute` called without `await` | both are async — `await` them | high |
| `get_strategy(name)` raises | unknown name (`ValueError`), or an arg-taking name like `conditional`/`nested` (`TypeError`) | use one of the nine no-arg names; construct arg-taking strategies directly | medium |
| `get_template(id)` returns `None` | no template with that id | list ids via `get_all_templates()` | low |
| A gate blocks but the agent never ran | a `GateSpec.agent_key` does not match any `WorkflowAgent.key` | the agent has no score so the gate fails closed — align the keys | medium |

### Risk areas

- **`run` and `execute` are async.** `AgentTeam.run` and
  `ExecutionStrategy.execute` must be awaited.
- **`get_strategy` resolves the nine no-arg strategies.** The registry
  also holds `conditional`/`multi_conditional`/`nested`/
  `nested_sequential`, which require constructor args (fetching them bare
  raises `TypeError`).
- **Gates fail closed.** A `GateSpec` whose agent errored or produced no
  score fails the gate rather than passing silently.

### Diagnosis order

1. `get_all_templates()` — what agents/templates are available?
2. Are `GateSpec.agent_key`s aligned with `WorkflowAgent.key`s?
3. `get_strategy(name)` — is the strategy name valid?
4. Async-not-awaited? `run` / `execute` must be awaited.
