---
type: warning
name: pypi-env-policies-may-whitelist-branches-only-tag-triggered
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Warning: PyPI env policies may whitelist branches only — tag-
  triggered publishes get rejected

## Condition

`pypi` environment deployment branch policies on attune-ai allowed `main` and `release/*` branches but not any tag pattern

## Risk

A `publish-pypi.yml` run fired by `release: types: [published]` executes against the tag ref (`refs/tags/v6.1.0`), which the env rejected with "Tag <X> is not allowed to deploy due to environment protection rules." Previous releases never hit this because they all ran via `workflow_dispatch --ref main`

## Mitigation

1. `pypi` environment deployment branch policies on attune-ai allowed `main` and `release/*` branches but not any tag pattern

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: PyPI env policies may whitelist branches only — tag-
  triggered publishes get rejected
