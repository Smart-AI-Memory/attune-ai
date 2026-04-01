---
type: faq
name: twine-cannot-prompt-for-tokens-in-claude-codes-non-interactive
tags: [claude-code, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `EOFError` (twine cannot prompt for tokens in Claude Code's non-interactive terminal)?

## Answer

`twine upload` hangs or raises `EOFError` when it tries to prompt for a PyPI token. Pass the token via environment variable: `TWINE_PASSWORD=pypi-... uv run twine upload dist/* --username __token__`.

```
twine upload
```

## Related Topics
- **Error**: Detailed error: Twine cannot prompt for tokens in Claude Code's non-interactive
  terminal
