---
type: error
name: llm-api-responses-lack-trailing-newlines
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: LLM API responses lack trailing newlines

## Signature

LLM API responses lack trailing newlines

## Root Cause

The Anthropic API doesn't guarantee a trailing newline in message content. When writing LLM output to files, always append `\n` if missing — otherwise `end-of-file-fixer` pre-commit hooks will reject the commit. Check with `if not text.endswith ("\n"): text += "\n"`.

## Resolution

1. Check with `if not text.endswith ("\n"): text += "\n"`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: LLM API responses lack trailing newlines
