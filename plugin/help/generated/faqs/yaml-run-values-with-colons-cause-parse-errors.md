---
name: yaml-run-values-with-colons-cause-parse-errors
source: .claude/CLAUDE.md
summary: 'This template explains why colons in `run:` step values cause YAML parsing
  errors and provides three solutions: wrapping the value in single quotes, using
  block scalars, or removing the colon.'
tags:
- ci
type: faq
---

# FAQ: Why does a colon in a `run:` value cause a YAML parse error?

## Answer

A `run:` step like the following will fail YAML parsing:

```yaml
run: gh pr review --body "Auto-approved: update"
```

The colon after `Auto-approved` causes the error. YAML interprets `"Auto-approved: update"` as a mapping key-value pair rather than a plain string, which breaks the document structure.

To fix this, use one of the following approaches:

**Option 1: Wrap the entire value in single quotes**

```yaml
run: 'gh pr review --body "Auto-approved: update"'
```

**Option 2: Use a block scalar (`|` or `>`)**

```yaml
run: |
  gh pr review --body "Auto-approved: update"
```

**Option 3: Remove or replace the colon**

```yaml
run: gh pr review --body "Auto-approved - update"
```

> **Note:** Quoted strings within a YAML value do not protect special characters like `:` from being parsed. The outer YAML layer must be quoted or use a block scalar.

## Related Topics

- **Error reference:** YAML `run:` values with colons cause parse errors
