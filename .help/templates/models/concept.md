---
type: concept
name: models
tags: [models, auth, llm, routing, performance]
source: developer-guidance
---

# Models

The models system manages LLM provider routing, authentication strategies, and performance-based model selection across Attune's AI workflows.

## What it does

The models system solves three core problems in multi-provider LLM orchestration:

1. **Smart routing** — Automatically selects the best model for each task based on historical performance metrics like success rate, latency, and cost
2. **Authentication strategy** — Determines whether to use Claude subscriptions or API keys based on your usage patterns and module size
3. **Resilience** — Handles provider failures with circuit breakers and automatic fallbacks to keep workflows running

## Core components

**Performance tracking and routing**
- `ModelPerformance` tracks success rates, latency, cost, and failure counts for each model on specific tasks
- `AdaptiveModelRouter` uses this telemetry to recommend the best model for each workflow stage, with constraints for maximum cost and latency
- Circuit breakers (`CircuitBreaker`) temporarily disable failing providers and gradually re-enable them

**Authentication strategy management**
- `AuthStrategy` determines whether to use Claude subscriptions vs API keys based on your code module size and usage patterns
- Automatically recommends subscription mode for small modules (under 500 lines) and API mode for larger codebases
- CLI commands handle interactive setup, status checking, and recommendations

**Execution and response handling**
- `EmpathyLLMExecutor` wraps the core LLM with intelligent routing and telemetry collection
- `LLMResponse` provides a standardized interface across all providers with cost estimates, token counts, and performance metadata
- `ExecutionContext` carries workflow information for routing decisions and telemetry tracking

## How the pieces work together

When you run an AI workflow:

1. The `EmpathyLLMExecutor` receives your task type (like "code_review" or "documentation")
2. The `AdaptiveModelRouter` queries performance history and selects the best model within your cost/latency constraints
3. The `AuthStrategy` determines whether to use subscription or API authentication based on your module size
4. Circuit breakers check if the selected provider is healthy
5. The LLM executes your task and returns a standardized `LLMResponse`
6. Performance metrics are recorded to improve future routing decisions

This creates a feedback loop where the system gets smarter about model selection as you use it more.

## Authentication strategy logic

The system automatically chooses between Claude subscription and API modes:

| Module size | Recommended mode | Why |
|-------------|------------------|-----|
| < 500 lines | Subscription | Interactive features work better for small codebases |
| 500-2000 lines | Auto-detect | Balances cost and functionality |
| > 2000 lines | API | Better cost control for large batch operations |

You can override these defaults through the CLI or by modifying your `AuthStrategy` configuration.
