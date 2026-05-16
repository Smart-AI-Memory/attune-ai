# Models architecture

LLM authentication, provider routing, and tier management.

## Purpose

The `models` subsystem owns everything between a workflow stage requesting an LLM call and the HTTP request leaving the process: task-to-tier mapping, model selection, authentication strategy, provider configuration, fallback chains, circuit breaking, retry logic, and telemetry recording. It does **not** own workflow definition, prompt construction, or result parsing — those belong to the callers. This boundary means you can change how a tier resolves to a model, or add a new fallback strategy, without touching any workflow code.

## Key classes

| Class | Responsibility | File |
|-------|---------------|------|
| `ModelRegistry` | Single source of truth for all known models, tiers, and pricing | `src/attune/models/registry.py` |
| `ModelInfo` | Carries per-model metadata (tier, provider, pricing) used throughout routing | `src/attune/models/registry.py` |
| `ModelTier` | Enum that maps symbolic tiers (CHEAP, CAPABLE, PREMIUM) to routing logic | `src/attune/models/registry.py` |
| `ModelProvider` | Enum of supported providers; Claude-native since v3.0.0 | `src/attune/models/registry.py` |
| `TaskType` | Canonical task-type identifiers shared by routers and telemetry | `src/attune/models/tasks.py` |
| `TaskInfo` | Associates a task type with its default tier and constraints | `src/attune/models/tasks.py` |
| `AuthStrategy` | Persisted configuration that resolves a module's line count to an `AuthMode` and cost estimate | `src/attune/models/auth_strategy.py` |
| `AuthMode` | Enum of authentication modes (e.g., API key vs. subscription) selected by `AuthStrategy` | `src/attune/models/auth_strategy.py` |
| `SubscriptionTier` | Enum of Claude subscription tiers referenced by `AuthStrategy` | `src/attune/models/auth_strategy.py` |
| `ProviderConfig` | User-scoped provider selection and credentials | `src/attune/models/provider_config.py` |
| `ProviderMode` | Enum of provider selection modes; Anthropic-only as of v5.0.0 | `src/attune/models/provider_config.py` |
| `ModelPerformance` | Aggregates success rate, latency, cost, and a derived `quality_score` for one model/task pair | `src/attune/models/adaptive_routing.py` |
| `AdaptiveModelRouter` | Queries telemetry to pick the best model for a workflow stage, with optional cost/latency caps; also recommends tier upgrades | `src/attune/models/adaptive_routing.py` |
| `ExecutionContext` | Request-scoped metadata (user, workflow, step, hints) threaded through an executor call | `src/attune/models/executor.py` |
| `LLMResponse` | Standardized response envelope with token counts, cost, latency, and backward-compat property aliases | `src/attune/models/executor.py` |
| `LLMExecutor` | Protocol that all executors implement; the seam for swapping execution backends | `src/attune/models/executor.py` |
| `MockLLMExecutor` | In-process test double implementing `LLMExecutor` | `src/attune/models/executor.py` |
| `EmpathyLLMExecutor` | Concrete executor that wraps `EmpathyLLM`, applies tier-based routing, and records telemetry | `src/attune/models/empathy_executor.py` |
| `CircuitBreakerState` | Mutable state (failure count, open/closed, timestamps) for one provider+tier slot | `src/attune/models/circuit_breaker.py` |
| `CircuitBreaker` | Opens/closes per-provider slots after threshold failures; resets after a recovery timeout | `src/attune/models/circuit_breaker.py` |
| `RetryPolicy` | Configures retry count and backoff for transient failures | `src/attune/models/retry.py` |
| `FallbackStep` | One node in an ordered fallback chain (provider, tier, model) | `src/attune/models/fallback_policy.py` |
| `FallbackPolicy` | Ordered list of `FallbackStep`s with a selection strategy | `src/attune/models/fallback_policy.py` |
| `FallbackStrategy` | Enum of strategies for choosing the next fallback (e.g., cheapest, fastest) | `src/attune/models/fallback_policy.py` |
| `ResilientExecutor` | Wraps any `LLMExecutor` and layers retry, circuit breaking, and fallback execution on top | `src/attune/models/resilient_executor.py` |
| `AllProvidersFailedError` | Raised by `ResilientExecutor` when every fallback step is exhausted | `src/attune/models/resilient_executor.py` |
| `TelemetryBackend` | Protocol for telemetry storage; implement this to swap the storage layer | `src/attune/models/telemetry/backend.py` |
| `TelemetryStore` | Default JSONL file-based implementation of `TelemetryBackend` | `src/attune/models/telemetry/storage.py` |
| `TelemetryAnalytics` | Reads from `TelemetryBackend` to produce performance summaries consumed by `AdaptiveModelRouter` | `src/attune/models/telemetry/analytics.py` |
| `LLMCallRecord` | Telemetry record for one API call (model, tokens, cost, latency) | `src/attune/models/telemetry/data_models.py` |
| `WorkflowStageRecord` | Telemetry record for one stage within a workflow run | `src/attune/models/telemetry/data_models.py` |
| `WorkflowRunRecord` | Telemetry record for a complete workflow execution | `src/attune/models/telemetry/data_models.py` |
| `TaskRoutingRecord` | Telemetry record capturing the model selection decision for a task | `src/attune/models/telemetry/data_models.py` |
| `TestExecutionRecord` | Telemetry record for QA test runs | `src/attune/models/telemetry/data_models.py` |
| `CoverageRecord` | Telemetry record for test coverage snapshots | `src/attune/models/telemetry/data_models.py` |
| `AgentAssignmentRecord` | Telemetry record for Tier 1 agent assignment events | `src/attune/models/telemetry/data_models.py` |
| `FileTestRecord` | Telemetry record linking a test execution to a specific source file | `src/attune/models/telemetry/data_models.py` |

> **Design note:** `TelemetryStore` (storage) and `TelemetryAnalytics` (query) are separate classes even though both touch the same JSONL files. This keeps write paths and read paths independently testable and makes it straightforward to replace the storage backend without changing analytics queries.

## Data flow

A call from workflow code travels through two parallel concerns — execution and telemetry — before returning a result that feeds back into routing decisions:

```
Workflow code
    │
    │  (workflow, stage, task_type, prompt)
    ▼
AdaptiveModelRouter ◄────────────────────────────────┐
    │  get_best_model(workflow, stage,                │
    │    max_cost, max_latency_ms, min_success_rate)  │
    │                                                 │
    │  queries                                        │
    ▼                                                 │
TelemetryAnalytics                                    │
    │  aggregates ModelPerformance                    │
    │  (quality_score = f(success_rate, latency,      │
    │                     cost, sample_size))         │
    │                                                 │
    │  returns model_id                               │
    ▼                                                 │
AuthStrategy                                          │
    │  resolves AuthMode for this call                │
    ▼                                                 │
EmpathyLLMExecutor                                    │
    │  .run(task_type, prompt, system,                │
    │       context: ExecutionContext)                │
    │                                                 │
    ▼                                                 │
ResilientExecutor                                     │
    │                                                 │
    ├──[attempt 1]──► CircuitBreaker.is_available?    │
    │                     │ yes                       │
    │                     ▼                           │
    │               EmpathyLLM (HTTP)                 │
    │                     │ success                   │
    │                     ▼                           │
    │               CircuitBreaker.record_success     │
    │                     │                           │
    │               LLMResponse ──────────────────────┤
    │                                                 │
    ├──[failure]──► RetryPolicy (backoff)             │
    │                     │ retries exhausted         │
    │                     ▼                           │
    │               CircuitBreaker.record_failure     │
    │                     │ threshold crossed         │
    │                     ▼                           │
    │               CircuitBreaker opens slot         │
    │                     │                           │
    └──[next FallbackStep]──► (repeat from attempt 1) │
          │ all steps exhausted                       │
          ▼                                           │
    AllProvidersFailedError                           │
                                                      │
LLMResponse                                           │
    │                                                 │
    ▼                                                 │
TelemetryStore (JSONL)                                │
    │  writes LLMCallRecord,                          │
    │  TaskRoutingRecord, WorkflowStageRecord, ...    │
    │                                                 │
    └─────────────────────────────────────────────────┘
         (next call reads updated performance data)
```

## Design decisions

**`LLMExecutor` as a Protocol, not a base class.** Callers depend only on the protocol; `EmpathyLLMExecutor`, `MockLLMExecutor`, and `ResilientExecutor` all satisfy it without sharing an inheritance hierarchy. This makes test substitution trivial and avoids MRO issues when `ResilientExecutor` wraps another executor instance.

**`ResilientExecutor` wraps rather than extends `EmpathyLLMExecutor`.** Resilience concerns (retry, circuit breaking, fallback) are applied as a decoration layer at construction time rather than baked into the base executor. This means you can use `EmpathyLLMExecutor` directly in tests where you want to observe raw failures, and apply `ResilientExecutor` only in production paths.

**Telemetry write path and read/analytics path are separate classes.** `TelemetryStore` owns writes; `TelemetryAnalytics` owns reads. `AdaptiveModelRouter` depends only on analytics, not on storage, so you can replace `TelemetryStore` with a database-backed backend without touching the router.

**`AuthStrategy` is file-persisted and size-aware.** Rather than requiring callers to pass auth configuration on every call, `AuthStrategy` is saved to disk and loaded globally via `get_auth_strategy()`. The `get_recommended_mode(module_lines)` method uses configurable line-count thresholds (`small_module_threshold`, `medium_module_threshold`) to recommend subscription vs. API-key mode — reflecting the cost-optimization goal described in [tier routing](concepts/tier-routing.md).

## Extension points

**Add a new execution backend.** Implement the `LLMExecutor` protocol in `src/attune/models/executor.py` — define `run()`, `get_model_for_task()`, and `estimate_cost()`. Wrap your implementation with `ResilientExecutor` to inherit retry, circuit breaking, and fallback for free.

**Swap the telemetry storage layer.** Implement `TelemetryBackend` (the protocol in `src/attune/models/telemetry/backend.py`) and pass your instance to `get_telemetry_store()`. `TelemetryAnalytics` and `AdaptiveModelRouter` will use it automatically without modification.

**Define a new fallback chain.** Construct a `FallbackPolicy` with an ordered list of `FallbackStep` objects and a `FallbackStrategy` enum value, then pass it to `ResilientExecutor`. The constants `DEFAULT_FALLBACK_POLICY` and `SONNET_TO_OPUS_FALLBACK` in `fallback_policy.py` are the reference examples.

**Register a new task type.** Add a `TaskType` entry and a corresponding `TaskInfo` in `src/attune/models/tasks.py`. Update `TASK_TIER_MAP` (exported from the registry module) to assign it a default tier. `AdaptiveModelRouter` and telemetry recording will pick it up automatically because both read from `TASK_TIER_MAP`.

**Adjust adaptive routing scoring.** `ModelPerformance.quality_score` is a derived property computed from `success_rate`, `avg_latency_ms`, `avg_cost`, and `sample_size`. Modifying its formula changes how `AdaptiveModelRouter.get_best_model()` ranks candidates across all workflows without requiring changes to the router itself.

For usage details, see the reference documentation rather than this document.

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 127 | error | `[tier routing](concepts/tier-routing.md)` — target does not exist |
| Line 48 | warning | `1 agent` — no deterministic verifier; please confirm manually |
