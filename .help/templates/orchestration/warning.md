---
type: warning
feature: orchestration
depth: warning
generated_at: 2026-04-14T15:17:38.164225+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration cautions

## What to watch for

The orchestration system manages dynamic agent teams and workflow execution strategies. Several patterns can lead to runtime failures or unexpected behavior.

## Risk areas

### Strategy registry collisions

`get_strategy()` raises `ValueError` for unknown strategy names, but the error message only shows available strategies at registration time. If you register strategies conditionally or in different order across environments, the same code can succeed in development but fail in production.

**Mitigation:** Always register strategies before calling `get_strategy()`, and use consistent registration order across environments.

### Workflow nesting depth bombs

`DelegationChainStrategy` and `NestedStrategy` enforce maximum depth limits (default 3), but nested workflows can still create exponential execution trees. A workflow that delegates to 3 sub-workflows, each delegating to 3 more, creates 9 execution paths at depth 2.

**Mitigation:** Set conservative `max_depth` values and monitor execution time in nested workflows.

### Template registry state leaks

`register_custom_template()` adds templates to a global registry that persists across test runs. Tests that register templates without cleanup can cause other tests to see unexpected templates or fail due to ID conflicts.

**Mitigation:** Use `unregister_template()` in test teardown, or prefer dependency injection over global registry access.

### Cached context staleness

`PromptCachedSequentialStrategy` caches context for `cache_ttl` seconds (default 3600). Long-running processes can serve stale cached context across workflow executions, causing agents to work with outdated information.

**Mitigation:** Set appropriate TTL values for your use case, or use fresh strategy instances for workflows that require current context.

### Conditional strategy branch misses

`ConditionalStrategy` and `MultiConditionalStrategy` execute the `else_branch` or `default_branch` when conditions don't match. If you don't provide default branches, failed conditions result in no execution rather than an error.

**Mitigation:** Always provide default branches in conditional strategies, even if they just log the unexpected condition.

## How to avoid problems

1. **Initialize strategies explicitly.** Don't rely on lazy strategy registration - register all strategies your application needs during startup.

2. **Test with realistic nesting.** Nested workflows can behave differently at depth 1 versus depth 3. Test the maximum nesting depth your application will use.

3. **Isolate test registry state.** Clear the template registry between tests that use `register_custom_template()` to prevent state leaks.

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`
