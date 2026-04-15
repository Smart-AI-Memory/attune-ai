---
type: reference
feature: release-prep
depth: reference
generated_at: 2026-04-14T14:49:52.038519+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release Prep reference

## Workflow classes

| Class | Description | Methods |
|-------|-------------|---------|
| `ReleasePreparationWorkflow` | Pre-release quality gate workflow powered by Agent SDK subagents | `execute(**kwargs: Any) -> WorkflowResult` |

## Agent classes

| Class | Description | Parameters | Returns |
|-------|-------------|------------|---------|
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation | `agent_id: str, role: str, redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | |
| | | `codebase_path: str = '.'` (process) | `ReleaseAgentResult` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | |
| `SecurityAuditorAgent` | Analyzes bandit output and classifies vulnerabilities by severity | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | |

## Team coordination classes

| Class | Description | Parameters | Returns |
|-------|-------------|------------|---------|
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents | `quality_gates: dict[str, Any] \| None = None, redis_url: str \| None = None` | |
| | `get_total_cost()` | | `float` |
| | `assess_readiness(codebase_path: str = '.')` | | `ReleaseReadinessReport` |

## Data model classes

### ReleaseAgentResult

| Field | Type | Default |
|-------|------|---------|
| `agent_id` | `str` | |
| `agent_role` | `str` | |
| `success` | `bool` | |
| `tier_used` | `Tier` | |
| `findings` | `dict[str, Any]` | `field(default_factory=dict)` |
| `score` | `float` | `0.0` |
| `confidence` | `float` | `0.0` |
| `cost` | `float` | `0.0` |
| `execution_time_ms` | `float` | `0.0` |
| `escalated` | `bool` | `False` |

### QualityGate

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | |
| `threshold` | `float` | |
| `actual` | `float` | `0.0` |
| `passed` | `bool` | `False` |
| `critical` | `bool` | `True` |
| `message` | `str` | `''` |

### ReleaseReadinessReport

| Field | Type | Default |
|-------|------|---------|
| `approved` | `bool` | |
| `confidence` | `str` | |
| `quality_gates` | `list[QualityGate]` | `field(default_factory=list)` |
| `agent_results` | `list[ReleaseAgentResult]` | `field(default_factory=list)` |
| `blockers` | `list[str]` | `field(default_factory=list)` |
| `warnings` | `list[str]` | `field(default_factory=list)` |
| `summary` | `str` | `''` |
| `timestamp` | `str` | `field(default_factory=lambda: datetime.now().isoformat())` |
| `total_duration` | `float` | `0.0` |
| `total_cost` | `float` | `0.0` |

### ReleaseReadinessReport methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Converts report to dictionary format |
| `format_console_output()` | `str` | Formats report for console display |

## Constants

| Name | Values |
|------|--------|
| `SUBAGENT_NAMES` | `health-checker`, `security-scanner`, `changelog-generator`, `release-assessor` |
