---
type: reference
name: agents-reference
feature: agents
depth: reference
generated_at: 2026-06-04T23:45:26.744532+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Agents reference

Create and manage agents, workflows, and framework adapters — including release preparation agents, state persistence, and recovery.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `AutoGenAgent` | Agent wrapping an AutoGen AssistantAgent or UserProxyAgent. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenWorkflow` | Workflow using AutoGen's GroupChat. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenAdapter` | Adapter for Microsoft AutoGen framework. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `HaystackAgent` | Agent wrapping a Haystack Pipeline or Component. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackWorkflow` | Workflow using Haystack Pipeline. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackAdapter` | Adapter for deepset Haystack framework. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `LangChainAgent` | Agent wrapping a LangChain chain or agent. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainWorkflow` | Workflow using LangChain's SequentialChain or custom routing. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainAdapter` | Adapter for LangChain framework. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangGraphAgent` | Agent wrapping a LangGraph node/runnable. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphWorkflow` | Workflow using LangGraph's StateGraph. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphAdapter` | Adapter for LangGraph framework. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `NativeAgent` | Agent using Empathy's native EmpathyLLM. | `src/attune/agent_factory/adapters/native.py` |
| `NativeWorkflow` | Workflow using sequential/parallel agent execution. | `src/attune/agent_factory/adapters/native.py` |
| `NativeAdapter` | Adapter for Empathy's native agent system. | `src/attune/agent_factory/adapters/native.py` |
| `WizardAgent` | Agent wrapper for existing wizards. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardWorkflow` | Workflow for chaining multiple wizards. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardAdapter` | Adapter for integrating wizards with Agent Factory. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `AgentRole` | Standard agent roles for multi-agent systems. | `src/attune/agent_factory/base.py` |
| `AgentCapability` | Capabilities an agent can have. | `src/attune/agent_factory/base.py` |
| `AgentConfig` | Configuration for creating an agent. | `src/attune/agent_factory/base.py` |
| `WorkflowConfig` | Configuration for creating a workflow/graph. | `src/attune/agent_factory/base.py` |
| `BaseAgent` | Abstract base class for framework-agnostic agents. | `src/attune/agent_factory/base.py` |
| `BaseWorkflow` | Abstract base class for framework-agnostic workflows. | `src/attune/agent_factory/base.py` |
| `BaseAdapter` | Abstract base class for framework adapters. | `src/attune/agent_factory/base.py` |
| `AgentFactory` | Universal factory for creating agents and workflows. | `src/attune/agent_factory/factory.py` |
| `Framework` | Supported agent frameworks. | `src/attune/agent_factory/framework.py` |
| `MemoryAwareAgent` | Agent wrapper that integrates with Memory Graph. | `src/attune/agent_factory/memory_integration.py` |
| `ResilienceConfig` | Configuration for resilience patterns. | `src/attune/agent_factory/resilient.py` |
| `ResilientAgent` | Agent wrapper that applies resilience patterns. | `src/attune/agent_factory/resilient.py` |
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity. | `src/attune/agents/release/quality_agent.py` |
| `Tier` | Model tier for progressive escalation. | `src/attune/agents/release/release_models.py` |
| `ReleaseAgentResult` | Result from an individual release agent. | `src/attune/agents/release/release_models.py` |
| `QualityGate` | Quality gate threshold for release readiness. | `src/attune/agents/release/release_models.py` |
| `ReleaseReadinessReport` | Aggregated release readiness assessment. | `src/attune/agents/release/release_models.py` |
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents. | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates ReleasePrepTeam with the CLI registry. | `src/attune/agents/release/release_prep_team.py` |
| `SecurityAuditorAgent` | Analyzes bandit output and classifies vulnerabilities by severity. | `src/attune/agents/release/security_agent.py` |
| `AgentExecutionRecord` | Single execution record for an agent. | `src/attune/agents/state/models.py` |
| `AgentStateRecord` | Persistent state for a single agent identity. | `src/attune/agents/state/models.py` |
| `AgentRecoveryManager` | Handles agent restart recovery from persistent state. | `src/attune/agents/state/recovery.py` |
| `AgentStateStore` | Persistent storage for agent state and execution history. | `src/attune/agents/state/store.py` |

## Class methods

### `AutoGenAgent`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: AgentConfig, autogen_agent = None` | — | Initializes the agent with the given config and optional AutoGen agent instance. |
| `invoke` | `input_data: str \| dict, context: dict \| None = None` | `dict` | Invokes the agent synchronously and returns a result dict. |
| `stream` | `input_data: str \| dict, context: dict \| None = None` | `AsyncGenerator[dict, None]` | Streams agent responses as an async generator of result dicts. |
| `get_autogen_agent` | — | `object \| None` | Returns the underlying AutoGen agent instance, or `None` if not set. |

### `AutoGenWorkflow`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: WorkflowConfig, agents: list[BaseAgent], group_chat = None, manager = None` | — | Initializes the workflow with config, agents, and optional GroupChat components. |
| `run` | `input_data: str \| dict, initial_state: dict \| None = None` | `dict` | Runs the workflow and returns a result dict. |
| `stream` | `input_data: str \| dict, initial_state: dict \| None = None` | — | Streams workflow execution results. |

### `AutoGenAdapter`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `provider: str = 'anthropic', api_key: str \| None = None` | — | Initializes the adapter with an LLM provider and optional API key. |
| `is_available` | — | `bool` | Returns `True` if the AutoGen framework is installed and available. |
| `create_agent` | `config: AgentConfig` | `AutoGenAgent` | Creates an `AutoGenAgent` from the given config. |
| `create_workflow` | `config: WorkflowConfig, agents: list[BaseAgent]` | `AutoGenWorkflow` | Creates an `AutoGenWorkflow` from the given config and agents. |
| `create_tool` | `name: str, description: str, func: Callable, args_schema: dict \| None = None` | `dict` | Wraps a callable as an AutoGen-compatible tool descriptor dict. |

#### `AutoGenAdapter` properties

| Property | Type | Description |
|----------|------|-------------|
| `framework_name` | `str` | Returns the framework name identifier. |

### `HaystackAgent`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: AgentConfig, pipeline = None, generator = None` | — | Initializes the agent with the given config and optional Haystack pipeline or generator. |
| `invoke` | `input_data: str \| dict, context: dict \| None = None` | `dict` | Invokes the agent synchronously and returns a result dict. |
| `stream` | `input_data: str \| dict, context: dict \| None = None` | `AsyncGenerator[dict, None]` | Streams agent responses as an async generator of result dicts. |

### `HaystackWorkflow`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: WorkflowConfig, agents: list[BaseAgent], pipeline = None` | — | Initializes the workflow with config, agents, and an optional Haystack pipeline. |
| `run` | `input_data: str \| dict, initial_state: dict \| None = None` | `dict` | Runs the workflow and returns a result dict. |
| `stream` | `input_data: str \| dict, initial_state: dict \| None = None` | — | Streams workflow execution results. |

### `HaystackAdapter`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `provider: str = 'anthropic', api_key: str \| None = None` | — | Initializes the adapter with an LLM provider and optional API key. |
| `is_available` | — | `bool` | Returns `True` if the Haystack framework is installed and available. |
| `create_agent` | `config: AgentConfig` | `HaystackAgent` | Creates a `HaystackAgent` from the given config. |
| `create_workflow` | `config: WorkflowConfig, agents: list[BaseAgent]` | `HaystackWorkflow` | Creates a `HaystackWorkflow` from the given config and agents. |
| `create_tool` | `name: str, description: str, func: Callable, args_schema: dict \| None = None` | `dict` | Wraps a callable as a Haystack-compatible tool descriptor dict. |
| `create_document_store` | `store_type: str = 'in_memory'` | `Any` | Creates a Haystack document store of the specified type. |

#### `HaystackAdapter` properties

| Property | Type | Description |
|----------|------|-------------|
| `framework_name` | `str` | Returns the framework name identifier. |

### `LangChainAgent`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: AgentConfig, chain = None, agent_executor = None` | — | Initializes the agent with the given config and optional LangChain chain or executor. |
| `invoke` | `input_data: str \| dict, context: dict \| None = None` | `dict` | Invokes the agent synchronously and returns a result dict. |
| `stream` | `input_data: str \| dict, context: dict \| None = None` | — | Streams agent responses. |

### `LangChainWorkflow`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: WorkflowConfig, agents: list[BaseAgent], chain = None` | — | Initializes the workflow with config, agents, and an optional LangChain chain. |
| `run` | `input_data: str \| dict, initial_state: dict \| None = None` | `dict` | Runs the workflow and returns a result dict. |
| `stream` | `input_data: str \| dict, initial_state: dict \| None = None` | — | Streams workflow execution results. |

### `LangChainAdapter`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `provider: str = 'anthropic', api_key: str \| None = None` | — | Initializes the adapter with an LLM provider and optional API key. |
| `is_available` | — | `bool` | Returns `True` if the LangChain framework is installed and available. |
| `create_agent` | `config: AgentConfig` | `LangChainAgent` | Creates a `LangChainAgent` from the given config. |
| `create_workflow` | `config: WorkflowConfig, agents: list[BaseAgent]` | `LangChainWorkflow` | Creates a `LangChainWorkflow` from the given config and agents. |
| `create_tool` | `name: str, description: str, func: Callable, args_schema: dict \| None = None` | `Any` | Wraps a callable as a LangChain-compatible tool. |

#### `LangChainAdapter` properties

| Property | Type | Description |
|----------|------|-------------|
| `framework_name` | `str` | Returns the framework name identifier. |

### `LangGraphAgent`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: AgentConfig, runnable = None, node_func = None` | — | Initializes the agent with the given config and optional LangGraph runnable or node function. |
| `invoke` | `input_data: str \| dict, context: dict \| None = None` | `dict` | Invokes the agent synchronously and returns a result dict. |
| `stream` | `input_data: str \| dict, context: dict \| None = None` | — | Streams agent responses. |

## Functions

| Function | Parameters | Returns | Description | Raises |
|----------|------------|---------|-------------|--------|
| `get_langchain_adapter` | — | — | Returns the LangChain adapter (lazy import). | — |
| `get_langgraph_adapter` | — | — | Returns the LangGraph adapter (lazy import). | — |
| `get_autogen_adapter` | — | — | Returns the AutoGen adapter (lazy import). | — |
| `get_haystack_adapter` | — | — | Returns the Haystack adapter (lazy import). | — |
| `wrap_wizard` | `wizard, name
