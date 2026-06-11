---
type: reference
name: release-prep-reference
feature: release-prep
depth: reference
generated_at: 2026-06-11T04:39:32.875454+00:00
source_hash: b484e3b8f8e27e1e37d71dd39e93de2e14c056d5969f51d404e9b11858bd81b7
status: generated
scaffold_hash: 83c37b9fadf0a212df19cec4c730dd92b02d065a4544f6352bc1521bf8fc20e5
---

# Release Prep reference

Assess codebase readiness for release by running parallel health, security, test coverage, and documentation checks through a team of specialized agents. Each agent's findings are aggregated into a `ReleaseReadinessReport` containing quality gate results, blockers, and actionable warnings.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity. | `src/attune/agents/release/quality_agent.py` |
| `SecurityAuditorAgent` | Analyzes bandit output and classifies vulnerabilities by severity. | `src/attune/agents/release/security_agent.py` |
| `Tier` | Model tier for progressive escalation. | `src/attune/agents/release/release_models.py` |
| `ReleaseAgentResult` | Result from an individual release agent. | `src/attune/agents/release/release_models.py` |
| `QualityGate` | Quality gate threshold for release readiness. | `src/attune/agents/release/release_models.py` |
| `ReleaseReadinessReport` | Aggregated release readiness assessment. | `src/attune/agents/release/release_models.py` |
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents. | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates ReleasePrepTeam with the CLI registry. | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePreparationWorkflow` | Pre-release quality gate workflow powered by Agent SDK subagents. | `src/attune/workflows/release_prep.py` |

## ReleaseAgent

`ReleaseAgent` is the base class for all specialized release agents and implements CHEAP → CAPABLE → PREMIUM tier escalation. In most workflows, instantiate `ReleasePrepTeam` rather than individual agents directly.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `agent_id: str, role: str, redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | `None` | Constructs the agent with an identity string, role label, and optional Redis and state store connections. |
| `process` | `codebase_path: str = '.'` | `ReleaseAgentResult` | Runs the agent against the given codebase path and returns a scored result. |

## Specialized agents

Each agent below extends `ReleaseAgent` and shares the same constructor signature.

| Class | Parameters | Description |
|-------|------------|-------------|
| `TestCoverageAgent` | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | Runs pytest --cov and parses coverage report. |
| `DocumentationAgent` | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | Checks docstring coverage, README currency, and CHANGELOG presence. |
| `CodeQualityAgent` | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | Runs ruff, checks type hints and complexity. |
| `SecurityAuditorAgent` | `redis_client: Any \| None = None, state_store: AgentStateStore \| None = None` | Analyzes bandit output and classifies vulnerabilities by severity. |

## ReleasePrepTeam

`ReleasePrepTeam` coordinates parallel execution of all release preparation agents and is the primary entry point for programmatic use.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `quality_gates: dict[str, Any] \| None = None, redis_url: str \| None = None` | `None` | Constructs the team with optional quality gate threshold overrides and a Redis connection URL. |
| `get_total_cost` | — | `float` | Returns the accumulated LLM cost across all agents in the most recent `assess_readiness` run. |
| `assess_readiness` | `codebase_path: str = '.'` | `ReleaseReadinessReport` | Runs all agents in parallel against the codebase and returns an aggregated readiness report. |

## ReleasePrepTeamWorkflow

`ReleasePrepTeamWorkflow` wraps `ReleasePrepTeam` so it can be registered and invoked through the CLI workflow registry.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `quality_gates: dict[str, float] \| None = None, **kwargs: Any` | `None` | Constructs the workflow with optional quality gate thresholds. |
| `run_stage` | `stage_name: str, tier: ModelTier, input_data: Any` | `Any` | Runs a named stage at the specified model tier. |
| `execute` | `path: str = '.', context: dict[str, Any] \| None = None, **kwargs: Any` | `WorkflowResult` | Runs the full release preparation workflow against the given codebase path. |

## ReleasePreparationWorkflow

`ReleasePreparationWorkflow` is the Agent SDK–backed workflow. It orchestrates four subagents — `health-checker`, `security-scanner`, `changelog-generator`, and `release-assessor` — and synthesizes their findings into a structured report.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `**kwargs: Any` | `WorkflowResult` | Runs the four-subagent pipeline and returns a synthesized release readiness report. |

## ReleaseAgentResult

Result returned by an individual release agent.

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

## QualityGate

A single named quality gate threshold used to evaluate release readiness.

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `threshold` | `float` | — |
| `actual` | `float` | `0.0` |
| `passed` | `bool` | `False` |
| `critical` | `bool` | `True` |
| `message` | `str` | `''` |

## ReleaseReadinessReport

Aggregated release readiness assessment produced by `ReleasePrepTeam.assess_readiness`.

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
| `format_console_output` | — | `str` | Formats the report for terminal display. |

## Constants

### `_SUBAGENT_NAMES`

Subagent names spawned by `ReleasePreparationWorkflow`.

| Constant | Members |
|----------|---------|
| `_SUBAGENT_NAMES` | `health-checker`, `security-scanner`, `changelog-generator`, `release-assessor` |

### `_SYSTEM_PROMPT`

System prompt used to configure the release preparation orchestrator.

```
You are a release preparation orchestrator. Coordinate four specialized subagents to assess release readiness and synthesize their findings into a single structured report. Be thorough but concise. Cite file paths and line numbers when possible.
```

### `_TASK_PROMPT_TEMPLATE`

Task prompt template passed to the orchestrator when `ReleasePreparationWorkflow.execute` runs. `{path}` is interpolated with the target codebase path.

```
Assess release readiness for the codebase at {path} using the four specialized subagents below. Each subagent should focus on its domain and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single report with these sections:

## Summary
Overall release readiness score (0-100) and a 2-3 sentence executive summary with a go/no-go recommendation.

## Health
Findings from the health checker — test results, dependency status, CI pipeline health.

## Security
Findings from the security scanner — vulnerabilities, outdated dependencies, secret leaks.

## Changelog
Generated changelog from the changelog generator — notable changes since last release.

## Suggestions
Actionable next steps ordered by priority, including any blockers that must be resolved before release.
```

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

## Tags

`release`, `publishing`, `quality`
