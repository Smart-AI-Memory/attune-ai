---
type: reference
name: agents-reference
feature: agents
depth: reference
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f67c2f70bbc6d8bdf391e3cbf1ac1e57c554913aa2b3b355f736347e5526634
status: generated
scaffold_hash: 4784cd713b49011cc685b0c641b8519c53bcfa436aa96ec99e0886eef0ff9158
---

# Agents reference

Create and run framework-agnostic agents and workflows across AutoGen, Haystack, LangChain, LangGraph, and native runtimes. The feature also covers release-preparation agents, persistent agent state, and recovery management.

## Classes

### Agent factory — base types

| Class | Description | File |
|-------|-------------|------|
| `AgentRole` | Standard roles for multi-agent systems. | `src/attune/agent_factory/base.py` |
| `AgentCapability` | Capabilities an agent can advertise. | `src/attune/agent_factory/base.py` |
| `AgentConfig` | Configuration for creating an agent. | `src/attune/agent_factory/base.py` |
| `WorkflowConfig` | Configuration for creating a workflow or graph. | `src/attune/agent_factory/base.py` |
| `BaseAgent` | Abstract base for framework-agnostic agents. | `src/attune/agent_factory/base.py` |
| `BaseWorkflow` | Abstract base for framework-agnostic workflows. | `src/attune/agent_factory/base.py` |
| `BaseAdapter` | Abstract base for framework adapters. | `src/attune/agent_factory/base.py` |
| `AgentFactory` | Universal factory for creating agents and workflows. | `src/attune/agent_factory/factory.py` |
| `Framework` | Supported agent frameworks. | `src/attune/agent_factory/framework.py` |

### Framework adapters

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
| `LangGraphAgent` | Agent wrapping a LangGraph node or runnable. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphWorkflow` | Workflow using LangGraph's StateGraph. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphAdapter` | Adapter for LangGraph framework. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `NativeAgent` | Agent using Empathy's native EmpathyLLM. | `src/attune/agent_factory/adapters/native.py` |
| `NativeWorkflow` | Workflow using sequential or parallel agent execution. | `src/attune/agent_factory/adapters/native.py` |
| `NativeAdapter` | Adapter for Empathy's native agent system. | `src/attune/agent_factory/adapters/native.py` |
| `WizardAgent` | Agent wrapper for existing wizards. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardWorkflow` | Workflow for chaining multiple wizards. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardAdapter` | Adapter for integrating wizards with Agent Factory. | `src/attune/agent_factory/adapters/wizard_adapter.py` |

### Resilience and memory

| Class | Description | File |
|-------|-------------|------|
| `MemoryAwareAgent` | Agent wrapper that integrates with Memory Graph. | `src/attune/agent_factory/memory_integration.py` |
| `ResilienceConfig` | Configuration for resilience patterns. | `src/attune/agent_factory/resilient.py` |
| `ResilientAgent` | Agent wrapper that applies resilience patterns. | `src/attune/agent_factory/resilient.py` |

### Release agents

| Class | Description | File |
|-------|-------------|------|
| `ReleaseAgent` | Base agent with CHEAP → CAPABLE → PREMIUM escalation. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest --cov and parses the coverage report. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity. | `src/attune/agents/release/quality_agent.py` |
| `SecurityAuditorAgent` | Analyzes bandit output and classifies vulnerabilities by severity. | `src/attune/agents/release/security_agent.py` |
| `Tier` | Model tier for progressive escalation. | `src/attune/agents/release/release_models.py` |
| `ReleaseAgentResult` | Result from an individual release agent. | `src/attune/agents/release/release_models.py` |
| `QualityGate` | Quality gate threshold for release readiness. | `src/attune/agents/release/release_models.py` |
| `ReleaseReadinessReport` | Aggregated release readiness assessment. | `src/attune/agents/release/release_models.py` |
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents. | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates `ReleasePrepTeam` with the CLI registry. | `src/attune/agents/release/release_prep_team.py` |

### State management

| Class | Description | File |
|-------|-------------|------|
| `AgentExecutionRecord` | Single execution record for an agent. | `src/attune/agents/state/models.py` |
| `AgentStateRecord` | Persistent state for a single agent identity. | `src/attune/agents/state/models.py` |
| `AgentStateStore` | Persistent storage for agent state and execution history. | `src/attune/agents/state/store.py` |
| `AgentRecoveryManager` | Handles agent restart recovery from persistent state. | `src/attune/agents/state/recovery.py` |

## Properties

Each framework adapter exposes a read-only `framework_name` property.

| Property | Type | Class | Description |
|----------|------|-------|-------------|
| `framework_name` | `str` | `AutoGenAdapter` | Framework name identifier. |
| `framework_name` | `str` | `HaystackAdapter` | Framework name identifier. |
| `framework_name` | `str` | `LangChainAdapter` | Framework name identifier. |

## Functions

| Function | Parameters | Returns | Raises | Description | File |
|----------|------------|---------|--------|-------------|------|
| `get_langchain_adapter` | — | — | — | Returns the LangChain adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |
| `get_langgraph_adapter` | — | — | — | Returns the LangGraph adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |
| `get_autogen_adapter` | — | — | — | Returns the AutoGen adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |
| `get_haystack_adapter` | — | — | — | Returns the Haystack adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |
| `wrap_wizard` | `wizard, name: str \| None = None, model_tier: str = 'capable'` | `WizardAgent` | — | Wraps a wizard as an agent. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `safe_agent_operation` | `operation_name: str` | `Callable[[F], F]` | `AgentOperationError` | Decorator for safe agent operations with logging and error handling. | `src/attune/agent_factory/decorators.py` |
| `retry_on_failure` | `max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)` | `Callable[[F], F]` | `last_exception` | Decorator to retry failed operations with exponential backoff. | `src/attune/agent_factory/decorators.py` |
| `log_performance` | `threshold_seconds: float = 1.0` | `Callable[[F], F]` | — | Decorator to log operations that exceed `threshold_seconds`. | `src/attune/agent_factory/decorators.py` |
| `validate_input` | `required_fields: list[str]` | — | `ValueError` — 'Input must be a dict, got {...}'<br>`ValueError` — 'Missing required fields: {...}' | Decorator to validate required fields in input data. | `src/attune/agent_factory/decorators.py` |
| `with_cost_tracking` | `operation_type: str = 'agent_call'` | — | — | Decorator to track API costs for operations. | `src/attune/agent_factory/decorators.py` |
| `graceful_degradation` | `fallback_value: Any = None, log_level: str = 'warning'` | — | — | Decorator for graceful degradation on failure. | `src/attune/agent_factory/decorators.py` |
| `detect_installed_frameworks` | — | `list[Framework]` | — | Detects which agent frameworks are installed. | `src/attune/agent_factory/framework.py` |
| `get_recommended_framework` | `use_case: str = 'general'` | `Framework` | — | Returns the recommended framework for a use case. | `src/attune/agent_factory/framework.py` |
| `get_framework_info` | `framework: Framework` | `dict[str, object]` | — | Returns information about a framework. | `src/attune/agent_factory/framework.py` |

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

## Tags

`agents`, `ai`, `release`
