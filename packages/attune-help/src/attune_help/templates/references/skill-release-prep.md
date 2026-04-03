---
type: reference
subtype: procedural
name: skill-release-prep
category: skill
tags: [release, skill, plugin, reference]
source: plugin/skills/release-prep/SKILL.md
---

# Release Prep Reference

Complete reference for the release prep skill --
every check it runs, how scoring works, blocker types,
and configuration options.

## Invocation

```
/release-prep <version or 'check'>
```

Or natural language:

```
is this ready to release?
prepare release 5.6.0
run the release preflight
check if I can ship this
```

## Guided scoping

The skill asks two questions before running. Both accept
natural language answers.

| Question | Options | Default |
|----------|---------|---------|
| What version? | A semver string, or "check" to auto-detect | Current version in pyproject.toml |
| What stage? | Full prep, prep check, changelog only, security only | Full prep |

Runs on your Claude subscription -- no API key or
additional cost.

## All check areas

### Health

| Check | What it verifies | Blocking? | Typical issue |
|-------|------------------|-----------|---------------|
| Test suite | All tests pass | Yes | Failing test from recent merge |
| Lint | ruff + black clean | Yes | Auto-fixable style violation |
| Coverage | Above configured threshold | Advisory | Coverage dip from new code |
| Type hints | No new mypy errors | Advisory | Missing annotation on public API |

### Security

| Check | What it verifies | Blocking? | Typical issue |
|-------|------------------|-----------|---------------|
| eval/exec scan | No dangerous eval or exec | Yes | eval() in utility function |
| Secrets scan | No hardcoded credentials | Yes | API key in test fixture |
| CVE check | No known vulnerabilities in deps | Yes | Outdated dependency with CVE |
| Path validation | File ops use validated paths | Advisory | Missing _validate_file_path() |

### Changelog

| Check | What it verifies | Blocking? | Typical issue |
|-------|------------------|-----------|---------------|
| Version entry | Section exists for target version | Yes | Forgot to add entry |
| Date | Release date is current or today | Advisory | Stale date from earlier prep |
| Format | Follows Keep a Changelog structure | Advisory | Missing category headers |
| Completeness | All merged PRs accounted for | Advisory | PR merged after changelog written |

### Dependencies

| Check | What it verifies | Blocking? | Typical issue |
|-------|------------------|-----------|---------------|
| Pinned versions | Lower bounds above known CVEs | Yes | pydantic>=2.0.0 allows vulnerable range |
| Compatibility | No conflicting version ranges | Yes | Two deps require different major versions |
| Lock file | Lock file in sync with pyproject.toml | Advisory | Forgot to run uv lock |
| Unused deps | No dependencies without imports | Advisory | Leftover from removed feature |

### Version

| Check | What it verifies | Blocking? | Typical issue |
|-------|------------------|-----------|---------------|
| Semver validity | Version string is valid semver | Yes | Typo like 5.6.0.1 |
| Bump type | Matches changes (breaking = major) | Advisory | Minor bump with breaking change |
| pyproject.toml | Version updated in source | Yes | Version still says old number |
| Dist build | `python -m build` succeeds | Yes | Missing MANIFEST.in entry |

## Output format

```markdown
## Release Readiness Assessment

**Verdict:** GO / NO-GO
**Version:** X.Y.Z -> A.B.C
**Date:** YYYY-MM-DD

### Check Results

| Area | Status | Summary |
|------|--------|---------|
| Health | PASS | 15,482 tests passing, 87% coverage |
| Security | PASS | No critical findings |
| Changelog | FAIL | No entry for vA.B.C |
| Dependencies | PASS | All pinned, no CVEs |
| Version | PASS | Semver valid, dist builds |

### Blockers

| Blocker | Area | Severity | Fix |
|---------|------|----------|-----|
| No changelog entry | Changelog | Blocking | Add vA.B.C section |

### Advisories

| Advisory | Area | Recommendation |
|----------|------|----------------|
| Coverage dipped 2% | Health | Add tests for new module |

### Recommendations

1. Add a vA.B.C section to CHANGELOG.md
2. Re-run release prep after fixing
```

## Scoring and verdicts

The verdict is binary: GO or NO-GO.

| Verdict | Meaning |
|---------|---------|
| **GO** | Zero blocking issues. Safe to tag and publish. |
| **NO-GO** | One or more blocking issues. Fix before releasing. |

Advisory findings do not block the release but are
included in the report for awareness.

## Blocker types

| Type | Severity | Effect |
|------|----------|--------|
| **Blocking** | Must fix | Prevents GO verdict |
| **Advisory** | Should fix | Included in report, does not block |

A single blocking issue is enough for a NO-GO verdict.
The report lists all blockers so you can fix them in
one pass.

## Configuration

### Coverage threshold

Set the minimum coverage in your project config:

```yaml
# attune.config.yml
release_prep:
  coverage_threshold: 80
```

### Excluding paths

Skip directories that don't need release checks:

```yaml
# attune.config.yml
release_prep:
  exclude:
    - "benchmarks/**"
    - "scripts/**"
    - "docs/**"
```

### Skipping specific checks

Disable individual check areas if they don't apply:

```yaml
# attune.config.yml
release_prep:
  skip:
    - type_hints
    - unused_deps
```

## After the assessment

| Goal | What to say |
|------|-------------|
| Fix all blockers | "fix the blockers" |
| Update changelog | "update the changelog for this release" |
| Re-run after fixes | "run release prep again" |
| Tag and publish | "tag and publish" |
| Export for CI | "export the assessment as JSON" |
| Compare with last run | "compare with the previous assessment" |

## Want to learn more?

- Say **"what is release prep?"** to go back to the
  overview
- Say **"how do I run release prep?"** for the
  step-by-step guide
- Say **"run a security audit"** to scan for
  vulnerabilities separately
- Say **"check my test coverage"** to analyze test
  gaps before releasing
