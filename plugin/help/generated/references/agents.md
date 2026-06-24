---
name: agents
source: content/features/agents.md
tags:
- agents
- ai
type: reference
---

# Universal Agent Factory — create, run, and orchestrate AI agents across frameworks

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
