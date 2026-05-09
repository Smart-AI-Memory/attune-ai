---
type: warning
name: gh-workflow-run-file-yml-ref-tag-re-triggers-a-release-gated
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Warning: `gh workflow run <file.yml> --ref <tag>` re-triggers
  a release-gated workflow cleanly without churning the
  release

## Condition

When a `publish.yml` triggered by `release: types: [published]` fails on the first shot (e.g

## Risk

When a `publish.yml` triggered by `release: types: [published]` fails on the first shot (e.g

## Mitigation

1. When a `publish.yml` triggered by `release: types: [published]` fails on the first shot (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `gh workflow run <file.yml> --ref <tag>` re-triggers
  a release-gated workflow cleanly without churning the
  release
