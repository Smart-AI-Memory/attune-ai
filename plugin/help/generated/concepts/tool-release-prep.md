---
name: tool-release-prep
source: plugin/skills/release-prep/SKILL.md
summary: Release Prep is an automated four-agent readiness assessment that evaluates
  security, tests, documentation, and versioning before shipping code to PyPI.
tags:
- release
- publishing
- ci
type: concept
---

# Release Prep

## What

Release Prep runs a four-agent readiness assessment before you ship. Each agent independently evaluates one concern — security, tests, documentation, or versioning — and returns a pass/fail verdict with supporting details. The orchestrator combines those verdicts into a single go/no-go recommendation.

| Agent | Responsibility |
|-------|----------------|
| Security | Scans for vulnerabilities and checks for new CVEs |
| Test | Runs the full test suite and verifies coverage thresholds |
| Docs | Validates the changelog, README links, and API documentation |
| Version | Checks the version bump, dependency pins, and distribution build |

## Why

Shipping without verifying security, tests, documentation, and dependency versions is how CVEs, broken installs, and stale READMEs reach PyPI. Release Prep automates the preflight checklist so nothing slips through at the last moment.

## When to Use

Run Release Prep in any of these situations:

- Before bumping the version in `pyproject.toml`
- Before running `twine upload` or publishing to PyPI
- After merging a large feature branch into `main`
- As a final gate in an automated release workflow

## Related Topics

- **Task:** Use the release-prep skill — step-by-step walkthrough
- **Reference:** Skill: release-prep — full option and output reference
