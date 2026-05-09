---
type: faq
name: attune-author-check-staleness-load-manifest-is-the-python-api
tags: [ci, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about attune_author.check_staleness + load_manifest is the Python API for programmatic stale detection?

## Answer

the `attune-author status` CLI emits only markdown tables. Parsing those with awk is brittle (divider rows sneak through, feature- name-starts-with-lowercase is hacky).

**How to fix:**
- Use this anywhere automation would otherwise parse the status table (GitHub Actions, SessionStart hooks, pre-commit scripts)

```
attune-author status
```

## Related Topics
- **Error**: Detailed error: `attune_author.check_staleness` +
  `load_manifest` is the Python API for programmatic
  stale detection
