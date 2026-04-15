---
type: comparison
feature: release-prep
depth: comparison
generated_at: 2026-04-14T14:51:38.200231+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release preparation: Workflow vs. agent team vs. individual agents

## Overview

The release-prep feature provides three approaches for pre-release quality checks: a high-level workflow, a coordinated agent team, and individual specialized agents. Each targets different integration patterns and control requirements.

## Feature comparison

| Feature | Workflow | Agent Team | Individual Agents |
|---------|----------|------------|-------------------|
| **Entry point** | `ReleasePreparationWorkflow.execute()` | `ReleasePrepTeam.assess_readiness()` | Direct agent instantiation |
| **Orchestration** | Agent SDK subagents | Parallel agent execution | Manual coordination |
| **Cost management** | Progressive tier escalation | Team-wide cost tracking | Per-agent control |
| **Report format** | Structured markdown sections | `ReleaseReadinessReport` object | Individual `ReleaseAgentResult` |
| **Quality gates** | Fixed thresholds | Configurable gates with pass/fail | Agent-specific scoring |
| **Execution model** | Sequential with synthesis | Parallel with aggregation | Independent execution |

## Detailed breakdown

### ReleasePreparationWorkflow
- **Best for:** Drop-in pre-release checks in existing CI pipelines
- **Strengths:** Minimal setup, structured output format, automatic escalation from CHEAP → CAPABLE → PREMIUM tiers
- **Constraints:** Fixed subagent composition, limited customization of quality gates

### ReleasePrepTeam
- **Best for:** Applications needing programmatic access to release assessment data
- **Strengths:** Parallel execution, configurable quality gates, detailed cost tracking via `get_total_cost()`
- **Constraints:** Requires explicit quality gate configuration, more complex integration

### Individual agents
Available agents: `TestCoverageAgent`, `DocumentationAgent`, `CodeQualityAgent`
- **Best for:** Targeted quality checks or custom orchestration logic
- **Strengths:** Maximum control over execution order, fine-grained result handling
- **Constraints:** Manual coordination required, no built-in aggregation or escalation

## Use this when...

**Choose ReleasePreparationWorkflow** when you need a "black box" solution for CI/CD integration. The structured markdown output works well for automated reporting and the progressive escalation optimizes cost vs. accuracy.

**Choose ReleasePrepTeam** when you're building release management tooling that needs to make programmatic decisions based on quality metrics. The `ReleaseReadinessReport` provides machine-readable pass/fail status for each quality gate.

**Choose individual agents** when you need custom quality check orchestration or want to integrate specific checks into existing workflows. For example, running only `TestCoverageAgent` during development builds but the full team before releases.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
