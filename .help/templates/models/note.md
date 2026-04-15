---
type: note
feature: models
depth: note
generated_at: 2026-04-14T15:15:39.801514+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Note: models

## Context

The models module handles LLM provider routing, authentication strategy management, and adaptive model selection based on performance telemetry.

## Model routing and performance

Attune routes tasks to different models based on historical performance data. The `AdaptiveModelRouter` analyzes telemetry to recommend the best model for each workflow stage, considering factors like success rate, latency, and cost. Model performance metrics are tracked through the `ModelPerformance` dataclass, which calculates quality scores for ranking models.

The routing system includes circuit breaker functionality to temporarily disable failing providers and prevent cascading failures. When providers fail repeatedly, the circuit breaker opens to give them time to recover.

## Authentication strategies

The module provides flexible authentication for Claude subscriptions versus API access. The `AuthStrategy` class determines the optimal authentication mode based on module size:

- Small modules (under 500 lines): Prefer subscription-based access
- Medium modules (500-2000 lines): Use automatic selection
- Large modules (over 2000 lines): Typically use API access for better cost control

Authentication configuration is managed through interactive CLI commands that guide users through setup based on their usage patterns and subscription tier.

## Execution context

LLM calls are wrapped with execution context that tracks workflow information, user sessions, and task metadata. The `EmpathyLLMExecutor` serves as the default executor, combining model routing with standardized response formatting through the `LLMResponse` dataclass.

## CLI interface

The module can be run as a CLI tool for authentication management:

- `cmd_auth_setup()`: Interactive first-time authentication setup
- `cmd_auth_status()`: Display current configuration
- `cmd_auth_recommend()`: Get authentication recommendations for specific files
- `cmd_auth_reset()`: Clear existing configuration

**Tags:** `models`, `auth`, `llm`
