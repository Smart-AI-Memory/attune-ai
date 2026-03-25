# Agent Factory Module Overview

The Agent Factory is a universal factory pattern implementation
that provides a framework-agnostic interface for creating agents
and workflows. It supports five agent frameworks while
maintaining a unified API with integrated cost optimization,
resilience patterns, and cross-agent learning.

---

## Architecture

```text
┌───────────────────────────────────────────────┐
│            AgentFactory (entry point)          │
│  create_agent() / create_workflow()            │
└──────────────────┬────────────────────────────┘
                   │ delegates to
                   ▼
┌──────────────────────────────────────────────┐
│          Framework Adapters                   │
│  Native │ LangChain │ LangGraph │ AutoGen │  │
│                                  Haystack │  │
└──────────────────┬───────────────────────────┘
                   │ creates
                   ▼
┌──────────────────────────────────────────────┐
│            BaseAgent instance                 │
└─────┬────────────────────┬───────────────────┘
      │ optional wrap       │ optional wrap
      ▼                     ▼
┌─────────────┐  ┌──────────────────────┐
│ MemoryAware │  │   ResilientAgent     │
│   Agent     │  │  circuit breaker     │
│  (inner)    │  │  retry + timeout     │
└─────────────┘  │  fallback (outer)    │
                 └──────────────────────┘
```

When both `memory_graph_enabled` and `resilience_enabled` are
set, the factory applies wrappers in this order:

1. Framework adapter creates the base agent
2. `MemoryAwareAgent` wraps it (inner)
3. `ResilientAgent` wraps the result (outer)

This means resilience patterns protect both the agent call
and the memory graph queries.

---

## Module Structure

```text
src/attune/agent_factory/
├── __init__.py              # Public API exports
├── base.py                  # Enums, configs, abstract classes
├── factory.py               # AgentFactory main class
├── framework.py             # Framework enum and detection
├── decorators.py            # Operation decorators
├── resilient.py             # ResilientAgent wrapper
├── memory_integration.py    # MemoryAwareAgent wrapper
└── adapters/
    ├── __init__.py          # Lazy-loading adapter registry
    ├── native.py            # Empathy native adapter
    ├── langchain_adapter.py # LangChain adapter
    ├── langgraph_adapter.py # LangGraph adapter
    ├── autogen_adapter.py   # Microsoft AutoGen adapter
    ├── haystack_adapter.py  # deepset Haystack adapter
    └── wizard_adapter.py    # Attune wizard adapter
```

---

## Design Patterns

| Pattern | Where | Purpose |
|---------|-------|---------|
| **Factory** | `AgentFactory` | Create agents/workflows via adapters |
| **Adapter** | `BaseAdapter` + implementations | Framework-specific agent creation |
| **Wrapper** | `ResilientAgent`, `MemoryAwareAgent` | Add cross-cutting concerns |
| **Decorator** | `decorators.py` | Reusable operation enhancements |
| **Lazy Loading** | `adapters/__init__.py` | Optional deps loaded on demand |
| **Configuration Object** | `AgentConfig`, `WorkflowConfig` | Structured creation params |

---

## Supported Frameworks

| Framework | Use Case | External Deps |
|-----------|----------|---------------|
| **Native** | Simple agents, cost optimization | None |
| **LangChain** | Chains, tools, RAG, prompt templates | `langchain`, `langchain-anthropic` |
| **LangGraph** | Stateful multi-agent workflows | `langgraph`, `langchain-anthropic` |
| **AutoGen** | Conversational multi-agent teams | `pyautogen` |
| **Haystack** | Document QA, RAG, NLP pipelines | `haystack-ai` |

The factory auto-detects installed frameworks and recommends
the best one for a given use case. Native is always available
as a zero-dependency fallback.

---

## Integration Points

The Agent Factory integrates with these Attune subsystems:

- **ModelRouter** (`attune.routing`) — Resolves model tier
  (`cheap`/`capable`/`premium`) to specific model IDs based
  on the provider and task type
- **CircuitBreaker** (`attune.resilience`) — Provides
  circuit breaker state management for `ResilientAgent`
- **MemoryGraph** (`attune.memory`) — Stores and queries
  cross-agent findings for `MemoryAwareAgent`
- **EmpathyLLM** — Powers the native adapter with built-in
  cost tracking and pattern learning

---

## Agent Roles

The factory provides 15 predefined roles organized into
three categories:

**Core:** Coordinator, Researcher, Writer, Reviewer, Editor,
Executor

**Specialized:** Debugger, Security, Architect, Tester,
Documenter

**RAG:** Retriever, Summarizer, Answerer

Plus `CUSTOM` for any other role.

---

## Resilience Patterns

When `resilience_enabled=True`, agents are wrapped with four
production-ready patterns:

1. **Circuit Breaker** — After N consecutive failures, the
   circuit opens and fast-fails for a cooldown period. Prevents
   cascading failures.
2. **Retry with Backoff** — Exponential backoff with jitter.
   Timeouts are not retried by default.
3. **Timeout** — Prevents hanging operations. Applied to both
   `invoke()` and `stream()`.
4. **Fallback** — Optional. Returns a configurable fallback
   response instead of raising.

---

## Memory Graph Integration

When `memory_graph_enabled=True`, agents gain cross-agent
learning:

**Before invocation:** Queries the memory graph for similar
past findings and injects them into the context dict under
`context["similar_findings"]`.

**After invocation:** Scans the agent's output for finding
patterns (bugs, vulnerabilities, performance issues) and
stores them in the graph with the agent's name as source.

This allows a debugger agent to benefit from a security
agent's past findings, and vice versa.

---

## Decorators

Six reusable decorators for agent operations:

| Decorator | Purpose |
|-----------|---------|
| `@safe_agent_operation` | Logging, timing, error wrapping, audit trail |
| `@retry_on_failure` | Exponential backoff retry |
| `@log_performance` | Warn on slow operations |
| `@validate_input` | Require dict fields |
| `@with_cost_tracking` | Track token usage and costs |
| `@graceful_degradation` | Return fallback instead of raising |

All decorators are designed for async methods.

---

## Testing

Tests are in `tests/agent_factory/` and cover:

- Core factory creation and framework switching
- All enum values and config dataclasses
- Framework detection and recommendation
- Resilience wrapper (circuit breaker, retry, timeout)
- Memory integration (query, store, graph stats)
- Individual adapter behavior
