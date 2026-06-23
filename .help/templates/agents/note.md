---
type: note
name: agents-note
feature: agents
depth: note
generated_at: 2026-06-23T22:44:18.994422+00:00
source_hash: 9f8352e822bbdc7e4000d3afae65bd38c29cb5a219fd6aded8e91de285f5a54a
status: generated
---

# Universal Agent Factory — create, run, and orchestrate AI agents across frameworks

## Overview

The agents feature is Attune's **Universal Agent Factory** — one
interface for creating, running, and orchestrating AI agents, backed by
your choice of framework (native, LangChain, LangGraph, AutoGen, or
Haystack) without rewriting code when you switch frameworks. The entry
point is **`AgentFactory`**: it picks a framework adapter, and its
`create_agent` / `create_workflow` methods return `BaseAgent` /
`BaseWorkflow` objects with a uniform interface.

The agent and workflow run methods (`invoke`, `run`, `stream`) are
**async** — `await` them.

You reach it two ways:

- the Python API — `from attune.agent_factory import AgentFactory,
  Framework` (the primary surface, documented throughout);
- the **`/agent`** skill, inside a Claude Code conversation — create
  and manage custom agents and teams.

There is no `attune agent` CLI command and no MCP tool.

> **Scope.** This feature is the framework-agnostic Agent Factory
> (`src/attune/agent_factory/`). The release-readiness agent **team**
> (`src/attune/agents/release/`) is documented under **release-prep**,
> and the agent state/recovery store (`src/attune/agents/state/`) is
> that team's persistence layer — not part of the Factory's public
> surface.

## Concepts

### One factory, many frameworks

`AgentFactory(framework=None, provider="anthropic", api_key=None,
use_case="general")` is the entry point. `framework` is a `Framework`
enum (or its string) — `native` (the default when unset), `langchain`,
`langgraph`, `autogen`, or `haystack`. Each non-native framework is an
optional dependency loaded lazily; `AgentFactory.list_frameworks(
installed_only=True)` reports what's available and
`AgentFactory.recommend_framework(use_case)` suggests one. Call
`switch_framework(framework)` to move an existing factory to another
backend.

### Create agents and workflows

| Method | Returns | What it does |
|--------|---------|--------------|
| `create_agent(name, role=AgentRole.CUSTOM, model_tier="capable", ...)` | `BaseAgent` | Build one agent. Many options — `capabilities`, `tools`, `system_prompt`, `temperature`, `memory_enabled`, `resilience_enabled`, … |
| `create_workflow(name, agents, mode="sequential", ...)` | `BaseWorkflow` | Coordinate several agents (sequential or other modes). |
| `create_tool(name, description, func, args_schema=None)` | tool | Wrap a Python callable as an agent tool. |
| `create_coordinator` / `create_researcher` / `create_writer` / `create_reviewer` / `create_debugger` | `BaseAgent` | Role-preset agent shortcuts. |
| `create_code_review_pipeline()` / `create_research_pipeline(topic, include_reviewer=True)` | `BaseWorkflow` | Ready-made multi-agent pipelines. |
| `get_agent(name)` / `list_agents()` | `BaseAgent \| None` / `list[str]` | Look up agents the factory has created. |

### Agents and workflows run async

A `BaseAgent` exposes async `invoke(input_data, context=None) -> dict`
and an async `stream(...)` generator, plus `add_tool`,
`get_conversation_history`, and `clear_history`. A `BaseWorkflow`
exposes async `run(input_data, initial_state=None) -> dict` and async
`stream(...)`, plus `get_agent` and `get_state`. Always `await` the
run methods.

### Config and taxonomy

`AgentConfig` and `WorkflowConfig` capture an agent's / workflow's
settings (the `create_*` kwargs map onto them). `AgentRole` enumerates
roles (coordinator, researcher, writer, reviewer, editor, executor,
debugger, security, architect, tester, documenter, retriever,
summarizer, answerer, custom) and `AgentCapability` enumerates
capabilities (code_execution, tool_use, web_search, file_access,
memory, retrieval, vision, function_calling).

### Adapters implement one protocol

Each framework is wrapped by a `BaseAdapter` with a uniform surface —
`create_agent(config)`, `create_workflow(config, agents)`,
`create_tool(...)`, `get_model_for_tier(tier, provider)`, and
`is_available()`. The factory selects the adapter; you normally don't
touch adapters directly.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `AgentFactory`, `Framework`, `BaseAdapter`, `BaseAgent`,
  `AgentConfig`, `WorkflowConfig`, `AgentRole`, and `AgentCapability`
  from `attune.agent_factory`. Framework-specific adapter/agent classes
  are internal.
- **`await` the run methods.** Only `invoke` / `run` / `stream` are
  async; the `create_*` builders are sync.
- **Start native.** The `native` framework needs no extra deps; reach
  for LangChain/LangGraph/AutoGen/Haystack when you need their
  features.
- **Use role presets and pipelines.** `create_researcher()` /
  `create_research_pipeline()` are faster than wiring configs by hand.
