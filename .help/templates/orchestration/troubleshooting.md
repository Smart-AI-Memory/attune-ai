---
type: troubleshooting
name: orchestration-troubleshooting
feature: orchestration
depth: troubleshooting
generated_at: 2026-06-24T04:42:36.420317+00:00
source_hash: 8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103
status: generated
---

# Dynamic agent teams, workflow composition, and meta-orchestration of multi-agent pipelines

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'execute' was never awaited` | `ExecutionStrategy.execute` called without `await` | it is async — `await` it | high |
| `get_strategy(name)` raises | unknown name (`ValueError`), or an arg-taking name like `conditional`/`nested` (`TypeError`) | use one of the nine no-arg names; construct arg-taking strategies directly | medium |
| `get_template(id)` returns `None` | no template with that id | list ids via `get_all_templates()` | low |
| Team build fails | a `TeamSpecification` references an unknown template/capability | check the spec against `get_all_templates()` | medium |

### Risk areas

- **Planning is sync; execution is async.** `MetaOrchestrator` methods
  and the builders are synchronous; `ExecutionStrategy.execute` is
  async.
- **`get_strategy` resolves the nine no-arg strategies.** The registry
  also holds `conditional`/`multi_conditional`/`nested`/
  `nested_sequential`, which require constructor args (fetching them bare
  raises `TypeError`).
- **Templates are matched by capability/tier.** A team is only as good
  as the templates the registry can supply.

### Diagnosis order

1. `get_all_templates()` — what agents are available?
2. `MetaOrchestrator().analyze_task(...)` — what does the planner infer?
3. `get_strategy(name)` — is the strategy name valid?
4. Async-not-awaited? `execute` must be awaited.
