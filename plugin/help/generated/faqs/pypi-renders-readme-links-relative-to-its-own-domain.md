---
name: pypi-renders-readme-links-relative-to-its-own-domain
source: .claude/CLAUDE.md
summary: This template explains why relative links in README files break when displayed
  on PyPI and provides the solution of using absolute GitHub URLs instead.
tags:
- security
- packaging
- python
type: faq
---

# FAQ: Why Do Relative Links Break on PyPI?

## Answer

PyPI renders relative links in `README.md` relative to its own domain rather than your GitHub repository. This means a link like:

```
docs/ARCHITECTURE.md
```

resolves to:

```
https://pypi.org/project/attune-ai/docs/ARCHITECTURE.md
```

which returns a 404 error. To prevent this, all links in `README.md` must use absolute GitHub URLs, for example:

```
https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/ARCHITECTURE.md
```

## Related Topics

- **Error**: PyPI renders README links relative to its own domain
