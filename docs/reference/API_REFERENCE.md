# Attune AI API Reference

**Version:** 11.1.0
**License:** Apache License 2.0
**Copyright:** 2025-2026 Smart AI Memory, LLC

---

## Table of Contents

- [Overview](#overview)
- [Core Framework](#core-framework)
  - [Exceptions](#exceptions)
- [Configuration](#configuration)
  - [AttuneConfig](#attuneconfig)
  - [ConfigLoader](#configloader)
  - [ModelTier](#modeltier)
- [Memory System](#memory-system)
  - [UnifiedMemory](#unifiedmemory)
  - [Classification](#classification)
  - [AccessTier](#accesstier)
  - [TTLStrategy](#ttlstrategy)
  - [MemoryBackend Protocol](#memorybackend-protocol)
  - [RedisShortTermMemory](#redisshorttermmemory)
  - [LongTermMemory](#longtermmemory)
- [Workflows](#workflows)
  - [BaseWorkflow](#baseworkflow)
  - [WorkflowResult](#workflowresult)
  - [CostReport](#costreport)
  - [Available Workflows](#available-workflows)
- [Models & Execution](#models-execution)
  - [ModelRegistry](#modelregistry)
  - [ModelInfo](#modelinfo)
  - [LLMExecutor Protocol](#llmexecutor-protocol)
  - [LLMResponse](#llmresponse)
  - [CircuitBreaker](#circuitbreaker)
  - [ResilientExecutor](#resilientexecutor)
  - [AdaptiveModelRouter](#adaptivemodelrouter)
- [MCP Server](#mcp-server)
  - [EmpathyMCPServer](#empathymcpserver)
  - [Tool Schemas](#tool-schemas)
  - [RateLimiter](#ratelimiter)
- [Orchestration](#orchestration)
  - [AgentTeam](#agentteam)
  - [AgentTemplate](#agenttemplate)
  - [ExecutionStrategy](#executionstrategy)
- [Meta-Workflows](#meta-workflows)
  - [MetaWorkflow](#metaworkflow)
  - [SocraticFormEngine](#socraticformengine)
  - [TemplateRegistry](#templateregistry)
- [Agents](#agents)
  - [AgentStateStore](#agentstatestore)
  - [ReleaseAgent](#releaseagent)
- [Wizards](#wizards)
  - [BaseWizard](#basewizard)
  - [WizardRegistry](#wizardregistry)
  - [ConfigDrivenWizard](#configdrivenwizard)
  - [TaskDecomposer](#taskdecomposer)
- [Telemetry](#telemetry)
  - [UsageTracker](#usagetracker)
  - [FeedbackLoop](#feedbackloop)
  - [ApprovalGate](#approvalgate)
  - [EventStreamer](#eventstreamer)
- [Monitoring](#monitoring)
  - [AlertConfig](#alertconfig)
  - [AlertEvent](#alertevent)
- [Project Index](#project-index)
  - [ProjectIndex](#projectindex)
  - [FileRecord](#filerecord)
  - [ProjectSummary](#projectsummary)
- [Plugin System](#plugin-system)
  - [BasePlugin](#baseplugin)
  - [PluginRegistry](#pluginregistry)
- [Security](#security)
  - [_validate_file_path](#_validate_file_path)
  - [SecretsDetector](#secretsdetector)
  - [PIIScrubber](#piiscrubber)
- [Voice Layer](#voice-layer)
  - [format_output](#format_output)
  - [format_error](#format_error)

---

## Overview

Attune AI is an AI Workflow-harness for Claude Code. It
provides cost-optimized workflows, multi-agent orchestration,
and a unified memory system.

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Workflows** | SDK-native multi-stage pipelines with 3-tier model routing |
| **Memory** | Two-tier system: Redis (short-term) + persistent (long-term) |
| **Orchestration** | Dynamic agent team composition based on task requirements |
| **MCP Server** | Model Context Protocol integration for Claude Code |
| **Wizards** | Interactive multi-step guided flows with XML task decomposition |

### Installation

```bash
pip install attune-ai                # Core
pip install 'attune-ai[developer]'   # Developer extras
pip install attune-ai       # Redis-backed memory + AMS plugin
```

---

## Core Framework

### Exceptions

`attune.exceptions`

| Exception | Base | Description |
|-----------|------|-------------|
| `EmpathyFrameworkError` | `Exception` | Base exception |
| `ValidationError` | `EmpathyFrameworkError` | Input validation failure |
| `PatternNotFoundError` | `EmpathyFrameworkError` | Pattern lookup miss |
| `EmpathyLevelError` | `EmpathyFrameworkError` | Invalid empathy level |
| `TrustThresholdError` | `EmpathyFrameworkError` | Trust check failure |
| `ConfidenceThresholdError` | `EmpathyFrameworkError` | Below confidence threshold |

---

## Configuration

### AttuneConfig

`attune.config.AttuneConfig`

Main configuration dataclass. Backward-compatible alias:
`EmpathyConfig`.

```python
from attune.config import AttuneConfig, load_config

config = load_config()
```

#### Key Functions

```python
load_config() -> AttuneConfig
```

---

### ConfigLoader

`attune.config.loader.ConfigLoader`

Discovers and loads configuration from YAML/JSON files.

```python
from attune.config.loader import ConfigLoader

loader = ConfigLoader(config_path="attune.yml")
config = loader.load()
```

| Method | Returns | Description |
|--------|---------|-------------|
| `discover_config_path()` | `Path \| None` | Auto-discover config file |
| `load()` | `UnifiedConfig` | Load and validate config |

---

### ModelTier

`attune.config.ModelTier`

Enum for model cost tiers used by workflow routing.

| Value | Description |
|-------|-------------|
| `CHEAP` | Haiku — summarization, classification |
| `CAPABLE` | Sonnet — analysis, code generation |
| `PREMIUM` | Opus — synthesis, architecture |

---

## Memory System

### UnifiedMemory

`attune.memory.UnifiedMemory`

Main API for the two-tier memory system (Redis short-term +
persistent long-term).

```python
from attune.memory import UnifiedMemory, Classification

memory = UnifiedMemory(user_id="dev-1")

# Short-term (Redis-backed with TTL)
memory.stash("context", {"topic": "auth"}, ttl=3600)
value = memory.retrieve("context")

# Long-term (persistent with classification)
result = memory.persist_pattern(
    content="Auth patterns use JWT",
    pattern_type="technique",
    classification=Classification.INTERNAL,
)
pattern = memory.recall_pattern(result["pattern_id"])

# Staging workflow
staged_id = memory.stage_pattern({"content": "draft"})
memory.promote_pattern(staged_id)
```

#### Constructor

```python
UnifiedMemory(
    user_id: str,
    environment: Environment = Environment.PRODUCTION
)
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `stash(key, value, ttl=None)` | `bool` | Store short-term value |
| `retrieve(key)` | `Any \| None` | Retrieve short-term value |
| `persist_pattern(content, pattern_type, classification)` | `dict` | Store long-term pattern |
| `recall_pattern(pattern_id)` | `SecurePattern \| None` | Retrieve long-term pattern |
| `stage_pattern(pattern)` | `str` | Stage for review |
| `promote_pattern(staged_id)` | `bool` | Promote staged to long-term |

---

### Classification

`attune.memory.Classification`

| Value | Description |
|-------|-------------|
| `PUBLIC` | No access restriction |
| `INTERNAL` | Team-visible only |
| `SENSITIVE` | Encrypted at rest |

---

### AccessTier

`attune.memory.AccessTier`

| Value | Description |
|-------|-------------|
| `OBSERVER` | Read-only |
| `CONTRIBUTOR` | Read + write |
| `VALIDATOR` | Read + write + approve |
| `STEWARD` | Full admin |

---

### TTLStrategy

`attune.memory.TTLStrategy`

Pre-defined TTL durations for short-term memory.

| Value | TTL | Use Case |
|-------|-----|----------|
| `WORKING_RESULTS` | 3600s | Intermediate workflow results |
| `STAGED_PATTERNS` | 86400s | Patterns awaiting promotion |

---

### MemoryBackend Protocol

`attune.memory.backend.MemoryBackend`

Formal interface for implementing custom memory backends.

```python
class MemoryBackend(Protocol):
    def stash(self, key: str, value: Any,
              ttl: int | None = None,
              agent_id: str | None = None) -> bool: ...
    def retrieve(self, key: str,
                 agent_id: str | None = None) -> Any | None: ...
    def search(self, pattern: str) -> list[tuple]: ...
    def forget(self, key: str,
               agent_id: str | None = None) -> bool: ...
```

---

### RedisShortTermMemory

`attune.memory.RedisShortTermMemory`

Redis-backed short-term memory with TTL expiration.

Requires: `pip install attune-ai`

---

### LongTermMemory

`attune.memory.LongTermMemory`

Persistent pattern storage with classification and
encryption support.

---

## Workflows

### BaseWorkflow

`attune.workflows.base.BaseWorkflow`

Abstract base class for all workflows. Provides mixins for
execution, cost tracking, caching, and verification.

All concrete workflows implement `async execute(**kwargs)`.

```python
from attune.workflows import SecurityAuditWorkflow

workflow = SecurityAuditWorkflow()
result = await workflow.execute(path="src/")
```

**Class attributes** (set by subclasses, not constructor
params):

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Workflow identifier |
| `description` | `str` | Human-readable description |
| `stages` | `list[str]` | Ordered stage names |
| `tier_map` | `dict[str, ModelTier]` | Stage-to-tier mapping |

---

### WorkflowResult

`attune.workflows.data_classes.WorkflowResult`

Returned by all workflow `execute()` calls.

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether workflow completed |
| `output` | `Any` | Workflow-specific output |
| `error` | `str \| None` | Error message if failed |
| `cost_report` | `CostReport` | Cost breakdown |
| `duration_ms` | `int` | Total execution time |
| `quality_score` | `float` | Quality assessment |
| `metadata` | `dict` | Additional metadata |

---

### CostReport

`attune.workflows.data_classes.CostReport`

| Field | Type | Description |
|-------|------|-------------|
| `total_cost` | `float` | Total API cost |
| `savings_percent` | `float` | Cost savings vs single-tier |
| `cost_by_tier` | `dict[str, float]` | Breakdown by tier |
| `token_counts` | `dict[str, int]` | Token usage by tier |

---

### Available Workflows

All workflows are SDK-native (Agent SDK powered). Run via
CLI or programmatic API:

```bash
attune workflow run <name> --path <target>
```

| Workflow | Description |
|----------|-------------|
| `bug-predict` | Predict likely bug locations with 3 subagents |
| `code-review` | Multi-pass code review with 4 subagents |
| `deep-review` | Deep review: security, quality, test gaps |
| `dependency-check` | Dependency vulnerability audit |
| `doc-audit` | Audit docs for staleness and broken links |
| `doc-gen` | Generate documentation from source code |
| `doc-orchestrator` | End-to-end doc-audit + doc-gen pipeline |
| `perf-audit` | Performance audit with 3 subagents |
| `rag-code-gen` | RAG-grounded code generation with citation-per-claim (requires `[rag]` extra) |
| `refactor-plan` | Prioritize tech debt with subagents |
| `release-prep` | Release readiness assessment |
| `research-synthesis` | Multi-source research synthesis |
| `security-audit` | Security audit with 4 subagents |
| `simplify-code` | Simplify over-engineered code |
| `test-audit` | Autonomous test coverage audit |
| `test-gen` | Test generation with 3 subagents |

---

## Models & Execution

### ModelRegistry

`attune.models.registry.ModelRegistry`

Central registry of available LLM models.

```python
from attune.models import MODEL_REGISTRY

model = MODEL_REGISTRY.get_model("claude-sonnet-5")
models = MODEL_REGISTRY.list_models(tier="capable")
```

| Method | Returns | Description |
|--------|---------|-------------|
| `get_model(model_id)` | `ModelInfo \| None` | Look up model |
| `list_models(tier=None)` | `list[ModelInfo]` | List models |
| `register_model(info)` | `bool` | Register custom model |

---

### ModelInfo

`attune.models.registry.ModelInfo`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Model identifier |
| `provider` | `str` | Provider name |
| `tier` | `str` | Cost tier |
| `input_cost_per_million` | `float` | Input token cost |
| `output_cost_per_million` | `float` | Output token cost |
| `max_tokens` | `int` | Max output tokens |
| `supports_vision` | `bool` | Vision capability |
| `supports_tools` | `bool` | Tool use capability |

---

### LLMExecutor Protocol

`attune.models.executor.LLMExecutor`

Protocol for LLM execution backends.

```python
class LLMExecutor(Protocol):
    async def execute(
        self,
        prompt: str,
        context: ExecutionContext
    ) -> LLMResponse: ...
```

---

### LLMResponse

`attune.models.executor.LLMResponse`

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Response text |
| `model_id` | `str` | Model used |
| `provider` | `str` | Provider name |
| `tier` | `str` | Cost tier |
| `tokens_input` | `int` | Input tokens |
| `tokens_output` | `int` | Output tokens |
| `cost_estimate` | `float` | Estimated cost |
| `latency_ms` | `int` | Response latency |
| `metadata` | `dict` | Additional data |

---

### CircuitBreaker

`attune.models.circuit_breaker.CircuitBreaker`

Fault tolerance pattern for LLM calls.

```python
from attune.models.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60
)
result = breaker.call(my_function, *args)
```

---

### ResilientExecutor

`attune.models.resilient_executor.ResilientExecutor`

Combines circuit breaker, retry, and fallback policies.

---

### AdaptiveModelRouter

`attune.models.adaptive_routing.AdaptiveModelRouter`

Routes requests to the appropriate model tier based on
task complexity and historical performance.

---

## MCP Server

### EmpathyMCPServer

`attune.mcp.server.EmpathyMCPServer`

Model Context Protocol server exposing workflows, memory,
and agents as MCP tools for Claude Code.

```python
from attune.mcp import create_server

server = create_server()
```

---

### Tool Schemas

`attune.mcp.tool_schemas`

Functions that return tool schema definitions:

| Function | Description |
|----------|-------------|
| `get_workflow_tools()` | Workflow execution tools |
| `get_memory_tools()` | Memory operation tools |
| `get_prompts()` | Available prompt templates |
| `get_resources()` | Exposed resources |

---

### RateLimiter

`attune.mcp.rate_limiter.RateLimiter`

Request rate limiting for MCP tool calls.

---

## Orchestration

### AgentTeam

`attune.agents.team.AgentTeam`

Fan-out a target across workflow agents, then gate the results.
Each agent runs its workflow; each gate asserts a minimum score.

```python
import asyncio
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent("security-audit", SecurityAuditWorkflow, files=["src/"]),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
        GateSpec("Security", "security-audit", 80.0),
    ],
)
report = asyncio.run(team.run(["src/"]))
print(report.passed, report.blockers, report.warnings, report.cost)
```

| Symbol | Description |
|--------|-------------|
| `WorkflowAgent(key, workflow_cls, *, files=None)` | One workflow agent |
| `GateSpec(name, agent_key, threshold, critical=True)` | Score gate |
| `AgentTeam(agents, gates)` | Fan-out team with gates |
| `team.run(target)` | Async; `target` is a path or `list[str]` |

`team.run(...)` returns a `TeamReport(passed, gates, results,
blockers, warnings, cost)`.

---

### AgentTemplate

`attune.orchestration.AgentTemplate`

Template for agent creation. 14 built-in templates.

| Field | Type | Description |
|-------|------|-------------|
| `role` | `str` | Agent role name |
| `capabilities` | `list[AgentCapability]` | What it can do |
| `description` | `str` | Human description |
| `tier` | `str` | Model tier (cheap/capable/premium) |

#### Registry Functions

```python
from attune.orchestration import (
    get_template,
    get_all_templates,
    get_templates_by_capability,
    get_templates_by_tier,
    register_custom_template,
)

templates = get_all_templates()  # 14 built-in templates
security = get_templates_by_capability("vulnerability_scan")
```

---

### ExecutionStrategy

`attune.orchestration.ExecutionStrategy`

Protocol defining how agents execute. Implementations:

| Strategy | Description |
|----------|-------------|
| `ToolEnhancedStrategy` | Agents use tool calling |
| `DelegationChainStrategy` | Sequential delegation |
| `PromptCachedSequentialStrategy` | Cache-optimized sequential |

---

## Meta-Workflows

### MetaWorkflow

`attune.meta_workflows.MetaWorkflow`

Dynamic agent team generation with Socratic discovery.

```python
from attune.meta_workflows import MetaWorkflow

meta = MetaWorkflow()
result = meta.execute(
    task="Generate tests for auth module",
    context={"path": "src/auth/"}
)
```

---

### SocraticFormEngine

`attune.meta_workflows.SocraticFormEngine`

Interactive multi-step questioning engine for workflow
scoping.

---

### TemplateRegistry

`attune.meta_workflows.TemplateRegistry`

Registry of workflow templates for auto-detection.

```python
from attune.meta_workflows import (
    auto_detect_template,
    detect_and_suggest,
)

template = auto_detect_template("review code for bugs")
suggestions = detect_and_suggest("security audit")
```

---

## Agents

### AgentStateStore

`attune.agents.AgentStateStore`

Persistent state storage for running agents.

Related: `AgentRecoveryManager`, `AgentExecutionRecord`,
`AgentStateRecord`.

---

### ReleaseAgent

`attune.agents.ReleaseAgent`

Automated release preparation agent.

Related: `ReleasePrepTeam`, `ReleasePrepTeamWorkflow`,
`ReleaseReadinessReport`.

---

## Wizards

### BaseWizard

`attune.wizards.BaseWizard`

Abstract base for interactive multi-step wizards.

```python
from attune.wizards import BaseWizard

class MyWizard(BaseWizard):
    async def execute_steps(
        self, form_response: FormResponse
    ) -> dict:
        # Implementation
        ...
```

#### Constructor

```python
BaseWizard(ask_user_callback: AskUserQuestionCallback, ...)
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `async run(inputs)` | `WizardResult` | Run the wizard |
| `async execute_steps(form_response)` | `dict` | Abstract — implement steps |

---

### WizardRegistry

`attune.wizards.WizardRegistry`

Note: `list_wizards()` is a module-level function, not a
class method.

```python
from attune.wizards import list_wizards, get_wizard

wizards = list_wizards()
wizard_class = get_wizard("security-coach")
```

| Function | Returns | Description |
|----------|---------|-------------|
| `list_wizards()` | `list[WizardConfig]` | All registered wizards |
| `get_wizard(id)` | `type[BaseWizard]` | Look up wizard class |
| `register_wizard(config, cls)` | `bool` | Register custom wizard |
| `save_custom_wizard(config, path)` | `bool` | Save wizard to YAML |
| `delete_custom_wizard(id)` | `bool` | Remove custom wizard |

---

### ConfigDrivenWizard

`attune.wizards.ConfigDrivenWizard`

Wizard instantiated from a YAML configuration file.

```python
from attune.wizards import ConfigDrivenWizard

wizard = ConfigDrivenWizard.from_yaml("my_wizard.yml")
result = await wizard.run(inputs={})
```

---

### TaskDecomposer

`attune.wizards.TaskDecomposer`

XML-based task decomposition for complex multi-step work.

```python
from attune.wizards import TaskDecomposer

decomposer = TaskDecomposer()
tasks = decomposer.decompose(
    "Migrate auth from sessions to JWT"
)
# Returns list[DecomposedTask]
```

---

## Telemetry

### UsageTracker

`attune.telemetry.UsageTracker`

Privacy-first, local-only usage tracking.

```python
from attune.telemetry import UsageTracker

tracker = UsageTracker()
tracker.log_llm_call(
    model="claude-sonnet-5",
    input_tokens=1500,
    output_tokens=800,
    cost=0.012,
)
stats = tracker.get_stats(days=30)
today_cost = tracker.get_today_cost()
```

#### Constructor

```python
UsageTracker(
    telemetry_dir: Path | None = None,
    retention_days: int = 90,
    max_file_size_mb: int = 10,
    buffer_size: int = 50,
)
```

---

### FeedbackLoop

`attune.telemetry.FeedbackLoop`

Agent-to-LLM quality feedback for tier optimization.

```python
from attune.telemetry import FeedbackLoop, FeedbackEntry

loop = FeedbackLoop()
loop.submit_feedback(FeedbackEntry(
    workflow_name="code-review",
    quality_score=0.92,
    latency_ms=4500,
    cost_estimate=0.08,
))
recommendation = loop.get_tier_recommendation()
```

---

### ApprovalGate

`attune.telemetry.ApprovalGate`

Human-in-the-loop approval workflow.

```python
from attune.telemetry import ApprovalGate

gate = ApprovalGate(
    workflow_name="release-prep",
    requires_approval=True,
    approval_timeout=3600,
)
request = gate.request_approval(data={"version": "5.3.2"})
gate.respond_to_request(
    request.id,
    ApprovalResponse(approved=True, comment="LGTM",
                     responder="patrick"),
)
```

---

### EventStreamer

`attune.telemetry.EventStreamer`

Real-time event streaming via Redis Streams.

Requires: `pip install attune-ai`

---

## Monitoring

### AlertConfig

`attune.monitoring.AlertConfig`

| Field | Type | Description |
|-------|------|-------------|
| `metric` | `AlertMetric` | What to monitor |
| `threshold` | `float` | Trigger threshold |
| `channel` | `AlertChannel` | Notification channel |
| `severity` | `AlertSeverity` | Alert severity |

**Enums:**

| Enum | Values |
|------|--------|
| `AlertMetric` | `DAILY_COST`, `ERROR_RATE`, `AVG_LATENCY`, `TOKEN_USAGE` |
| `AlertChannel` | `WEBHOOK`, `EMAIL`, `VSCODE_OUTPUT`, `STDOUT` |
| `AlertSeverity` | `INFO`, `WARNING`, `CRITICAL` |

---

### AlertEvent

`attune.monitoring.AlertEvent`

Triggered alert instance with `config_id`, `metric`,
`value`, `timestamp`, and `severity`.

---

## Project Index

### ProjectIndex

`attune.project_index.ProjectIndex`

Codebase intelligence layer for tracking file metadata.

```python
from attune.project_index import ProjectIndex

index = ProjectIndex(project_root=".")
summary = index.scan()
record = index.get_file_record("src/auth.py")
```

#### Constructor

```python
ProjectIndex(
    project_root: str,
    config: IndexConfig | None = None,
    redis_client: Any | None = None,
    workers: int | None = None,
    use_parallel: bool = True,
)
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `scan()` | `ProjectSummary` | Scan entire project |
| `get_file_record(path)` | `FileRecord \| None` | Look up file |
| `query_files(pattern)` | `Iterator[FileRecord]` | Search files |
| `update_file_metadata(path, meta)` | `bool` | Update metadata |
| `persist()` | `None` | Save index to disk |

---

### FileRecord

`attune.project_index.FileRecord`

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | File path |
| `file_type` | `str` | Detected file type |
| `last_modified` | `datetime` | Last modification |
| `lines_of_code` | `int` | LOC count |
| `test_coverage` | `float \| None` | Coverage percentage |
| `dependencies` | `list[str]` | Import dependencies |
| `is_test` | `bool` | Whether it's a test file |

---

### ProjectSummary

`attune.project_index.ProjectSummary`

| Field | Type | Description |
|-------|------|-------------|
| `total_files` | `int` | Files scanned |
| `total_lines` | `int` | Total LOC |
| `average_coverage` | `float` | Mean coverage |
| `files_without_tests` | `list[str]` | Untested files |
| `stale_files` | `list[str]` | Stale files |
| `key_dependencies` | `list[str]` | Top dependencies |

---

## Plugin System

### BasePlugin

`attune.plugins.BasePlugin`

Abstract base class for extending Attune AI.

```python
from attune.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="my-plugin",
        version="1.0.0",
        domain="custom",
        description="My custom plugin",
        author="Dev",
        license="MIT",
        requires_core_version=">=5.0.0",
    )
```

---

### PluginRegistry

`attune.plugins.PluginRegistry`

```python
from attune.plugins import get_global_registry

registry = get_global_registry()
registry.register_plugin(MyPlugin)
plugins = registry.list_plugins()
```

| Method | Returns | Description |
|--------|---------|-------------|
| `register_plugin(cls)` | `bool` | Register plugin |
| `get_plugin(id)` | `BasePlugin \| None` | Look up plugin |
| `list_plugins()` | `list[BasePlugin]` | All plugins |
| `discover_plugins()` | `list[type[BasePlugin]]` | Auto-discover |

---

## Security

### _validate_file_path

`attune.security.path_validation._validate_file_path`

Validates file paths to prevent path traversal (CWE-22).
Used in 77+ files across the codebase.

```python
from attune.security.path_validation import _validate_file_path

validated = _validate_file_path(
    path="output.json",
    allowed_dir="./data"
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` | Path to validate |
| `allowed_dir` | `str \| None` | Restrict to directory |

**Returns:** `Path` — resolved, validated path.

**Raises:** `ValueError` for null bytes, system directories,
or paths outside `allowed_dir`.

---

### SecretsDetector

`attune.security.SecretsDetector`

Detects hardcoded secrets (API keys, passwords, tokens).

```python
from attune.security import SecretsDetector, detect_secrets

findings = detect_secrets(file_path="config.py")
```

---

### PIIScrubber

`attune.security.PIIScrubber`

Scrubs personally identifiable information from text.

---

## Voice Layer

### format_output

`attune.voice.format_output`

All user-facing output passes through this function for
consistent personality and formatting.

```python
from attune.voice import format_output

text = format_output(
    workflow_name="security-audit",
    result=workflow_result,
    compact=False,
)
```

---

### format_error

`attune.voice.format_error`

Format error messages with personality and next-step
guidance.

```python
from attune.voice import format_error

msg = format_error(
    message="File not found: auth.py",
    context="workflow",
)
```

---

## Module Summary

| Module | Purpose | Key Export |
|--------|---------|-----------|
| `attune` | Core framework | `AttuneConfig` |
| `attune.config` | Configuration | `AttuneConfig`, `load_config` |
| `attune.memory` | Two-tier memory | `UnifiedMemory` |
| `attune.workflows` | SDK-native pipelines | `BaseWorkflow`, 15 workflows |
| `attune.models` | Model registry + execution | `MODEL_REGISTRY`, `LLMResponse` |
| `attune.mcp` | MCP server for Claude Code | `create_server` |
| `attune.orchestration` | Agent templates + strategies | `get_all_templates` |
| `attune.meta_workflows` | Socratic discovery | `MetaWorkflow` |
| `attune.agents` | State + release agents | `AgentStateStore` |
| `attune.wizards` | Interactive wizards | `list_wizards`, `BaseWizard` |
| `attune.telemetry` | Privacy-first tracking | `UsageTracker` |
| `attune.monitoring` | Alerts + observability | `AlertConfig` |
| `attune.project_index` | Codebase intelligence | `ProjectIndex` |
| `attune.plugins` | Extension system | `BasePlugin` |
| `attune.security` | Path + secret validation | `_validate_file_path` |
| `attune.voice` | Output formatting | `format_output` |

---

**Version:** 11.1.0 | **License:** Apache 2.0
**Repo:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
