---
feature: agents
depth: reference
generated_at: 2026-04-13T16:59:12.095920+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Agents reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ReleaseAgent` | Base agent with CHEAP → CAPABLE → PREMIUM escalation tiers. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Executes pytest with coverage reporting and parses results. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Validates docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Executes ruff linting and validates type hints and complexity metrics. | `src/attune/agents/release/quality_agent.py` |
| `Tier` | Model tier enumeration for progressive cost escalation. | `src/attune/agents/release/release_models.py` |
| `ReleaseAgentResult` | Individual release agent execution result. | `src/attune/agents/release/release_models.py` |
| `QualityGate` | Threshold configuration for release readiness criteria. | `src/attune/agents/release/release_models.py` |
| `ReleaseReadinessReport` | Consolidated release readiness assessment from all agents. | `src/attune/agents/release/release_models.py` |
| `ReleasePrepTeam` | Orchestrates parallel execution of release preparation agents. | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | CLI-integrated workflow wrapper for ReleasePrepTeam. | `src/attune/agents/release/release_prep_team.py` |
| `SecurityAuditorAgent` | Processes bandit security scan output and classifies vulnerabilities. | `src/attune/agents/release/security_agent.py` |
| `AgentExecutionRecord` | Single agent execution record with timestamps and results. | `src/attune/agents/state/models.py` |
| `AgentStateRecord` | Persistent state storage for agent identity and history. | `src/attune/agents/state/models.py` |
| `AgentRecoveryManager` | Manages agent restart recovery from persistent state. | `src/attune/agents/state/recovery.py` |
| `AgentStateStore` | Persistent storage backend for agent state and execution history. | `src/attune/agents/state/store.py` |
| `AutoGenAgent` | Microsoft AutoGen AssistantAgent or UserProxyAgent wrapper. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenWorkflow` | AutoGen GroupChat-based workflow implementation. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `AutoGenAdapter` | Microsoft AutoGen framework integration adapter. | `src/attune/agent_factory/adapters/autogen_adapter.py` |
| `HaystackAgent` | Deepset Haystack Pipeline or Component wrapper. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackWorkflow` | Haystack Pipeline-based workflow implementation. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `HaystackAdapter` | Deepset Haystack framework integration adapter. | `src/attune/agent_factory/adapters/haystack_adapter.py` |
| `LangChainAgent` | LangChain chain or agent wrapper. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainWorkflow` | LangChain SequentialChain or custom routing workflow. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangChainAdapter` | LangChain framework integration adapter. | `src/attune/agent_factory/adapters/langchain_adapter.py` |
| `LangGraphAgent` | LangGraph node or runnable wrapper. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphWorkflow` | LangGraph StateGraph-based workflow implementation. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `LangGraphAdapter` | LangGraph framework integration adapter. | `src/attune/agent_factory/adapters/langgraph_adapter.py` |
| `NativeAgent` | Empathy native EmpathyLLM-based agent. | `src/attune/agent_factory/adapters/native.py` |
| `NativeWorkflow` | Sequential and parallel native agent execution workflow. | `src/attune/agent_factory/adapters/native.py` |
| `NativeAdapter` | Empathy native agent system integration adapter. | `src/attune/agent_factory/adapters/native.py` |
| `WizardAgent` | Existing wizard wrapper for agent compatibility. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardWorkflow` | Sequential wizard chaining workflow. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `WizardAdapter` | Wizard-to-Agent Factory integration adapter. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `AgentRole` | Standardized agent role definitions for multi-agent systems. | `src/attune/agent_factory/base.py` |
| `AgentCapability` | Agent capability enumeration and configuration. | `src/attune/agent_factory/base.py` |
| `AgentConfig` | Agent creation configuration parameters. | `src/attune/agent_factory/base.py` |
| `WorkflowConfig` | Workflow and graph creation configuration parameters. | `src/attune/agent_factory/base.py` |
| `BaseAgent` | Framework-agnostic agent abstract base class. | `src/attune/agent_factory/base.py` |
| `BaseWorkflow` | Framework-agnostic workflow abstract base class. | `src/attune/agent_factory/base.py` |
| `BaseAdapter` | Framework adapter abstract base class. | `src/attune/agent_factory/base.py` |
| `AgentFactory` | Universal agent and workflow creation factory. | `src/attune/agent_factory/factory.py` |
| `Framework` | Supported agent framework enumeration. | `src/attune/agent_factory/framework.py` |
| `MemoryAwareAgent` | Memory Graph-integrated agent wrapper. | `src/attune/agent_factory/memory_integration.py` |
| `ResilienceConfig` | Resilience pattern configuration parameters. | `src/attune/agent_factory/resilient.py` |
| `ResilientAgent` | Resilience pattern-enhanced agent wrapper. | `src/attune/agent_factory/resilient.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_langchain_adapter()` | Returns LangChain adapter with lazy import handling. | `src/attune/agent_factory/adapters/__init__.py` |
| `get_langgraph_adapter()` | Returns LangGraph adapter with lazy import handling. | `src/attune/agent_factory/adapters/__init__.py` |
| `get_autogen_adapter()` | Returns AutoGen adapter with lazy import handling. | `src/attune/agent_factory/adapters/__init__.py` |
| `get_haystack_adapter()` | Returns Haystack adapter with lazy import handling. | `src/attune/agent_factory/adapters/__init__.py` |
| `wrap_wizard()` | Converts existing wizard into agent-compatible wrapper. | `src/attune/agent_factory/adapters/wizard_adapter.py` |
| `safe_agent_operation()` | Decorates agent operations with logging and error handling. | `src/attune/agent_factory/decorators.py` |
| `retry_on_failure()` | Decorates operations with exponential backoff retry logic. | `src/attune/agent_factory/decorators.py` |
| `log_performance()` | Decorates operations with performance timing and logging. | `src/attune/agent_factory/decorators.py` |
| `validate_input()` | Decorates operations with required field validation. | `src/attune/agent_factory/decorators.py` |
| `with_cost_tracking()` | Decorates operations with API cost tracking and reporting. | `src/attune/agent_factory/decorators.py` |
| `graceful_degradation()` | Decorates operations with graceful failure handling. | `src/attune/agent_factory/decorators.py` |
| `detect_installed_frameworks()` | Scans environment for available agent frameworks. | `src/attune/agent_factory/framework.py` |
| `get_recommended_framework()` | Returns optimal framework recommendation for use case. | `src/attune/agent_factory/framework.py` |
| `get_framework_info()` | Returns detailed information about specified framework. | `src/attune/agent_factory/framework.py` |

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

## Tags

`agents`, `ai`, `release`
