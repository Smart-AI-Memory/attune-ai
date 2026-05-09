---
type: error
name: pypi-env-policies-may-whitelist-branches-only-tag-triggered
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Error: PyPI env policies may whitelist branches only — tag-
  triggered publishes get rejected

## Signature

PyPI env policies may whitelist branches only — tag-
  triggered publishes get rejected

## Root Cause

`pypi` environment deployment branch policies on attune-ai allowed `main` and `release/*` branches but not any tag pattern. A `publish-pypi.yml` run fired by `release: types: [published]` executes against the tag ref (`refs/tags/v6.1.0`), which the env rejected with "Tag <X> is not allowed to deploy due to environment protection rules." Previous releases never hit this because they all ran via `workflow_dispatch --ref main`. Fix (fastest): re-trigger via `gh workflow run publish-pypi.yml --ref main` — the build pulls the latest main which already has the version bump merged in. Alternative fix (if you prefer tag-triggered publishes): add `v*` to the env's `deployment-branch-policies` via `gh api repos/<owner>/<repo>/environments/pypi/deployment-branch-policies -F name=v* -F type=tag`. attune-rag and attune-author don't have this issue because I set up their `pypi` envs with no branch/tag restriction when creating them for the RAG release.

## Resolution

1. `pypi` environment deployment branch policies on attune-ai allowed `main` and `release/*` branches but not any tag pattern

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: PyPI env policies may whitelist branches only — tag-
  triggered publishes get rejected
- Tip: Best practice: PyPI env policies may whitelist branches only — tag-
  triggered publishes get rejected
- Task: Update test mocks and assertions
