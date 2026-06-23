# Agents

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

<!-- attune-generated: source_hash=9f8352e822bbdc7e4000d3afae65bd38c29cb5a219fd6aded8e91de285f5a54a feature=agents kind=how-to generated_at=2026-06-23 -->
