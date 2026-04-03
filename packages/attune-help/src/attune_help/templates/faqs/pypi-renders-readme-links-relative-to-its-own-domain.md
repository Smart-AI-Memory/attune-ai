---
type: faq
name: pypi-renders-readme-links-relative-to-its-own-domain
tags: [security, packaging, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about pyPI renders README links relative to its own domain?

## Answer

Relative links like `docs/ARCHITECTURE.md` become `https://pypi.org/project/attune-ai/docs/ARCHITECTURE.md` which 404s. All links in README.md must use absolute GitHub URLs (`https://github.com/Smart-AI-Memory/attune-ai/blob/main/...`).

```
docs/ARCHITECTURE.md
```

## Related Topics
- **Error**: Detailed error: PyPI renders README links relative to its own domain
