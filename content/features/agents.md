---
feature: agents
summary: Universal Agent Factory — create, run, and orchestrate AI agents across frameworks
tags: [agents, ai]
source_globs:
  - src/attune/agent_factory/**
nav:
  help: agents
  mkdocs:
    how-to: how-to/agents
    architecture: architecture/agents
    reference: reference/agents
---

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

## Quickstart

Create an agent and invoke it. `invoke` is a coroutine, so drive it
with `asyncio.run`:

```python
import asyncio

from attune.agent_factory import AgentFactory


async def main() -> None:
    factory = AgentFactory()  # native framework by default
    agent = factory.create_agent(
        name="helper",
        description="Answers questions about the codebase.",
    )
    result = await agent.invoke("What does the release-prep gate check?")
    print(result)


asyncio.run(main())
```

`AgentFactory()` uses the `native` framework; pass
`AgentFactory(framework="langgraph")` (or a `Framework` value) to use
another backend.

## Tasks

### Build and run a single agent

**Goal:** create one agent and get a result.

**Steps:**

```python
import asyncio

from attune.agent_factory import AgentFactory, AgentRole


async def main() -> None:
    factory = AgentFactory()
    reviewer = factory.create_agent(
        name="reviewer",
        role=AgentRole.REVIEWER,
        model_tier="capable",
    )
    result = await reviewer.invoke({"code": "def f(): return 1/0"})
    print(result)


asyncio.run(main())
```

**Verify:** `invoke` is a coroutine — `await` it; it returns a `dict`.
`role` accepts an `AgentRole` (or its string). `model_tier` is
`"cheap"` / `"capable"` / `"premium"`.

### Orchestrate a multi-agent workflow

**Goal:** coordinate several agents and run them.

**Steps:**

```python
import asyncio

from attune.agent_factory import AgentFactory


async def main() -> None:
    factory = AgentFactory()
    researcher = factory.create_researcher()
    writer = factory.create_writer()
    workflow = factory.create_workflow(
        name="research-and-write",
        agents=[researcher, writer],
        mode="sequential",
    )
    result = await workflow.run("Summarize attune's memory tiers.")
    print(result)


asyncio.run(main())
```

**Verify:** `run` is a coroutine — `await` it; it returns a `dict`.
The role-preset shortcuts (`create_researcher`, `create_writer`, …)
return `BaseAgent`s. For ready-made pipelines, use
`create_code_review_pipeline()` or `create_research_pipeline(topic)`.

### Pick or switch the framework

**Goal:** choose a backend and see what's installed.

**Steps:**

```python
from attune.agent_factory import AgentFactory, Framework

print(AgentFactory.list_frameworks(installed_only=True))
print(AgentFactory.recommend_framework("general"))   # -> Framework.NATIVE

factory = AgentFactory(framework=Framework.LANGGRAPH)
factory.switch_framework("native")
```

**Verify:** `list_frameworks` and `recommend_framework` are callable on
the class. `Framework` values are `native`, `langchain`, `langgraph`,
`autogen`, `haystack`. Non-native frameworks are optional deps —
`list_frameworks(installed_only=True)` shows only those installed.

## Reference

The public surface is re-exported from `attune.agent_factory`:
`AgentFactory`, `Framework`, `BaseAdapter`, `BaseAgent`, `AgentConfig`,
`WorkflowConfig`, `AgentRole`, `AgentCapability`.

### `AgentFactory` — `attune.agent_factory`

| Member | Purpose |
|--------|---------|
| `AgentFactory(framework=None, provider="anthropic", api_key=None, use_case="general")` | Construct the factory; `framework` defaults to `native`. |
| `create_agent(name, role=AgentRole.CUSTOM, model_tier="capable", ...) -> BaseAgent` | Build an agent. |
| `create_workflow(name, agents, mode="sequential", ...) -> BaseWorkflow` | Build a coordinating workflow. |
| `create_tool(name, description, func, args_schema=None)` | Wrap a callable as a tool. |
| `create_coordinator / create_researcher / create_writer / create_reviewer / create_debugger(...) -> BaseAgent` | Role-preset agents. |
| `create_code_review_pipeline() -> BaseWorkflow` · `create_research_pipeline(topic="", include_reviewer=True) -> BaseWorkflow` | Ready-made pipelines. |
| `get_agent(name) -> BaseAgent \| None` · `list_agents() -> list[str]` | Look up created agents. |
| `list_frameworks(installed_only=True) -> list[dict]` · `recommend_framework(use_case="general") -> Framework` · `switch_framework(framework) -> None` | Framework management. |

### `BaseAgent` / `BaseWorkflow`

`BaseAgent` is re-exported from `attune.agent_factory`; `BaseWorkflow`
lives in `attune.agent_factory.base`. You rarely import either directly
— the factory's `create_agent` / `create_workflow` return them.

| Member | Purpose |
|--------|---------|
| `BaseAgent.invoke(input_data, context=None) -> dict` | **Async.** Run the agent once. |
| `BaseAgent.stream(input_data, context=None)` | **Async** generator of incremental output. |
| `BaseAgent.add_tool(tool)` · `get_conversation_history()` · `clear_history()` | Tool + history management. |
| `BaseWorkflow.run(input_data, initial_state=None) -> dict` | **Async.** Run the multi-agent workflow. |
| `BaseWorkflow.stream(input_data, initial_state=None)` | **Async** generator. |
| `BaseWorkflow.get_agent(name)` · `get_state()` | Inspect the workflow. |

### Taxonomy

| Type | Values / fields |
|------|-----------------|
| `Framework` | `native`, `langchain`, `langgraph`, `autogen`, `haystack`. |
| `AgentRole` | coordinator, researcher, writer, reviewer, editor, executor, debugger, security, architect, tester, documenter, retriever, summarizer, answerer, custom. |
| `AgentCapability` | code_execution, tool_use, web_search, file_access, memory, retrieval, vision, function_calling. |
| `AgentConfig` | name, role, description, model_tier, model_override, capabilities, tools, system_prompt, temperature, max_tokens, … |
| `WorkflowConfig` | name, description, mode, max_iterations, timeout_seconds, state_schema, checkpointing, retry_on_error, max_retries, framework_options. |

### `BaseAdapter` — `attune.agent_factory`

| Member | Purpose |
|--------|---------|
| `create_agent(config) -> BaseAgent` · `create_workflow(config, agents) -> BaseWorkflow` · `create_tool(...)` | Framework-specific construction. |
| `get_model_for_tier(tier, provider="anthropic") -> str` · `is_available() -> bool` | Model mapping + availability. |

### Entry points

| Surface | Invocation |
|---------|------------|
| Python | `AgentFactory(...).create_agent(...)`, then `await agent.invoke(...)`. |
| Skill | `/agent` in a Claude Code conversation — create/manage agents and teams. |

No `attune agent` CLI command and no MCP tool exist.

## Comparison

The Agent Factory is the **build-your-own-agent** surface, distinct
from the packaged workflows and from wizards:

| | agents (Factory) | workflows | wizards |
|--|------------------|-----------|---------|
| What | Create/run/orchestrate custom agents across frameworks | Pre-built analysis pipelines (security, review, …) | Interactive multi-step guided flows |
| Entry | `AgentFactory(...)` + `await invoke/run` | `attune workflow run <slug>` | `/wizard` skill + `await run()` |
| Frameworks | native / langchain / langgraph / autogen / haystack | n/a | n/a |

Reach for the **Factory** when you need bespoke agents or want
framework portability; reach for **workflows** when a packaged pipeline
already does the job; reach for **wizards** for an interactive,
user-in-the-loop task.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'BaseAgent.invoke' was never awaited` | `invoke` / `run` called without `await` | They are coroutines — `await` them or use `asyncio.run` | high |
| Constructing a non-native factory raises / `is_available()` is `False` | The framework's optional dependency isn't installed | Install the framework extra, or use `native`; check `list_frameworks(installed_only=True)` | high |
| `recommend_framework` / `list_frameworks` "needs an instance" error | Called as if instance-only | They are callable on the class; call `AgentFactory.list_frameworks()` | low |
| `get_agent(name)` returns `None` | No agent with that name was created on this factory | Check `list_agents()`; names are per-factory | low |
| A tool isn't used by the agent | Tool not added / wrong schema | Build it with `create_tool(...)` and pass it via `tools=` or `add_tool(...)` | medium |

### Risk areas

- **The run methods are async.** `invoke`, `run`, and `stream` are
  coroutines — forgetting to `await` is the most common mistake.
- **Non-native frameworks are optional.** They load lazily; check
  `is_available()` / `list_frameworks(installed_only=True)` before
  selecting one.
- **Scope.** This feature is the Factory; the release agent team and
  its state store live under release-prep, not here.

### Diagnosis order

1. Confirm you are awaiting: `await agent.invoke(...)` /
   `await workflow.run(...)`.
2. Confirm the framework is installed: `AgentFactory.list_frameworks(
   installed_only=True)`.
3. For a missing agent, check `list_agents()`.
4. For tool issues, confirm the tool was built with `create_tool` and
   attached.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What is the Agent Factory?
  **A:** `AgentFactory` is one interface to create, run, and
  orchestrate AI agents across frameworks (native, LangChain,
  LangGraph, AutoGen, Haystack) without rewriting code when you switch.
- **Q:** Which framework runs by default?
  **A:** `native`. Pass `AgentFactory(framework="langgraph")` (or a
  `Framework` value) for another; check availability with
  `list_frameworks(installed_only=True)`.
- **Q:** Are the calls async?
  **A:** Yes — `BaseAgent.invoke` / `stream` and `BaseWorkflow.run` /
  `stream` are coroutines. The factory's `create_*` methods are sync.
- **Q:** How do I coordinate multiple agents?
  **A:** Build them, then `create_workflow(name, agents, mode=...)` and
  `await workflow.run(...)` — or use a ready-made pipeline like
  `create_research_pipeline(topic)`.
- **Q:** Is this the same as the release-prep agents?
  **A:** No. This is the framework-agnostic Factory. The
  release-readiness agent team is documented under release-prep.

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

## Design & extension

### Design decisions

- **One factory over many frameworks.** `AgentFactory` hides
  framework differences behind `create_agent` / `create_workflow`, so
  switching backends (`switch_framework`) doesn't rewrite caller code.
- **Uniform agent/workflow interface.** Every adapter produces objects
  implementing `BaseAgent` / `BaseWorkflow`, so `invoke` / `run` /
  `stream` behave the same regardless of framework.
- **Optional frameworks, lazy load.** Non-native frameworks are
  optional dependencies imported on demand; `is_available()` /
  `list_frameworks` keep the factory usable with none of them
  installed.
- **Config as data.** `AgentConfig` / `WorkflowConfig` capture
  settings; the `create_*` kwargs populate them, and adapters consume
  them.

### Extension points

- **Add a framework:** implement a `BaseAdapter`
  (`create_agent` / `create_workflow` / `create_tool` /
  `get_model_for_tier` / `is_available`).
- **Add a tool:** `create_tool(name, description, func)` and attach via
  `tools=` or `add_tool`.
- **Tune the agent:** `create_agent` exposes capabilities, memory,
  resilience (circuit breaker / retry / timeout), and model tier.
- **Compose pipelines:** combine agents with `create_workflow`, or
  start from `create_code_review_pipeline` /
  `create_research_pipeline`.
