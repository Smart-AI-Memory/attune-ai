---
type: warning
name: pypi-renders-readme-links-relative-to-its-own-domain
confidence: Verified
tags: [security, packaging, python]
source: .claude/CLAUDE.md
---

# Warning: PyPI renders README links relative to its own domain

## Condition

Relative links like `docs/ARCHITECTURE.md` become `https://pypi.org/project/attune-ai/docs/ARCHITECTURE.md` which 404s

## Risk

Ignoring this guidance may cause: PyPI renders README links relative to its own domain

## Mitigation

1. Relative links like `docs/ARCHITECTURE.md` become `https://pypi.org/project/attune-ai/docs/ARCHITECTURE.md` which 404s

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: PyPI renders README links relative to its own domain
