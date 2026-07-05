---
description: How to create agents and workflows across multiple frameworks (LangChain, LangGraph, AutoGen, Haystack, or native) through a single unified factory.
---

# Agent Factory

`attune.agent_factory` provides a **universal factory** for creating agents
and workflows across multiple frameworks through one common interface.
Pick your framework once, and the same `create_agent` / `create_workflow`
calls work whether the underlying agents are LangChain chains, LangGraph
state machines, AutoGen conversational agents, Haystack pipelines, or
Attune's native adapter.

The factory layers Attune-side features — model-tier routing,
cost-tracking flags, optional resilience wrapping — on top of the
chosen framework.

## Supported frameworks

| Framework value          | Adapter                                                   | Install                                  |
|--------------------------|-----------------------------------------------------------|------------------------------------------|
| `Framework.NATIVE`       | `NativeAdapter` (built-in)                                | included                                 |
| `Framework.LANGCHAIN`    | `LangChainAdapter` (lazy)                                 | `pip install langchain langchain-anthropic` |
| `Framework.LANGGRAPH`    | `LangGraphAdapter` (lazy)                                 | `pip install langgraph langchain-anthropic` |
| `Framework.AUTOGEN`      | `AutoGenAdapter` (lazy)                                   | `pip install pyautogen`                  |
| `Framework.HAYSTACK`     | `HaystackAdapter` (lazy)                                  | `pip install haystack-ai`                |

Framework adapters are imported lazily — you only pay the import cost for
the one you use. `Framework.NATIVE` is always available.

If a framework isn't selected explicitly, `AgentFactory` picks one based
on what's installed and the `use_case` argument, falling back to
`Framework.NATIVE`.

## Quick start

```python
from attune.agent_factory import AgentFactory, Framework

# Create factory with your preferred framework
factory = AgentFactory(framework=Framework.LANGGRAPH)

# Create agents
researcher = factory.create_agent(
    name="researcher",
    role="researcher",
    model_tier="capable",
)

writer = factory.create_agent(
    name="writer",
    role="writer",
    model_tier="premium",
)

# Create workflow
pipeline = factory.create_workflow(
    name="research_pipeline",
    agents=[researcher, writer],
    mode="sequential",
)

# Run (workflows are async)
result = await pipeline.run("Research AI trends in 2025")
print(result["output"])
```

`framework=` can be a `Framework` enum value or a string like
`"langgraph"` / `"langchain"` / `"autogen"` / `"haystack"` / `"native"`.

## The `AgentFactory` class

### Constructor

```python
AgentFactory(
    framework: Framework | str | None = None,
    provider: str = "anthropic",
    api_key: str | None = None,
    use_case: str = "general",
)
```

- `framework` — explicit framework choice. If `None`, auto-selected from
  installed packages and `use_case` (falls back to `Framework.NATIVE`).
- `provider` — LLM provider name. Defaults to `"anthropic"`.
- `api_key` — API key string. If not provided, falls back to the
  `ANTHROPIC_API_KEY` env var (or `OPENAI_API_KEY` when `provider="openai"`).
- `use_case` — recommendation hint when `framework` is `None`. Valid values:
  `"general"`, `"rag"`, `"multi_agent"`, `"code_analysis"`, `"workflow"`,
  `"conversational"`.

### `create_agent(...) -> BaseAgent`

Creates an agent through the active adapter. Frequently used arguments:

| Argument           | Type                            | Default              | Notes                                                  |
|--------------------|---------------------------------|----------------------|--------------------------------------------------------|
| `name`             | `str`                           | required             | Unique agent name (tracked for `get_agent` / `list_agents`) |
| `role`             | `AgentRole` or `str`            | `AgentRole.CUSTOM`   | One of the values in `AgentRole` (see below)           |
| `description`      | `str`                           | `""`                 |                                                        |
| `model_tier`       | `str`                           | `"capable"`          | `"cheap"`, `"capable"`, `"premium"`                    |
| `model_override`   | `str | None`                    | `None`               | Specific model ID, bypassing tier routing              |
| `capabilities`     | `list[AgentCapability] | None`  | `None`               | See `AgentCapability` below                            |
| `tools`            | `list[Any] | None`              | `None`               | Framework-native tool objects (or what `create_tool` returns) |
| `system_prompt`    | `str | None`                    | `None`               | Custom system prompt                                   |
| `temperature`      | `float`                         | `0.7`                |                                                        |
| `max_tokens`       | `int`                           | `4096`               |                                                        |
| `empathy_level`    | `int`                           | `4`                  | 1–5; used by Attune-side features                      |
| `use_patterns`     | `bool`                          | `True`               | Load learned patterns (config flag)                    |
| `track_costs`      | `bool`                          | `True`               | Track API costs (config flag)                          |
| `memory_enabled`   | `bool`                          | `True`               | Conversation memory                                    |
| `memory_type`      | `str`                           | `"conversation"`     | `"conversation"`, `"summary"`, `"vector"`              |
| `resilience_enabled` | `bool`                        | `False`              | Wraps result in a `ResilientAgent` (see below)         |

Returns an object that implements `BaseAgent` — i.e. has
`async def invoke(input_data, context=None) -> dict` and
`async def stream(input_data, context=None)`.

### `create_workflow(name, agents, mode="sequential", ...) -> BaseWorkflow`

Creates a workflow from a list of agents.

- `mode` — `"sequential"`, `"parallel"`, `"graph"`, or `"conversation"`.
  Which modes are actually supported depends on the active adapter
  (e.g. `"conversation"` is most natural in AutoGen, `"graph"` in
  LangGraph).
- Other arguments: `max_iterations=10`, `timeout_seconds=300`,
  `state_schema=None`, `checkpointing=True`, `retry_on_error=True`,
  `max_retries=3`, `framework_options=None`.

Returns an object implementing `BaseWorkflow` —
`async def run(input_data, initial_state=None) -> dict` and
`async def stream(input_data, initial_state=None)`.

### `create_tool(name, description, func, args_schema=None) -> Any`

Creates a tool in the active adapter's native format. The exact return
type is adapter-specific; the default `BaseAdapter` implementation
returns a `dict` and individual adapters may override.

### `get_agent(name) -> BaseAgent | None` / `list_agents() -> list[str]`

Look up an agent (or list names of agents) previously created on this
factory instance. Agents are tracked by name inside the factory.

### `switch_framework(framework)`

Switches the factory to a new framework. **Clears the agent registry** —
existing agents created under the previous framework are not migrated.

### `list_frameworks(installed_only=True)` (classmethod)

Returns a list of dicts describing frameworks. Each dict has
`framework`, `installed`, plus the fields from
`framework.get_framework_info` (`name`, `description`, `best_for`,
`install_command`, `docs_url`). When `installed_only=False`, all five
supported frameworks are returned regardless of installation status.

### `recommend_framework(use_case="general")` (classmethod)

Returns a `Framework` enum value: the best-installed framework for the
given use case, or `Framework.NATIVE` if no preferred option is
installed.

### Convenience constructors

Thin wrappers around `create_agent` with role + sensible tier defaults:

- `create_researcher(name="researcher", model_tier="capable", **kwargs)`
- `create_writer(name="writer", model_tier="premium", **kwargs)`
- `create_reviewer(name="reviewer", model_tier="capable", **kwargs)`
- `create_debugger(name="debugger", model_tier="capable", **kwargs)` —
  also enables `AgentCapability.CODE_EXECUTION`
- `create_coordinator(name="coordinator", model_tier="premium", **kwargs)`

### Pipeline helpers

- `create_research_pipeline(topic="", include_reviewer=True)` —
  research → write → (review) sequential pipeline.
- `create_code_review_pipeline()` — security → debug → review sequential
  pipeline.

## Enums

### `AgentRole`

Built-in roles (string values shown):

```
COORDINATOR    "coordinator"
RESEARCHER     "researcher"
WRITER         "writer"
REVIEWER       "reviewer"
EDITOR         "editor"
EXECUTOR       "executor"
DEBUGGER       "debugger"
SECURITY       "security"
ARCHITECT      "architect"
TESTER         "tester"
DOCUMENTER     "documenter"
RETRIEVER      "retriever"
SUMMARIZER     "summarizer"
ANSWERER       "answerer"
CUSTOM         "custom"
```

You can pass either the enum value (`role=AgentRole.RESEARCHER`) or the
lowercase string (`role="researcher"`).

### `AgentCapability`

```
CODE_EXECUTION     "code_execution"
TOOL_USE           "tool_use"
WEB_SEARCH         "web_search"
FILE_ACCESS        "file_access"
MEMORY             "memory"
RETRIEVAL          "retrieval"
VISION             "vision"
FUNCTION_CALLING   "function_calling"
```

## Model tiers

`model_tier` is resolved by the adapter's `get_model_for_tier`, which
delegates to `attune.routing.ModelRouter` when available. The hard-coded
fallback for `provider="anthropic"` (used when the router is not
importable) maps:

| Tier      | Fallback model (Anthropic) |
|-----------|----------------------------|
| `cheap`   | `claude-haiku-4-5-20251001` |
| `capable` | `claude-sonnet-5`         |
| `premium` | `claude-opus-4-8`           |

These IDs are fallback constants — the live mapping is whatever
`ModelRouter` resolves at runtime.

## Optional wrappers

When you set the right flag on `create_agent`, the returned agent is
wrapped with:

### `ResilientAgent` — Circuit breaker / retry / timeout

Enabled by `resilience_enabled=True`. Imported lazily from
`attune.agent_factory.resilient`; if the import fails, the flag is
logged and ignored (the underlying agent is returned unwrapped).
Tuning args: `circuit_breaker_threshold` (default `3`),
`retry_max_attempts` (default `2`), `timeout_seconds` (default `30.0`).

## Public exports

```python
from attune.agent_factory import (
    AgentCapability,
    AgentConfig,
    AgentFactory,
    AgentRole,
    BaseAdapter,
    BaseAgent,
    Framework,
    WorkflowConfig,
)
```

That list is the `__all__` of `attune.agent_factory`. `ResilientAgent`,
`ResilienceConfig`, and the framework-specific adapters are importable
from their submodules but not re-exported at the top level.

## Example: code review pipeline

```python
from attune.agent_factory import AgentFactory, AgentRole

factory = AgentFactory(framework="langgraph")

security = factory.create_agent(
    name="security",
    role=AgentRole.SECURITY,
    model_tier="capable",
    system_prompt="Analyze code for security vulnerabilities.",
)

quality = factory.create_agent(
    name="quality",
    role=AgentRole.REVIEWER,
    model_tier="capable",
    system_prompt="Review code quality and suggest improvements.",
)

coordinator = factory.create_agent(
    name="coordinator",
    role=AgentRole.COORDINATOR,
    model_tier="premium",
    system_prompt="Synthesize reviews into actionable feedback.",
)

pipeline = factory.create_workflow(
    name="code_review",
    agents=[security, quality, coordinator],
    mode="sequential",
)

result = await pipeline.run("Review this code:\n<paste code here>")
print(result["output"])
```

The same code works with `framework="langchain"`, `"autogen"`,
`"haystack"`, or `"native"` — the adapter handles the framework-specific
mechanics, and the call sites are identical.

## Next steps

- [Resilience patterns](./resilience-patterns.md) — deeper detail on
  `ResilientAgent` configuration.
- [Reference index](../reference/index.md)
