# Agent Factory API Reference

Complete API documentation for `attune.agent_factory`.

---

## Public API

```python
from attune.agent_factory import (
    AgentFactory,       # Main entry point
    Framework,          # Supported frameworks enum
    AgentRole,          # Agent role enum
    AgentCapability,    # Agent capability enum
    AgentConfig,        # Agent configuration dataclass
    AgentGraphConfig,   # Agent-graph configuration dataclass
    BaseAgent,          # Abstract agent interface
    BaseAdapter,        # Abstract adapter interface
)
```

---

## AgentFactory

**Module:** `attune.agent_factory.factory`

The main entry point for creating agents and workflows across
any supported framework.

### Constructor

```python
AgentFactory(
    framework: Framework | str | None = None,
    provider: str = "anthropic",
    api_key: str | None = None,
    use_case: str = "general",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| framework | `Framework \| str \| None` | `None` | Framework to use (auto-detected if `None`) |
| provider | `str` | `"anthropic"` | LLM provider (`anthropic`, `openai`, `local`) |
| api_key | `str \| None` | `None` | API key (falls back to env var) |
| use_case | `str` | `"general"` | Use case for auto-recommendation |

### Core Methods

#### create_agent

```python
def create_agent(
    name: str,
    role: AgentRole | str = AgentRole.CUSTOM,
    description: str = "",
    model_tier: str = "capable",
    model_override: str | None = None,
    capabilities: list[AgentCapability] | None = None,
    tools: list[Any] | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    empathy_level: int = 4,
    use_patterns: bool = True,
    track_costs: bool = True,
    memory_enabled: bool = True,
    memory_type: str = "conversation",
    framework_options: dict | None = None,
    resilience_enabled: bool = False,
    circuit_breaker_threshold: int = 3,
    retry_max_attempts: int = 2,
    timeout_seconds: float = 30.0,
) -> BaseAgent
```

Creates an agent using the configured framework. Automatically
applies the `ResilientAgent` wrapper when the corresponding
option is enabled.

**Returns:** `BaseAgent` implementation (may be wrapped).

#### create_workflow

```python
def create_workflow(
    name: str,
    agents: list[BaseAgent],
    description: str = "",
    mode: str = "sequential",
    max_iterations: int = 10,
    timeout_seconds: int = 300,
    state_schema: dict | None = None,
    checkpointing: bool = True,
    retry_on_error: bool = True,
    max_retries: int = 3,
    framework_options: dict | None = None,
) -> BaseWorkflow
```

Creates a workflow/pipeline from a list of agents.

| Mode | Description |
|------|-------------|
| `sequential` | Agents run one after another |
| `parallel` | Agents run concurrently |
| `graph` | Stateful graph execution (LangGraph) |
| `conversation` | Agent-to-agent conversation (AutoGen) |

**Returns:** `BaseWorkflow` implementation.

#### create_tool

```python
def create_tool(
    name: str,
    description: str,
    func: Callable,
    args_schema: dict | None = None,
) -> Any
```

Creates a tool in the framework's native format.

#### get_agent

```python
def get_agent(name: str) -> BaseAgent | None
```

Retrieves a previously created agent by name.

#### list_agents

```python
def list_agents() -> list[str]
```

Returns names of all agents created by this factory instance.

#### switch_framework

```python
def switch_framework(framework: Framework | str) -> None
```

Switches to a different framework. Clears all existing agents.

### Class Methods

#### list_frameworks

```python
@classmethod
def list_frameworks(
    installed_only: bool = True,
) -> list[dict]
```

Returns list of framework info dicts with keys: `framework`,
`installed`, `name`, `description`, `best_for`,
`install_command`, `docs_url`.

#### recommend_framework

```python
@classmethod
def recommend_framework(
    use_case: str = "general",
) -> Framework
```

Returns the recommended framework for a use case. Valid use
cases: `general`, `rag`, `multi_agent`, `code_analysis`,
`workflow`, `conversational`.

### Convenience Factories

All accept `**kwargs` passed through to `create_agent()`.

| Method | Default Role | Default Tier |
|--------|-------------|--------------|
| `create_researcher(name, model_tier, **kw)` | `RESEARCHER` | `capable` |
| `create_writer(name, model_tier, **kw)` | `WRITER` | `premium` |
| `create_reviewer(name, model_tier, **kw)` | `REVIEWER` | `capable` |
| `create_debugger(name, model_tier, **kw)` | `DEBUGGER` | `capable` |
| `create_coordinator(name, model_tier, **kw)` | `COORDINATOR` | `premium` |

### Pipeline Factories

#### create_research_pipeline

```python
def create_research_pipeline(
    topic: str = "",
    include_reviewer: bool = True,
) -> BaseWorkflow
```

Creates a sequential `researcher -> writer -> reviewer`
pipeline.

#### create_code_review_pipeline

```python
def create_code_review_pipeline() -> BaseWorkflow
```

Creates a sequential `security_analyzer -> debugger ->
reviewer` pipeline.

---

## Framework

**Module:** `attune.agent_factory.framework`

```python
class Framework(Enum):
    NATIVE = "native"       # No external deps
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    AUTOGEN = "autogen"
    HAYSTACK = "haystack"
```

### Methods

#### from_string

```python
@classmethod
def from_string(name: str) -> Framework
```

Case-insensitive conversion. Aliases: `"empathy"` ->
`NATIVE`, `"lang_graph"` -> `LANGGRAPH`, `"auto_gen"` ->
`AUTOGEN`.

**Raises:** `ValueError` if unknown.

### Module-Level Functions

```python
def detect_installed_frameworks() -> list[Framework]
def get_recommended_framework(use_case: str = "general") -> Framework
def get_framework_info(framework: Framework) -> dict[str, object]
```

---

## AgentRole

**Module:** `attune.agent_factory.base`

```python
class AgentRole(Enum):
    # Core
    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    WRITER = "writer"
    REVIEWER = "reviewer"
    EDITOR = "editor"
    EXECUTOR = "executor"

    # Specialized
    DEBUGGER = "debugger"
    SECURITY = "security"
    ARCHITECT = "architect"
    TESTER = "tester"
    DOCUMENTER = "documenter"

    # RAG
    RETRIEVER = "retriever"
    SUMMARIZER = "summarizer"
    ANSWERER = "answerer"

    # Custom
    CUSTOM = "custom"
```

---

## AgentCapability

**Module:** `attune.agent_factory.base`

```python
class AgentCapability(Enum):
    CODE_EXECUTION = "code_execution"
    TOOL_USE = "tool_use"
    WEB_SEARCH = "web_search"
    FILE_ACCESS = "file_access"
    MEMORY = "memory"
    RETRIEVAL = "retrieval"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
```

---

## AgentConfig

**Module:** `attune.agent_factory.base`

Dataclass for agent creation configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | required | Unique agent name |
| `role` | `AgentRole` | `CUSTOM` | Agent role |
| `description` | `str` | `""` | Description |
| `model_tier` | `str` | `"capable"` | `cheap`, `capable`, `premium` |
| `model_override` | `str \| None` | `None` | Specific model ID |
| `capabilities` | `list[AgentCapability]` | `[]` | Agent capabilities |
| `tools` | `list[Any]` | `[]` | Tools |
| `system_prompt` | `str \| None` | `None` | System prompt |
| `temperature` | `float` | `0.7` | LLM temperature |
| `max_tokens` | `int` | `4096` | Max response tokens |
| `empathy_level` | `int` | `4` | Empathy level (1-5) |
| `use_patterns` | `bool` | `True` | Use learned patterns |
| `track_costs` | `bool` | `True` | Track API costs |
| `memory_enabled` | `bool` | `True` | Enable memory |
| `memory_type` | `str` | `"conversation"` | `conversation`, `summary`, `vector` |
| `framework_options` | `dict` | `{}` | Framework-specific options |
| `resilience_enabled` | `bool` | `False` | Enable resilience wrapper |
| `circuit_breaker_threshold` | `int` | `3` | Failures before open |
| `retry_max_attempts` | `int` | `2` | Max retries |
| `timeout_seconds` | `float` | `30.0` | Invocation timeout |

---

## AgentGraphConfig

**Module:** `attune.agent_factory.base`

Dataclass for agent-graph creation configuration (named
`WorkflowConfig` before 16.0.0; renamed per spec
`models-workflows-layering` D5).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | required | Workflow name |
| `description` | `str` | `""` | Description |
| `mode` | `str` | `"sequential"` | `sequential`, `parallel`, `graph`, `conversation` |
| `max_iterations` | `int` | `10` | Max loop iterations |
| `timeout_seconds` | `int` | `300` | Workflow timeout |
| `state_schema` | `dict \| None` | `None` | State schema |
| `checkpointing` | `bool` | `True` | Enable checkpointing |
| `retry_on_error` | `bool` | `True` | Retry failed steps |
| `max_retries` | `int` | `3` | Max retries |
| `framework_options` | `dict` | `{}` | Framework-specific options |

---

## BaseAgent

**Module:** `attune.agent_factory.base`

Abstract base class for all framework-agnostic agents.

### Abstract Methods

```python
async def invoke(
    input_data: str | dict,
    context: dict | None = None,
) -> dict
```

Returns dict with at least `{"output": str, "metadata": dict}`.

```python
async def stream(
    input_data: str | dict,
    context: dict | None = None,
)
```

Async generator yielding response chunks.

### Concrete Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_tool` | `(tool: Any) -> None` | Add a tool |
| `get_conversation_history` | `() -> list[dict]` | Get history (copy) |
| `clear_history` | `() -> None` | Clear history |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Model ID or `"tier:<tier>"` |

---

## BaseAdapter

**Module:** `attune.agent_factory.base`

Abstract base class for framework adapters.

### Abstract Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `framework_name` (property) | `str` | Framework name |
| `is_available()` | `bool` | Whether framework is installed |
| `create_agent(config)` | `BaseAgent` | Create agent |
| `create_workflow(config, agents)` | `BaseWorkflow` | Create workflow |

### Concrete Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `create_tool(name, desc, func, schema)` | `Any` | Create tool (default: dict) |
| `get_model_for_tier(tier, provider)` | `str` | Resolve model ID from tier |

---

## ResilienceConfig

**Module:** `attune.agent_factory.resilient`

Dataclass for resilience pattern configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_circuit_breaker` | `bool` | `True` | Enable circuit breaker |
| `failure_threshold` | `int` | `3` | Failures before open |
| `reset_timeout` | `float` | `60.0` | Seconds before half-open |
| `half_open_max_calls` | `int` | `3` | Test calls in half-open |
| `enable_retry` | `bool` | `True` | Enable retry |
| `max_attempts` | `int` | `2` | Max retry attempts |
| `initial_delay` | `float` | `1.0` | Initial retry delay (s) |
| `backoff_factor` | `float` | `2.0` | Backoff multiplier |
| `max_delay` | `float` | `30.0` | Max delay between retries |
| `jitter` | `bool` | `True` | Add random jitter |
| `enable_timeout` | `bool` | `True` | Enable timeout |
| `timeout_seconds` | `float` | `30.0` | Timeout duration |
| `enable_fallback` | `bool` | `False` | Enable fallback |
| `fallback_value` | `Any` | `{"output": "...", ...}` | Fallback response |

### Class Methods

```python
@classmethod
def from_agent_config(config: AgentConfig) -> ResilienceConfig
```

---

## ResilientAgent

**Module:** `attune.agent_factory.resilient`

Wraps any `BaseAgent` with circuit breaker, retry, timeout,
and fallback patterns.

### Constructor

```python
ResilientAgent(
    agent: BaseAgent,
    config: ResilienceConfig | None = None,
)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `circuit_state` | `str \| None` | Circuit breaker state |

### Methods

| Method | Description |
|--------|-------------|
| `reset_circuit_breaker()` | Manual circuit breaker reset |

---

## Decorators

**Module:** `attune.agent_factory.decorators`

| Decorator | Parameters | Description |
|-----------|------------|-------------|
| `@safe_agent_operation(name)` | `operation_name: str` | Logging + error handling + audit trail |
| `@retry_on_failure(...)` | `max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,)` | Exponential backoff retry |
| `@log_performance(...)` | `threshold_seconds=1.0` | Log warning for slow operations |
| `@validate_input(...)` | `required_fields: list[str]` | Validate required dict fields |
| `@with_cost_tracking(...)` | `operation_type="agent_call"` | Track API costs |
| `@graceful_degradation(...)` | `fallback_value=None, log_level="warning"` | Return fallback on failure |

---

## Framework Adapters

All adapters are in `attune.agent_factory.adapters` and are
lazy-loaded to avoid importing unused dependencies.

| Adapter | Framework | Install |
|---------|-----------|---------|
| `NativeAdapter` | Empathy native | (included) |
| `LangChainAdapter` | LangChain | `pip install langchain langchain-anthropic` |
| `LangGraphAdapter` | LangGraph | `pip install langgraph langchain-anthropic` |
| `AutoGenAdapter` | AutoGen | `pip install pyautogen` |
| `HaystackAdapter` | Haystack | `pip install haystack-ai` |
| `WizardAdapter` | Attune wizards | (included) |

Access adapters via factory functions:

```python
from attune.agent_factory.adapters import (
    NativeAdapter,
    get_langchain_adapter,
    get_langgraph_adapter,
    get_autogen_adapter,
    get_haystack_adapter,
)
```
