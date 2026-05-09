---
type: faq
name: pr-test-workflows-may-not-auto-trigger-after-close-reopen-or
tags: [testing, git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about PR test workflows may not auto-trigger after close/reopen or branch reuse?

## Answer

When a PR branch is reused after a previous PR was merged, the `pull_request` trigger may not fire on new pushes. `gh workflow run tests.yml --ref <branch>` is the reliable manual fallback.

```
pull_request
```

## Related Topics
- **Error**: Detailed error: PR test workflows may not auto-trigger after close/reopen or
  branch reuse
