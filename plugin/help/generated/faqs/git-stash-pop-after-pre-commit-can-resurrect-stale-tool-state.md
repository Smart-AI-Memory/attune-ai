---
type: faq
name: git-stash-pop-after-pre-commit-can-resurrect-stale-tool-state
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about git stash pop after pre-commit can resurrect stale tool state?

## Answer

When pre-commit's `detect-secrets` hook bumps `.secrets.baseline`'s schema version (e.g. `1.4.0 → 1.5.0`) during a commit, a previously stashed copy of `.secrets.baseline` will conflict on `git stash pop` and revert the schema bump.

```
detect-secrets
```

## Related Topics
- **Error**: Detailed error: `git stash pop` after pre-commit can resurrect stale
  tool state
