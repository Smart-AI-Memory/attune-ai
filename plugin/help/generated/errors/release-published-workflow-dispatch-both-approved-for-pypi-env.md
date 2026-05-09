---
type: error
name: release-published-workflow-dispatch-both-approved-for-pypi-env
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Error: `release: published` + `workflow_dispatch` both
  approved for `pypi` env = duplicate publish, the
  second fails "File already exists"

## Signature

`release: published` + `workflow_dispatch` both
  approved for `pypi` env = duplicate publish, the
  second fails "File already exists"

## Root Cause

on v6.2.0, approving the `pypi` environment deployment on BOTH the tag-triggered (`release: published`) and manual (`workflow_dispatch`) runs caused the first to upload successfully and the second to 400 with `File already exists ('attune_ai-6.2.0-py3-none-any .whl', with blake2_256 hash ...)`. The release is fine — files are live on PyPI — but the failed run looks alarming. Two fixes: (1) only approve ONE of the two runs per release; (2) guard the publish job with `if: ${{ github.event_name == 'workflow_dispatch' }}` so tag-triggered runs short-circuit before twine uploads. Related to the existing `pypi` env branch-policy lesson — that one bites when only tag-triggered runs exist; this one bites when both paths are enabled and both get approved.

## Resolution

1. on v6.2.0, approving the `pypi` environment deployment on BOTH the tag-triggered (`release: published`) and manual (`workflow_dispatch`) runs caused the first to upload successfully and the second to 400 with `File already exists ('attune_ai-6.2.0-py3-none-any .whl', with blake2_256 hash ...)`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `release: published` + `workflow_dispatch` both
  approved for `pypi` env = duplicate publish, the
  second fails "File already exists"
- Task: Update test mocks and assertions
