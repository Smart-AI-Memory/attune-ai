---
type: faq
name: selective-hook-skip-with-skip-hookname-is-not-the-same-as-no
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about selective hook skip with SKIP=hookname is not the same as --no-verify?

## Answer

`SKIP=check-docs-freshness git commit …` runs every other pre-commit hook (black, ruff, bandit, detect-secrets, etc.) and skips only the named one. This is defensible when one specific hook fails on state orthogonal to the commit (e.g., docs-freshness flagging pre-existing template staleness when the commit is unrelated).

```
SKIP=check-docs-freshness git commit …
```

## Related Topics
- **Error**: Detailed error: Selective hook skip with `SKIP=hookname` is not the same
  as `--no-verify`
