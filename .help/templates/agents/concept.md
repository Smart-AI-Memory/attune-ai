---
type: concept
feature: agents
depth: concept
generated_at: 2026-05-04T02:32:50.053871+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Agents

Agents are AI entities that wrap different LLM frameworks into a unified interface for building conversational workflows and automated processes.

## What agents provide

The agent system solves the framework fragmentation problem in AI development. Instead of learning separate APIs for AutoGen, Haystack, and LangChain, you work with a common agent interface that handles:

- **Unified invocation** — Call `agent.invoke()` regardless of whether the underlying implementation uses AutoGen's AssistantAgent, Haystack's Pipeline, or LangChain's chains
- **Consistent streaming** — Get real-time responses through `agent.stream()` with the same async pattern across all frameworks
- **Framework adaptation** — Adapters translate between Attune's agent config and each framework's native configuration format
- **Recovery and persistence** — State management and error recovery that works across framework boundaries

## Core components

**Agent wrappers** encapsulate framework-specific implementations:
- `AutoGenAgent` wraps AutoGen's AssistantAgent or UserProxyAgent for multi-agent conversations
- `HaystackAgent` wraps Haystack Pipelines for document processing and RAG workflows
- `LangChainAgent` wraps LangChain chains for sequential processing pipelines

**Workflow orchestrators** coordinate multiple agents:
- `AutoGenWorkflow` uses AutoGen's GroupChat for multi-agent discussions
- `HaystackWorkflow` runs Haystack Pipelines with multiple processing stages
- `LangChainWorkflow` chains multiple agents through SequentialChain or custom routing

**Framework adapters** provide factory methods for creating agents and workflows:
- `AutoGenAdapter` creates AutoGen-based agents with Microsoft's conversation patterns
- `HaystackAdapter` creates Haystack-based agents with deepset's pipeline architecture
- `LangChainAdapter` creates LangChain-based agents with Langchain's ecosystem

## How agent creation works

You don't instantiate agents directly. Instead, you use adapter factory methods that handle framework-specific setup:

```python
# Get the adapter for your preferred framework
adapter = get_autogen_adapter(provider='anthropic')

# Create an agent with unified configuration
agent = adapter.create_agent(AgentConfig(
    name="code_reviewer",
    role=AgentRole.ASSISTANT,
    capability=AgentCapability.CODE_ANALYSIS
))
```

The adapter translates your `AgentConfig` into whatever the underlying framework expects—AutoGen's agent configuration, Haystack's component setup, or LangChain's chain definition.

## State persistence and recovery

Release agents include specialized state management through `AgentStateStore` and `AgentRecoveryManager`. These components track agent execution across runs and recover from failures without losing conversation context or progress through multi-step workflows.

The `AgentExecutionRecord` captures each agent operation for replay, while `AgentStateRecord` maintains the agent's working memory between invocations.
