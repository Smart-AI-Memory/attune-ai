---
type: faq
name: release-published-workflow-dispatch-both-approved-for-pypi-env
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why does release: published + workflow_dispatch both approved for pypi env = duplicate publish, the second fails "File already exists"?

## Answer

on v6.2.0, approving the `pypi` environment deployment on BOTH the tag-triggered (`release: published`) and manual (`workflow_dispatch`) runs caused the first to upload successfully and the second to 400 with `File already exists ('attune_ai-6.2.0-py3-none-any .whl', with blake2_256 hash ...)`. The release is fine — files are live on PyPI — but the failed run looks alarming.

```
 environment deployment on BOTH the tag-triggered (
```

## Related Topics
- **Error**: Detailed error: `release: published` + `workflow_dispatch` both
  approved for `pypi` env = duplicate publish, the
  second fails "File already exists"
