---
name: agents
source: content/features/agents.md
tags:
- agents
- ai
type: faq
---

# Agents FAQ

## What is the Agent Factory?

`AgentFactory` is one interface to create, run, and
orchestrate AI agents across frameworks (native, LangChain,
LangGraph, AutoGen, Haystack) without rewriting code when you switch.

## Which framework runs by default?

`native`. Pass `AgentFactory(framework="langgraph")` (or a
`Framework` value) for another; check availability with
`list_frameworks(installed_only=True)`.

## Are the calls async?

Yes — `BaseAgent.invoke` / `stream` and `BaseWorkflow.run` /
`stream` are coroutines. The factory's `create_*` methods are sync.

## How do I coordinate multiple agents?

Build them, then `create_workflow(name, agents, mode=...)` and
`await workflow.run(...)` — or use a ready-made pipeline like
`create_research_pipeline(topic)`.

## Is this the same as the release-prep agents?

No. This is the framework-agnostic Factory. The
release-readiness agent team is documented under release-prep.
