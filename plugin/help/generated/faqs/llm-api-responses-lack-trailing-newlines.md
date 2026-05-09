---
type: faq
name: llm-api-responses-lack-trailing-newlines
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about LLM API responses lack trailing newlines?

## Answer

The Anthropic API doesn't guarantee a trailing newline in message content. When writing LLM output to files, always append `\n` if missing — otherwise `end-of-file-fixer` pre-commit hooks will reject the commit.

**How to fix:**
- Check with `if not text.endswith ("\n"): text += "\n"`

```
 if missing — otherwise
```

## Related Topics
- **Error**: Detailed error: LLM API responses lack trailing newlines
