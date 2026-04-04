---
feature: agents
depth: reference
generated_at: 2026-04-04T02:25:50.462661+00:00
source_hash: f4444f832b2067c6c0ece4cfebdca1ecf9eb7d5b16efcf3ba756c35f5da24167
status: generated
---

# Agents Reference

## Classes

| Class | Description | File |

|-------|-------------|------|

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


## Functions

| Function | Description | File |

|----------|-------------|------|

| `get_langchain_adapter()` | Get LangChain adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |

| `get_langgraph_adapter()` | Get LangGraph adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |

| `get_autogen_adapter()` | Get AutoGen adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |

| `get_haystack_adapter()` | Get Haystack adapter (lazy import). | `src/attune/agent_factory/adapters/__init__.py` |

| `wrap_wizard()` | Quick helper to wrap a wizard as an agent. | `src/attune/agent_factory/adapters/wizard_adapter.py` |

| `safe_agent_operation()` | Decorator for safe agent operations with logging and error handling. | `src/attune/agent_factory/decorators.py` |

| `retry_on_failure()` | Decorator to retry failed operations with exponential backoff. | `src/attune/agent_factory/decorators.py` |

| `log_performance()` | Decorator to log slow operations. | `src/attune/agent_factory/decorators.py` |

| `validate_input()` | Decorator to validate required fields in input data. | `src/attune/agent_factory/decorators.py` |

| `with_cost_tracking()` | Decorator to track API costs for operations. | `src/attune/agent_factory/decorators.py` |

| `graceful_degradation()` | Decorator for graceful degradation on failure. | `src/attune/agent_factory/decorators.py` |

| `detect_installed_frameworks()` | Detect which agent frameworks are installed. | `src/attune/agent_factory/framework.py` |

| `get_recommended_framework()` | Get recommended framework for a use case. | `src/attune/agent_factory/framework.py` |

| `get_framework_info()` | Get information about a framework. | `src/attune/agent_factory/framework.py` |


## Source Files

- `src/attune/agents/**`

- `src/attune/agent_factory/**`


## Tags

`agents`, `ai`, `release`
