---
type: error
name: pr-test-workflows-may-not-auto-trigger-after-close-reopen-or
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Error: PR test workflows may not auto-trigger after close/reopen or
  branch reuse

## Signature

PR test workflows may not auto-trigger after close/reopen or
  branch reuse

## Root Cause

When a PR branch is reused after a previous PR was merged, the `pull_request` trigger may not fire on new pushes. `gh workflow run tests.yml --ref <branch>` is the reliable manual fallback. The `synchronize` event only fires for pushes to an *open* PR — if the PR was closed during the push, the event is lost.

## Resolution

1. When a PR branch is reused after a previous PR was merged, the `pull_request` trigger may not fire on new pushes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: PR test workflows may not auto-trigger after close/reopen or
  branch reuse
- Task: Update test mocks and assertions
