---
type: faq
name: generated-content-with-trailing-whitespace-causes-perpetual-pre
tags: [git, claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: Why does Generated content with trailing whitespace causes perpetual
  pre-commit failures?

## Answer

If a Jinja2 template renders source data that contains trailing spaces (e.g. a sentence ending with "after "), the `trailing-whitespace` pre-commit hook strips it on commit.


**Fix:**

- strip trailing whitespace per-line in the generator's render output before writing: `"\n".join(line.rstrip() for line in rendered .splitlines()) + "\n"`

```
trailing-whitespace
```

## Related Topics
- **Error**: Detailed error: Generated content with trailing whitespace causes perpetual
  pre-commit failures
