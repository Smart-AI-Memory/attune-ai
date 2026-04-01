---
type: error
name: twine-cannot-prompt-for-tokens-in-claude-codes-non-interactive
confidence: Verified
tags: [claude-code, packaging]
source: .claude/CLAUDE.md
---

# Error: Twine cannot prompt for tokens in Claude Code's non-interactive
  terminal

## Signature

EOFError

## Root Cause

`twine upload` hangs or raises `EOFError` when it tries to prompt for a PyPI token. Pass the token via environment variable: `TWINE_PASSWORD=pypi-... uv run twine upload dist/* --username __token__`.

## Resolution

1. Pass the token via environment variable: `TWINE_PASSWORD=pypi-... uv run twine upload dist/* --username __token__`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Twine cannot prompt for tokens in Claude Code's non-interactive
  terminal
