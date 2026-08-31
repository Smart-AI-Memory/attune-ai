---
name: release-prep
description: "Pre-release preparation with health checks, security audit, changelog validation, version bumps, and dependency audits. Triggers on: release, publish, ship, deploy, version bump, changelog."
argument-hint: "<version or 'check'>"
---

# Release Prep

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="release-prep", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Release Prep** — Runs pre-release checks — health, security, changelog, and go/no-go assessment.

## Scoping

Before running, ask:

1. **Version**: "What version are you releasing? Or
   should I check the current version and suggest?"
2. **Scope**: "Full advisory or a specific check?"
   - Full: advisory across security, testing, docs,
     versioning
   - Specific: Single check (e.g., just changelog)

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `release_notes` | Changelog draft + go/no-go advisory (single-agent SDK) |
| `health_check` | Project health score (tests + lint + coverage) |
| `dependency_check` | Dependency audit and vulnerability scan |
| `secure_release` | Full release pipeline with security gates |

> **Advisory vs gate.** `release_notes` is *advisory* — it drafts a
> changelog and gives a recommendation, it does not block. The
> deterministic 4-agent gate (real bandit/ruff/pytest + hard
> thresholds) is CLI-only: `attune workflow run release-gate`.

## Shared command workspace (preferred)

When the generic command-workspace tools are available, open adapter
`release-prep` with the selected version, scope, and project path. Present its
widget or returned Markdown and collect its bound `start_release_prep` action
before invoking checks. Publish each real Security, Testing, Documentation,
and Versioning receipt as `gate_result`, then publish
`assessment_complete`.

The workspace reviews one gate at a time and then issues a separate final
release approval. A critical `FAIL`, `ERROR`, or synthesized `MISSING` receipt
can only be fixed and rerun; it cannot be accepted. A Documentation warning
may be accepted only through its explicit bound action. Publish tool crashes
as `ERROR` receipts — a failed gatekeeper fails the gate and never disappears.
If the shared tools are unavailable, retain the same repeated decisions in
compact text/form gates.

## Execution

Call the `release_notes` MCP tool for a changelog draft and
go/no-go recommendation:

```
release_notes(path="<project root>")
```

For targeted checks, use individual tools:

```
health_check(path="<project root>")
dependency_check(path="<project root>")
secure_release(path="<project root>")
```

The full release prep covers four areas:

- **Security** — scans for vulnerabilities that block
  release
- **Testing** — checks test coverage, identifies gaps
- **Documentation** — validates changelog, README, and
  documentation freshness
- **Versioning** — checks version bumps, dependency
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

## Help

After presenting results, call:

```
help_lookup(topic="release-prep", mode="workflow_help")
```

If templates are returned, offer: "I have tips about
release preparation — want to see them?"

## Follow-Up

After presenting results, offer:

- "Want me to fix the blockers?"
- "Should I update the changelog?"
- "Ready to tag and publish?"
