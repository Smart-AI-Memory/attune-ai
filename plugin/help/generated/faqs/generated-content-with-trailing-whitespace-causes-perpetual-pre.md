---
name: generated-content-with-trailing-whitespace-causes-perpetual-pre
source: .claude/CLAUDE.md
summary: This template explains why generated files with trailing whitespace trigger
  infinite pre-commit hook failures and provides a code solution to strip whitespace
  from rendered output before writing to disk.
tags:
- git
- claude-code
type: faq
---

# FAQ: Why Does Generated Content with Trailing Whitespace Cause Perpetual Pre-commit Failures?

## Answer

When a Jinja2 template renders source data that contains trailing spaces (for example, a string ending with `"after "`), the `trailing-whitespace` pre-commit hook automatically strips those spaces on each commit attempt. Because the hook modifies the file, the commit fails — and if the generator rewrites the file with trailing whitespace again before the next commit, the cycle repeats indefinitely.

**How to fix:**

Strip trailing whitespace from each line in the generator's render output before writing the file to disk:

```python
"\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"
```

This ensures the generated file is already clean before the `trailing-whitespace` hook runs, preventing repeated failures.

## Related Topics

- **Error:** Generated content with trailing whitespace causes perpetual pre-commit failures
