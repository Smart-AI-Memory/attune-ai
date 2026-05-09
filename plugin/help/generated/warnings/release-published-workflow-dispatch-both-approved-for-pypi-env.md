---
type: warning
name: release-published-workflow-dispatch-both-approved-for-pypi-env
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Warning: `release: published` + `workflow_dispatch` both
  approved for `pypi` env = duplicate publish, the
  second fails "File already exists"

## Condition

on v6.2.0, approving the `pypi` environment deployment on BOTH the tag-triggered (`release: published`) and manual (`workflow_dispatch`) runs caused the first to upload successfully and the second to 400 with `File already exists ('attune_ai-6.2.0-py3-none-any .whl', with blake2_256 hash ...)`

## Risk

The release is fine — files are live on PyPI — but the failed run looks alarming

## Mitigation

1. on v6.2.0, approving the `pypi` environment deployment on BOTH the tag-triggered (`release: published`) and manual (`workflow_dispatch`) runs caused the first to upload successfully and the second to 400 with `File already exists ('attune_ai-6.2.0-py3-none-any .whl', with blake2_256 hash ...)`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `release: published` + `workflow_dispatch` both
  approved for `pypi` env = duplicate publish, the
  second fails "File already exists"
