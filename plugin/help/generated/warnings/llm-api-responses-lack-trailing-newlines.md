---
type: warning
name: llm-api-responses-lack-trailing-newlines
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: LLM API responses lack trailing newlines

## Condition

The Anthropic API doesn't guarantee a trailing newline in message content

## Risk

When writing LLM output to files, always append `\n` if missing — otherwise `end-of-file-fixer` pre-commit hooks will reject the commit

## Mitigation

1. Check with `if not text.endswith ("\n"): text += "\n"`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: LLM API responses lack trailing newlines
