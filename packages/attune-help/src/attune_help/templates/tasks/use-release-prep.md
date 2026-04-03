---
type: task
name: use-release-prep
tags: [release, skill, task]
source: plugin/skills/release-prep/SKILL.md
---

# How to Run Release Prep

## Quick start

The fastest way: just say what you want.

```
is this project ready to release?
```

Or use the skill directly:

```
/release-prep check
```

That kicks off the full preflight checklist. You'll get a
go/no-go assessment in about two minutes.

## The guided flow

When you invoke release prep, it asks two questions
before running:

1. **What version?** -- "What version are you releasing?
   Or should I check the current version and suggest the
   next bump?"

2. **What stage?** -- "Full release prep, or a specific
   check?"
   - **Full** -- health, security, changelog, deps, version
   - **Prep check** -- just verify readiness without
     version bump
   - **Changelog only** -- validate the changelog entry
   - **Security only** -- run the security gate

Answer in natural language. If you say "just check
everything," it runs the full assessment.

## What you'll type

| Goal | What to say |
|------|-------------|
| Full preflight | `/release-prep 5.6.0` |
| Check without version bump | `/release-prep check` |
| Just the security gate | `run the security check for release` |
| Just changelog validation | `check if the changelog is ready for release` |

## Reading the assessment

Results come back as a structured report:

```
Release Readiness Assessment
Verdict: NO-GO
Version: 5.5.0 -> 5.6.0

Health          PASS   Tests: 15,482 passing, coverage 87%
Security        PASS   No critical findings, 2 advisory
Changelog       FAIL   No entry for v5.6.0
Dependencies    PASS   All pinned, no known CVEs
Version         PASS   Semver valid, dist builds clean

Blockers (1)
  Changelog — No entry for v5.6.0 in CHANGELOG.md

Recommendations
  1. Add a v5.6.0 section to CHANGELOG.md
  2. Re-run release prep after fixing
```

Each check area shows PASS or FAIL with a one-line
summary. Blockers are listed separately so you know
exactly what to fix.

## Handling blockers

After reviewing the report:

- **"Fix the blockers"** -- the skill will attempt to
  resolve each issue (update changelog, fix lint, etc.)
- **"Update the changelog"** -- generates a changelog
  entry from recent commits
- **"Re-run the check"** -- runs the assessment again
  after you've made fixes
- **"Tag and publish"** -- if the verdict is GO, proceeds
  to tag and upload

## Want to learn more?

- Say **"tell me more"** for the full reference with
  every check area, scoring, and configuration
- Say **"what is release prep?"** to go back to the
  overview
- Say **"run a security audit"** to scan for
  vulnerabilities separately
