---
type: concept
feature: models
depth: concept
generated_at: 2026-04-14T15:13:03.992405+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Models

The models feature is Attune AI's unified system for routing LLM requests to optimal providers based on performance data, authentication strategy, and cost constraints.

## Core architecture

The system centers around intelligent routing that adapts based on real-world performance:

- **`AdaptiveModelRouter`** learns from telemetry to route tasks like `workflow_step` or `code_generation` to the best-performing models
- **`ModelPerformance`** tracks success rates, latency, and costs for each model-task combination, calculating quality scores for ranking
- **`CircuitBreaker`** temporarily disables failing providers when they exceed failure thresholds (default: 5 failures)
- **`EmpathyLLMExecutor`** wraps the routing logic and provides a unified interface for LLM execution

## Authentication strategy

The `AuthStrategy` class automatically selects between Claude subscriptions and API access based on your usage patterns:

- Estimates tokens using a 4:1 lines-of-code multiplier
- Recommends subscription mode for small modules (<500 lines), API mode for large modules (>2000 lines)
- Calculates cost comparisons between subscription tiers (Pro, Team) and pay-per-token API usage
- Stores preferences like `prefer_subscription` and `cost_optimization` for consistent decisions

## Performance tracking

Every LLM call generates an `LLMResponse` with execution metrics:

```
content: "Generated code or text"
model_id: "claude-3-5-sonnet-20241022"
tokens_input: 1250
tokens_output: 800
cost_estimate: 0.0234
latency_ms: 1800
```

The router uses this data to build `ModelPerformance` records tracking success rates and average costs per task type, then routes future requests to models with the highest quality scores.

## Task-based routing

The system recognizes task types like `chat`, `code_generation`, and `security_incident`, with special handling for `REALTIME_REQUIRED_TASKS` that need immediate responses. The router can enforce constraints like maximum cost (`max_cost`) or latency (`max_latency_ms`) when selecting models.
