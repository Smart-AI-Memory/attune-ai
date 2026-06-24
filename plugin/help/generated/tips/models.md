---
name: models
source: content/features/models.md
tags:
- models
- auth
- llm
type: tip
---

# LLM authentication, provider routing, and tier management

## Notes & tips

- **Depend only on the public API.** `attune.models` re-exports the
  registry (`MODEL_REGISTRY`, `ModelInfo`, `ModelTier`, `get_model`,
  `get_all_models`, `get_pricing_for_model`), task routing
  (`TaskType`, `get_tier_for_task`, `get_tasks_for_tier`,
  `is_known_task`), auth (`AuthStrategy`, `AuthMode`,
  `get_auth_strategy`), provider config (`ProviderConfig`,
  `ProviderMode`, `get_provider_config`), and execution (`LLMExecutor`,
  `LLMResponse`, `ExecutionContext`, `MockLLMExecutor`,
  `AdaptiveModelRouter`). Treat anything not exported as private.
- **Pass `tier.value` to the registry.** `get_model` and the registry
  key on the string value; the routing functions accept the enum. When
  in doubt, `.value`.
- **`get_recommended_mode` is pure.** It reads the strategy's
  `subscription_tier`, `default_mode`, thresholds, and the LOC argument
  — no I/O — so it is safe to call in tight loops or tests.
- **Use `MockLLMExecutor` in tests.** It satisfies the `LLMExecutor`
  protocol, returns a deterministic `LLMResponse`, and records calls in
  `call_history` for assertions — no network, no spend.
