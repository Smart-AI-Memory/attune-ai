---
type: faq
name: agents-faq
feature: agents
depth: faq
status: manual
---

# Agents FAQ

## What is the Agent Factory?

`AgentFactory` is one interface to create, run, and orchestrate AI
agents across frameworks — native (the default), LangChain, LangGraph,
AutoGen, and Haystack — without rewriting code when you switch. Its
`create_agent` / `create_workflow` methods return `BaseAgent` /
`BaseWorkflow` objects with a uniform interface.

## How do I create and run an agent?

Build it with the factory, then `await` its async `invoke`:

```python
import asyncio

from attune.agent_factory import AgentFactory


async def main() -> None:
    factory = AgentFactory()                  # native framework
    agent = factory.create_agent(name="helper")
    print(await agent.invoke("Hello"))


asyncio.run(main())
```

There is no `attune agent` CLI command and no MCP tool — use the
Python API or the `/agent` skill.

## Are the calls async?

Yes — `BaseAgent.invoke` / `stream` and `BaseWorkflow.run` / `stream`
are coroutines (`await` them). The factory's `create_*` builders are
synchronous.

## Which frameworks are supported?

`native` (default, no extra deps), `langchain`, `langgraph`, `autogen`,
`haystack`. The non-native ones are optional dependencies loaded
lazily — `AgentFactory.list_frameworks(installed_only=True)` shows
what's installed, and `recommend_framework(use_case)` suggests one.
Switch with `switch_framework(...)`.

## How do I coordinate multiple agents?

Create the agents, then `create_workflow(name, agents, mode=...)` and
`await workflow.run(...)`. For ready-made teams use
`create_code_review_pipeline()` or
`create_research_pipeline(topic)`. Role-preset shortcuts
(`create_researcher`, `create_writer`, `create_reviewer`,
`create_coordinator`, `create_debugger`) return `BaseAgent`s.

## Is this the same as the release-prep agents?

No. This feature is the framework-agnostic **Agent Factory**
(`src/attune/agent_factory/`). The release-readiness agent team
(`src/attune/agents/release/`) is documented under **release-prep**,
and its state/recovery store (`src/attune/agents/state/`) is that
team's persistence layer.

## What's the public API surface?

`AgentFactory`, `Framework`, `BaseAdapter`, `BaseAgent`, `AgentConfig`,
`WorkflowConfig`, `AgentRole`, and `AgentCapability` — all from
`attune.agent_factory`. Framework-specific adapter/agent classes are
internal.

**Tags:** `agents`, `ai`
