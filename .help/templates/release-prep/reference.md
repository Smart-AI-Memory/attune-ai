---
type: reference
name: release-prep-reference
feature: release-prep
depth: reference
generated_at: 2026-06-02T10:56:02.698216+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Release Prep reference

Run pre-release health checks, security audits, changelog validation, and version verification to produce a go/no-go readiness assessment.

## Classes

| Class | Description |
|-------|-------------|
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation. |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report. |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity. |
| `Tier` | Model tier for progressive escalation. |
| `ReleaseAgentResult` | Result from an individual release agent. |
| `QualityGate` | Quality gate threshold for release readiness. |
| `ReleaseReadinessReport` | Aggregated release readiness assessment. |
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents. |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates ReleasePrepTeam with the CLI registry. |
| `SecurityAuditorAgent` | Analyzes bandit output and classifies vulnerabilities by severity. |
| `ReleasePreparationWorkflow` | Pre-release quality gate workflow powered by Agent SDK subagents. |

---

## `ReleaseAgent`

Base agent with CHEAP -> CAPABLE -> PREMIUM escalation. Subclass this to implement a specialized release check.

### Constructor

| Parameters | Type | Default |
|------------|------|---------|
| `agent_id` | `str` | — |
| `role` | `str` | — |
| `redis_client` | `Any \| None` | `None` |
| `state_store` | `AgentStateStore \| None` | `None` |

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `process` | `codebase_path: str = '.'` | `ReleaseAgentResult` | Runs this agent's check against the codebase at `codebase_path`. |

---

## `TestCoverageAgent`

Runs pytest --cov and parses the coverage report.

### Constructor

| Parameters | Type | Default |
|------------|------|---------|
| `redis_client` | `Any \| None` | `None` |
| `state_store` | `AgentStateStore \| None` | `None` |

---

## `DocumentationAgent`

Checks docstring coverage, README currency, and CHANGELOG presence.

### Constructor

| Parameters | Type | Default |
|------------|------|---------|
| `redis_client` | `Any \| None` | `None` |
| `state_store` | `AgentStateStore \| None` | `None` |

---

## `CodeQualityAgent`

Runs ruff, checks type hints and complexity.

### Constructor

| Parameters | Type | Default |
|------------|------|---------|
| `redis_client` | `Any \| None` | `None` |
| `state_store` | `AgentStateStore \| None` | `None` |

---

## `SecurityAuditorAgent`

Analyzes bandit output and classifies vulnerabilities by severity.

### Constructor

| Parameters | Type | Default |
|------------|------|---------|
| `redis_client` | `Any \| None` | `None` |
| `state_store` | `AgentStateStore \| None` | `None` |

---

## `ReleaseAgentResult`

Result produced by an individual release agent after `process()` completes.

### Fields

| Field | Type | Default |
|-------|------|---------|
| `agent_id` | `str` | — |
| `agent_role` | `str` | — |
| `success` | `bool` | — |
| `tier_used` | `Tier` | — |
| `findings` | `dict[str, Any]` | `field(default_factory=dict)` |
| `score` | `float` | `0.0` |
| `confidence` | `float` | `0.0` |
| `cost` | `float` | `0.0` |
| `execution_time_ms` | `float` | `0.0` |
| `escalated` | `bool` | `False` |

---

## `QualityGate`

Quality gate threshold used to evaluate release readiness for a single check area.

### Fields

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `threshold` | `float` | — |
| `actual` | `float` | `0.0` |
| `passed` | `bool` | `False` |
| `critical` | `bool` | `True` |
| `message` | `str` | `''` |

---

## `ReleaseReadinessReport`

Aggregated go/no-go assessment produced by `ReleasePrepTeam.assess_readiness()`.

### Fields

| Field | Type | Default |
|-------|------|---------|
| `approved` | `bool` | — |
| `confidence` | `str` | — |
| `quality_gates` | `list[QualityGate]` | `field(default_factory=list)` |
| `agent_results` | `list[ReleaseAgentResult]` | `field(default_factory=list)` |
| `blockers` | `list[str]` | `field(default_factory=list)` |
| `warnings` | `list[str]` | `field(default_factory=list)` |
| `summary` | `str` | `''` |
| `timestamp` | `str` | `field(default_factory=lambda: datetime.now().isoformat())` |
| `total_duration` | `float` | `0.0` |
| `total_cost` | `float` | `0.0` |

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | — | `dict[str, Any]` | Serializes the report to a plain dictionary. |
| `format_console_output` | — | `str` | Formats the report as a human-readable console string. |

---

## `ReleasePrepTeam`

Coordinates parallel execution of release preparation agents and aggregates their results into a `ReleaseReadinessReport`.

### Constructor

| Parameters | Type | Default |
|------------|------|---------|
| `quality_gates` | `dict[str, Any] \| None` | `None` |
| `redis_url` | `str \| None` | `None` |

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `assess_readiness` | `codebase_path: str = '.'` | `ReleaseReadinessReport` | Runs all agents against the codebase and returns an aggregated readiness report. |
| `get_total_cost` | — | `float` | Returns the total token cost accumulated across all agents in this run. |

---

## `ReleasePrepTeamWorkflow`

Workflow wrapper that integrates `ReleasePrepTeam` with the CLI registry.

### Constructor

| Parameters | Type | Default |
|------------|------|---------|
| `quality_gates` | `dict[str, float] \| None` | `None` |
| `**kwargs` | `Any` | — |

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run_stage` | `stage_name: str, tier: ModelTier, input_data: Any` | `Any` | Executes a single named stage at the specified model tier. |
| `execute` | `path: str = '.', context: dict[str, Any] \| None = None, **kwargs: Any` | `ReleaseReadinessReport` | Runs the full release prep workflow and returns the readiness report. |

---

## `ReleasePreparationWorkflow`

Pre-release quality gate workflow powered by Agent SDK subagents.

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `**kwargs: Any` | `WorkflowResult` | Runs the full preparation workflow and returns the result. |

---

## Subagent names

The orchestrator spawns the following named subagents:

| Name | Role |
|------|------|
| `health-checker` | Test results, dependency status, CI pipeline health |
| `security-scanner` | Vulnerabilities, outdated dependencies, secret leaks |
| `changelog-generator` | Notable changes since last release |
| `release-assessor` | Overall go/no-go synthesis |

---

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

## Tags

`release`, `publishing`, `quality`
