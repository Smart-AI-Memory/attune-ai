---
type: faq
name: skill-frontmatter-has-a-strict-allowlist
tags: [claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Skill frontmatter has a strict allowlist?

## Answer

Claude Code skills only support these YAML frontmatter fields: `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `compatibility`, `license`, `metadata`. Fields like `allowed-tools`, `model`, `context`, `agent`, and `hooks` are NOT valid for skills (they may apply to agents or commands).

```
description
```

## Related Topics
- **Error**: Detailed error: Skill frontmatter has a strict allowlist
