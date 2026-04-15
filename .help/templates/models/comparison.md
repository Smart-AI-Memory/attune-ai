---
type: comparison
feature: models
depth: comparison
generated_at: 2026-04-14T15:15:51.197941+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Choosing between authentication strategies for Claude AI

## Authentication options

The models feature provides two authentication approaches for Claude AI integration: subscription-based access and API key access. Your choice affects cost, latency, and usage limits.

| Feature | Subscription Mode | API Mode |
|---------|------------------|----------|
| **Cost structure** | Monthly subscription fee | Pay-per-token usage |
| **Best for** | Regular, predictable usage | Sporadic or variable usage |
| **Token limits** | Higher daily limits | Rate-limited by tier |
| **Latency** | Lower latency for interactive tasks | Standard API latency |
| **Setup complexity** | Subscription management required | Simple API key setup |
| **Cost optimization** | Fixed monthly cost regardless of usage spikes | Scales directly with usage |

## Model routing strategies

When you have multiple providers configured, the `AdaptiveModelRouter` chooses models based on performance telemetry:

**Quality-first routing** prioritizes models with the highest success rates and lowest failure counts for your specific workflows. The router calculates a quality score from `success_rate`, `avg_latency_ms`, and `recent_failures`.

**Cost-constrained routing** respects your `max_cost` parameter while still meeting minimum success rate thresholds (default 0.8). Use this when operating under budget constraints.

**Latency-optimized routing** filters by `max_latency_ms` requirements, essential for real-time tasks like `chat`, `interactive_debug`, and `live_coding`.

## Circuit breaker behavior

The `CircuitBreaker` temporarily disables failing providers to prevent cascading failures:

- **Closed state**: Normal operation, requests flow through
- **Open state**: Provider disabled after 5 consecutive failures (configurable)
- **Half-open state**: Limited test requests after 60-second recovery timeout

Failed providers automatically re-enter rotation once they demonstrate stability.

## Use subscription mode when

- You process more than 2,000 lines of code regularly (above `medium_module_threshold`)
- You need consistent access to premium tiers for complex tasks
- Your workflow includes real-time tasks requiring low latency
- You want predictable monthly costs regardless of usage spikes

## Use API mode when

- You process fewer than 500 lines of code per session (`small_module_threshold`)
- Your usage is sporadic or experimental
- You need granular cost control tied directly to usage
- You're evaluating Claude integration before committing to a subscription

## Use adaptive routing when

- You have multiple providers configured with performance telemetry
- Your workloads have varying requirements for cost, latency, and reliability
- You want automatic failover when providers experience issues
- You need tier upgrade recommendations based on historical performance

The `AuthStrategy.get_recommended_mode()` method analyzes your module size and usage patterns to suggest the most cost-effective approach. For modules under 500 lines, it typically recommends API mode; for larger codebases with regular usage, subscription mode offers better value.
