---
name: release-prep
description: "Multi-agent release readiness assessment"
type: subagent
team: release
agents:
  - security-auditor
  - test-coverage
  - code-quality
  - documentation
coordination: parallel
tier_strategy: progressive
---

# Release Prep Agent Team

A 4-agent team for automated release readiness assessment.

## Agents

| Agent | Role | Tools |
| ----- | ---- | ----- |
| Security Auditor | Run bandit, classify vulnerabilities | bandit, SAST |
| Test Coverage | Run pytest --cov, parse coverage | pytest, coverage |
| Code Quality | Run ruff, check complexity | ruff, radon |
| Documentation | Check docstring coverage | interrogate |

## Execution

- **Coordination:** Parallel execution with result aggregation
- **Tier Strategy:** Progressive (CHEAP -> CAPABLE -> PREMIUM)
- **Output:** `ReleaseReadinessReport` with go/no-go decision

## Usage

```text
/agent release-prep
```
