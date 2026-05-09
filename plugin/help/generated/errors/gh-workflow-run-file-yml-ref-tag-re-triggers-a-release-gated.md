---
type: error
name: gh-workflow-run-file-yml-ref-tag-re-triggers-a-release-gated
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Error: `gh workflow run <file.yml> --ref <tag>` re-triggers
  a release-gated workflow cleanly without churning the
  release

## Signature

`gh workflow run <file.yml> --ref <tag>` re-triggers
  a release-gated workflow cleanly without churning the
  release

## Root Cause

When a `publish.yml` triggered by `release: types: [published]` fails on the first shot (e.g. invalid trusted publisher config on PyPI side), don't delete and recreate the release — if the workflow also declares `workflow_dispatch:`, `gh workflow run publish.yml --repo owner/repo --ref <tag>` fires a fresh run against the same tag, skipping the release-tag churn. Build + publish steps run identically.

## Resolution

1. When a `publish.yml` triggered by `release: types: [published]` fails on the first shot (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `gh workflow run <file.yml> --ref <tag>` re-triggers
  a release-gated workflow cleanly without churning the
  release
- Task: Update test mocks and assertions
