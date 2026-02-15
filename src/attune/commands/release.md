---
name: release
description: Release preparation, security scanning, and publishing
category: hub
aliases: [ship, publish]
tags: [release, publish, version, changelog, security]
version: "1.0.0"
question:
  header: "Release Hub"
  question: "What release task do you need?"
  multiSelect: false
  options:
    - label: "Prepare release"
      description: "Version bump, changelog, pre-flight checks"
    - label: "Security scan"
      description: "Pre-release security audit"
    - label: "Health check"
      description: "Test suite, coverage, lint — full project health"
    - label: "Publish"
      description: "Build and publish to PyPI"
---

# release

Release preparation, security scanning, and publishing hub.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/release prep` | Full release preparation workflow |
| `/release security` | Pre-release security audit |
| `/release health` | Full project health check |
| `/release publish` | Build and publish to PyPI |
| `/release version <v>` | Bump version number |

## Natural Language

Describe what you need:

- "prepare for release"
- "run a security scan before shipping"
- "is the project healthy enough to release?"
- "publish to PyPI"
- "bump version to 5.2.0"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST execute the workflow, not answer ad-hoc.**

### Context Gathering (ALWAYS DO FIRST)

Before executing any action below, gather current project context:

1. Run: `git status --short`
2. Run: `git log --oneline -5`
3. Run: `git branch --show-current`
4. Run: `grep '^version' pyproject.toml` (current version)

Use this context to inform release decisions (e.g., uncommitted changes, current version, branch).

### Reasoning Approach

For release decisions, use structured reasoning to make a go/no-go recommendation:

<analysis-steps>
1. **Test verification** — Run full test suite, check pass rate (target: 100%) and coverage (target: ≥80%)
2. **Security verification** — Run security audit, confirm zero CRITICAL/HIGH findings; document any accepted MEDIUM risks
3. **Lint verification** — Run ruff check, confirm zero errors; warnings are acceptable if documented
4. **Changelog verification** — Confirm CHANGELOG.md has entries for all commits since last release tag
5. **Version verification** — Confirm version in pyproject.toml matches intended release; check for pre-release suffixes
6. **Go/no-go recommendation** — Synthesize all checks into a clear recommendation with blocking issues listed first
</analysis-steps>

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/release prep` | Run Release-Prep wizard: version info → readiness check → changelog → decompose tasks → preview → confirm |
| `/release security` | Run Security wizard: define scope → scan → generate fixes → decompose remediation → preview |
| `/release health` | Run pytest + coverage + ruff + bandit, report aggregate results |
| `/release publish` | `uv run python -m build && uv run twine upload dist/*` |
| `/release version <v>` | Update version in pyproject.toml and `src/attune/__init__.py` |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "prepare", "prep", "ready" | Run Release-Prep wizard flow |
| "security", "vulnerabilities", "scan" | Run Security wizard flow |
| "health", "status", "ready to ship" | Run full health check |
| "publish", "pypi", "upload" | Build and publish |
| "version", "bump" | Update version numbers |

**IMPORTANT:** When arguments are provided, DO NOT just display documentation. EXECUTE the action.

### Pre-Release Checklist

Before publishing, verify:

1. All tests passing: `uv run pytest`
2. Coverage above 80%: `uv run pytest --cov=src --cov-report=term-missing`
3. No security issues: `uv run attune workflow run security-audit`
4. No lint warnings: `uv run ruff check src/`
5. CHANGELOG.md updated
6. Version bumped in pyproject.toml

### CLI Reference

```bash
uv run attune workflow run release-prep
uv run attune workflow run security-audit
uv run python -m build
uv run twine upload dist/*
```
