---
type: tip
name: orchestration-tip
feature: orchestration
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 1d31bb00ab6284a8ff06a91f07123af0d56d15af02f09b6311f660814398d142
status: generated
---

# Tip: Choose your execution strategy before wiring agents together

Pick the right `ExecutionStrategy` subclass up front — swapping strategies later requires rethinking data flow between every agent in the pipeline.

**Why:** Each strategy defines not just execution order but also how results pass between stages, so the wrong choice compounds across every step.

Use `get_strategy(strategy_name)` to retrieve a strategy by name rather than instantiating subclasses directly. If the name isn't registered, you get an explicit `ValueError` listing available options — far cheaper than a silent misconfiguration discovered mid-pipeline.

```python
from attune.orchestration import get_strategy

strategy = get_strategy("sequential")  # raises ValueError with available names if unknown
```

For pipelines that reuse the same context across many agents, prefer `PromptCachedSequentialStrategy` over a plain sequential approach — it shares a cached context with a configurable TTL (`cache_ttl`, default 3600 s), which avoids redundant computation on each agent call.

For hierarchical delegation, `DelegationChainStrategy` enforces a `max_depth` (default 3) that prevents runaway recursive delegation. If you find yourself raising that limit, treat it as a signal that the pipeline needs restructuring rather than a deeper chain.

**Tradeoff:** `get_strategy()` returns a pre-configured instance. If you need non-default parameters — such as a custom `max_depth` for `DelegationChainStrategy` or a specific `cached_context` string — instantiate the class directly instead of going through the registry.

## Source files

- `src/attune/orchestration/_strategies/__init__.py`
- `src/attune/orchestration/_strategies/nesting.py`

**Tags:** `orchestration`, `teams`
