---
type: reference
feature: agents
depth: reference
generated_at: 2026-05-04T02:33:19.099768+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Agents reference

Create, configure, and orchestrate AI agents across multiple frameworks. Build single agents or multi-agent workflows with adapters for AutoGen, Haystack, LangChain, LangGraph, and Empathy's native agent system.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `AutoGenAgent` | Agent wrapping an AutoGen AssistantAgent or UserProxyAgent | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenWorkflow` | Workflow using AutoGen's GroupChat | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenAdapter` | Adapter for Microsoft AutoGen framework | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `HaystackAgent` | Agent wrapping a Haystack Pipeline or Component | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackWorkflow` | Workflow using Haystack Pipeline | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackAdapter` | Adapter for deepset Haystack framework | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `LangChainAgent` | Agent wrapping a LangChain chain or agent | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainWorkflow` | Workflow using LangChain's SequentialChain or custom routing | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainAdapter` | Adapter for LangChain framework | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangGraphAgent` | Agent wrapping a LangGraph node/runnable | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphWorkflow` | Workflow using LangGraph's StateGraph | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphAdapter` | Adapter for LangGraph framework | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `NativeAgent` | Agent using Empathy's native EmpathyLLM | `src/attune/agent_factory/adapters/native.py` |
| `NativeWorkflow` | Workflow using sequential/parallel agent execution | `src/attune/agent_factory/adapters/native.py` |
| `NativeAdapter` | Adapter for Empathy's native agent system | `src/attune/agent_factory/adapters/native.py` |
| `WizardAgent` | Agent wrapper for existing wizards | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardWorkflow` | Workflow for chaining multiple wizards | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardAdapter` | Adapter for integrating wizards with Agent Factory | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `AgentRole` | Standard agent roles for multi-agent systems | `src/attune/agent_factory/base.py` |
| `AgentCapability` | Capabilities an agent can have | `src/attune/agent_factory/base.py` |
| `AgentConfig` | Configuration for creating an agent | `src/attune/agent_factory/base.py` |
| `WorkflowConfig` | Configuration for creating a workflow/graph | `src/attune/agent_factory/base.py` |
| `BaseAgent` | Abstract base class for framework-agnostic agents | `src/attune/agent_factory/base.py` |
| `BaseWorkflow` | Abstract base class for framework-agnostic workflows | `src/attune/agent_factory/base.py` |
| `BaseAdapter` | Abstract base class for framework adapters | `src/attune/agent_factory/base.py` |
| `AgentFactory` | Universal factory for creating agents and workflows | `src/attune/agent_factory/factory.py` |
| `Framework` | Supported agent frameworks | `src/attune/agent_factory/framework.py` |
| `MemoryAwareAgent` | Agent wrapper that integrates with Memory Graph | `src/attune/agent_factory/memory_integration.py` |
| `ResilienceConfig` | Configuration for resilience patterns | `src/attune/agent_factory/resilient.py` |
| `ResilientAgent` | Agent wrapper that applies resilience patterns | `src/attune/agent_factory/resilient.py` |
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity | `src/attune/agents/release/quality_agent.py` |
| `Tier` | Model tier for progressive escalation | `src/attune/agents/release/release_models.py` |
| `ReleaseAgentResult` | Result from an individual release agent | `src/attune/agents/release/release_models.py` |
| `QualityGate` | Quality gate threshold for release readiness | `src/attune/agents/release/release_models.py` |
| `ReleaseReadinessReport` | Aggregated release readiness assessment | `src/attune/agents/release/release_models.py` |
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates ReleasePrepTeam with the CLI registry | `src/attune/agents/release/release_prep_team.py` |
| `SecurityAuditorAgent` | Analyzes bandit output and classifies vulnerabilities by severity | `src/attune/agents/release/security_agent.py` |
| `AgentExecutionRecord` | Single execution record for an agent | `src/attune/agents/state/models.py` |
| `AgentStateRecord` | Persistent state for a single agent identity | `src/attune/agents/state/models.py` |
| `AgentRecoveryManager` | Handles agent restart recovery from persistent state | `src/attune/agents/state/recovery.py` |
| `AgentStateStore` | Persistent storage for agent state and execution history | `src/attune/agents/state/store.py` |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_langchain_adapter` | — | `LangChainAdapter` | Get LangChain adapter (lazy import) |
| `get_langgraph_adapter` | — | `LangGraphAdapter` | Get LangGraph adapter (lazy import) |
| `get_autogen_adapter` | — | `AutoGenAdapter` | Get AutoGen adapter (lazy import) |
| `get_haystack_adapter` | — | `HaystackAdapter` | Get Haystack adapter (lazy import) |
| `wrap_wizard` | `wizard`, `name: str \| None = None`, `model_tier: str = 'capable'` | `WizardAgent` | Quick helper to wrap a wizard as an agent |
| `safe_agent_operation` | `operation_name: str` | `Callable[[F], F]` | Decorator for safe agent operations with logging and error handling |
| `retry_on_failure` | `max_attempts: int = 3`, `delay: float = 1.0`, `backoff: float = 2.0`, `exceptions: tuple = (Exception,)` | `Callable[[F], F]` | Decorator to retry failed operations with exponential backoff |
| `log_performance` | `threshold_seconds: float = 1.0` | `Callable[[F], F]` | Decorator to log slow operations |
| `validate_input` | `required_fields: list[str]` | — | Decorator to validate required fields in input data |
| `with_cost_tracking` | `operation_type: str = 'agent_call'` | — | Decorator to track API costs for operations |
| `graceful_degradation` | — | — | Decorator for graceful degradation on failure |
| `detect_installed_frameworks` | — | — | Detect which agent frameworks are installed |
| `get_recommended_framework` | — | — | Get recommended framework for a use case |
| `get_framework_info` | — | — | Get information about a framework |

### Raises

| Function | Raises | Message |
|----------|---------|---------|
| `safe_agent_operation` | `AgentOperationError` | — |
| `retry_on_failure` | `last_exception` | — |
| `validate_input` | `ValueError` | 'Input must be a dict, got {...}' |
| `validate_input` | `ValueError` | 'Missing required fields: {...}' |

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

## Tags

`agents`, `ai`, `release`
