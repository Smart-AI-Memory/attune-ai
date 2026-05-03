---
name: claude-plugin-install-is-marketplace-only
source: .claude/CLAUDE.md
summary: This template explains that the `claude plugin install` command only works
  with marketplace plugins and directs developers to use the `--plugin-dir` flag as
  an alternative for loading local plugins during development.
tags:
- testing
- claude-code
type: faq
---

# FAQ: How do I handle "claude plugin install is marketplace-only"?

## Answer

The `claude plugin install` command only supports installing plugins from the official marketplace and does not accept local file paths.

To load a plugin from a local directory during development or testing, use the `--plugin-dir` flag instead:

```bash
claude --plugin-dir ./my-plugin
```

## Related Topics

- **Error reference**: `claude plugin install` is marketplace-only
