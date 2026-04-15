---
type: reference
feature: agents
depth: reference
generated_at: 2026-04-14T15:08:08.249680+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Agents reference

## Release preparation agents

| Class | Description | Parameters |
|-------|-------------|------------|
| `ReleaseAgent` | Base agent with CHEAP → CAPABLE → PREMIUM escalation | `agent_id: str, role: str, redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` |
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents | `quality_gates: dict[str, Any] \| None = None, redis_url: str \| None = None` |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates ReleasePrepTeam with the CLI registry | `quality_gates: dict[str, float] \| None = None, **kwargs: Any` |

### ReleaseAgent methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `process` | `codebase_path: str = '.'` | `ReleaseAgentResult` | Process codebase analysis |

### ReleasePrepTeam methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_total_cost` | | `float` | Get total cost of all agent operations |
| `assess_readiness` | `codebase_path: str = '.'` | `ReleaseReadinessReport` | Assess release readiness across all agents |

### ReleasePrepTeamWorkflow methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run_stage` | `stage_name: str, tier: ModelTier, input_data: Any` | `Any` | Run a specific workflow stage |
| `execute` | `path: str = '.', context: dict[str, Any] \| None = None, **kwargs: Any` | `ReleaseReadinessReport` | Execute the full release preparation workflow |

## Data models

### ReleaseAgentResult fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_id` | `str` | | Agent identifier |
| `agent_role` | `str` | | Agent role designation |
| `success` | `bool` | | Whether the agent completed successfully |
| `tier_used` | `Tier` | | Model tier used for processing |
| `findings` | `dict[str, Any]` | `field(default_factory=dict)` | Analysis findings and results |
| `score` | `float` | `0.0` | Quality score assigned by agent |
| `confidence` | `float` | `0.0` | Confidence level in results |
| `cost` | `float` | `0.0` | API cost incurred |
| `execution_time_ms` | `float` | `0.0` | Execution time in milliseconds |
| `escalated` | `bool` | `False` | Whether tier escalation occurred |

### QualityGate fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Quality gate name |
| `threshold` | `float` | | Required threshold value |
| `actual` | `float` | `0.0` | Actual measured value |
| `passed` | `bool` | `False` | Whether the gate passed |
| `critical` | `bool` | `True` | Whether this is a critical gate |
| `message` | `str` | `''` | Status or error message |

### ReleaseReadinessReport fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `approved` | `bool` | | Whether release is approved |
| `confidence` | `str` | | Overall confidence level |
| `quality_gates` | `list[QualityGate]` | `field(default_factory=list)` | All quality gate results |
| `agent_results` | `list[ReleaseAgentResult]` | `field(default_factory=list)` | Results from all agents |
| `blockers` | `list[str]` | `field(default_factory=list)` | Critical issues blocking release |
| `warnings` | `list[str]` | `field(default_factory=list)` | Non-critical warnings |
| `summary` | `str` | `''` | Executive summary |
| `timestamp` | `str` | `field(default_factory=lambda: datetime.now().isoformat())` | Report generation timestamp |
| `total_duration` | `float` | `0.0` | Total execution time |
| `total_cost` | `float` | `0.0` | Total API costs |

### ReleaseReadinessReport methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | | `dict[str, Any]` | Convert report to dictionary |
| `format_console_output` | | `str` | Format report for console display |

## Agent state management

| Class | Description | Parameters |
|-------|-------------|------------|
| `AgentStateStore` | Persistent storage for agent state and execution history | |
| `AgentRecoveryManager` | Handles agent restart recovery from persistent state | |
| `AgentStateRecord` | Persistent state for a single agent identity | |
| `AgentExecutionRecord` | Single execution record for an agent | |

## Framework adapters

| Class | Description | Parameters |
|-------|-------------|------------|
| `NativeAdapter` | Adapter for Empathy's native agent system | |
| `WizardAdapter` | Adapter for integrating wizards with Agent Factory | |
| `LangChainAdapter` | Adapter for LangChain framework | |
| `LangGraphAdapter` | Adapter for LangGraph framework | |
| `AutoGenAdapter` | Adapter for Microsoft AutoGen framework | |
| `HaystackAdapter` | Adapter for deepset Haystack framework | |

## Configuration classes

| Class | Description | Purpose |
|-------|-------------|---------|
| `AgentConfig` | Configuration for creating an agent | Agent initialization |
| `WorkflowConfig` | Configuration for creating a workflow/graph | Workflow setup |
| `Framework` | Supported agent frameworks | Framework selection |
| `AgentRole` | Standard agent roles for multi-agent systems | Role assignment |
| `AgentCapability` | Capabilities an agent can have | Capability tracking |

## Utility functions

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|--------|-------------|
| `get_langchain_adapter` | | | | Get LangChain adapter (lazy import) |
| `get_langgraph_adapter` | | | | Get LangGraph adapter (lazy import) |
| `get_autogen_adapter` | | | | Get AutoGen adapter (lazy import) |
| `get_haystack_adapter` | | | | Get Haystack adapter (lazy import) |
| `wrap_wizard` | `wizard, name: str \| None = None, model_tier: str = 'capable'` | `WizardAgent` | | Quick helper to wrap a wizard as an agent |

## Decorator functions

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|--------|-------------|
| `safe_agent_operation` | `operation_name: str` | `Callable[[F], F]` | `AgentOperationError` | Decorator for safe agent operations with logging and error handling |
| `retry_on_failure` | `max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)` | `Callable[[F], F]` | `last_exception` | Decorator to retry failed operations with exponential backoff |
| `log_performance` | `threshold_seconds: float = 1.0` | `Callable[[F], F]` | | Decorator to log slow operations |
| `validate_input` | `required_fields: list[str]` | | `ValueError` | Decorator to validate required fields in input data |
| `with_cost_tracking` | `operation_type: str = 'agent_call'` | | | Decorator to track API costs for operations |

### validate_input error messages

| Exception | Message |
|-----------|---------|
| `ValueError` | `'Input must be a dict, got {...}'` |
| `ValueError` | `'Missing required fields: {...}'` |
