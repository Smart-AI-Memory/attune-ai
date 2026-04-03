---
type: concept
name: tool-release-prep
tags: [release, publishing, ci]
source: plugin/skills/release-prep/SKILL.md
---

# Release Prep

Release prep runs a preflight checklist across your
project before you publish. It checks health, security,
changelog, dependencies, and version consistency, then
produces a go/no-go assessment telling you whether the
release is safe to ship.

## What it checks

| Check area | What it verifies | Blocking? |
|------------|------------------|-----------|
| **Health** | Tests pass, lint clean, coverage above threshold | Yes if tests fail |
| **Security** | No new CVEs, no eval/exec, secrets scan clean | Yes if critical findings |
| **Changelog** | Entry exists for this version, date is current | Yes if missing |
| **Dependencies** | Pinned versions, no known vulnerabilities, compatible ranges | Yes if vulnerable dep |
| **Version** | Semver bump matches changes, pyproject.toml updated, dist builds cleanly | Yes if version mismatch |

## The go/no-go decision

After all checks complete, you get a single verdict:

- **GO** -- every check passed or has only advisory
  warnings. Safe to tag, build, and publish.
- **NO-GO** -- one or more blocking issues found. The
  report lists exactly what to fix before retrying.

The assessment is conservative. A stale changelog entry
or a failing test is enough to block. Better to catch
it here than after the package is on PyPI.

## When to use it

- Before bumping the version in pyproject.toml
- Before running `twine upload` or publishing to PyPI
- After merging a large feature branch to main
- As the final gate before tagging a release
- When you're unsure whether the codebase is release-ready

## Want to learn more?

- Say **"how do I run release prep?"** for step-by-step
  instructions
- Say **"tell me more"** for the full reference with
  all check areas, scoring, and configuration
- Say **"run a security audit"** to scan for
  vulnerabilities separately
- Say **"check my test coverage"** to look at tests
  before releasing
