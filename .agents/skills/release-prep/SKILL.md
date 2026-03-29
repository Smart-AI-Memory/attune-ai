---
name: release-prep
description: "Pre-release preparation with health checks, security audit, changelog validation, version bumps, and dependency audits. Triggers on: release, publish, ship, deploy, version bump, changelog."
---
# Release Prep

## Scoping

Before running, ask:

1. **Version**: "What version are you releasing? Or
   should I check the current version and suggest?"
2. **Scope**: "Full release prep or a specific check?"
   - Full: All 4 agents (security, testing, docs,
     versioning)
   - Specific: Single check (e.g., just changelog)

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `release_prep` | Full release readiness (4-agent team) |
| `health_check` | Project health score (tests + lint + coverage) |
| `dependency_check` | Dependency audit and vulnerability scan |
| `secure_release` | Full release pipeline with security gates |

## Execution

Call the `release_prep` MCP tool for a full assessment:

```
release_prep(path="<project root>")
```

For targeted checks, use individual tools:

```
health_check(path="<project root>")
dependency_check(path="<project root>")
secure_release(path="<project root>")
```

The full `release_prep` orchestrates a 4-agent team:

- **Security Agent** — runs security_audit, flags
  vulnerabilities that block release
- **Testing Agent** — checks test coverage, runs
  test_generation for gaps
- **Docs Agent** — validates changelog, README, and
  documentation freshness
- **Version Agent** — checks version bumps, dependency
  compatibility, semver compliance

## Output Format

```markdown
## Release Readiness Report

**Verdict:** READY / NOT READY
**Version:** X.Y.Z → A.B.C
**Date:** YYYY-MM-DD

### Agent Reports

#### Security
- Status: PASS / FAIL
- Issues: [list if any]

#### Testing
- Coverage: X%
- Missing tests: [list if any]

#### Documentation
- Changelog: UP TO DATE / NEEDS UPDATE
- README: CURRENT / STALE

#### Versioning
- Semver: VALID / INVALID
- Breaking changes: YES / NO
- Dependencies: ALL COMPATIBLE / [list conflicts]

### Blockers
| Blocker | Agent | Severity |
|---------|-------|----------|

### Recommendations
1. [Ordered list of actions before release]
```

## Follow-Up

After presenting results, offer:

- "Want me to fix the blockers?"
- "Should I update the changelog?"
- "Ready to tag and publish?"
