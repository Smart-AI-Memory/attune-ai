---
type: concept
feature: release-prep
depth: concept
generated_at: 2026-05-04T02:26:51.738297+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Release Prep

Release prep is an automated quality gate that runs a comprehensive pre-release assessment across your codebase to determine whether it's safe to publish.

## Core assessment areas

The system coordinates four specialized agents to evaluate different aspects of release readiness:

- **Test coverage** — Runs `pytest --cov` and parses coverage reports to verify test completeness
- **Code quality** — Uses ruff to check linting, type hints, and complexity metrics
- **Documentation health** — Verifies docstring coverage, README currency, and CHANGELOG presence
- **Security posture** — Scans for vulnerabilities, outdated dependencies, and potential secret leaks

Each agent operates independently and reports structured findings that get synthesized into a single go/no-go recommendation.

## Progressive cost management

The `ReleaseAgent` base class implements a three-tier escalation strategy to balance thoroughness with cost:

1. **CHEAP** tier — Fast heuristics and cached results
2. **CAPABLE** tier — Standard analysis with moderate compute
3. **PREMIUM** tier — Deep inspection for complex edge cases

Agents automatically escalate to higher tiers when confidence is low or when critical issues need deeper investigation.

## Quality gate mechanics

The `ReleasePrepTeam` orchestrates parallel agent execution and applies configurable quality gates:

```python
quality_gates = {
    "test_coverage": 80.0,      # Minimum coverage percentage
    "code_quality": 8.0,        # Ruff score threshold
    "security_score": 90.0      # Security assessment minimum
}
```

The `ReleaseReadinessReport` aggregates all findings into:
- Overall approval status (approved/blocked)
- Confidence level with supporting evidence
- Specific blockers that must be addressed
- Prioritized suggestions for improvement

## When release prep matters

Use release prep as the final checkpoint before:
- Bumping version numbers in `pyproject.toml`
- Creating git tags for releases
- Publishing packages to PyPI
- Merging release branches to main

The assessment is intentionally conservative — a single failing test or stale changelog entry will block the release until fixed.
