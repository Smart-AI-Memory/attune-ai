---
type: troubleshooting
name: orchestration-troubleshooting
feature: orchestration
depth: troubleshooting
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 1d31bb00ab6284a8ff06a91f07123af0d56d15af02f09b6311f660814398d142
status: generated
---

# Troubleshoot orchestration

## Before you start

This page covers issues with meta-orchestration: dynamic team composition, execution strategies (Sequential, Parallel, Debate, Teaching, Refinement, Adaptive, and conditional variants), workflow registration, and agent template resolution.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `ValueError: Unknown strategy: {...}` | The strategy name passed to `get_strategy()` is misspelled or not yet registered. Print `get_strategy.__doc__` or catch the error — the message lists available strategies. |
| `ValueError: Unknown workflow: {...}` | The workflow ID passed to `get_workflow()` was never registered. Call `register_workflow()` before referencing it in a `NestedStrategy` or `NestedSequentialStrategy`. |
| `get_template()` returns `None` | The template ID is not in the registry. Call `get_all_templates()` to list every registered ID and confirm yours is present. |
| `DelegationChainStrategy` raises or hangs | The `max_depth` limit (default: 3) was hit. Either reduce nesting depth or increase `max_depth` in the constructor: `DelegationChainStrategy(max_depth=5)`. |
| `NestedStrategy` or `NestedSequentialStrategy` raises | The `WorkflowReference` points to an unregistered workflow. Verify with `get_workflow(workflow_id)` before constructing the strategy. |
| A workflow stage silently produces no output | Check whether the `StrategyResult` from `execute()` carries an error field rather than raising. Log the full result object before discarding it. |
| `ConditionalStrategy` always takes the same branch | The `Condition` evaluates against the `context` dict. Print the context at the branch point to confirm the expected keys and values are present. |
| Intermittent failures across runs | Look for shared mutable state: `WORKFLOW_REGISTRY` is a module-level registry, so tests or concurrent calls that register/unregister entries can interfere. Isolate with fresh registrations per test. |
| `PromptCachedSequentialStrategy` returns stale results | The cache TTL (default: 3600 s) has not expired. Instantiate with a shorter TTL or pass a fresh `cached_context` string: `PromptCachedSequentialStrategy(cache_ttl=0)`. |

## Diagnose the failure

Work through these steps in order — each one is cheaper than the next.

### 1. Reproduce in isolation

Strip the failing call to its minimum required arguments and run it directly in a Python shell or a short script. For strategy failures:

```python
from attune.orchestration import get_strategy
strategy = get_strategy("SequentialStrategy")   # replace with your strategy name
```

If this raises `ValueError`, the name is wrong or the strategy is not registered.

### 2. List what is registered

Before assuming a bug in execution logic, confirm that your strategies, workflows, and templates are actually registered:

```python
from attune.orchestration import get_all_templates
from attune.orchestration._strategies import get_strategy   # catches ValueError on bad name

# List all agent templates
print([t.id for t in get_all_templates()])

# List templates by capability or tier
from attune.orchestration import get_templates_by_capability, get_templates_by_tier
print(get_templates_by_capability("security"))
print(get_templates_by_tier("senior"))
```

### 3. Enable DEBUG logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Re-run your orchestration pipeline. Log output will show which agents are dispatched and where execution stops.

### 4. Inspect strategy execution directly

Call `execute()` on the strategy with a minimal agent list and context dict, then inspect the full `StrategyResult` before it gets consumed by higher-level code:

```python
result = strategy.execute(agents=my_agents, context={"target": "src/"})
print(result)   # check for error fields or empty outputs
```

### 5. Run the relevant tests

```bash
pytest -k "orchestration" -v
```

If a test covers the failing path, its fixtures give you a known-good minimal setup to compare against your inputs.

## Common fixes

**Unknown strategy name**
The error message from `get_strategy()` lists available strategies. Register a custom one if yours is missing:

```python
from attune.orchestration._strategies import register_strategy
from my_module import MyCustomStrategy
register_strategy("MyCustomStrategy", MyCustomStrategy)
```

**Unregistered workflow for nested execution**
Register the workflow before building any `NestedStrategy` or `NestedSequentialStrategy` that references it:

```python
from attune.orchestration._strategies.nesting import register_workflow
register_workflow(my_workflow_definition)   # WorkflowDefinition instance
```

**Template not found**
Register the template at runtime before the orchestrator resolves it:

```python
from attune.orchestration import register_custom_template
register_custom_template(my_template)   # AgentTemplate instance
```

To remove a template that is interfering with resolution:

```python
from attune.orchestration import unregister_template
removed = unregister_template("bad-template-id")   # returns False if ID not found
```

**Delegation depth exceeded**
Reduce your nesting or raise the limit explicitly:

```python
from attune.orchestration import DelegationChainStrategy
strategy = DelegationChainStrategy(max_depth=5)
```

**Stale cache in `PromptCachedSequentialStrategy`**
Force a fresh execution by setting `cache_ttl=0` or passing a new `cached_context`:

```python
from attune.orchestration import PromptCachedSequentialStrategy
strategy = PromptCachedSequentialStrategy(cached_context=fresh_context, cache_ttl=0)
```

**Dependency version mismatch**
If orchestration broke after an install or update, confirm the installed package versions match what the project expects:

```bash
pip show attune
pip install --upgrade attune   # or pin to a known-good version
```

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 94 (code fence) | error | `from my_module import …` — module not importable |
