---
feature: agents
depth: reference
generated_at: 2026-04-06T04:32:32.769509+00:00
source_hash: f4444f832b2067c6c0ece4cfebdca1ecf9eb7d5b16efcf3ba756c35f5da24167
status: generated
---

# Agents reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ReleaseAgent` | Base agent with progressive tier escalation from cheap to premium models. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest with coverage analysis and parses coverage reports. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Validates docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Executes ruff linting and validates type hints and code complexity. | `src/attune/agents/release/quality_agent.py` |
| `Tier` | Model tier enumeration for progressive escalation strategies. | `src/attune/agents/release/release_models.py` |
| `ReleaseAgentResult` | Contains the execution result from an individual release agent. | `src/attune/agents/release/release_models.py` |
| `QualityGate` | Defines quality thresholds for release readiness validation. | `src/attune/agents/release/release_models.py` |
| `ReleaseReadinessReport` | Aggregates results from all release preparation agents. | `src/attune/agents/release/release_models.py` |
| `ReleasePrepTeam` | Orchestrates parallel execution of multiple release preparation agents. | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | Integrates ReleasePrepTeam with the CLI registry for workflow execution. | `src/attune/agents/release/release_prep_team.py` |
| `SecurityAuditorAgent` | Analyzes bandit security scan output and classifies vulnerabilities by severity. | `src/attune/agents/release/security_agent.py` |
| `AgentExecutionRecord` | Records a single execution event for an agent instance. | `src/attune/agents/state/models.py` |
| `AgentStateRecord` | Stores persistent state data for a single agent identity. | `src/attune/agents/state/models.py` |
| `AgentRecoveryManager` | Manages agent restart and recovery from persistent state storage. | `src/attune/agents/state/recovery.py` |
| `AgentStateStore` | Provides persistent storage for agent state and execution history. | `src/attune/agents/state/store.py` |
| `AutoGenAgent` | Wraps Microsoft AutoGen AssistantAgent or UserProxyAgent instances. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenWorkflow` | Implements workflow execution using AutoGen's GroupChat functionality. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenAdapter` | Provides integration adapter for Microsoft AutoGen framework. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `HaystackAgent` | Wraps deepset Haystack Pipeline or Component instances. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackWorkflow` | Implements workflow execution using Haystack Pipeline architecture. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackAdapter` | Provides integration adapter for deepset Haystack framework. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `LangChainAgent` | Wraps LangChain chain or agent instances for unified interface. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainWorkflow` | Implements workflow using LangChain's SequentialChain or custom routing. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainAdapter` | Provides integration adapter for LangChain framework. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangGraphAgent` | Wraps LangGraph node or runnable components. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphWorkflow` | Implements workflow execution using LangGraph's StateGraph. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphAdapter` | Provides integration adapter for LangGraph framework. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `NativeAgent` | Implements agents using Empathy's native EmpathyLLM system. | `src/attune/agent_factory/adapters/native.py` |
| `NativeWorkflow` | Provides sequential and parallel agent execution for native agents. | `src/attune/agent_factory/adapters/native.py` |
| `NativeAdapter` | Provides integration adapter for Empathy's native agent system. | `src/attune/agent_factory/adapters/native.py` |
| `WizardAgent` | Wraps existing wizard components as agents for integration. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardWorkflow` | Chains multiple wizards together in workflow sequences. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardAdapter` | Integrates wizard components with the Agent Factory system. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `AgentRole` | Defines standard agent roles for multi-agent system coordination. | `src/attune/agent_factory/base.py` |
| `AgentCapability` | Enumerates capabilities that agents can possess and advertise. | `src/attune/agent_factory/base.py` |
| `AgentConfig` | Contains configuration parameters for agent creation and setup. | `src/attune/agent_factory/base.py` |
| `WorkflowConfig` | Contains configuration parameters for workflow and graph creation. | `src/attune/agent_factory/base.py` |
| `BaseAgent` | Abstract base class providing framework-agnostic agent interface. | `src/attune/agent_factory/base.py` |
| `BaseWorkflow` | Abstract base class providing framework-agnostic workflow interface. | `src/attune/agent_factory/base.py` |
| `BaseAdapter` | Abstract base class for implementing framework integration adapters. | `src/attune/agent_factory/base.py` |
| `AgentFactory` | Universal factory for creating agents and workflows across frameworks. | `src/attune/agent_factory/factory.py` |
| `Framework` | Enumerates supported agent frameworks for factory selection. | `src/attune/agent_factory/framework.py` |
| `MemoryAwareAgent` | Wraps agents with Memory Graph integration for persistent context. | `src/attune/agent_factory/memory_integration.py` |
| `ResilienceConfig` | Configures resilience patterns like retries and circuit breakers. | `src/attune/agent_factory/resilient.py` |
| `ResilientAgent` | Wraps agents with resilience patterns for fault tolerance. | `src/attune/agent_factory/resilient.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_langchain_adapter()` | Returns LangChain adapter instance with lazy framework import. | `src/attune/agent_factory/adapters/__init__.py` |
| `get_langgraph_adapter()` | Returns LangGraph adapter instance with lazy framework import. | `src/attune/agent_factory/adapters/__init__.py` |
| `get_autogen_adapter()` | Returns AutoGen adapter instance with lazy framework import. | `src/attune/agent_factory/adapters/__init__.py` |
| `get_haystack_adapter()` | Returns Haystack adapter instance with lazy framework import. | `src/attune/agent_factory/adapters/__init__.py` |
| `wrap_wizard()` | Converts existing wizard components into agent-compatible interfaces. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `safe_agent_operation()` | Decorator that adds logging and error handling to agent operations. | `src/attune/agent_factory/decorators.py` |
| `retry_on_failure()` | Decorator that retries failed operations with exponential backoff. | `src/attune/agent_factory/decorators.py` |
| `log_performance()` | Decorator that logs execution time for slow operations. | `src/attune/agent_factory/decorators.py` |
| `validate_input()` | Decorator that validates required fields in input data structures. | `src/attune/agent_factory/decorators.py` |
| `with_cost_tracking()` | Decorator that tracks and logs API costs for operations. | `src/attune/agent_factory/decorators.py` |
| `graceful_degradation()` | Decorator that enables graceful degradation when operations fail. | `src/attune/agent_factory/decorators.py` |
| `detect_installed_frameworks()` | Scans environment to identify which agent frameworks are available. | `src/attune/agent_factory/framework.py` |
| `get_recommended_framework()` | Suggests the best framework for a specific use case. | `src/attune/agent_factory/framework.py` |
| `get_framework_info()` | Returns detailed information about a specific framework. | `src/attune/agent_factory/framework.py` |


## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

## Tags

`agents`, `ai`, `release`
