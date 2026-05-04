---
type: reference
feature: release-prep
depth: reference
generated_at: 2026-05-04T02:27:19.978842+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Release prep reference

Run preflight checks across your project before publishing. Assesses health, security, changelog, dependencies, and version consistency, then provides a go/no-go recommendation.

## Classes

| Class | Description |
|-------|-------------|
| `ReleaseAgent` | Base agent with progressive tier escalation from cheap to premium models |
| `TestCoverageAgent` | Runs pytest with coverage analysis and parses results |
| `DocumentationAgent` | Validates docstring coverage, README currency, and changelog presence |
| `CodeQualityAgent` | Runs linting, checks type hints, and measures code complexity |
| `SecurityAuditorAgent` | Analyzes security vulnerabilities and classifies findings by severity |
| `Tier` | Model tier enumeration for progressive escalation |
| `ReleaseAgentResult` | Individual agent execution result with findings and metrics |
| `QualityGate` | Release readiness threshold with pass/fail status |
| `ReleaseReadinessReport` | Consolidated assessment with go/no-go recommendation |
| `ReleasePrepTeam` | Orchestrates parallel execution of specialized release agents |
| `ReleasePrepTeamWorkflow` | CLI-integrated workflow wrapper for release preparation |
| `ReleasePreparationWorkflow` | Quality gate workflow powered by agent subteams |

## ReleaseAgent

Base agent with progressive tier escalation.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `agent_id: str, role: str, redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | `None` | Initializes release agent with role and optional state management |
| `process` | `codebase_path: str = '.'` | `ReleaseAgentResult` | Processes codebase and returns analysis results |

## TestCoverageAgent

Runs pytest --cov and parses coverage report.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | `None` | Initializes coverage agent with optional state management |

## DocumentationAgent

Checks docstring coverage, README currency, and CHANGELOG presence.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | `None` | Initializes documentation agent with optional state management |

## CodeQualityAgent

Runs ruff, checks type hints and complexity.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | `None` | Initializes code quality agent with optional state management |

## ReleaseAgentResult

Result from an individual release agent.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_id` | `str` | | Agent identifier |
| `agent_role` | `str` | | Agent's specialized role |
| `success` | `bool` | | Whether agent execution succeeded |
| `tier_used` | `Tier` | | Model tier used for analysis |
| `findings` | `dict[str, Any]` | `{}` | Structured findings from agent analysis |
| `score` | `float` | `0.0` | Quality score from 0-100 |
| `confidence` | `float` | `0.0` | Confidence level in results |
| `cost` | `float` | `0.0` | Execution cost in credits |
| `execution_time_ms` | `float` | `0.0` | Processing time in milliseconds |
| `escalated` | `bool` | `False` | Whether agent escalated to higher tier |

## QualityGate

Quality gate threshold for release readiness.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Gate name identifier |
| `threshold` | `float` | | Required minimum score |
| `actual` | `float` | `0.0` | Measured score |
| `passed` | `bool` | `False` | Whether gate passed |
| `critical` | `bool` | `True` | Whether failure blocks release |
| `message` | `str` | `''` | Status message |

## ReleaseReadinessReport

Aggregated release readiness assessment.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `to_dict` | | `dict[str, Any]` | Converts report to dictionary format |
| `format_console_output` | | `str` | Formats report for terminal display |

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `approved` | `bool` | | Whether release is approved |
| `confidence` | `str` | | Confidence level in assessment |
| `quality_gates` | `list[QualityGate]` | `[]` | Individual gate results |
| `agent_results` | `list[ReleaseAgentResult]` | `[]` | Results from each agent |
| `blockers` | `list[str]` | `[]` | Critical issues blocking release |
| `warnings` | `list[str]` | `[]` | Non-blocking concerns |
| `summary` | `str` | `''` | Executive summary |
| `timestamp` | `str` | current ISO time | Assessment timestamp |
| `total_duration` | `float` | `0.0` | Total execution time |
| `total_cost` | `float` | `0.0` | Total execution cost |

## ReleasePrepTeam

Coordinates parallel execution of release preparation agents.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `quality_gates: dict[str, Any] \| None = None, redis_url: str \| None = None` | `None` | Initializes team with quality gates and Redis connection |
| `get_total_cost` | | `float` | Calculates total execution cost across agents |
| `assess_readiness` | `codebase_path: str = '.'` | `ReleaseReadinessReport` | Runs full release assessment |

## ReleasePrepTeamWorkflow

Workflow wrapper that integrates ReleasePrepTeam with the CLI registry.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `quality_gates: dict[str, float] \| None = None, **kwargs: Any` | `None` | Initializes workflow with quality gates |
| `run_stage` | `stage_name: str, tier: ModelTier, input_data: Any` | `Any` | Executes specific workflow stage |
| `execute` | `path: str = '.', context: dict[str, Any] \| None = None, **kwargs: Any` | `ReleaseReadinessReport` | Runs complete release preparation workflow |

## ReleasePreparationWorkflow

Pre-release quality gate workflow powered by Agent SDK subagents.

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_stage` | `stage_name: str, tier: ModelTier, input_data: Any` | `Any` | Executes workflow stage with specified model tier |
| `execute` | `path: str = '.', context: dict[str, Any] \| None = None, **kwargs: Any` | `ReleaseReadinessReport` | Runs full preparation workflow |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `_SUBAGENT_NAMES` | `['health-checker', 'security-scanner', 'changelog-generator', 'release-assessor']` | Specialized agent roles for release preparation |
