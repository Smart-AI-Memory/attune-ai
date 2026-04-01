---
type: concept
name: tool-release-prep
tags: [release, publishing, ci]
source: plugin/skills/release-prep/SKILL.md
---

# Release Prep

## What

Runs a 4-agent release readiness assessment covering
security audit, test validation, documentation checks, and
version/dependency verification. Each agent produces a
pass/fail verdict with details, and the orchestrator
combines them into a go/no-go recommendation.

## Why

Shipping a release without checking security, tests, docs,
and versions is how CVEs, broken installs, and stale
READMEs reach PyPI. Release prep automates the preflight
checklist so nothing slips through.

## When to use

- Before bumping the version in pyproject.toml
- Before running `twine upload` or publishing to PyPI
- After merging a large feature branch to main
- As the final gate in a release workflow

## What it checks

| Agent | Responsibility |
|-------|----------------|
| Security | Runs security-audit, checks for new CVEs |
| Test | Runs full test suite, verifies coverage thresholds |
| Docs | Validates changelog, README links, API docs |
| Version | Checks version bump, dependency pins, dist build |

## Related Topics

- **Task**: Use the release-prep skill -- step-by-step
- **Reference**: Skill: release-prep -- full reference
