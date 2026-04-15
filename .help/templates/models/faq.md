---
type: faq
feature: models
depth: faq
generated_at: 2026-04-14T15:15:09.063402+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Models FAQ

## What is the models feature?

The models feature provides intelligent model selection and authentication management for LLM operations. It automatically routes tasks to the best-performing models based on historical performance data and manages authentication strategies for Claude subscriptions versus API access.

## When should I use models?

Use the models feature when you need to:
- Automatically select the best model for your task type
- Manage authentication between Claude subscription and API modes
- Track model performance across different workflows
- Implement circuit breakers for failing providers
- Optimize costs and latency for LLM operations

## How do I set up authentication?

Run `cmd_auth_setup()` to configure your authentication strategy interactively. This will help you choose between subscription and API modes based on your usage patterns and module size.

You can check your current setup with `cmd_auth_status()` or reset it entirely with `cmd_auth_reset()`.

## How does adaptive model routing work?

The `AdaptiveModelRouter` analyzes historical performance data to select the best model for each task. It considers success rates, latency, costs, and recent failures when making routing decisions.

Use `get_best_model()` with constraints like maximum cost or latency requirements, and the router will recommend the optimal model for your workflow stage.

## What authentication modes are available?

The system supports automatic switching between:
- **Subscription mode**: Uses your Claude Pro/Team subscription for smaller tasks
- **API mode**: Uses Claude API tokens for larger or batch operations
- **Auto mode**: Automatically chooses based on module size and cost optimization

The `AuthStrategy` class manages these preferences and provides cost estimates for different approaches.

## How do circuit breakers protect against failing models?

The `CircuitBreaker` temporarily disables models or providers that exceed failure thresholds. When a provider fails repeatedly, the circuit opens and routes traffic elsewhere until the provider recovers.

You can check circuit breaker status and reset failed providers as needed.

## How do I debug model routing issues?

First, run `pytest -k "models" -v` to verify the system is working correctly.

Check routing statistics with `get_routing_stats()` to see which models are being selected and why. If models aren't performing as expected, examine the telemetry data that feeds into routing decisions.

For authentication issues, use `cmd_auth_status()` to verify your current configuration matches your intended setup.

## Where are the source files?

- `src/attune/models/**`

**Tags:** `models`, `auth`, `llm`
