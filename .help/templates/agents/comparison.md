---
type: comparison
name: agents-comparison
feature: agents
depth: comparison
generated_at: 2026-06-04T23:45:26.769779+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Comparison: Agent framework adapters

## Overview

Attune's agent factory supports four external frameworks — AutoGen, Haystack, LangChain, and LangGraph — plus a lightweight native path that wraps an existing wizard directly. Each option exposes the same `BaseAgent` interface, but the underlying frameworks have meaningfully different strengths. This page helps you pick the right adapter for your use case.

## Feature comparison

| Capability | AutoGen (`AutoGenAdapter`) | Haystack (`HaystackAdapter`) | LangChain (`LangChainAdapter`) | LangGraph (`LangGraphAgent`) | Native (`wrap_wizard`) |
|---|---|---|---|---|---|
| **Agent class** | `AutoGenAgent` | `HaystackAgent` | `LangChainAgent` | `LangGraphAgent` | `WizardAgent` |
| **Workflow class** | `AutoGenWorkflow` (GroupChat) | `HaystackWorkflow` (Pipeline) | `LangChainWorkflow` (SequentialChain / custom routing) | — | — |
| **Multi-agent coordination** | ✅ GroupChat built in | ❌ Single pipeline | ⚠️ Custom routing only | ✅ Node/runnable graph | ❌ Single agent |
| **Document store support** | ❌ | ✅ `create_document_store()` | ❌ | ❌ | ❌ |
| **Streaming** | ✅ `stream()` | ✅ `stream()` | ✅ `stream()` | ✅ `stream()` | ❌ |
| **Tool creation** | ✅ `create_tool()` returns `dict` | ✅ `create_tool()` returns `dict` | ✅ `create_tool()` returns `Any` | — | — |
| **Lazy import** | ✅ `get_autogen_adapter()` | ✅ `get_haystack_adapter()` | ✅ `get_langchain_adapter()` | ✅ `get_langgraph_adapter()` | — |
| **Wraps existing object** | AssistantAgent or UserProxyAgent | Pipeline or Component | Chain or AgentExecutor | Node or Runnable | Wizard directly via `wrap_wizard()` |
| **Extra setup** | `autogen` package required | `haystack-ai` package required | `langchain` package required | `langgraph` package required | None — uses Attune internals |
| **Best for** | Multi-agent group conversations | RAG / document-retrieval pipelines | Sequential chains, broad ecosystem | Stateful graph workflows | Quickly promoting a wizard to an agent |

## Tradeoffs in detail

### AutoGen — best for group conversations

`AutoGenAdapter` wraps Microsoft AutoGen's GroupChat, making it the only adapter with native multi-agent coordination. Use it when you need several agents to deliberate, vote, or hand off tasks to each other. The tradeoff is that AutoGen has no document store support and its tool schema returns a plain `dict`, so you own the serialization.

### Haystack — best for document retrieval

`HaystackAdapter` is the only adapter that exposes `create_document_store()`, making it the clear choice for RAG pipelines and any workflow that needs to index or query documents. It does not support multi-agent coordination; `HaystackWorkflow` runs a single Pipeline end to end.

### LangChain — best for ecosystem breadth

`LangChainAdapter` supports `SequentialChain` and custom routing, giving you access to LangChain's large ecosystem of integrations. `create_tool()` returns `Any` rather than a typed `dict`, which gives you flexibility but less predictability than the AutoGen or Haystack equivalents. Choose LangChain when an existing LangChain chain or `AgentExecutor` is already part of your stack.

### LangGraph — best for stateful graph workflows

`LangGraphAgent` wraps a node or runnable inside a graph, supporting stateful multi-step flows without the GroupChat model. Unlike the other adapters, LangGraph does not have a corresponding workflow class or `create_tool()` method in the current API, so it works best as a single stateful node rather than a coordinating layer.

### `wrap_wizard` — best for zero-dependency promotion

`wrap_wizard(wizard, name, model_tier)` converts an existing Attune wizard into a `WizardAgent` without importing any external framework. It does not support streaming, tools, or multi-agent workflows. It is the lowest-friction option when you already have a working wizard and want it to participate in an agent pipeline.

## Use X when...

| You need… | Use this |
|---|---|
| Multiple agents debating or handing off tasks | `AutoGenAdapter` → `AutoGenWorkflow` |
| RAG or document-retrieval pipelines | `HaystackAdapter` → `HaystackWorkflow` with `create_document_store()` |
| An existing LangChain chain or broad ecosystem integrations | `LangChainAdapter` → `LangChainWorkflow` |
| A stateful graph where each node holds its own state | `LangGraphAgent` via `get_langgraph_adapter()` |
| Minimal setup, no external packages, existing wizard in hand | `wrap_wizard()` → `WizardAgent` |
| Release pipeline automation (`ReleaseAgent`, `ReleasePrepTeam`) | Whichever adapter matches your existing stack; the agent classes are framework-agnostic |

If you are unsure, **AutoGen** is the strongest default for multi-agent scenarios and **Haystack** is the strongest default for document-heavy workloads. For everything else with an existing LangChain investment, stay with **LangChain**.

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

**Tags:** `agents`, `ai`, `release`
