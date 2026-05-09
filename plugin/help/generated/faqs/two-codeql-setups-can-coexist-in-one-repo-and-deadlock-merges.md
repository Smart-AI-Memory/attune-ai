---
type: faq
name: two-codeql-setups-can-coexist-in-one-repo-and-deadlock-merges
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle two CodeQL setups can coexist in one repo and deadlock merges silently?

## Answer

`attune-ai` had BOTH `.github/workflows/codeql.yml` (custom, with `pull_request:` trigger) AND GitHub's default CodeQL setup (`"schedule":"weekly"`, no PR trigger). The custom workflow was disabled manually at some point (probably when default setup was enabled), leaving only the weekly cron.

```
 had BOTH
```

## Related Topics
- **Error**: Detailed error: Two CodeQL setups can coexist in one repo and
  deadlock merges silently
